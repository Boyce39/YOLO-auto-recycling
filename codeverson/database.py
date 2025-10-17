import sqlite3

def connect_db():
    return sqlite3.connect("garbage_data.db")

def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trash_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            category TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trash_full (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bin_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()