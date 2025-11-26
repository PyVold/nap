# ============================================================================
# api/routes/audit_schedules.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.audit_schedule import AuditSchedule, AuditScheduleCreate, AuditScheduleUpdate
from services.audit_schedule_service import AuditScheduleService
from services.device_service import DeviceService
from services.device_group_service import DeviceGroupService
from services.rule_service import RuleService
from services.audit_service import AuditService
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

audit_schedule_service = AuditScheduleService()
device_service = DeviceService()
device_group_service = DeviceGroupService()
rule_service = RuleService()


@router.get("/", response_model=List[AuditSchedule])
async def get_all_audit_schedules(db: Session = Depends(get_db)):
    """Get all audit schedules"""
    return audit_schedule_service.get_all_schedules(db)


@router.get("/{schedule_id}", response_model=AuditSchedule)
async def get_audit_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Get a specific audit schedule by ID"""
    schedule = audit_schedule_service.get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit schedule with ID {schedule_id} not found"
        )
    return schedule


@router.post("/", response_model=AuditSchedule, status_code=status.HTTP_201_CREATED)
async def create_audit_schedule(
    schedule_create: AuditScheduleCreate,
    db: Session = Depends(get_db)
):
    """Create a new audit schedule"""
    try:
        return audit_schedule_service.create_schedule(db, schedule_create)
    except Exception as e:
        logger.error(f"Error creating audit schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{schedule_id}", response_model=AuditSchedule)
async def update_audit_schedule(
    schedule_id: int,
    schedule_update: AuditScheduleUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing audit schedule"""
    try:
        return audit_schedule_service.update_schedule(db, schedule_id, schedule_update)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating audit schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete an audit schedule"""
    try:
        audit_schedule_service.delete_schedule(db, schedule_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{schedule_id}/run")
async def run_audit_schedule_now(
    schedule_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run an audit schedule immediately"""
    schedule = audit_schedule_service.get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit schedule with ID {schedule_id} not found"
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No devices found to audit"
        )

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

    # Run audit in background
    async def run_audit_task():
        from database import SessionLocal
        from engine.audit_engine import AuditEngine
        task_db = SessionLocal()
        try:
            audit_engine = AuditEngine()
            from services.audit_service import AuditService
            task_audit_service = AuditService(audit_engine)
            await task_audit_service.execute_audit(task_db, devices, rules)
            audit_schedule_service.update_run_timestamps(task_db, schedule_id)
            logger.info(f"Audit schedule {schedule_id} completed: {len(devices)} devices, {len(rules)} rules")
        except Exception as e:
            logger.error(f"Audit schedule {schedule_id} failed: {str(e)}")
        finally:
            task_db.close()

    background_tasks.add_task(run_audit_task)

    return {
        "status": "started",
        "message": f"Audit started for schedule '{schedule.name}'",
        "devices": len(devices),
        "rules": len(rules)
    }
