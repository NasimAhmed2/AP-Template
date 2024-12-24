import sqlite3
from django.conf import settings

# Function to ensure the table exists and then insert/update data
def ensure_table_and_update(file_name, path, upload_date, okay_status, okay_message, status='waiting'):
    print("Ensuring table and updating database...")
    """
    Ensures the table exists and then adds or updates the entry.

    Args:
        file_name (str): The name of the file.
        path (str): The full path of the file.
        status (str): The status to set, defaults to 'waiting'.
    """
    # Path to the SQLite database
    db_path = settings.DATABASES['default']['NAME']

    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure the table exists
    create_table_query = """
    CREATE TABLE IF NOT EXISTS invoice_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT UNIQUE NOT NULL,
        path TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        okay_status TEXT,
        okay_message TEXT,
        status TEXT DEFAULT 'waiting'
    );
    """
    cursor.execute(create_table_query)

    # Insert or update the record (Correct the table name here to match the created table)
    upsert_query = """
    INSERT INTO invoice_detail (file_name, path, upload_date, okay_status, okay_message, status)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(file_name) DO UPDATE SET
        path = excluded.path,
        status = excluded.status,
        okay_status = excluded.okay_status,
        okay_message = excluded.okay_message;
    """
    try:
        cursor.execute(upsert_query, (file_name, path, upload_date, okay_status, okay_message, status))
        conn.commit()
        print(f"Entry for '{file_name}' added/updated successfully.")
    except sqlite3.Error as e:
        print(f"Error updating/creating entry for '{file_name}': {e}")
    finally:
        conn.close()

db_path = settings.DATABASES['default']['NAME']
print(f"Connecting to database at {db_path}")

