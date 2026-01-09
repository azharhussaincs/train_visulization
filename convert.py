import json
import csv

with open('stations.json') as f:
    data = json.load(f)

with open('src/stations.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Code', 'Full Name'])
    for feature in data['features']:
        props = feature['properties']
        code = props.get('code', '').strip().upper()
        name = props.get('name', '').strip()
        if code and name:
            writer.writerow([code, name])

print("stations.csv created!")