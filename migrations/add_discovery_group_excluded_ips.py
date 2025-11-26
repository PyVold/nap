"""
Migration: Add excluded_ips column to discovery_groups table
Run this script to add the excluded_ips column for IP exclusion feature
"""
import sqlite3
import sys
import json
from pathlib import Path

# Add parent directory to path to import database config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings


def upgrade():
    """Add excluded_ips column to discovery_groups"""
    database_url = settings.database_url or "sqlite:///./network_audit.db"
    db_path = database_url.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(discovery_groups)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'excluded_ips' not in columns:
            print("Adding excluded_ips column...")
            # SQLite doesn't support adding JSON columns directly with DEFAULT
            # We'll add as TEXT and set default to empty list JSON
            cursor.execute("""
                ALTER TABLE discovery_groups
                ADD COLUMN excluded_ips TEXT DEFAULT '[]'
            """)
            print("✓ Added excluded_ips column")
        else:
            print("⊘ excluded_ips column already exists")

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def downgrade():
    """Remove excluded_ips column from discovery_groups"""
    print("Note: SQLite doesn't support DROP COLUMN directly.")
    print("To downgrade, you would need to recreate the table without this column.")
    print("This is not recommended for production databases.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add Discovery Group IP Exclusion")
    print("=" * 60)
    print()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
