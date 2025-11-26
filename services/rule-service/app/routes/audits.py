# ============================================================================
# api/routes/audits.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db, SessionLocal
from models.audit import AuditRequest, AuditResult
from services.device_service import DeviceService
from services.rule_service import RuleService
from services.audit_service import AuditService
from engine.audit_engine import AuditEngine
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

device_service = DeviceService()
rule_service = RuleService()
audit_engine = AuditEngine()
audit_service = AuditService(audit_engine)

async def execute_audit_background(devices: List, rules: List):
    """Background task to execute audit - creates its own database session"""
    db = SessionLocal()
    try:
        await audit_service.execute_audit(db, devices, rules)
    except Exception as e:
        logger.error(f"Background audit task failed: {e}")
    finally:
        db.close()

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def run_audit(
    audit_request: AuditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute audit on specified devices with specified rules"""

    # Determine which devices to audit
    if audit_request.device_ids:
        devices = [
            device_service.get_device_by_id(db, did)
            for did in audit_request.device_ids
        ]
        devices = [d for d in devices if d is not None]
    else:
        devices = device_service.get_all_devices(db)

    if not devices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No devices to audit"
        )

    # Determine which rules to use
    if audit_request.rule_ids:
        rules = [
            rule_service.get_rule_by_id(db, rid)
            for rid in audit_request.rule_ids
        ]
        rules = [r for r in rules if r is not None]
    else:
        rules = rule_service.get_enabled_rules(db)

    if not rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rules to execute"
        )

    # Start audit in background - note we don't pass db session
    background_tasks.add_task(
        execute_audit_background,
        devices,
        rules
    )

    return {
        "status": "started",
        "device_count": len(devices),
        "rule_count": len(rules),
        "message": "Audit started in background"
    }

@router.get("/results", response_model=List[AuditResult])
async def get_audit_results(
    latest_only: bool = True,  # Default to latest per device for scalability
    db: Session = Depends(get_db)
):
    """
    Get audit results

    By default (latest_only=true), returns only the latest result per device for scalability.
    Set latest_only=false to get all audit results (may be slow with many devices).
    """
    if latest_only:
        return audit_service.get_latest_results_per_device(db)
    else:
        return audit_service.get_all_results(db)

@router.get("/results/{device_id}", response_model=AuditResult)
async def get_device_audit_result(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Get latest audit result for a specific device"""
    result = audit_service.get_latest_result_by_device(db, device_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit results found for device {device_id}"
        )
    return result

@router.get("/results/{device_id}/history", response_model=List[AuditResult])
async def get_device_audit_history(
    device_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get audit history for a specific device (latest N results)"""
    results = audit_service.get_results_by_device(db, device_id)
    # Limit to N most recent results
    return results[:limit] if results else []

@router.get("/compliance")
async def get_compliance_summary(db: Session = Depends(get_db)):
    """Get overall compliance summary"""
    return audit_service.get_compliance_summary(db)

@router.delete("/results/cleanup")
async def cleanup_old_results(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Clean up audit results older than specified days"""
    removed = audit_service.clear_old_results(db, days)
    return {
        "status": "success",
        "removed": removed,
        "message": f"Removed {removed} audit results older than {days} days"
    }
