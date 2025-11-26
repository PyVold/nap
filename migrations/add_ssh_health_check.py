"""
Migration: Add SSH health check columns to health_checks table
Run this script to add ssh_status and ssh_message columns
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path to import database config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings


def upgrade():
    """Add SSH health check columns"""
    database_url = settings.database_url or "sqlite:///./network_audit.db"
    db_path = database_url.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(health_checks)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'ssh_status' not in columns:
            print("Adding ssh_status column...")
            cursor.execute("""
                ALTER TABLE health_checks
                ADD COLUMN ssh_status BOOLEAN DEFAULT 0
            """)
            print("✓ Added ssh_status column")
        else:
            print("⊘ ssh_status column already exists")

        if 'ssh_message' not in columns:
            print("Adding ssh_message column...")
            cursor.execute("""
                ALTER TABLE health_checks
                ADD COLUMN ssh_message TEXT
            """)
            print("✓ Added ssh_message column")
        else:
            print("⊘ ssh_message column already exists")

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def downgrade():
    """Remove SSH health check columns"""
    print("Note: SQLite doesn't support DROP COLUMN directly.")
    print("To downgrade, you would need to recreate the table without these columns.")
    print("This is not recommended for production databases.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add SSH Health Check Columns")
    print("=" * 60)
    print()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
