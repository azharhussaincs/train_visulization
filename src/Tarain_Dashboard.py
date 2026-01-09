import pandas as pd
import folium
from folium.plugins import MarkerCluster
from dash import Dash, dcc, html
import plotly.express as px
import requests

# Load the rake data
df = pd.read_csv('data.csv')

# Define relevant columns
movement_cols = ['RAVSRVGSTTN', 'RAVSCTN', 'RAVSTTN', 'RAVSTTNFROM', 'RAVSTTNTO', 'RAVDVSN', 'RAVZONE', 'RAVIWRDDRTN',
                 'RAVOWRDDRTN', 'RAVRAKESTTS']
load_cols = ['RAVRAKETYPE', 'RAVLOADNAME', 'RAVRAKENAME', 'RAVGRUPRAKECMDT', 'RAVCNSR', 'RAVCNSG', 'RACLEFLAG',
             'RAVCRNTLOADID']
army_cols = ['RAVRAKENAME', 'RAVLOADNAME', 'RAVRAKETYPE']

all_cols = list(set(movement_cols + load_cols + army_cols + ['RAVRAKEID']))
df_full = df[all_cols].copy()

# Updated working GeoJSON URL for Indian Railway stations (from datameet/railways)
stations_url = 'https://raw.githubusercontent.com/datameet/railways/master/stations.geojson'
response = requests.get(stations_url)
if response.status_code != 200:
    print("Failed to load stations GeoJSON. Using fallback empty dict.")
    station_coords = {}
else:
    stations_data = response.json()
    station_coords = {}
    for feature in stations_data['features']:
        props = feature.get('properties', {})
        code = props.get('code', '').strip().upper()
        if code and feature.get('geometry', {}).get('type') == 'Point':
            coords = feature['geometry']['coordinates']  # [lon, lat]
            station_coords[code] = (coords[1], coords[0])  # folium: (lat, lon)
    print(f"Successfully loaded {len(station_coords)} station coordinates dynamically.")

# Safe army/defence filter
army_keywords = ['DRDO', 'SPL', 'DEFENCE', 'MILITARY', 'ARMY']
mask = pd.Series(False, index=df_full.index)
for col in ['RAVRAKENAME', 'RAVLOADNAME']:
    if col in df_full.columns:
        mask |= df_full[col].astype(str).str.contains('|'.join(army_keywords), case=False, na=False)

df_army = df_full[mask].copy()
print(f"Found {len(df_army)} defence/special rakes.")


# Function to create Folium map
def create_movement_map(df_subset, filename='map.html', title='Train Movements'):
    if df_subset.empty:
        print(f"No data for {title}, skipping map.")
        return None

    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles='OpenStreetMap')
    marker_cluster = MarkerCluster().add_to(m)

    plotted_rakes = 0
    for idx, row in df_subset.iterrows():
        from_st = str(row.get('RAVSTTNFROM', '') or '').strip().upper()
        curr_st = str(row.get('RAVSTTN', '') or '').strip().upper()
        to_st = str(row.get('RAVSTTNTO', '') or '').strip().upper()
        rake_id = row.get('RAVRAKEID', 'Unknown')
        load_info = str(row.get('RAVLOADNAME') or row.get('RAVRAKENAME') or '')
        rake_type = row.get('RAVRAKETYPE', '')

        points = []
        labels = []

        if from_st and from_st in station_coords:
            lat, lon = station_coords[from_st]
            points.append((lat, lon))
            labels.append(f"From: {from_st}")
            folium.Marker((lat, lon),
                          popup=f"<b>From:</b> {from_st}<br><b>Rake ID:</b> {rake_id}<br><b>Load:</b> {load_info}<br><b>Type:</b> {rake_type}",
                          icon=folium.Icon(color='green')).add_to(marker_cluster)

        if curr_st and curr_st in station_coords:
            lat, lon = station_coords[curr_st]
            points.append((lat, lon))
            labels.append(f"Current: {curr_st}")
            folium.Marker((lat, lon),
                          popup=f"<b>Current:</b> {curr_st}<br><b>Rake ID:</b> {rake_id}<br><b>Load:</b> {load_info}<br><b>Type:</b> {rake_type}",
                          icon=folium.Icon(color='blue')).add_to(marker_cluster)

        if to_st and to_st in station_coords:
            lat, lon = station_coords[to_st]
            points.append((lat, lon))
            labels.append(f"To: {to_st}")
            folium.Marker((lat, lon),
                          popup=f"<b>To:</b> {to_st}<br><b>Rake ID:</b> {rake_id}<br><b>Load:</b> {load_info}<br><b>Type:</b> {rake_type}",
                          icon=folium.Icon(color='red')).add_to(marker_cluster)

        if len(points) >= 2:
            folium.PolyLine(points, color="purple", weight=3, opacity=0.8, tooltip=" → ".join(labels)).add_to(m)
            plotted_rakes += 1

    print(f"Plotted {plotted_rakes} rakes with valid coordinates on {title} map.")
    m.save(filename)
    return m


# Generate maps
all_map_file = 'all_rakes_movements_map.html'
army_map_file = 'defence_rakes_movements_map.html'

create_movement_map(df_full, all_map_file, 'All Rakes Movements')
create_movement_map(df_army, army_map_file, 'Defence Rakes Movements')

# Dash Dashboard
app = Dash(__name__, title='Indian Railways Freight Rake Dashboard')

app.layout = html.Div([
    html.H1('Indian Railways Freight Rake Dashboard', style={'textAlign': 'center', 'marginBottom': 30}),

    html.Div([
        html.P(f"Loaded {len(station_coords)} station coordinates dynamically (auto-updates with new data)."),
        html.P("When you replace 'data.csv' with updated file, new stations will appear on map if in dataset.")
    ], style={'textAlign': 'center', 'fontStyle': 'italic'}),

    dcc.Tabs([
        dcc.Tab(label='Rake Movements on Map', children=[
            html.H3('Interactive Maps'),
            html.Ul([
                html.Li(html.A('All Rakes Map (open in browser for zoom/click)', href=all_map_file, target='_blank')),
                html.Li(html.A('Defence/Special Rakes Map', href=army_map_file, target='_blank'))
            ]),
            html.H4('Summary'),
            dcc.Graph(figure=px.bar(df_full['RAVZONE'].value_counts().reset_index(), x='RAVZONE', y='count',
                                    title='Rakes per Zone')),
            dcc.Graph(figure=px.bar(df_full['RAVDVSN'].value_counts().head(20).reset_index(), x='RAVDVSN', y='count',
                                    title='Top 20 Divisions')),
        ]),

        dcc.Tab(label='Load & Commodity Details', children=[
            dcc.Graph(figure=px.pie(df_full, names='RAVRAKETYPE', title='Rake Types Distribution')),
            dcc.Graph(figure=px.bar(df_full['RAVRAKETYPE'].value_counts().reset_index(), x='RAVRAKETYPE', y='count',
                                    title='Rake Type Counts')),
            dcc.Graph(figure=px.bar(df_full['RAVCNSR'].value_counts().head(15).reset_index(), x='RAVCNSR', y='count',
                                    title='Top Consignors')),
            dcc.Graph(figure=px.bar(df_full['RAVCNSG'].value_counts().head(15).reset_index(), x='RAVCNSG', y='count',
                                    title='Top Consignees')),
            dcc.Graph(figure=px.sunburst(df_full, path=['RAVZONE', 'RAVDVSN', 'RAVRAKETYPE'],
                                         title='Zone → Division → Rake Type'))
        ]),

        dcc.Tab(label='Defence / Special Rakes', children=[
            html.H3(f'{len(df_army)} Defence/Special Rakes Found'),
            html.A('Open Defence Map', href=army_map_file, target='_blank', style={'fontSize': '18px'}),
            dcc.Graph(figure=px.pie(df_army, names='RAVRAKETYPE', title='Defence Rake Types')),
            dcc.Graph(figure=px.bar(df_army, x='RAVRAKENAME', title='Defence Rake Names')),
            html.H4('Matching Rakes Table'),
            html.Pre(df_army[
                         ['RAVRAKEID', 'RAVRAKENAME', 'RAVLOADNAME', 'RAVSTTN', 'RAVSTTNFROM', 'RAVSTTNTO', 'RAVZONE',
                          'RAVDVSN']].to_string(index=False))
        ])
    ])
])

if __name__ == '__main__':
    print("Starting server at http://127.0.0.1:8050")
    print("Open generated HTML maps in browser for best interactivity.")
    app.run_server(debug=True)  # Fixed: Use app.run_server() - it's still valid in current Dash versions