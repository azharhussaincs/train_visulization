import mysql.connector

# -----------------------------
# Remote MySQL connection
# -----------------------------
remote_host = "100.97.0.88"
remote_user = "railuser"
remote_password = "r4dh4@rail#501"
remote_db = "in_railin"
table_name = "rail_rem_rake_20251126100147"

# -----------------------------
# Local MySQL connection
# -----------------------------
local_host = "localhost"
local_user = "root"
local_password = "admin"
local_db = "in_railin_local"

try:
    # Connect to remote DB
    remote_conn = mysql.connector.connect(
        host=remote_host,
        user=remote_user,
        password=remote_password,
        database=remote_db
    )

    if remote_conn.is_connected():
        print("✅ Connected to remote DB.")
        remote_cursor = remote_conn.cursor()
        remote_cursor.execute(f"SELECT * FROM {table_name};")
        rows = remote_cursor.fetchall()
        columns = [i[0] for i in remote_cursor.description]

    # Connect to local MySQL server
    local_conn = mysql.connector.connect(
        host=local_host,
        user=local_user,
        password=local_password
    )
    local_cursor = local_conn.cursor()

    # Create local database if it doesn't exist
    local_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {local_db};")
    local_conn.commit()
    print(f"✅ Local database '{local_db}' ensured.")

    # Switch to local database
    local_conn.database = local_db

    # Create table
    column_definitions = ", ".join([f"{col} TEXT" for col in columns])
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        local_id INT AUTO_INCREMENT PRIMARY KEY,
        {column_definitions}
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    local_cursor.execute(create_table_sql)
    local_conn.commit()
    print(f"✅ Local table '{table_name}' ensured.")

    # 🔹 ADD UNIQUE INDEX TO PREVENT DUPLICATES (SAFE)
    unique_cols = ", ".join(columns)
    create_unique_index_sql = f"""
    CREATE UNIQUE INDEX IF NOT EXISTS uniq_{table_name}
    ON {table_name} ({unique_cols});
    """
    try:
        local_cursor.execute(create_unique_index_sql)
        local_conn.commit()
        print("✅ Unique index ensured (duplicates prevention enabled).")
    except mysql.connector.Error:
        pass  # index already exists

    # Insert rows (IGNORE duplicates)
    inserted_count = 0
    for row in rows:
        placeholders = ", ".join(["%s"] * len(row))
        columns_str = ", ".join(columns)
        sql = f"""
        INSERT IGNORE INTO {table_name} ({columns_str})
        VALUES ({placeholders})
        """
        local_cursor.execute(sql, row)
        inserted_count += local_cursor.rowcount

    local_conn.commit()
    print(f"✅ {inserted_count} NEW rows inserted (duplicates ignored).")

except mysql.connector.Error as err:
    print("❌ MySQL error:", err)

finally:
    if 'remote_conn' in locals() and remote_conn.is_connected():
        remote_cursor.close()
        remote_conn.close()
    if 'local_conn' in locals() and local_conn.is_connected():
        local_cursor.close()
        local_conn.close()
    print("ℹ️ Connections closed.")
