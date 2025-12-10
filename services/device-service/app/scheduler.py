# ============================================================================
# services/device-service/app/scheduler.py
# Background Scheduler for Device Service
# ============================================================================

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from sqlalchemy.orm import Session
from shared.database import SessionLocal
from shared.config import settings
from shared.logger import setup_logger
from services.discovery_group_service import DiscoveryGroupService
from services.device_service import DeviceService
from services.discovery_service import DiscoveryService
from services.health_service import HealthService
from shared.crypto import decrypt_password
from models.device import Device
from models.enums import VendorType

logger = setup_logger(__name__)

# Initialize services
discovery_group_service = DiscoveryGroupService()
device_service = DeviceService()
discovery_service = DiscoveryService()
health_service = HealthService()


async def run_scheduled_discoveries():
    """Check for and run scheduled discoveries"""
    db = SessionLocal()
    try:
        groups = discovery_group_service.get_scheduled_groups(db)
        if not groups:
            logger.debug("No scheduled discovery groups due to run")
            return
            
        logger.info(f"Found {len(groups)} discovery groups due to run")

        for group in groups:
            try:
                # Get decrypted password
                password = discovery_group_service.get_decrypted_password(db, group.id)

                # Run discovery
                logger.info(f"Running scheduled discovery for group: {group.name}")
                discovered = await discovery_service.discover_subnet(
                    subnet=group.subnet,
                    username=group.username,
                    password=password,
                    port=group.port,
                    excluded_ips=group.excluded_ips
                )

                # Merge discovered devices
                added_count, device_ids = device_service.merge_discovered_devices(db, discovered)

                # Collect metadata for discovered/updated devices
                if device_ids:
                    logger.info(f"Scheduled discovery '{group.name}': Collecting metadata for {len(device_ids)} devices")
                    await device_service.collect_metadata_for_discovered_devices(db, device_ids)

                # Update timestamps
                discovery_group_service.update_run_timestamps(db, group.id)

                logger.info(f"Scheduled discovery '{group.name}': found {len(discovered)}, added {added_count}")

            except Exception as e:
                logger.error(f"Error running scheduled discovery for group {group.id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in run_scheduled_discoveries: {str(e)}")
    finally:
        db.close()


async def run_health_checks():
    """Run health checks on all devices"""
    db = SessionLocal()
    try:
        # Get all devices
        devices_db = device_service.get_all_devices(db)
        
        if not devices_db:
            logger.debug("No devices found for health checks")
            return
            
        logger.info(f"Starting periodic health checks for {len(devices_db)} devices")

        # Convert to Device models - decrypt passwords for health checks
        devices = []
        for device_db in devices_db:
            try:
                # Decrypt password before passing to health service
                decrypted_pwd = decrypt_password(device_db.password) if device_db.password else None
                device = Device(
                    id=device_db.id,
                    hostname=device_db.hostname,
                    vendor=device_db.vendor,
                    ip=device_db.ip,
                    port=device_db.port,
                    username=device_db.username,
                    password=decrypted_pwd,
                    status=device_db.status
                )
                devices.append(device)
            except Exception as e:
                logger.error(f"Error converting device {device_db.hostname}: {str(e)}")

        # Run health checks with concurrency control (handled by health_service)
        if devices:
            results = await health_service.check_all_devices_health(db, devices)
            
            # Count statuses
            healthy = sum(1 for r in results if r.get('overall_status') == 'healthy')
            degraded = sum(1 for r in results if r.get('overall_status') == 'degraded')
            unreachable = sum(1 for r in results if r.get('overall_status') == 'unreachable')
            skipped = sum(1 for r in results if r.get('skipped', False))
            
            logger.info(f"Health checks completed: {len(results)} devices checked "
                       f"(healthy: {healthy}, degraded: {degraded}, unreachable: {unreachable}, skipped: {skipped})")

    except Exception as e:
        logger.error(f"Error in run_health_checks: {str(e)}")
        logger.exception("Health check exception details:")
    finally:
        db.close()


class DeviceServiceScheduler:
    """Background scheduler for device service periodic tasks"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Set up scheduled jobs"""
        
        # Check for scheduled discoveries every 2 minutes
        self.scheduler.add_job(
            run_scheduled_discoveries,
            trigger=IntervalTrigger(minutes=2),
            id='discovery_check',
            name='Check for scheduled discoveries',
            replace_existing=True
        )
        logger.info("Scheduled discovery check job configured (every 2 minutes)")

        # Run health checks at configured interval
        health_check_interval = getattr(settings, 'health_check_interval_minutes', 5)
        self.scheduler.add_job(
            run_health_checks,
            trigger=IntervalTrigger(minutes=health_check_interval),
            id='health_check',
            name='Run device health checks',
            replace_existing=True
        )
        logger.info(f"Health check scheduled every {health_check_interval} minutes")

        logger.info("Device service scheduler jobs configured")

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Device service background scheduler started")
        else:
            logger.warning("Scheduler already running")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Device service background scheduler stopped")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> DeviceServiceScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DeviceServiceScheduler()
    return _scheduler_instance
