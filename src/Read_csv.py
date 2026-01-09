import json
import csv

# Path to your JSON file
json_file = "list_of_stations.json"
csv_file = "stations.csv"

# Read JSON data
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Check the structure of the first element
# print(data[0])  # uncomment to see how JSON is structured

# Write to CSV
# Assuming JSON is a list of dicts like: [{"Station Code": "AADR", "Station Name": "Amb andaura"}, ...]
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    if len(data) > 0:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

print(f"Saved {len(data)} stations to {csv_file}")

