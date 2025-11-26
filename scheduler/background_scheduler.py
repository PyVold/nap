# ============================================================================
# scheduler/background_scheduler.py
# ============================================================================

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from database import SessionLocal
from services.discovery_group_service import DiscoveryGroupService
from services.device_service import DeviceService
from services.discovery_service import DiscoveryService
from services.audit_schedule_service import AuditScheduleService
from services.device_group_service import DeviceGroupService
from services.rule_service import RuleService
from services.audit_service import AuditService
from services.health_service import HealthService
from services.config_backup_service import ConfigBackupService
from engine.audit_engine import AuditEngine
from models.device import Device
from models.enums import VendorType
from utils.logger import setup_logger
from config import settings

logger = setup_logger(__name__)

# Initialize services
discovery_group_service = DiscoveryGroupService()
device_service = DeviceService()
discovery_service = DiscoveryService()
audit_schedule_service = AuditScheduleService()
device_group_service = DeviceGroupService()
rule_service = RuleService()
health_service = HealthService()


async def run_scheduled_discoveries():
    """Check for and run scheduled discoveries"""
    db = SessionLocal()
    try:
        groups = discovery_group_service.get_scheduled_groups(db)
        logger.info(f"Found {len(groups)} discovery groups due to run")

        for group in groups:
            try:
                # Get decrypted password
                password = discovery_group_service.get_decrypted_password(db, group.id)

                # Run discovery
                logger.info(f"Running discovery for group: {group.name}")
                discovered = await discovery_service.discover_subnet(
                    subnet=group.subnet,
                    username=group.username,
                    password=password,
                    port=group.port,
                    excluded_ips=group.excluded_ips
                )

                # Merge discovered devices
                added_count = device_service.merge_discovered_devices(db, discovered)

                # Update timestamps
                discovery_group_service.update_run_timestamps(db, group.id)

                logger.info(f"Discovery group '{group.name}': found {len(discovered)}, added {added_count}")

            except Exception as e:
                logger.error(f"Error running discovery for group {group.id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in run_scheduled_discoveries: {str(e)}")
    finally:
        db.close()


async def run_scheduled_audits():
    """Check for and run scheduled audits"""
    db = SessionLocal()
    try:
        schedules = audit_schedule_service.get_due_schedules(db)
        logger.info(f"Found {len(schedules)} audit schedules due to run")

        for schedule in schedules:
            try:
                # Determine which devices to audit
                device_ids = []
                if schedule.device_group_id:
                    device_ids = device_group_service.get_group_devices(db, schedule.device_group_id)
                elif schedule.device_ids:
                    device_ids = schedule.device_ids
                else:
                    # All devices
                    all_devices = device_service.get_all_devices(db)
                    device_ids = [d.id for d in all_devices]

                if not device_ids:
                    logger.warning(f"Audit schedule '{schedule.name}': no devices found")
                    continue

                # Get devices
                devices = [device_service.get_device_by_id(db, did) for did in device_ids]
                devices = [d for d in devices if d is not None]

                # Determine which rules to use
                if schedule.rule_ids:
                    rules = [rule_service.get_rule_by_id(db, rid) for rid in schedule.rule_ids]
                    rules = [r for r in rules if r is not None]
                else:
                    # Use all enabled rules
                    rules = rule_service.get_enabled_rules(db)

                logger.info(f"Running audit for schedule: {schedule.name} ({len(devices)} devices, {len(rules)} rules)")

                # Run audit
                audit_engine = AuditEngine()
                audit_service = AuditService(audit_engine)
                await audit_service.execute_audit(db, devices, rules)

                # Update timestamps
                audit_schedule_service.update_run_timestamps(db, schedule.id)

                logger.info(f"Audit schedule '{schedule.name}' completed successfully")

            except Exception as e:
                logger.error(f"Error running audit schedule {schedule.id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in run_scheduled_audits: {str(e)}")
    finally:
        db.close()


async def run_health_checks():
    """Run health checks on all devices"""
    if not settings.health_check_enabled:
        return

    db = SessionLocal()
    try:
        # Get all devices
        devices_db = device_service.get_all_devices(db)
        logger.info(f"Running health checks for {len(devices_db)} devices")

        # Convert to Device models
        devices = []
        for device_db in devices_db:
            try:
                device = Device(
                    id=device_db.id,
                    hostname=device_db.hostname,
                    vendor=VendorType(device_db.vendor),
                    ip=device_db.ip,
                    port=device_db.port,
                    username=device_db.username,
                    password=device_db.password
                )
                devices.append(device)
            except Exception as e:
                logger.error(f"Error converting device {device_db.hostname}: {str(e)}")

        # Run health checks
        if devices:
            results = await health_service.check_all_devices_health(db, devices)
            logger.info(f"Health checks completed: {len(results)} devices checked")

    except Exception as e:
        logger.error(f"Error in run_health_checks: {str(e)}")
    finally:
        db.close()


async def run_config_backups():
    """Run automated config backups on all devices"""
    if not settings.config_backup_enabled:
        return

    db = SessionLocal()
    try:
        # Get all devices
        devices_db = device_service.get_all_devices(db)
        logger.info(f"Running config backups for {len(devices_db)} devices")

        # Convert to Device models and backup each device
        backup_count = 0
        for device_db in devices_db:
            try:
                device = Device(
                    id=device_db.id,
                    hostname=device_db.hostname,
                    vendor=VendorType(device_db.vendor),
                    ip=device_db.ip,
                    port=device_db.port,
                    username=device_db.username,
                    password=device_db.password
                )

                # Create backup
                backup = await ConfigBackupService.backup_device(
                    db=db,
                    device=device,
                    backup_type='auto',
                    created_by='scheduler'
                )

                if backup:
                    backup_count += 1
                    logger.info(f"Backup created for device: {device.hostname}")

            except Exception as e:
                logger.exception(f"Error backing up device {device_db.hostname}: {str(e)}")

        logger.info(f"Config backups completed: {backup_count}/{len(devices_db)} devices backed up")

    except Exception as e:
        logger.error(f"Error in run_config_backups: {str(e)}")
    finally:
        db.close()


class BackgroundScheduler:
    """Background scheduler for running periodic tasks"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Set up scheduled jobs"""
        # Check for scheduled discoveries every minute
        self.scheduler.add_job(
            run_scheduled_discoveries,
            trigger=IntervalTrigger(minutes=1),
            id='discovery_check',
            name='Check for scheduled discoveries',
            replace_existing=True
        )

        # Check for scheduled audits every minute
        self.scheduler.add_job(
            run_scheduled_audits,
            trigger=IntervalTrigger(minutes=1),
            id='audit_check',
            name='Check for scheduled audits',
            replace_existing=True
        )

        # Run health checks at configured interval
        if settings.health_check_enabled:
            self.scheduler.add_job(
                run_health_checks,
                trigger=IntervalTrigger(minutes=settings.health_check_interval_minutes),
                id='health_check',
                name='Run device health checks',
                replace_existing=True
            )
            logger.info(f"Health check scheduled every {settings.health_check_interval_minutes} minutes")

        # Run config backups at configured interval
        if settings.config_backup_enabled:
            self.scheduler.add_job(
                run_config_backups,
                trigger=IntervalTrigger(minutes=settings.config_backup_interval_minutes),
                id='config_backup',
                name='Run automated config backups',
                replace_existing=True
            )
            logger.info(f"Config backup scheduled every {settings.config_backup_interval_minutes} minutes")

        logger.info("Background scheduler jobs configured")

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Background scheduler started")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Background scheduler stopped")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundScheduler()
    return _scheduler_instance
