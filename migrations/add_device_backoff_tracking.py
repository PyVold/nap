"""
Migration: Add exponential backoff tracking columns to devices table
Run this script to add consecutive_failures, last_check_attempt, and next_check_due columns
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path to import database config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings


def upgrade():
    """Add exponential backoff tracking columns"""
    database_url = settings.database_url or "sqlite:///./network_audit.db"
    db_path = database_url.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(devices)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'consecutive_failures' not in columns:
            print("Adding consecutive_failures column...")
            cursor.execute("""
                ALTER TABLE devices
                ADD COLUMN consecutive_failures INTEGER DEFAULT 0
            """)
            print("✓ Added consecutive_failures column")
        else:
            print("⊘ consecutive_failures column already exists")

        if 'last_check_attempt' not in columns:
            print("Adding last_check_attempt column...")
            cursor.execute("""
                ALTER TABLE devices
                ADD COLUMN last_check_attempt DATETIME
            """)
            print("✓ Added last_check_attempt column")
        else:
            print("⊘ last_check_attempt column already exists")

        if 'next_check_due' not in columns:
            print("Adding next_check_due column...")
            cursor.execute("""
                ALTER TABLE devices
                ADD COLUMN next_check_due DATETIME
            """)
            print("✓ Added next_check_due column")
        else:
            print("⊘ next_check_due column already exists")

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def downgrade():
    """Remove exponential backoff tracking columns"""
    print("Note: SQLite doesn't support DROP COLUMN directly.")
    print("To downgrade, you would need to recreate the table without these columns.")
    print("This is not recommended for production databases.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add Device Backoff Tracking Columns")
    print("=" * 60)
    print()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
