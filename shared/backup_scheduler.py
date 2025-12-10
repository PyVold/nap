"""
Backup Scheduler Service

Handles scheduling of automatic configuration backups based on admin settings.
Uses APScheduler for flexible scheduling.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages automatic backup scheduling"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone='UTC',
            job_defaults={
                'coalesce': True,  # Combine missed jobs
                'max_instances': 1,  # Only one instance of each job
                'misfire_grace_time': 300  # 5 minutes grace period
            }
        )
        self.scheduler.start()
        logger.info("Backup scheduler started")

    def load_and_update_schedule(self, db: Session):
        """Load backup configuration from database and update schedule"""
        try:
            # Try local db_models first (service-specific), fall back to shared
            try:
                from db_models import SystemConfigDB
            except ImportError:
                from shared.db_models import SystemConfigDB

            # Get backup configuration
            config = db.query(SystemConfigDB).filter(
                SystemConfigDB.key == "backup_config"
            ).first()

            if not config:
                logger.warning("No backup configuration found")
                return

            backup_config = json.loads(config.value)

            # Remove existing backup jobs
            self.scheduler.remove_all_jobs()

            if not backup_config.get('enabled', True):
                logger.info("Automatic backups are disabled")
                return

            # Schedule based on configuration
            schedule_type = backup_config.get('scheduleType', 'daily')
            schedule_time = backup_config.get('scheduleTime', '02:00')

            hour, minute = map(int, schedule_time.split(':'))

            if schedule_type == 'hourly':
                # Every hour
                self.scheduler.add_job(
                    self.run_backup_job,
                    trigger=IntervalTrigger(hours=1),
                    id='config_backup',
                    args=[db],
                    name='Hourly Config Backup'
                )
                logger.info("Scheduled hourly backups")

            elif schedule_type == 'every6hours':
                # Every 6 hours
                self.scheduler.add_job(
                    self.run_backup_job,
                    trigger=IntervalTrigger(hours=6),
                    id='config_backup',
                    args=[db],
                    name='6-Hour Config Backup'
                )
                logger.info("Scheduled backups every 6 hours")

            elif schedule_type == 'every12hours':
                # Every 12 hours
                self.scheduler.add_job(
                    self.run_backup_job,
                    trigger=IntervalTrigger(hours=12),
                    id='config_backup',
                    args=[db],
                    name='12-Hour Config Backup'
                )
                logger.info("Scheduled backups every 12 hours")

            elif schedule_type == 'daily':
                # Once per day at specified time
                self.scheduler.add_job(
                    self.run_backup_job,
                    trigger=CronTrigger(hour=hour, minute=minute),
                    id='config_backup',
                    args=[db],
                    name='Daily Config Backup'
                )
                logger.info(f"Scheduled daily backups at {schedule_time}")

            elif schedule_type == 'weekly':
                # Once per week on Sunday at specified time
                self.scheduler.add_job(
                    self.run_backup_job,
                    trigger=CronTrigger(day_of_week='sun', hour=hour, minute=minute),
                    id='config_backup',
                    args=[db],
                    name='Weekly Config Backup'
                )
                logger.info(f"Scheduled weekly backups on Sunday at {schedule_time}")

            elif schedule_type == 'monthly':
                # Once per month on the 1st at specified time
                self.scheduler.add_job(
                    self.run_backup_job,
                    trigger=CronTrigger(day=1, hour=hour, minute=minute),
                    id='config_backup',
                    args=[db],
                    name='Monthly Config Backup'
                )
                logger.info(f"Scheduled monthly backups on the 1st at {schedule_time}")

            else:
                logger.error(f"Unknown schedule type: {schedule_type}")

        except Exception as e:
            logger.error(f"Error loading backup schedule: {e}")

    def run_backup_job(self, db: Session):
        """Execute backup job for all devices"""
        try:
            # Try local db_models first (service-specific), fall back to shared
            try:
                from db_models import DeviceDB, ConfigBackupDB, SystemConfigDB
            except ImportError:
                from shared.db_models import DeviceDB, ConfigBackupDB, SystemConfigDB
            from shared.notification_service import notification_service

            logger.info("Starting scheduled backup job...")

            # Get backup configuration
            config = db.query(SystemConfigDB).filter(
                SystemConfigDB.key == "backup_config"
            ).first()

            if not config:
                logger.error("Backup config not found")
                return

            backup_config = json.loads(config.value)

            # Get all devices - deleted devices are removed from DB, not marked
            # Only backup devices that are reachable (ONLINE or DEGRADED)
            try:
                from models.enums import DeviceStatus
            except ImportError:
                from shared.models.enums import DeviceStatus
            devices = db.query(DeviceDB).filter(
                DeviceDB.status.in_([DeviceStatus.ONLINE, DeviceStatus.DEGRADED, DeviceStatus.REGISTERED])
            ).all()

            logger.info(f"Backing up {len(devices)} devices")

            success_count = 0
            failure_count = 0
            failed_devices = []

            for device in devices:
                try:
                    # Call backup service to create backup
                    # This would normally call the actual backup creation logic
                    result = self.create_device_backup(device, backup_config, db)

                    if result['success']:
                        success_count += 1
                    else:
                        failure_count += 1
                        failed_devices.append((device.hostname, result.get('error', 'Unknown error')))

                        # Send notification if enabled
                        if backup_config.get('notifyOnFailure', True):
                            notification_service.send_backup_failure_notification(
                                device.hostname,
                                result.get('error', 'Unknown error'),
                                db
                            )

                except Exception as e:
                    logger.error(f"Error backing up device {device.hostname}: {e}")
                    failure_count += 1
                    failed_devices.append((device.hostname, str(e)))

            logger.info(f"Backup job completed: {success_count} success, {failure_count} failed")

            # Clean up old backups based on retention settings
            self.cleanup_old_backups(backup_config, db)

        except Exception as e:
            logger.error(f"Error in backup job: {e}")

    def create_device_backup(self, device, backup_config, db: Session):
        """
        Create a configuration backup for a device by calling the backup-service API
        """
        import httpx
        import os

        try:
            # Get backup service URL from environment or use default
            backup_service_url = os.environ.get('BACKUP_SERVICE_URL', 'http://backup-service:3003')

            # Call the backup-service API to create a real backup
            with httpx.Client(timeout=120.0) as client:  # 2 min timeout for slow devices
                response = client.post(
                    f"{backup_service_url}/config-backups/",
                    json={
                        "device_id": device.id,
                        "backup_type": "scheduled",
                        "notes": "Automatic scheduled backup"
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Created backup for device: {device.hostname} (backup_id: {result.get('id')})")
                    return {
                        "success": True,
                        "backup_id": result.get('id')
                    }
                else:
                    error_detail = response.json().get('detail', response.text)
                    logger.error(f"Backup failed for {device.hostname}: {error_detail}")
                    return {
                        "success": False,
                        "error": error_detail
                    }

        except httpx.TimeoutException:
            logger.error(f"Timeout creating backup for {device.hostname}")
            return {
                "success": False,
                "error": "Timeout connecting to device"
            }
        except Exception as e:
            logger.error(f"Error creating backup for {device.hostname}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def cleanup_old_backups(self, backup_config, db: Session):
        """
        Clean up old backups based on retention settings
        """
        try:
            # Try local db_models first (service-specific), fall back to shared
            try:
                from db_models import ConfigBackupDB, DeviceDB
            except ImportError:
                from shared.db_models import ConfigBackupDB, DeviceDB

            retention_days = backup_config.get('retentionDays', 30)
            max_backups_per_device = backup_config.get('maxBackupsPerDevice', 10)

            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Delete backups older than retention period
            deleted = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.timestamp < cutoff_date
            ).delete()

            if deleted > 0:
                logger.info(f"Deleted {deleted} backups older than {retention_days} days")

            # Keep only N most recent backups per device
            devices = db.query(DeviceDB).all()

            for device in devices:
                # Get all backups for this device, ordered by date (newest first)
                backups = db.query(ConfigBackupDB).filter(
                    ConfigBackupDB.device_id == device.id
                ).order_by(
                    ConfigBackupDB.timestamp.desc()
                ).all()

                # If more than max, delete the oldest ones
                if len(backups) > max_backups_per_device:
                    to_delete = backups[max_backups_per_device:]
                    for backup in to_delete:
                        db.delete(backup)
                    logger.info(f"Deleted {len(to_delete)} old backups for device {device.hostname}")

            db.commit()

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def get_next_run_time(self):
        """Get the next scheduled backup run time"""
        jobs = self.scheduler.get_jobs()
        if jobs:
            return jobs[0].next_run_time
        return None

    def shutdown(self):
        """Shut down the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Backup scheduler shutdown")


# Singleton instance
backup_scheduler = BackupScheduler()
