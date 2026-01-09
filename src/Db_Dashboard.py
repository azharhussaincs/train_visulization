import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import mysql.connector
import math

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Indian Railways Strategic Rake Dashboard",
    layout="wide"
)

st.title("🚆 Indian Railways Strategic Rake Dashboard")

# ===============================
# LOAD DATA FROM DB
# ===============================
@st.cache_data(show_spinner=False)
def load_rake_data():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin",
        database="in_railin_local"
    )
    df = pd.read_sql(
        "SELECT * FROM rail_rem_rake_20251126100147",
        conn
    )
    conn.close()
    df["RADSTTSCHNGTIME"] = pd.to_datetime(df["RADSTTSCHNGTIME"], errors="coerce")
    return df

@st.cache_data(show_spinner=False)
def load_station_data():
    return pd.read_csv("indian_stations_with_city.csv")

df = load_rake_data()
stations = load_station_data()

# ===============================
# AVAILABLE DATES
# ===============================
available_dates = (
    df["RADSTTSCHNGTIME"]
    .dt.date
    .dropna()
    .sort_values()
    .unique()
)

# ===============================
# DATE SELECTION
# ===============================
st.subheader("📅 Select Date Range")

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    from_date = st.selectbox("From Date", options=available_dates, index=0)
with c2:
    to_date = st.selectbox("To Date", options=available_dates, index=len(available_dates) - 1)
with c3:
    apply_filter = st.button("✅ Apply")

if from_date > to_date:
    st.error("❌ From Date must be before To Date")
    st.stop()
if not apply_filter:
    st.info("ℹ️ Select date range and click **Apply** to load dashboard")
    st.stop()

# ===============================
# DATE FILTER
# ===============================
filtered_df = df[
    (df["RADSTTSCHNGTIME"] >= pd.to_datetime(from_date)) &
    (df["RADSTTSCHNGTIME"] <= pd.to_datetime(to_date) + pd.Timedelta(days=1))
].copy()

# ===============================
# STATION LOOKUP
# ===============================
station_map = {
    row["StationCode"]: {
        "lat": row["Latitude"],
        "lon": row["Longitude"],
        "city": row["City"]
    }
    for _, row in stations.iterrows()
}

def get_station_info(code):
    """Safe lookup for station info"""
    return station_map.get(code, None)

# ===============================
# MILITARY LOGIC
# ===============================
military_keywords = [
    "defence", "ordnance", "army", "ammunition",
    "explosive", "missile", "fuel", "special"
]

def is_military(row):
    text = f"{row['RAVLOADNAME']} {row['RAVGRUPRAKECMDT']} {row['RAVAUTHNUMB']}"
    return (
        any(k in str(text).lower() for k in military_keywords)
        or row.get("RACSPCLPREMFLAG") == "Y"
        or row.get("RACPREMFLAG") == "Y"
        or row.get("RACCCFLAG") == "Y"
    )

filtered_df["MILITARY_RELATED"] = filtered_df.apply(is_military, axis=1)
military_df = filtered_df[filtered_df["MILITARY_RELATED"]]

# ===============================
# KPI SECTION
# ===============================
st.subheader(f"📊 Strategic Overview ({from_date} → {to_date})")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Rakes", len(filtered_df))
k2.metric("Strategic Rakes", len(military_df))
k3.metric("Loaded Rakes", int((filtered_df["RACLEFLAG"] == "L").sum()))
k4.metric(
    "Premium / CC",
    int(((filtered_df["RACPREMFLAG"] == "Y") | (filtered_df["RACCCFLAG"] == "Y")).sum())
)

# ===============================
# HELPER: CALCULATE BEARING FOR ARROWS
# ===============================
def calculate_bearing(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return 0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360

# ===============================
# STRATEGIC MILITARY MOVEMENTS MAP
# ===============================
st.subheader("🗺 Strategic Military Movements")

route_df = (
    military_df
    .groupby(["RAVSTTNFROM", "RAVSTTNTO"])
    .agg({
        "RAVRAKEID": lambda x: ', '.join(x.astype(str)),
        "RAVLOADNAME": lambda x: ', '.join(x.astype(str)),
        "RAVZONE": lambda x: ', '.join(x.astype(str))
    })
    .reset_index()
)

# Calculate movements
route_df["movements"] = route_df["RAVRAKEID"].apply(lambda x: len(x.split(',')))
route_df = route_df[route_df["movements"] > 0]

fig = go.Figure()
max_count = route_df["movements"].max() if not route_df.empty else 1

for _, r in route_df.iterrows():
    origin = get_station_info(r["RAVSTTNFROM"])
    destination = get_station_info(r["RAVSTTNTO"])
    if not origin or not destination:
        continue

    hover_info = (
        f"<b>{origin['city']} → {destination['city']}</b><br>"
        f"Movements: {r['movements']}<br>"
        f"Rake IDs: {r['RAVRAKEID']}<br>"
        f"Load Names: {r['RAVLOADNAME']}<br>"
        f"Zones: {r['RAVZONE']}"
    )

    # Draw line
    fig.add_trace(go.Scattergeo(
        lat=[origin["lat"], destination["lat"]],
        lon=[origin["lon"], destination["lon"]],
        mode="lines",
        line=dict(width=1 + (r["movements"]/max_count)*10, color="red"),
        opacity=0.7,
        hoverinfo="text",
        hovertext=hover_info,
        showlegend=False
    ))

    bearing = calculate_bearing(origin["lat"], origin["lon"], destination["lat"], destination["lon"])

    # Red arrow at origin
    fig.add_trace(go.Scattergeo(
        lat=[origin["lat"]],
        lon=[origin["lon"]],
        mode="markers",
        marker=dict(size=12, color="red", symbol="arrow-bar-up", angle=bearing),
        hoverinfo="text",
        hovertext=hover_info,
        showlegend=False
    ))

    # Green arrow at destination
    fig.add_trace(go.Scattergeo(
        lat=[destination["lat"]],
        lon=[destination["lon"]],
        mode="markers",
        marker=dict(size=14, color="green", symbol="arrow-bar-up", angle=bearing),
        hoverinfo="text",
        hovertext=hover_info,
        showlegend=False
    ))

fig.update_layout(
    geo=dict(
        scope="asia",
        projection_type="mercator",
        showland=True,
        landcolor="#ECECEC",
        fitbounds="locations"
    ),
    height=900,
    margin=dict(l=0,r=0,t=0,b=0)
)

st.success(f"🛤 Unique strategic routes (moving only): {len(route_df)}")
st.plotly_chart(fig, use_container_width=True, key=f"map_{from_date}_{to_date}")

# ===============================
# BAR CHART
# ===============================
st.subheader("📊 Strategic Rakes per Zone")
zone_counts = military_df.groupby("RAVZONE")["RAVRAKEID"].count().reset_index()
fig_bar = go.Figure(go.Bar(
    x=zone_counts["RAVZONE"],
    y=zone_counts["RAVRAKEID"],
    text=zone_counts["RAVRAKEID"],
    textposition="auto",
    marker_color="crimson"
))
st.plotly_chart(fig_bar, use_container_width=True)

# ===============================
# PIE CHART
# ===============================
st.subheader("📊 Loaded vs Empty Strategic Rakes")
load_counts = military_df["RACLEFLAG"].value_counts().reset_index()
load_counts.columns = ["LoadStatus", "Count"]
fig_pie = go.Figure(go.Pie(
    labels=load_counts["LoadStatus"],
    values=load_counts["Count"],
    hole=0.4
))
st.plotly_chart(fig_pie, use_container_width=True)
