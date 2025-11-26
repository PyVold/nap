"""
Remediation API - Auto-fix failed audit checks
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from api.deps import get_db, require_admin_or_operator
from services.remediation_service import RemediationService
from utils.logger import setup_logger

router = APIRouter(prefix="/remediation", tags=["Remediation"])
logger = setup_logger(__name__)


class RemediationRequest(BaseModel):
    device_ids: List[int]
    dry_run: bool = True
    re_audit: bool = True  # Re-audit after successful remediation


class RemediationResponse(BaseModel):
    success: bool
    dry_run: bool
    total_devices: int
    successful: int
    failed: int
    results: List[dict]


@router.post("/push", response_model=RemediationResponse)
async def push_remediation(
    request: RemediationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Push remediation configurations to devices based on failed audit checks

    **Requires**: admin or operator role

    **Process**:
    1. Fetches latest audit results for specified devices
    2. Identifies failed checks with expected_config
    3. Generates remediation configuration
    4. Creates pre-remediation backup
    5. Applies configuration (if dry_run=False)
    6. Returns results

    **Dry Run Mode** (default):
    - Validates configurations without applying
    - Safe to test remediation plans
    - Set dry_run=False to actually apply changes
    """
    try:
        result = await RemediationService.push_remediation_bulk(
            db=db,
            device_ids=request.device_ids,
            dry_run=request.dry_run,
            re_audit=request.re_audit
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remediation failed for all devices"
            )

        return result

    except Exception as e:
        logger.error(f"Remediation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Remediation failed: {str(e)}"
        )


@router.get("/status/{device_id}")
async def get_remediation_status(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Get remediation status/history for a device

    **Requires**: admin or operator role
    """
    from db_models import ConfigBackupDB

    # Get pre-remediation backups as indicator of remediation history
    backups = db.query(ConfigBackupDB).filter(
        ConfigBackupDB.device_id == device_id,
        ConfigBackupDB.backup_type == 'pre_remediation'
    ).order_by(ConfigBackupDB.timestamp.desc()).limit(10).all()

    return {
        "device_id": device_id,
        "remediation_count": len(backups),
        "last_remediation": backups[0].timestamp if backups else None,
        "history": [
            {
                "timestamp": b.timestamp,
                "triggered_by": b.triggered_by,
                "backup_id": b.id
            }
            for b in backups
        ]
    }
