# ============================================================================
# services/config_backup_service.py
# ============================================================================

import hashlib
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from models.device import Device
from db_models import ConfigBackupDB, ConfigChangeEventDB
from connectors.netconf_connector import NetconfConnector
from connectors.nokia_sros_connector import NokiaSROSConnector
from models.enums import VendorType
from shared.logger import setup_logger
import difflib

logger = setup_logger(__name__)


class ConfigBackupService:
    """Service for managing device configuration backups"""

    @staticmethod
    def _calculate_hash(config_data: str) -> str:
        """Calculate SHA256 hash of configuration"""
        return hashlib.sha256(config_data.encode()).hexdigest()

    @staticmethod
    def create_backup_sync(
        db: Session,
        device: Device,
        config_data: str,
        backup_type: str = "auto",
        created_by: Optional[str] = None
    ) -> ConfigBackupDB:
        """
        Create a new configuration backup (synchronous version)

        Args:
            db: Database session
            device: Device to backup
            config_data: Configuration data
            backup_type: Type of backup (auto, manual, pre_change, post_change)
            created_by: Username who created the backup

        Returns:
            Created ConfigBackupDB instance
        """
        try:
            config_hash = ConfigBackupService._calculate_hash(config_data)

            # Check if this exact config already exists (no changes)
            existing_backup = db.query(ConfigBackupDB).filter(
                and_(
                    ConfigBackupDB.device_id == device.id,
                    ConfigBackupDB.config_hash == config_hash
                )
            ).order_by(desc(ConfigBackupDB.timestamp)).first()

            if existing_backup and backup_type == "auto":
                logger.debug(f"No configuration changes detected for device {device.hostname}, skipping backup")
                return existing_backup

            # Get previous backup for change detection
            previous_backup = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.device_id == device.id
            ).order_by(desc(ConfigBackupDB.timestamp)).first()

            # Create new backup
            backup = ConfigBackupDB(
                device_id=device.id,
                config_data=config_data,
                config_hash=config_hash,
                backup_type=backup_type,
                triggered_by=created_by,
                size_bytes=len(config_data)
            )

            db.add(backup)
            db.flush()  # Get the backup ID

            # Detect changes if there's a previous backup
            if previous_backup and previous_backup.config_hash != config_hash:
                ConfigBackupService._create_change_event_sync(
                    db=db,
                    device_id=device.id,
                    previous_backup_id=previous_backup.id,
                    current_backup_id=backup.id,
                    previous_config=previous_backup.config_data,
                    current_config=config_data,
                    changed_by=created_by
                )

            db.commit()
            logger.info(f"Created {backup_type} backup for device {device.hostname} (ID: {backup.id})")

            # Cleanup old backups - keep only last 30 per device
            ConfigBackupService._cleanup_old_backups_sync(db, device.id, keep_count=30)

            return backup

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create backup for device {device.hostname}: {str(e)}")
            raise

    @staticmethod
    async def create_backup(
        db: Session,
        device: Device,
        config_data: str,
        backup_type: str = "auto",
        created_by: Optional[str] = None
    ) -> ConfigBackupDB:
        """
        Create a new configuration backup

        Args:
            db: Database session
            device: Device to backup
            config_data: Configuration data
            backup_type: Type of backup (auto, manual, pre_change, post_change)
            created_by: Username who created the backup

        Returns:
            Created ConfigBackupDB instance
        """
        try:
            config_hash = ConfigBackupService._calculate_hash(config_data)

            # Check if this exact config already exists (no changes)
            existing_backup = db.query(ConfigBackupDB).filter(
                and_(
                    ConfigBackupDB.device_id == device.id,
                    ConfigBackupDB.config_hash == config_hash
                )
            ).order_by(desc(ConfigBackupDB.timestamp)).first()

            if existing_backup and backup_type == "auto":
                logger.debug(f"No configuration changes detected for device {device.hostname}, skipping backup")
                return existing_backup

            # Get previous backup for change detection
            previous_backup = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.device_id == device.id
            ).order_by(desc(ConfigBackupDB.timestamp)).first()

            # Create new backup
            backup = ConfigBackupDB(
                device_id=device.id,
                config_data=config_data,
                config_hash=config_hash,
                backup_type=backup_type,
                triggered_by=created_by,
                size_bytes=len(config_data)
            )

            db.add(backup)
            db.flush()  # Get the backup ID

            # Detect changes if there's a previous backup
            if previous_backup and previous_backup.config_hash != config_hash:
                ConfigBackupService._create_change_event_sync(
                    db=db,
                    device_id=device.id,
                    previous_backup_id=previous_backup.id,
                    current_backup_id=backup.id,
                    previous_config=previous_backup.config_data,
                    current_config=config_data,
                    changed_by=created_by
                )

            db.commit()
            logger.info(f"Created {backup_type} backup for device {device.hostname} (ID: {backup.id})")

            # Cleanup old backups - keep only last 30 per device
            await ConfigBackupService._cleanup_old_backups(db, device.id, keep_count=30)

            return backup

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create backup for device {device.hostname}: {str(e)}")
            raise

    @staticmethod
    def _create_change_event_sync(
        db: Session,
        device_id: int,
        previous_backup_id: int,
        current_backup_id: int,
        previous_config: str,
        current_config: str,
        changed_by: Optional[str] = None
    ):
        """Create a configuration change event (synchronous version)"""
        try:
            # Generate unified diff
            diff = ConfigBackupService.generate_diff(previous_config, current_config)

            # Count changes
            lines_added = diff.count('\n+')
            lines_removed = diff.count('\n-')
            lines_changed = lines_added + lines_removed

            # Determine severity based on change magnitude
            if lines_changed > 50:
                severity = "high"
            elif lines_changed > 10:
                severity = "medium"
            else:
                severity = "low"

            change_event = ConfigChangeEventDB(
                device_id=device_id,
                previous_backup_id=previous_backup_id,
                current_backup_id=current_backup_id,
                change_type="drift",
                diff_text=diff,
                change_summary={
                    'added_lines': lines_added,
                    'removed_lines': lines_removed,
                    'total_changes': lines_changed
                },
                severity=severity
            )

            db.add(change_event)
            logger.info(f"Detected configuration change for device ID {device_id}: {lines_changed} lines changed")

            # Note: Notifications are not sent in sync mode to avoid event loop issues
            # Notifications will be handled in async audit flow

        except Exception as e:
            logger.error(f"Failed to create change event: {str(e)}")
            # Don't raise - we don't want to fail the backup just because notification failed
            logger.debug(f"Change event creation error details: {e}", exc_info=True)

    @staticmethod
    async def _create_change_event(
        db: AsyncSession,
        device_id: int,
        previous_backup_id: int,
        current_backup_id: int,
        previous_config: str,
        current_config: str,
        changed_by: Optional[str] = None
    ):
        """Create a configuration change event"""
        try:
            # Generate unified diff
            diff = ConfigBackupService.generate_diff(previous_config, current_config)

            # Count changes
            lines_added = diff.count('\n+')
            lines_removed = diff.count('\n-')
            lines_changed = lines_added + lines_removed

            # Determine severity based on change magnitude
            if lines_changed > 50:
                severity = "high"
            elif lines_changed > 10:
                severity = "medium"
            else:
                severity = "low"

            change_event = ConfigChangeEventDB(
                device_id=device_id,
                previous_backup_id=previous_backup_id,
                current_backup_id=current_backup_id,
                change_type="drift",
                diff_text=diff,
                change_summary={
                    'added_lines': lines_added,
                    'removed_lines': lines_removed,
                    'total_changes': lines_changed
                },
                severity=severity
            )

            db.add(change_event)
            logger.info(f"Detected configuration change for device ID {device_id}: {lines_changed} lines changed")

        except Exception as e:
            logger.error(f"Failed to create change event: {str(e)}")
            raise

    @staticmethod
    def generate_diff(old_config: str, new_config: str) -> str:
        """Generate unified diff between two configurations"""
        old_lines = old_config.splitlines(keepends=True)
        new_lines = new_config.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='previous',
            tofile='current',
            lineterm='\n'
        )

        return ''.join(diff)

    @staticmethod
    async def backup_device(
        db: Session,
        device: Device,
        backup_type: str = "manual",
        created_by: Optional[str] = None
    ) -> ConfigBackupDB:
        """
        Backup a device by connecting and retrieving its configuration

        Args:
            db: Database session
            device: Device to backup
            backup_type: Type of backup
            created_by: Username who initiated the backup

        Returns:
            Created ConfigBackupDB instance
        """
        connector = None
        try:
            # Nokia SROS: Use SSH CLI (tests prove it works!)
            if device.vendor == VendorType.NOKIA_SROS:
                import asyncio
                from connectors.ssh_connector import SSHConnector
                connector = SSHConnector(device)

                # Run sync method in executor to avoid blocking
                loop = asyncio.get_event_loop()
                config_data = await loop.run_in_executor(None, connector.get_config_cli_sync)
            else:
                # Other vendors not currently supported
                raise DeviceConnectionError(f"Vendor {device.vendor} not currently supported")

            # Create backup
            backup = await ConfigBackupService.create_backup(
                db=db,
                device=device,
                config_data=config_data,
                backup_type=backup_type,
                created_by=created_by
            )

            # Keep only last 30 backups per device
            await ConfigBackupService._cleanup_old_backups(db, device.id, keep_count=30)

            return backup

        except Exception as e:
            logger.exception(f"Failed to backup device {device.hostname}: {str(e)}")
            raise
        finally:
            if connector:
                await connector.disconnect()

    @staticmethod
    async def _cleanup_old_backups(db: Session, device_id: int, keep_count: int = 30):
        """
        Delete old backups, keeping only the most recent N backups per device

        Args:
            db: Database session
            device_id: Device ID
            keep_count: Number of backups to keep (default 30)
        """
        try:
            # Get all backups for this device, ordered by timestamp descending
            all_backups = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.device_id == device_id
            ).order_by(desc(ConfigBackupDB.timestamp)).all()

            # If we have more than keep_count backups, delete the oldest ones
            if len(all_backups) > keep_count:
                backups_to_delete = all_backups[keep_count:]
                for backup in backups_to_delete:
                    db.delete(backup)

                db.commit()
                logger.info(f"Cleaned up {len(backups_to_delete)} old backups for device {device_id}, kept latest {keep_count}")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups for device {device_id}: {str(e)}")
            # Don't raise - cleanup failure shouldn't break the backup process

    @staticmethod
    def _cleanup_old_backups_sync(db: Session, device_id: int, keep_count: int = 30):
        """
        Delete old backups, keeping only the most recent N backups per device (synchronous version)

        Args:
            db: Database session
            device_id: Device ID
            keep_count: Number of backups to keep (default 30)
        """
        try:
            # Get all backups for this device, ordered by timestamp descending
            all_backups = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.device_id == device_id
            ).order_by(desc(ConfigBackupDB.timestamp)).all()

            # If we have more than keep_count backups, delete the oldest ones
            if len(all_backups) > keep_count:
                backups_to_delete = all_backups[keep_count:]
                for backup in backups_to_delete:
                    db.delete(backup)

                db.commit()
                logger.info(f"Cleaned up {len(backups_to_delete)} old backups for device {device_id}, kept latest {keep_count}")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups for device {device_id}: {str(e)}")
            # Don't raise - cleanup failure shouldn't break the backup process

    @staticmethod
    async def get_device_backups(
        db: AsyncSession,
        device_id: int,
        limit: int = 50
    ) -> List[ConfigBackupDB]:
        """Get backup history for a device"""
        stmt = select(ConfigBackupDB).where(
            ConfigBackupDB.device_id == device_id
        ).order_by(desc(ConfigBackupDB.timestamp)).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_backup_by_id(db: AsyncSession, backup_id: int) -> Optional[ConfigBackupDB]:
        """Get a specific backup by ID"""
        stmt = select(ConfigBackupDB).where(ConfigBackupDB.id == backup_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def compare_backups(
        db: AsyncSession,
        backup_id_1: int,
        backup_id_2: int
    ) -> Tuple[ConfigBackupDB, ConfigBackupDB, str]:
        """
        Compare two configuration backups

        Returns:
            Tuple of (backup1, backup2, diff_text)
        """
        backup1 = await ConfigBackupService.get_backup_by_id(db, backup_id_1)
        backup2 = await ConfigBackupService.get_backup_by_id(db, backup_id_2)

        if not backup1 or not backup2:
            raise ValueError("One or both backups not found")

        diff = ConfigBackupService.generate_diff(
            backup1.config_data,
            backup2.config_data
        )

        return backup1, backup2, diff

    @staticmethod
    async def get_device_change_history(
        db: AsyncSession,
        device_id: int,
        limit: int = 50
    ) -> List[ConfigChangeEventDB]:
        """Get configuration change history for a device"""
        stmt = select(ConfigChangeEventDB).where(
            ConfigChangeEventDB.device_id == device_id
        ).order_by(desc(ConfigChangeEventDB.detected_at)).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def restore_config(
        db: AsyncSession,
        device: Device,
        backup_id: int,
        restored_by: Optional[str] = None
    ) -> bool:
        """
        Restore a device to a previous configuration

        Note: This creates a pre_change backup before restoration
        """
        connector = None
        try:
            # Get the backup to restore
            backup = await ConfigBackupService.get_backup_by_id(db, backup_id)
            if not backup:
                raise ValueError(f"Backup {backup_id} not found")

            if backup.device_id != device.id:
                raise ValueError(f"Backup {backup_id} does not belong to device {device.hostname}")

            # Create pre-restore backup
            if device.vendor == VendorType.NOKIA_SROS:
                connector = NokiaSROSConnector(device)
            else:
                connector = NetconfConnector(device)

            await connector.connect()
            current_config = await connector.get_config()

            await ConfigBackupService.create_backup(
                db=db,
                device=device,
                config_data=current_config,
                backup_type="pre_change",
                created_by=restored_by
            )

            # TODO: Implement actual config restoration via NETCONF edit-config
            # This requires careful implementation to avoid breaking device connectivity
            logger.warning(f"Configuration restoration not yet implemented for {device.hostname}")

            return True

        except Exception as e:
            logger.error(f"Failed to restore configuration for {device.hostname}: {str(e)}")
            raise
        finally:
            if connector:
                await connector.disconnect()
