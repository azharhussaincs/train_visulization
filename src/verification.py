import pandas as pd
import mysql.connector

# ---------------------------
# Your MySQL credentials
# ---------------------------
local_host = "localhost"
local_user = "root"
local_password = "admin"
local_db = "in_railin_local"
table_name = "rail_rem_rake_20251126100147"

# ---------------------------
# Load filtered data (YOUR SQL LOGIC)
# ---------------------------
conn = mysql.connector.connect(
    host=local_host,
    user=local_user,
    password=local_password,
    database=local_db
)

query = f"""
SELECT RADSTTSCHNGTIME, RAVRAKENAME
FROM {table_name}
WHERE 
    RADSTTSCHNGTIME >= '2025-11-26 00:00:00'
AND RADSTTSCHNGTIME <  '2025-11-27 00:00:00'
AND (
       UPPER(RAVRAKENAME) LIKE '%DRDO%'
    OR UPPER(RAVRAKENAME) LIKE '%ARMY%'
    OR UPPER(RAVRAKENAME) LIKE '%MILY%'
    OR UPPER(RAVRAKENAME) LIKE '%MILITARY%'
    OR UPPER(RAVRAKENAME) LIKE '%DEFENCE%'
    OR UPPER(RAVRAKENAME) LIKE '%DEFENSE%'
    OR UPPER(RAVRAKENAME) LIKE '%ORDNANCE%'
    OR UPPER(RAVRAKENAME) LIKE '%SPL%'
)
"""

df = pd.read_sql(query, conn)
conn.close()

# Convert to datetime
df["RADSTTSCHNGTIME"] = pd.to_datetime(df["RADSTTSCHNGTIME"], errors="coerce")

# Create Month-Year column
df["Month_Year"] = df["RADSTTSCHNGTIME"].dt.to_period("M").astype(str)

# ---------------------------
# Month-wise verification
# ---------------------------
summary = (
    df.groupby("Month_Year")
    .size()
    .reset_index(name="Movement_Count")
    .sort_values("Month_Year")
)

print("\n===== MONTH-WISE MOVEMENT VERIFICATION =====\n")
print(summary.to_string(index=False))

print("\nTotal filtered records:", len(df))
