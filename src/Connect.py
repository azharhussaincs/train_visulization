import mysql.connector

# Database connection details
host = "100.97.0.88"
user = "railuser"
password = "r4dh4@rail#501"
database = "in_railin"

try:
    # Establish the connection
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

    if connection.is_connected():
        print("Successfully connected to the database!")

        cursor = connection.cursor()

        # Table name
        table_name = "rail_rem_rake_20251126100147"

        # Fetch first 10 rows
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 10;")
        rows = cursor.fetchall()

        # Print column names
        column_names = [i[0] for i in cursor.description]
        print("Columns:", column_names)

        # Print first 10 rows
        for row in rows:
            print(row)

except mysql.connector.Error as err:
    print("Error while connecting to MySQL:", err)

finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
        print("Connection closed.")
