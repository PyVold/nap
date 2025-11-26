# ============================================================================
# services/audit_schedule_service.py
# ============================================================================

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.audit_schedule import AuditSchedule, AuditScheduleCreate, AuditScheduleUpdate
from db_models import AuditScheduleDB
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AuditScheduleService:
    """Service for audit schedule management operations"""

    def get_all_schedules(self, db: Session) -> List[AuditSchedule]:
        """Get all audit schedules"""
        db_schedules = db.query(AuditScheduleDB).all()
        return [self._to_pydantic(s) for s in db_schedules]

    def get_schedule_by_id(self, db: Session, schedule_id: int) -> Optional[AuditSchedule]:
        """Get audit schedule by ID"""
        db_schedule = db.query(AuditScheduleDB).filter(AuditScheduleDB.id == schedule_id).first()
        return self._to_pydantic(db_schedule) if db_schedule else None

    def create_schedule(self, db: Session, schedule_create: AuditScheduleCreate) -> AuditSchedule:
        """Create a new audit schedule"""
        db_schedule = AuditScheduleDB(
            name=schedule_create.name,
            description=schedule_create.description,
            device_group_id=schedule_create.device_group_id,
            device_ids=schedule_create.device_ids,
            rule_ids=schedule_create.rule_ids,
            schedule_enabled=schedule_create.schedule_enabled,
            cron_expression=schedule_create.cron_expression,
            schedule_interval=schedule_create.schedule_interval,
            active=True
        )

        # Calculate next_run if schedule is enabled
        if schedule_create.schedule_enabled:
            db_schedule.next_run = self._calculate_next_run(db_schedule)

        db.add(db_schedule)
        db.commit()
        db.refresh(db_schedule)

        logger.info(f"Created audit schedule: {db_schedule.name} (ID: {db_schedule.id})")
        return self._to_pydantic(db_schedule)

    def update_schedule(self, db: Session, schedule_id: int, schedule_update: AuditScheduleUpdate) -> AuditSchedule:
        """Update an existing audit schedule"""
        db_schedule = db.query(AuditScheduleDB).filter(AuditScheduleDB.id == schedule_id).first()
        if not db_schedule:
            raise ValueError(f"Audit schedule with ID {schedule_id} not found")

        update_data = schedule_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_schedule, field, value)

        # Recalculate next_run if schedule settings changed
        if any(key in update_data for key in ['schedule_enabled', 'cron_expression', 'schedule_interval']):
            if db_schedule.schedule_enabled:
                db_schedule.next_run = self._calculate_next_run(db_schedule)
            else:
                db_schedule.next_run = None

        db_schedule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_schedule)

        logger.info(f"Updated audit schedule: {db_schedule.name} (ID: {db_schedule.id})")
        return self._to_pydantic(db_schedule)

    def delete_schedule(self, db: Session, schedule_id: int) -> bool:
        """Delete an audit schedule"""
        db_schedule = db.query(AuditScheduleDB).filter(AuditScheduleDB.id == schedule_id).first()
        if not db_schedule:
            raise ValueError(f"Audit schedule with ID {schedule_id} not found")

        db.delete(db_schedule)
        db.commit()

        logger.info(f"Deleted audit schedule ID: {schedule_id}")
        return True

    def get_due_schedules(self, db: Session) -> List[AuditSchedule]:
        """Get schedules that are due to run"""
        now = datetime.utcnow()
        db_schedules = db.query(AuditScheduleDB).filter(
            AuditScheduleDB.schedule_enabled == True,
            AuditScheduleDB.active == True,
            AuditScheduleDB.next_run <= now
        ).all()
        return [self._to_pydantic(s) for s in db_schedules]

    def update_run_timestamps(self, db: Session, schedule_id: int):
        """Update last_run and next_run timestamps after audit execution"""
        db_schedule = db.query(AuditScheduleDB).filter(AuditScheduleDB.id == schedule_id).first()
        if db_schedule:
            db_schedule.last_run = datetime.utcnow()
            if db_schedule.schedule_enabled:
                db_schedule.next_run = self._calculate_next_run(db_schedule)
            db.commit()

    def _calculate_next_run(self, schedule: AuditScheduleDB) -> datetime:
        """Calculate the next run time based on schedule configuration"""
        now = datetime.utcnow()

        if schedule.schedule_interval:
            # Simple interval-based scheduling
            return now + timedelta(minutes=schedule.schedule_interval)

        elif schedule.cron_expression:
            # For cron expressions, we'd need croniter library
            # For now, default to 1 hour
            return now + timedelta(hours=1)

        else:
            # Default to 24 hours if no schedule is set
            return now + timedelta(hours=24)

    def _to_pydantic(self, db_schedule: AuditScheduleDB) -> AuditSchedule:
        """Convert SQLAlchemy model to Pydantic model"""
        return AuditSchedule(
            id=db_schedule.id,
            name=db_schedule.name,
            description=db_schedule.description,
            device_group_id=db_schedule.device_group_id,
            device_ids=db_schedule.device_ids,
            rule_ids=db_schedule.rule_ids,
            schedule_enabled=db_schedule.schedule_enabled,
            cron_expression=db_schedule.cron_expression,
            schedule_interval=db_schedule.schedule_interval,
            last_run=db_schedule.last_run.isoformat() if db_schedule.last_run else None,
            next_run=db_schedule.next_run.isoformat() if db_schedule.next_run else None,
            active=db_schedule.active,
            created_at=db_schedule.created_at.isoformat() if db_schedule.created_at else None,
            updated_at=db_schedule.updated_at.isoformat() if db_schedule.updated_at else None
        )
