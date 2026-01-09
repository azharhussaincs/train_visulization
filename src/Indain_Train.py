import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import mysql.connector
import math

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Indian Railways Military Rake Dashboard",
    layout="wide"
)

st.title("🚆 Indian Railways Military / Strategic Rake Movements")

# ===============================
# LOAD DATA
# ===============================
@st.cache_data(show_spinner=False)
def load_rake_data():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin",
        database="in_railin_local"
    )
    df = pd.read_sql("SELECT * FROM rail_rem_rake_20251126100147", conn)
    conn.close()
    df["RADSTTSCHNGTIME"] = pd.to_datetime(df["RADSTTSCHNGTIME"], errors="coerce")
    return df

@st.cache_data(show_spinner=False)
def load_station_data():
    return pd.read_csv("indian_stations_with_city.csv")

df = load_rake_data()
stations = load_station_data()

# ===============================
# DATE FILTER
# ===============================
available_dates = sorted(df["RADSTTSCHNGTIME"].dt.date.dropna().unique())

st.subheader("📅 Select Date Range")
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    from_date = st.selectbox("From Date", options=available_dates, index=0)
with c2:
    to_date = st.selectbox("To Date", options=available_dates, index=len(available_dates)-1)
with c3:
    apply_filter = st.button("✅ Apply")

if from_date > to_date:
    st.error("From Date must be before To Date")
    st.stop()
if not apply_filter:
    st.info("Select date range and click Apply")
    st.stop()

filtered_df = df[
    (df["RADSTTSCHNGTIME"] >= pd.to_datetime(from_date)) &
    (df["RADSTTSCHNGTIME"] <= pd.to_datetime(to_date) + pd.Timedelta(days=1))
].copy()

# ===============================
# STATION LOOKUP
# ===============================
station_map = {
    r["StationCode"]: {
        "lat": r["Latitude"],
        "lon": r["Longitude"],
        "city": r["City"] or r["StationCode"]
    }
    for _, r in stations.iterrows()
}

def get_station(code):
    return station_map.get(str(code).strip(), None)

# ===============================
# BEARING
# ===============================
def bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

# ===============================
# STRICT MILITARY FILTER
# ===============================
keywords = ["defence","ordnance","army","ammunition","explosive","missile","fuel","special","drdo"]

def is_military(row):
    text = f"{row.get('RAVLOADNAME','')} {row.get('RAVGRUPRAKECMDT','')}".lower()
    return any(k in text for k in keywords)

filtered_df["MILITARY"] = filtered_df.apply(is_military, axis=1)
military_df = filtered_df[filtered_df["MILITARY"]].copy()

if military_df.empty:
    st.warning("No military rakes found")
    st.stop()

# ===============================
# ROUTE SUMMARY
# ===============================
routes = (
    military_df
    .groupby(["RAVSTTNFROM","RAVSTTNTO"])
    .size()
    .reset_index(name="movements")
)

routes["Route"] = routes["RAVSTTNFROM"] + " → " + routes["RAVSTTNTO"]

# ===============================
# KPI
# ===============================
k1, k2, k3, k4 = st.columns(4)
k1.metric("Military Records", len(military_df))
k2.metric("Unique Rakes", military_df["RAVRAKEID"].nunique())
k3.metric("Routes", len(routes))
k4.metric("Zones", military_df["RAVZONE"].nunique())

# ===============================
# FULL PAGE INDIA MAP
# ===============================
st.subheader("🗺 Military Rake Movement Map (India Only)")

fig = go.Figure()

for _, r in routes.iterrows():
    o = get_station(r["RAVSTTNFROM"])
    d = get_station(r["RAVSTTNTO"])
    if not o or not d:
        continue

    hover = f"""
    <b>{r['Route']}</b><br>
    Movements: {r['movements']}<br>
    From: {o['city']}<br>
    To: {d['city']}
    """

    # Line
    fig.add_trace(go.Scattergeo(
        lat=[o["lat"], d["lat"]],
        lon=[o["lon"], d["lon"]],
        mode="lines",
        line=dict(width=2 + r["movements"], color="black"),
        hovertext=hover,
        hoverinfo="text",
        showlegend=False
    ))

    # Origin (RED)
    fig.add_trace(go.Scattergeo(
        lat=[o["lat"]],
        lon=[o["lon"]],
        mode="markers",
        marker=dict(size=10, color="red"),
        showlegend=False
    ))

    # Destination (GREEN + arrow)
    fig.add_trace(go.Scattergeo(
        lat=[d["lat"]],
        lon=[d["lon"]],
        mode="markers",
        marker=dict(
            size=14,
            color="green",
            symbol="arrow",
            angle=bearing(o["lat"], o["lon"], d["lat"], d["lon"])
        ),
        showlegend=False
    ))

fig.update_layout(
    geo=dict(
        scope="asia",
        center=dict(lat=22.5, lon=80),
        projection_scale=4.2,
        showland=True,
        landcolor="#eeeeee"
    ),
    height=850,
    margin=dict(l=0, r=0, t=0, b=0)
)

st.plotly_chart(fig, use_container_width=True)

# ===============================
# NEW BAR: EACH MOVEMENT LINE
# ===============================
st.subheader("📊 Military Movement – One Bar per Origin → Destination")

fig_bar = go.Figure(go.Bar(
    y=routes["Route"],
    x=routes["movements"],
    orientation="h",
    text=routes["movements"],
    textposition="outside"
))

fig_bar.update_layout(
    height=max(600, len(routes)*22),
    yaxis=dict(autorange="reversed"),
    xaxis_title="Number of Movements",
    yaxis_title="Route"
)

st.plotly_chart(fig_bar, use_container_width=True)

# ===============================
# ZONE DISTRIBUTION
# ===============================
st.subheader("📊 Military Rakes by Zone")
zone_df = military_df["RAVZONE"].value_counts().reset_index()
zone_df.columns = ["Zone","Count"]

fig_zone = go.Figure(go.Bar(
    x=zone_df["Zone"],
    y=zone_df["Count"],
    text=zone_df["Count"],
    textposition="auto"
))

st.plotly_chart(fig_zone, use_container_width=True)

st.caption("Strict keyword-based military detection • India-focused • Directional movement clarity")
