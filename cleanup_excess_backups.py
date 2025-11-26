#!/usr/bin/env python3
"""
One-time cleanup script to remove excess config backups
Keeps only the latest 30 backups per device
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal
from db_models import ConfigBackupDB, DeviceDB
from sqlalchemy import func, desc
from utils.logger import setup_logger

logger = setup_logger(__name__)


def cleanup_excess_backups(keep_count: int = 30, dry_run: bool = True):
    """
    Clean up excess config backups, keeping only the latest N per device

    Args:
        keep_count: Number of backups to keep per device (default: 30)
        dry_run: If True, only show what would be deleted without actually deleting
    """
    db = SessionLocal()
    try:
        # Get all devices
        devices = db.query(DeviceDB).all()

        total_deleted = 0
        total_kept = 0

        for device in devices:
            # Get all backups for this device, ordered by timestamp descending
            all_backups = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.device_id == device.id
            ).order_by(desc(ConfigBackupDB.timestamp)).all()

            backup_count = len(all_backups)
            total_kept += min(backup_count, keep_count)

            # If we have more than keep_count backups, delete the oldest ones
            if backup_count > keep_count:
                backups_to_delete = all_backups[keep_count:]
                delete_count = len(backups_to_delete)
                total_deleted += delete_count

                logger.info(
                    f"Device '{device.hostname}' (ID: {device.id}): "
                    f"Has {backup_count} backups, will keep {keep_count}, "
                    f"{'WOULD DELETE' if dry_run else 'DELETING'} {delete_count}"
                )

                if not dry_run:
                    for backup in backups_to_delete:
                        db.delete(backup)
            else:
                logger.info(
                    f"Device '{device.hostname}' (ID: {device.id}): "
                    f"Has {backup_count} backups (within limit of {keep_count})"
                )

        if not dry_run:
            db.commit()
            logger.info(f"\n✅ Cleanup completed!")
        else:
            logger.info(f"\n🔍 DRY RUN - No changes made")

        logger.info(f"Summary:")
        logger.info(f"  - Total backups kept: {total_kept}")
        logger.info(f"  - Total backups {'that would be' if dry_run else ''} deleted: {total_deleted}")
        logger.info(f"  - Devices processed: {len(devices)}")

        if dry_run:
            logger.info(f"\nRun with '--execute' flag to actually delete excess backups")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during cleanup: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup excess config backups")
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete backups (default is dry-run mode)'
    )
    parser.add_argument(
        '--keep',
        type=int,
        default=30,
        help='Number of backups to keep per device (default: 30)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Config Backup Cleanup Script")
    print("=" * 70)
    print()

    if args.execute:
        print("⚠️  EXECUTE MODE - Will actually delete excess backups!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    else:
        print("🔍 DRY RUN MODE - Will only show what would be deleted")
        print("   Use --execute flag to actually delete backups")

    print()

    cleanup_excess_backups(keep_count=args.keep, dry_run=not args.execute)
