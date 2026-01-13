import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, dash_table
import mysql.connector
import warnings
import logging

warnings.filterwarnings(
    "ignore",
    message="pandas only supports SQLAlchemy connectable"
)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ---------------------------
# Local MySQL connection
# ---------------------------
local_host = "localhost"
local_user = "root"
local_password = "admin"
local_db = "in_railin_local"
table_name = "rail_rem_rake_20251126100147"

# ---------------------------
# Load dataset from MySQL
# ---------------------------
def load_data():
    conn = mysql.connector.connect(
        host=local_host,
        user=local_user,
        password=local_password,
        database=local_db
    )
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()

    if "RADSTTSCHNGTIME" in df.columns:
        df["RADSTTSCHNGTIME"] = pd.to_datetime(df["RADSTTSCHNGTIME"], errors="coerce")
        df["Date"] = df["RADSTTSCHNGTIME"].dt.date

    return df

# ---------------------------
# Detect Military Records
# ---------------------------
def detect_military(row):
    text = " ".join(str(x) for x in row.values).upper()
    keywords = ["DRDO", "ARMY", "MILY", "MILITARY", "DEFENCE", "DEFENSE", "ORDNANCE", "SPL"]
    return any(k in text for k in keywords)

# ---------------------------
# Charts
# ---------------------------
def build_figure(mil_df):
    if mil_df.empty:
        return {}
    summary = mil_df["RAVRAKENAME"].astype(str).value_counts().reset_index()
    summary.columns = ["Rake Name", "Count"]

    fig = px.bar(
        summary,
        x="Rake Name",
        y="Count",
        text="Count",
        title="Military-Related Movements by Rake Name",
        template="plotly_white"
    )
    fig.update_traces(textposition="outside", marker_color="#2c3e50")
    fig.update_yaxes(tickformat="d")
    return fig

def build_datewise_figure(mil_df):
    if mil_df.empty or "Date" not in mil_df.columns:
        return {}

    summary = (
        mil_df.groupby(["Date", "RAVRAKENAME"])
        .size()
        .reset_index(name="Count")
        .sort_values("Date")
    )

    fig = px.bar(
        summary,
        x="Date",
        y="Count",
        color="RAVRAKENAME",
        text="Count",
        title="Date-wise Military Movement Count (Rake-wise)",
        template="plotly_white"
    )
    fig.update_layout(barmode="stack")
    fig.update_traces(textposition="inside")
    fig.update_yaxes(tickformat="d")
    return fig

# ---------------------------
# ✅ NEW: Month-wise Chart (Jan–Dec, clean & elegant)
# ---------------------------
def build_monthwise_figure(mil_df):
    if mil_df.empty or "Date" not in mil_df.columns:
        return {}

    df_m = mil_df.copy()
    df_m["MonthNum"] = pd.to_datetime(df_m["Date"]).dt.month

    summary = (
        df_m.groupby("MonthNum")
        .size()
        .reindex(range(1, 13), fill_value=0)
        .reset_index(name="Count")
    )

    month_map = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    summary["Month"] = summary["MonthNum"].map(month_map)

    fig = px.bar(
        summary,
        x="Month",
        y="Count",
        text="Count",
        title="Month-wise Military Movement Count (January–December)",
        template="plotly_white"
    )

    fig.update_traces(
        marker_color="#34495e",
        textposition="outside"
    )

    fig.update_yaxes(
        tickformat="d",
        title="Total Count"
    )

    fig.update_xaxes(
        title="Month",
        categoryorder="array",
        categoryarray=list(month_map.values())
    )

    fig.update_layout(showlegend=False)

    return fig

# ---------------------------
# Load Data
# ---------------------------
df = load_data()
df["Military_Flag"] = df.apply(detect_military, axis=1)
mil_df = df[df["Military_Flag"]].copy()

TARGET_RAKE = "DRDO/SPL"
mil_df = mil_df[
    mil_df["RAVRAKENAME"].astype(str).str.contains(TARGET_RAKE, case=False, na=False)
]

fig_rake = build_figure(mil_df)
fig_datewise = build_datewise_figure(mil_df)
fig_monthwise = build_monthwise_figure(mil_df)

station_cols = [c for c in ["RAVRAKENAME", "RAVSTTNFROM", "RAVSRVGSTTN"] if c in mil_df.columns]
station_df = mil_df[station_cols].drop_duplicates()

# ---------------------------
# Tooltip Components
# ---------------------------
def TOOLTIP(word, definition, color):
    return html.Span(
        word,
        title=definition,
        style={
            "color": color,
            "fontWeight": "600",
            "textDecoration": "underline dotted",
            "cursor": "help"
        }
    )

RAKE = lambda: TOOLTIP(
    "Rake",
    "A fixed group of railway wagons that move together as one unit from origin to destination.",
    "#f1c40f"
)
DRDO = lambda: TOOLTIP(
    "DRDO",
    "Defence Research and Development Organisation consignments via Indian Railways.",
    "#1abc9c"
)
SPL = lambda: TOOLTIP(
    "SPL",
    "Special priority rake movement for sensitive or time-critical cargo.",
    "#9b59b6"
)
NGCM = lambda: TOOLTIP(
    "NGCM",
    "New Generation Covered Wagon for secure defence transportation.",
    "#3498db"
)

# ---------------------------
# UI Styles
# ---------------------------
PAGE = {
    "backgroundColor": "#eef2f7",
    "padding": "30px",
    "fontFamily": "Segoe UI, Roboto, Arial"
}

CONTAINER = {
    "maxWidth": "1400px",
    "margin": "0 auto"
}

CARD = {
    "backgroundColor": "white",
    "padding": "22px",
    "borderRadius": "14px",
    "boxShadow": "0 4px 14px rgba(0,0,0,0.07)",
    "marginBottom": "24px"
}

KPI = {
    "flex": "1",
    "padding": "24px",
    "borderRadius": "14px",
    "background": "linear-gradient(135deg, #ffffff, #f8f9fb)",
    "boxShadow": "0 4px 14px rgba(0,0,0,0.07)",
    "textAlign": "center"
}

# ---------------------------
# Dash App
# ---------------------------
app = Dash(__name__)

app.index_string = """
<!DOCTYPE html>
<html>
<head>
{%metas%}
{%title%}
{%favicon%}
{%css%}
<style>
span[title]:hover { color:#e74c3c !important; }
</style>
</head>
<body>
{%app_entry%}
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
</html>
"""

app.layout = html.Div(style=PAGE, children=[
    html.Div(style=CONTAINER, children=[

        # Header
        html.Div(style={
            "background": "linear-gradient(90deg,#1f2c3c,#34495e)",
            "color": "white",
            "padding": "28px",
            "borderRadius": "16px",
            "marginBottom": "28px"
        }, children=[
            html.H2(
                ["Military Railway Movement Dashboard (", RAKE(), " | ", DRDO(), " | ", SPL(), " | ", NGCM(), ")"],
                style={"margin": "0"}
            ),
            html.P(
                ["Strategic ", RAKE(), " analytics for defence logistics"],
                style={"opacity": "0.85", "marginTop": "6px"}
            )
        ]),

        # KPIs
        html.Div(style={"display": "flex", "gap": "22px", "marginBottom": "28px"}, children=[
            html.Div(style=KPI, children=[
                html.Div("Total Records", style={"color": "#7f8c8d"}),
                html.Div(len(df), style={"fontSize": "34px", "fontWeight": "700"})
            ]),
            html.Div(style=KPI, children=[
                html.Div(["Military ", RAKE(), " Records"], style={"color": "#7f8c8d"}),
                html.Div(len(mil_df), style={"fontSize": "34px", "fontWeight": "700", "color": "#c0392b"})
            ])
        ]),

        # Charts
        html.Div(style=CARD, children=[dcc.Graph(figure=fig_rake)]),
        html.Div(style=CARD, children=[dcc.Graph(figure=fig_datewise)]),
        html.Div(style=CARD, children=[dcc.Graph(figure=fig_monthwise)]),

        # Table
        html.Div(style=CARD, children=[
            html.H4(["Station Codes per ", RAKE(), " (", DRDO(), " / ", SPL(), " / ", NGCM(), ")"]),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in station_cols],
                data=station_df.to_dict("records"),
                page_size=15,
                style_header={
                    "backgroundColor": "#2c3e50",
                    "color": "white",
                    "fontWeight": "bold"
                },
                style_cell={
                    "padding": "10px",
                    "fontFamily": "monospace",
                    "fontSize": "13px",
                    "textAlign": "left"
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f4f6f9"}
                ]
            )
        ])
    ])
])

# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=False)
