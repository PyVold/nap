# ============================================================================
# services/drift_detection_service.py
# ============================================================================

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from db_models import ConfigBackupDB, ConfigChangeEventDB, DeviceDB
from models.device import Device
from models.enums import VendorType
from services.config_backup_service import ConfigBackupService
from services.notification_service import NotificationService
from utils.crypto import decrypt_password
from shared.logger import setup_logger

logger = setup_logger(__name__)


class DriftDetectionService:
    """Service for detecting and managing configuration drift"""

    @staticmethod
    def detect_drift_for_device(
        db: Session,
        device: Device
    ) -> Optional[Dict[str, Any]]:
        """
        Detect configuration drift for a single device

        Compares current config with baseline/last known good config

        Returns:
            Drift information if drift detected, None otherwise
        """
        try:
            # Get all backups for device, ordered by creation time
            backups = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.device_id == device.id
            ).order_by(desc(ConfigBackupDB.timestamp)).limit(10).all()

            if len(backups) < 2:
                logger.debug(f"Not enough backups for drift detection on {device.hostname}")
                return None

            # Latest backup (current state)
            current_backup = backups[0]

            # Find baseline backup (marked with backup_type = "baseline")
            baseline_backup = None
            for backup in backups:
                if backup.backup_type == "baseline":
                    baseline_backup = backup
                    break

            # If no baseline found, use backup from 24 hours ago or oldest available
            if not baseline_backup:
                baseline_backup = backups[-1]

            # Compare configurations
            if current_backup.config_hash == baseline_backup.config_hash:
                logger.debug(f"No drift detected for {device.hostname}")
                return None

            # Drift detected!
            diff = ConfigBackupService.generate_diff(
                baseline_backup.config_data,
                current_backup.config_data
            )

            lines_changed = diff.count('\n+') + diff.count('\n-')

            drift_info = {
                "device_id": device.id,
                "device_name": device.hostname,
                "baseline_backup_id": baseline_backup.id,
                "current_backup_id": current_backup.id,
                "baseline_timestamp": baseline_backup.timestamp.isoformat(),
                "current_timestamp": current_backup.timestamp.isoformat(),
                "lines_changed": lines_changed,
                "diff": diff,
                "severity": "high" if lines_changed > 50 else "medium" if lines_changed > 10 else "low"
            }

            logger.warning(
                f"Configuration drift detected for {device.hostname}: "
                f"{lines_changed} lines changed since baseline"
            )

            return drift_info

        except Exception as e:
            logger.error(f"Failed to detect drift for {device.hostname}: {str(e)}")
            return None

    @staticmethod
    def detect_drift_for_all_devices(db: Session) -> List[Dict[str, Any]]:
        """
        Scan all devices for configuration drift

        Returns:
            List of drift information for devices with detected drift
        """
        drifts = []

        try:
            # Get all devices
            devices_db = db.query(DeviceDB).all()

            logger.info(f"Starting drift detection scan for {len(devices_db)} devices")

            for device_db in devices_db:
                decrypted_pwd = decrypt_password(device_db.password) if device_db.password else None
                device = Device(
                    id=device_db.id,
                    hostname=device_db.hostname,
                    vendor=VendorType(device_db.vendor),
                    ip=device_db.ip,
                    port=device_db.port,
                    username=device_db.username,
                    password=decrypted_pwd
                )

                drift_info = DriftDetectionService.detect_drift_for_device(db, device)

                if drift_info:
                    drifts.append(drift_info)

            logger.info(f"Drift detection complete: {len(drifts)} devices with drift detected")

        except Exception as e:
            logger.error(f"Error during drift detection scan: {str(e)}")

        return drifts

    @staticmethod
    def set_baseline(db: Session, device_id: int, backup_id: Optional[int] = None) -> bool:
        """
        Set a configuration backup as the baseline for drift detection

        Args:
            db: Database session
            device_id: Device ID
            backup_id: Backup ID to use as baseline (if None, uses latest)

        Returns:
            True if successful
        """
        try:
            # Clear existing baselines for this device
            existing_baselines = db.query(ConfigBackupDB).filter(
                and_(
                    ConfigBackupDB.device_id == device_id,
                    ConfigBackupDB.backup_type == "baseline"
                )
            ).all()

            for baseline in existing_baselines:
                baseline.backup_type = "auto"  # Reset to auto

            # Set new baseline
            if backup_id:
                backup = db.query(ConfigBackupDB).filter(
                    and_(
                        ConfigBackupDB.id == backup_id,
                        ConfigBackupDB.device_id == device_id
                    )
                ).first()
            else:
                backup = db.query(ConfigBackupDB).filter(
                    ConfigBackupDB.device_id == device_id
                ).order_by(desc(ConfigBackupDB.timestamp)).first()

            if not backup:
                logger.error(f"Backup not found for device {device_id}")
                return False

            # Mark as baseline
            backup.backup_type = "baseline"

            db.commit()

            logger.info(f"Set backup {backup.id} as baseline for device {device_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set baseline: {str(e)}")
            return False

    @staticmethod
    def get_drift_summary(db: Session) -> Dict[str, Any]:
        """
        Get drift detection summary statistics

        Returns:
            Summary statistics about configuration drift
        """
        try:
            # Get total devices
            total_devices = db.query(DeviceDB).count()

            # Get devices with recent changes (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_changes = db.query(ConfigChangeEventDB).filter(
                ConfigChangeEventDB.timestamp >= yesterday
            ).count()

            # Get high severity changes
            high_severity = db.query(ConfigChangeEventDB).filter(
                and_(
                    ConfigChangeEventDB.timestamp >= yesterday,
                    ConfigChangeEventDB.severity == "high"
                )
            ).count()

            # Get devices with baselines (count unique device IDs from change events)
            devices_with_baseline = db.query(ConfigChangeEventDB.device_id).distinct().count()

            return {
                "total_devices": total_devices,
                "devices_with_baseline": devices_with_baseline,
                "recent_changes_24h": recent_changes,
                "high_severity_changes_24h": high_severity,
                "last_scan": None  # TODO: Track last scan time
            }

        except Exception as e:
            logger.error(f"Failed to get drift summary: {str(e)}")
            return {
                "error": str(e)
            }

    @staticmethod
    def auto_detect_and_notify(db: Session):
        """
        Automatically detect drift and send notifications

        This can be called by a scheduled task
        """
        try:
            drifts = DriftDetectionService.detect_drift_for_all_devices(db)

            # Send notifications for detected drifts
            for drift in drifts:
                # Use the config change notification mechanism
                NotificationService.notify_config_change(
                    db=db,
                    device_id=drift["device_id"],
                    device_name=drift["device_name"],
                    lines_changed=drift["lines_changed"],
                    severity=drift["severity"]
                )

            logger.info(f"Auto drift detection complete: {len(drifts)} drifts found and notified")

        except Exception as e:
            logger.error(f"Auto drift detection failed: {str(e)}")
