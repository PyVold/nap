"""
Database Migration: Add metadata column to devices table

This migration adds a JSON metadata column to store protocol and system information
collected during device discovery (BGP, ISIS/OSPF, LDP, system IPs, etc.)
"""

import sqlite3
import psycopg2
import os


def upgrade():
    """Add metadata column to devices table"""
    db_url = os.getenv('DATABASE_URL', 'postgresql://nap_user:nap_password@database:5432/nap_db')

    if 'postgresql' in db_url:
        # PostgreSQL
        parts = db_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        host_port = host_db[0].split(':')

        conn = psycopg2.connect(
            dbname=host_db[1],
            user=user_pass[0],
            password=user_pass[1],
            host=host_port[0],
            port=host_port[1] if len(host_port) > 1 else 5432
        )
        cursor = conn.cursor()

        # Check if column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='devices' AND column_name='metadata'
        """)

        if not cursor.fetchone():
            print("Adding metadata column to devices table...")
            cursor.execute("""
                ALTER TABLE devices
                ADD COLUMN metadata JSONB
            """)
            conn.commit()
            print("✅ Migration completed: metadata column added")
        else:
            print("⏭️  Metadata column already exists, skipping...")

        cursor.close()
        conn.close()

    else:
        # SQLite
        conn = sqlite3.connect(db_url.replace('sqlite:///', ''))
        cursor = conn.cursor()

        # Check if column exists
        cursor.execute("PRAGMA table_info(devices)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'metadata' not in columns:
            print("Adding metadata column to devices table...")
            cursor.execute("""
                ALTER TABLE devices
                ADD COLUMN metadata TEXT
            """)
            conn.commit()
            print("✅ Migration completed: metadata column added")
        else:
            print("⏭️  Metadata column already exists, skipping...")

        cursor.close()
        conn.close()


if __name__ == '__main__':
    upgrade()
