"""
Migration: Add xpath column to config_templates table
"""
import sqlite3
import os

DB_PATH = "network_audit.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if xpath column already exists
        cursor.execute("PRAGMA table_info(config_templates)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'xpath' in columns:
            print("Column 'xpath' already exists in config_templates table")
        else:
            # Add xpath column
            cursor.execute("ALTER TABLE config_templates ADD COLUMN xpath TEXT")
            conn.commit()
            print("Successfully added 'xpath' column to config_templates table")

    except sqlite3.Error as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
