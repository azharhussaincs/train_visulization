import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import re
from datetime import datetime

# ─── Page Config & Browser Auto-Refresh (Every 10 Minutes) ─────
st.set_page_config(page_title="Rail Monitoring Dashboard", layout="wide")
st.markdown(
    """
    <meta http-equiv="refresh" content="600">
    <style>
    .big-font {font-size: 22px !important; font-weight: bold;}
    </style>
    """,
    unsafe_allow_html=True
)

# ─── Header with Live Time ────────────────────────────────────
st.title("Indian Railways - Rake Movement Dashboard")
current_time = datetime.now().strftime("%d %B %Y • %H:%M:%S")
st.markdown(f"**Live Overview of Train Movements**  \n**Last Updated:** **{current_time}**", unsafe_allow_html=True)


# ─── Database Connection ──────────────────────────────────────
@st.cache_resource
def get_engine():
    return create_engine(
        "mysql+mysqlconnector://railuser:r4dh4%40rail%23501@100.97.0.88/in_railin",
        echo=False,
        future=True
    )


# ─── Get Latest Table Name (Checked Frequently) ────────────────
@st.cache_data(ttl=60)
def get_latest_table_name():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES LIKE 'rail_rem_rake_%'"))
        tables = [row[0] for row in result]

    if not tables:
        return None, None

    def get_table_time(t):
        match = re.search(r'(\d{14})', t)
        return datetime.strptime(match.group(1), '%Y%m%d%H%M%S') if match else datetime(1900, 1, 1)

    latest_table = max(tables, key=get_table_time)
    latest_time = get_table_time(latest_table)
    return latest_table, latest_time


# ─── Load Data Using Current Table as Cache Key ────────────────
@st.cache_data(ttl=300)
def get_latest_data(_table_name):
    engine = get_engine()
    with st.spinner("Loading latest train movement data..."):
        query = text(f"SELECT * FROM `{_table_name}`")
        df = pd.read_sql(query, engine)
    df = df.replace('null', None)
    return df


# ─── Auto-Detect New Data ─────────────────────────────────────
current_table, current_table_time = get_latest_table_name()

if current_table is None:
    st.error("No train movement tables found in database!")
    st.stop()

# Display current data source
st.info(f"**Data Source:** `{current_table}`  \n**Snapshot Time:** {current_table_time.strftime('%d %B %Y, %H:%M')}")

# Auto-refresh logic
if 'last_table' not in st.session_state:
    st.session_state.last_table = None

if st.session_state.last_table != current_table:
    st.session_state.last_table = current_table
    get_latest_data.clear()

df = get_latest_data(current_table)

st.success(f"**Loaded {len(df):,}** train movement records")

# ─── Column Renaming & Data Cleaning ──────────────────────────
rename_map = {
    'RAVRAKENAME': 'Rake Name',
    'RAVLOADNAME': 'Load / Commodity',
    'RANACTLUNTS': 'No. of Wagons',
    'RAVRAKETYPE': 'Wagon Type',
    'RANTOTLTNGE': 'Tonnage (t)',
    'RAVSTTNFROM': 'Origin',
    'RAVSTTN': 'Current Location',
    'RAVSTTNTO': 'Destination',
    'RAVOWRDDRTN': 'Direction',
    'RADMVMTTIME': 'Last Reported',
    'RAVZONE': 'Zone',
    'RAVDVSN': 'Division',
    'RAVCNSR': 'Consignor',
    'RAVCNSG': 'Consignee',
    'RAVGRUPRAKECMDT': 'Commodity Code',
    'RAVRAKESTTS': 'Status'
}
df = df.rename(columns=rename_map)

df['No. of Wagons'] = pd.to_numeric(df['No. of Wagons'], errors='coerce').fillna(0)
df['Tonnage (t)'] = pd.to_numeric(df['Tonnage (t)'], errors='coerce').fillna(0)
df['Last Reported'] = pd.to_datetime(df['Last Reported'], errors='coerce')

# ─── Sidebar Controls ─────────────────────────────────────────
st.sidebar.header("Controls")
if st.sidebar.button("Refresh Data Now"):
    st.cache_data.clear()
    st.rerun()

# ─── Key Summary Metrics ──────────────────────────────────────
st.markdown("### 📊 Overview Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Active Trains", f"{len(df):,}")
col2.metric("Total Wagons", f"{int(df['No. of Wagons'].sum()):,}")
col3.metric("Total Tonnage", f"{int(df['Tonnage (t)'].sum()):,} t")
col4.metric("Average Wagons per Train", f"{df['No. of Wagons'].mean():.1f}")

# ─── Visualizations ───────────────────────────────────────────
st.markdown("---")
st.subheader("📈 Movement Visualizations")

tab1, tab2, tab3 = st.tabs(["Zone Overview", "Wagon Types", "Direction Split"])

with tab1:
    st.write("**Shows which railway zones have the most active trains right now.**")
    zone_data = df['Zone'].value_counts().head(15)
    st.bar_chart(zone_data, width='stretch')
    st.caption("Top 15 Zones by Number of Trains")

with tab2:
    st.write("**Shows the most common types of wagons being used.**")
    type_data = df['Wagon Type'].value_counts().head(10)
    st.bar_chart(type_data, width='stretch')
    st.caption("Top 10 Wagon Types in Use")

with tab3:
    st.write("**Shows the split between UP and DOWN direction trains.**")
    direction_data = df['Direction'].value_counts()
    col1, col2 = st.columns(2)
    with col1:
        st.write(direction_data)
    with col2:
        st.bar_chart(direction_data, width='stretch')
    st.caption("Train Direction Distribution (UP vs DOWN)")

# ─── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666;'>"
    "Rail Movement Monitoring Tool • Source: Indian Railways REM Data • "
    "Auto-refreshes every 10 minutes • For Operational Use"
    "</p>",
    unsafe_allow_html=True
)