import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, dash_table, Input, Output
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
    local_conn = mysql.connector.connect(
        host=local_host,
        user=local_user,
        password=local_password,
        database=local_db
    )
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, local_conn)
    local_conn.close()
    return df

# ---------------------------
# Detect Military Related Records
# ---------------------------
def detect_military(row):
    text = " ".join(str(x) for x in row.values).upper()
    keywords = [
        "DRDO",
        "ARMY",
        "MILY",
        "MILITARY",
        "DEFENCE",
        "DEFENSE",
        "ORDNANCE",
        "SPL"
    ]
    return any(k in text for k in keywords)

# ---------------------------
# Build bar chart
# ---------------------------
def build_figure(mil_df):
    if mil_df.empty or "RAVRAKENAME" not in mil_df.columns:
        return {}

    rake_summary = (
        mil_df["RAVRAKENAME"]
        .astype(str)
        .value_counts()
        .reset_index()
    )
    rake_summary.columns = ["Rake Name", "Count"]
    rake_summary["Count"] = rake_summary["Count"].astype(int)

    fig = px.bar(
        rake_summary,
        x="Rake Name",
        y="Count",
        text="Count",
        title="Military-Related Movements by Rake Name",
        template="plotly_white"
    )
    fig.update_traces(textposition="outside", marker_color="#2c3e50")
    fig.update_yaxes(tickformat="d")
    return fig

# ---------------------------
# Initial data load
# ---------------------------
df = load_data()
df["Military_Flag"] = df.apply(detect_military, axis=1)
mil_df = df[df["Military_Flag"] == True].copy()

TARGET_RAKE = "DRDO/SPL"

if "RAVRAKENAME" in mil_df.columns:
    mil_df = mil_df[
        mil_df["RAVRAKENAME"]
        .astype(str)
        .str.contains(TARGET_RAKE, case=False, na=False)
    ]

fig_military_flag = build_figure(mil_df)

station_cols = [
    c for c in ["RAVRAKENAME", "RAVSTTNFROM", "RAVSRVGSTTN"]
    if c in mil_df.columns
]
station_df = mil_df[station_cols].drop_duplicates()

# ---------------------------
# Dash App
# ---------------------------
app = Dash(__name__)

app.layout = html.Div(
    style={
        "backgroundColor": "#f4f6f9",
        "padding": "20px",
        "fontFamily": "Segoe UI, Arial"
    },
    children=[

        # Header
        html.Div(
            style={
                "backgroundColor": "#1f2c3c",
                "color": "white",
                "padding": "20px",
                "borderRadius": "8px",
                "marginBottom": "15px"
            },
            children=[
                html.H2("Military-Related Railway Movement Dashboard", style={"margin": "0"})
            ]
        ),

        # Refresh Button
        html.Button(
            "🔄 Refresh Data",
            id="refresh-btn",
            n_clicks=0,
            disabled=False,
            style={
                "backgroundColor": "#2c3e50",
                "color": "white",
                "border": "none",
                "padding": "10px 18px",
                "borderRadius": "6px",
                "cursor": "pointer",
                "marginBottom": "20px"
            }
        ),

        # KPI Cards
        html.Div(
            style={"display": "flex", "gap": "20px", "marginBottom": "20px"},
            children=[
                html.Div(
                    style={
                        "flex": "1",
                        "backgroundColor": "white",
                        "padding": "15px",
                        "borderRadius": "8px",
                        "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
                    },
                    children=[
                        html.H4("Total Records"),
                        html.H2(id="total-records", children=len(df))
                    ]
                ),
                html.Div(
                    style={
                        "flex": "1",
                        "backgroundColor": "white",
                        "padding": "15px",
                        "borderRadius": "8px",
                        "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
                    },
                    children=[
                        html.H4("Military-Related Records"),
                        html.H2(id="military-records", children=len(mil_df))
                    ]
                )
            ]
        ),

        # Chart with spinner
        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "8px",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.1)",
                "marginBottom": "20px"
            },
            children=[
                dcc.Loading(
                    type="circle",
                    children=[
                        dcc.Graph(id="rake-bar-chart", figure=fig_military_flag)
                    ]
                )
            ]
        ),

        # Table
        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "8px",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
            },
            children=[
                html.H4("Station Codes (Origin → Destination)"),
                dash_table.DataTable(
                    id="station-table",
                    columns=[{"name": c, "id": c} for c in station_df.columns],
                    data=station_df.to_dict("records"),
                    page_size=15,
                    style_header={
                        "backgroundColor": "#2c3e50",
                        "color": "white",
                        "fontWeight": "bold"
                    },
                    style_cell={
                        "fontFamily": "monospace",
                        "fontSize": 13,
                        "padding": "8px",
                        "textAlign": "left"
                    },
                    style_data_conditional=[
                        {
                            "if": {"row_index": "odd"},
                            "backgroundColor": "#f2f2f2"
                        }
                    ]
                )
            ]
        )
    ]
)

# ---------------------------
# Refresh callback
# ---------------------------
@app.callback(
    Output("rake-bar-chart", "figure"),
    Output("station-table", "data"),
    Output("total-records", "children"),
    Output("military-records", "children"),
    Output("refresh-btn", "children"),
    Output("refresh-btn", "disabled"),
    Input("refresh-btn", "n_clicks")
)
def refresh_dashboard(n_clicks):
    button_text = "⏳ Refreshing..." if n_clicks else "🔄 Refresh Data"

    df = load_data()
    df["Military_Flag"] = df.apply(detect_military, axis=1)
    mil_df = df[df["Military_Flag"] == True].copy()

    if "RAVRAKENAME" in mil_df.columns:
        mil_df = mil_df[
            mil_df["RAVRAKENAME"]
            .astype(str)
            .str.contains(TARGET_RAKE, case=False, na=False)
        ]

    fig = build_figure(mil_df)

    station_cols = [
        c for c in ["RAVRAKENAME", "RAVSTTNFROM", "RAVSRVGSTTN"]
        if c in mil_df.columns
    ]
    station_df = mil_df[station_cols].drop_duplicates()

    return (
        fig,
        station_df.to_dict("records"),
        len(df),
        len(mil_df),
        "🔄 Refresh Data",
        False
    )

# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=False)
