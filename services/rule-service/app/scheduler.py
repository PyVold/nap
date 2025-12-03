# ============================================================================
# services/rule-service/app/scheduler.py
# Background Scheduler for Rule Service (Audit Scheduling)
# ============================================================================

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from sqlalchemy.orm import Session
from shared.database import SessionLocal
from shared.config import settings
from shared.logger import setup_logger
from services.audit_schedule_service import AuditScheduleService
from services.device_service import DeviceService
from services.device_group_service import DeviceGroupService
from services.rule_service import RuleService
from services.audit_service import AuditService
from engines.audit_engine import AuditEngine

logger = setup_logger(__name__)

# Initialize services
audit_schedule_service = AuditScheduleService()
device_service = DeviceService()
device_group_service = DeviceGroupService()
rule_service = RuleService()


async def run_scheduled_audits():
    """Check for and run scheduled audits"""
    db = SessionLocal()
    try:
        schedules = audit_schedule_service.get_due_schedules(db)

        if not schedules:
            logger.debug("No scheduled audits due to run")
            return

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
                    # Still update timestamps to prevent repeated warnings
                    audit_schedule_service.update_run_timestamps(db, schedule.id)
                    continue

                # Get devices
                devices = [device_service.get_device_by_id(db, did) for did in device_ids]
                devices = [d for d in devices if d is not None]

                if not devices:
                    logger.warning(f"Audit schedule '{schedule.name}': no valid devices found")
                    audit_schedule_service.update_run_timestamps(db, schedule.id)
                    continue

                # Determine which rules to use
                if schedule.rule_ids:
                    rules = [rule_service.get_rule_by_id(db, rid) for rid in schedule.rule_ids]
                    rules = [r for r in rules if r is not None]
                else:
                    # Use all enabled rules
                    rules = rule_service.get_enabled_rules(db)

                if not rules:
                    logger.warning(f"Audit schedule '{schedule.name}': no rules found")
                    audit_schedule_service.update_run_timestamps(db, schedule.id)
                    continue

                logger.info(f"Running audit for schedule: {schedule.name} ({len(devices)} devices, {len(rules)} rules)")

                # Run audit
                audit_engine = AuditEngine()
                audit_service_instance = AuditService(audit_engine)
                await audit_service_instance.execute_audit(db, devices, rules)

                # Update timestamps
                audit_schedule_service.update_run_timestamps(db, schedule.id)

                logger.info(f"Audit schedule '{schedule.name}' completed successfully")

            except Exception as e:
                logger.error(f"Error running audit schedule '{schedule.name}' (ID: {schedule.id}): {str(e)}")
                logger.exception("Audit schedule exception details:")
                # Still update timestamp to prevent stuck schedules
                try:
                    audit_schedule_service.update_run_timestamps(db, schedule.id)
                except Exception as update_error:
                    logger.error(f"Failed to update timestamp for schedule {schedule.id}: {str(update_error)}")

    except Exception as e:
        logger.error(f"Error in run_scheduled_audits: {str(e)}")
        logger.exception("Scheduled audits exception details:")
    finally:
        db.close()


class RuleServiceScheduler:
    """Background scheduler for rule service periodic tasks"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Set up scheduled jobs"""

        # Check for scheduled audits every 1 minute
        # This checks which audits are due based on their next_run timestamp
        self.scheduler.add_job(
            run_scheduled_audits,
            trigger=IntervalTrigger(minutes=1),
            id='audit_check',
            name='Check for scheduled audits',
            replace_existing=True
        )
        logger.info("Scheduled audit check job configured (every 1 minute)")

        logger.info("Rule service scheduler jobs configured")

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Rule service background scheduler started")
        else:
            logger.warning("Scheduler already running")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Rule service background scheduler stopped")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> RuleServiceScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RuleServiceScheduler()
    return _scheduler_instance
