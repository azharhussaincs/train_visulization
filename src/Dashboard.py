import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, dash_table, Input, Output, State
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
# Load dataset from MySQL (extended safely)
# ---------------------------
def load_data(selected_year=None):
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
        df["Year"] = df["RADSTTSCHNGTIME"].dt.year
        df["Month"] = df["RADSTTSCHNGTIME"].dt.month  # added for easier filtering

    if selected_year is not None:
        df = df[df["Year"] == selected_year]

    return df


# ---------------------------
# Detect Military Records (unchanged)
# ---------------------------
def detect_military(row):
    text = " ".join(str(x) for x in row.values).upper()
    keywords = ["DRDO", "ARMY", "MILY", "MILITARY", "DEFENCE", "DEFENSE", "ORDNANCE", "SPL"]
    return any(k in text for k in keywords)


# ---------------------------
# Charts (unchanged)
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
        title="Month-wise Military Movement Count",
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
# From → To Summary (unchanged)
# ---------------------------
def build_from_to_summary(mil_df):
    if mil_df.empty:
        return pd.DataFrame()
    summary = (
        mil_df.groupby(["RAVSTTNFROM", "RAVSRVGSTTN"])
        .agg(
            Movement_Count=("Date", "size"),
            First_Movement=("Date", "min"),
            Last_Movement=("Date", "max")
        )
        .reset_index()
        .sort_values("Movement_Count", ascending=False)
    )
    summary["Duration_Days"] = (
            pd.to_datetime(summary["Last_Movement"]) -
            pd.to_datetime(summary["First_Movement"])
    ).dt.days
    return summary


# ---------------------------
# Tooltips (unchanged)
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


RAKE = lambda: TOOLTIP("Rake",
                       "A fixed group of railway wagons that move together as one unit from origin to destination.",
                       "#f1c40f")
DRDO = lambda: TOOLTIP("DRDO", "Defence Research and Development Organisation consignments via Indian Railways.",
                       "#1abc9c")
SPL = lambda: TOOLTIP("SPL", "Special priority rake movement for sensitive or time-critical cargo.", "#9b59b6")
NGCM = lambda: TOOLTIP("NGCM", "New Generation Covered Wagon for secure defence transportation.", "#3498db")

# ---------------------------
# UI Styles (unchanged)
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

        # ======= YEAR + OPTIONAL MONTH FILTER =======
        html.Div(style=CARD, children=[
            html.Div("Select Year", style={"fontWeight": "bold", "marginBottom": "8px"}),
            dcc.Dropdown(
                id="year-dropdown",
                options=[{"label": str(y), "value": y}
                         for y in range(2000, pd.Timestamp.now().year + 1)],
                value=None,
                clearable=False,
                style={"width": "220px"}
            ),

            html.Div("Select Month (optional)",
                     style={"fontWeight": "bold", "marginTop": "16px", "marginBottom": "8px"}),
            dcc.Dropdown(
                id="month-dropdown",
                options=[
                    {"label": "January", "value": 1},
                    {"label": "February", "value": 2},
                    {"label": "March", "value": 3},
                    {"label": "April", "value": 4},
                    {"label": "May", "value": 5},
                    {"label": "June", "value": 6},
                    {"label": "July", "value": 7},
                    {"label": "August", "value": 8},
                    {"label": "September", "value": 9},
                    {"label": "October", "value": 10},
                    {"label": "November", "value": 11},
                    {"label": "December", "value": 12},
                ],
                value=None,
                clearable=True,
                placeholder="All months",
                style={"width": "220px"}
            ),

            html.Button(
                "Apply Filter",
                id="submit-btn",
                n_clicks=0,
                style={"marginTop": "20px", "padding": "10px 24px", "fontWeight": "bold"}
            )
        ]),

        # KPIs
        html.Div(style={"display": "flex", "gap": "22px", "marginBottom": "28px"}, children=[
            html.Div(style=KPI, children=[
                html.Div("Total Records", style={"color": "#7f8c8d"}),
                html.Div(id="kpi-total", style={"fontSize": "34px", "fontWeight": "700"})
            ]),
            html.Div(style=KPI, children=[
                html.Div(["Military ", RAKE(), " Records"], style={"color": "#7f8c8d"}),
                html.Div(id="kpi-military",
                         style={"fontSize": "34px", "fontWeight": "700", "color": "#c0392b"})
            ])
        ]),

        # Graphs
        html.Div(style=CARD, children=[dcc.Graph(id="graph-rake")]),
        html.Div(style=CARD, children=[dcc.Graph(id="graph-datewise")]),
        html.Div(style=CARD, children=[dcc.Graph(id="graph-monthwise")]),

        # Table
        html.Div(style=CARD, children=[
            html.H4("Most Frequent From → To Military Movements"),
            dash_table.DataTable(
                id="from-to-table",
                columns=[
                    {"name": "From Station", "id": "RAVSTTNFROM"},
                    {"name": "To Station", "id": "RAVSRVGSTTN"},
                    {"name": "Movement Count", "id": "Movement_Count"},
                ],
                page_size=10,
                sort_action="native",
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
        ]),
    ])
])


# ---------------------------
# CALLBACK: load and filter data
# ---------------------------
@app.callback(
    Output("kpi-total", "children"),
    Output("kpi-military", "children"),
    Output("graph-rake", "figure"),
    Output("graph-datewise", "figure"),
    Output("graph-monthwise", "figure"),
    Output("from-to-table", "data"),
    Input("submit-btn", "n_clicks"),
    State("year-dropdown", "value"),
    State("month-dropdown", "value")
)
def refresh_dashboard(n_clicks, selected_year, selected_month):
    # First load (n_clicks == 0) → show ALL data
    if n_clicks == 0:
        df = load_data()  # no year filter
    else:
        # Load data for selected year (or all if year is None)
        df = load_data(selected_year)

        # Apply optional month filter
        if selected_month is not None and "Date" in df.columns:
            df = df[df["Month"] == selected_month]

    if df.empty:
        return 0, 0, {}, {}, {}, []

    # Military detection
    df["Military_Flag"] = df.apply(detect_military, axis=1)
    mil_df = df[df["Military_Flag"]].copy()

    if mil_df.empty:
        return len(df), 0, {}, {}, {}, []

    # Your specific rake filter
    TARGET_RAKE = "DRDO/SPL"
    mil_df = mil_df[
        mil_df["RAVRAKENAME"].astype(str)
        .str.contains(TARGET_RAKE, case=False, na=False)
    ]

    # Build visuals
    fig_rake = build_figure(mil_df)
    fig_datewise = build_datewise_figure(mil_df)
    fig_monthwise = build_monthwise_figure(mil_df)
    from_to_df = build_from_to_summary(mil_df)

    return (
        len(df),
        len(mil_df),
        fig_rake,
        fig_datewise,
        fig_monthwise,
        from_to_df.to_dict("records")
    )


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=False)