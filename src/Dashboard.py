import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, dash_table
import mysql.connector
import warnings
warnings.filterwarnings(
    "ignore",
    message="pandas only supports SQLAlchemy connectable"
)


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
local_conn = mysql.connector.connect(
    host=local_host,
    user=local_user,
    password=local_password,
    database=local_db
)

query = f"SELECT * FROM {table_name}"
df = pd.read_sql(query, local_conn)

local_conn.close()

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

df["Military_Flag"] = df.apply(detect_military, axis=1)

# ---------------------------
# Military-only dataframe
# ---------------------------
mil_df = df[df["Military_Flag"] == True].copy()

# ---------------------------
# OPTIONAL: Focus on specific rake
# ---------------------------
TARGET_RAKE = "DRDO/SPL"

if "RAVRAKENAME" in mil_df.columns:
    mil_df = mil_df[
        mil_df["RAVRAKENAME"]
        .astype(str)
        .str.contains(TARGET_RAKE, case=False, na=False)
    ]

# ---------------------------
# BAR CHART – MILITARY COUNTS BY RAKE NAME
# ---------------------------
if "RAVRAKENAME" in mil_df.columns:
    rake_summary = (
        mil_df["RAVRAKENAME"]
        .astype(str)
        .value_counts()
        .reset_index()
    )
    rake_summary.columns = ["Rake Name", "Count"]
    rake_summary["Count"] = rake_summary["Count"].astype(int)

    fig_military_flag = px.bar(
        rake_summary,
        x="Rake Name",
        y="Count",
        text="Count",
        title="Military-Related Movements by Rake Name",
        template="plotly_white"
    )

    fig_military_flag.update_traces(
        textposition="outside",
        marker_color="#2c3e50"
    )
    fig_military_flag.update_yaxes(tickformat="d")
else:
    fig_military_flag = None

# ---------------------------
# Station Codes Table
# ---------------------------
station_cols = [
    c for c in ["RAVRAKENAME", "RAVSTTNFROM", "RAVSRVGSTTN"]
    if c in mil_df.columns
]

station_df = mil_df[station_cols].drop_duplicates()

# Optional export
station_df.to_csv("military_station_codes_only.csv", index=False)

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

        html.Div(
            style={
                "backgroundColor": "#1f2c3c",
                "color": "white",
                "padding": "20px",
                "borderRadius": "8px",
                "marginBottom": "20px"
            },
            children=[
                html.H2("Military-Related Railway Movement Dashboard", style={"margin": "0"}),
                # html.P(f"Focused Rake: {TARGET_RAKE}", style={"opacity": "0.8"})
            ]
        ),

        html.Div(
            style={
                "display": "flex",
                "gap": "20px",
                "marginBottom": "20px"
            },
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
                        html.H2(len(df))
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
                        html.H2(len(mil_df))
                    ]
                )
            ]
        ),

        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "8px",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.1)",
                "marginBottom": "20px"
            },
            children=[dcc.Graph(figure=fig_military_flag)]
        ),

        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "8px",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
            },
            children=[
                html.H4("Station Codes (Origin → Destination)"),
                # html.P("Codes only | Internal management use"),

                dash_table.DataTable(
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

if __name__ == "__main__":
    app.run(debug=True)
