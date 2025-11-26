# ============================================================================
# api/routes/drift_detection.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from shared.deps import get_db
from db_models import DeviceDB
from models.device import Device
from models.enums import VendorType
from services.drift_detection_service import DriftDetectionService

router = APIRouter(prefix="/drift-detection", tags=["drift-detection"])


# ============================================================================
# Pydantic Models
# ============================================================================

class DriftInfo(BaseModel):
    device_id: int
    device_name: str
    baseline_backup_id: int
    current_backup_id: int
    baseline_timestamp: str
    current_timestamp: str
    lines_changed: int
    severity: str


class DriftInfoDetailed(DriftInfo):
    diff: str


class SetBaselineRequest(BaseModel):
    backup_id: Optional[int] = None


class DriftSummary(BaseModel):
    total_devices: int
    devices_with_baseline: int
    recent_changes_24h: int
    high_severity_changes_24h: int
    last_scan: Optional[str]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/summary", response_model=DriftSummary)
def get_drift_summary(db: Session = Depends(get_db)):
    """Get drift detection summary statistics"""
    summary = DriftDetectionService.get_drift_summary(db)
    return summary


@router.get("/scan", response_model=List[DriftInfo])
def scan_all_devices(db: Session = Depends(get_db)):
    """Scan all devices for configuration drift"""
    drifts = DriftDetectionService.detect_drift_for_all_devices(db)

    # Return without diff for list view
    return [
        {
            "device_id": d["device_id"],
            "device_name": d["device_name"],
            "baseline_backup_id": d["baseline_backup_id"],
            "current_backup_id": d["current_backup_id"],
            "baseline_timestamp": d["baseline_timestamp"],
            "current_timestamp": d["current_timestamp"],
            "lines_changed": d["lines_changed"],
            "severity": d["severity"]
        }
        for d in drifts
    ]


@router.get("/device/{device_id}", response_model=Optional[DriftInfoDetailed])
def detect_drift_for_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Detect configuration drift for a specific device"""
    # Get device from database
    device_db = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()

    if not device_db:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Convert to Device model
    device = Device(
        id=device_db.id,
        hostname=device_db.hostname,
        vendor=VendorType(device_db.vendor),
        ip=device_db.ip,
        port=device_db.port,
        username=device_db.username,
        password=device_db.password
    )

    # Detect drift
    drift_info = DriftDetectionService.detect_drift_for_device(db, device)

    if not drift_info:
        return None

    return drift_info


@router.post("/device/{device_id}/baseline")
def set_baseline(
    device_id: int,
    request: SetBaselineRequest,
    db: Session = Depends(get_db)
):
    """Set a configuration backup as the baseline for drift detection"""
    # Verify device exists
    device_db = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()

    if not device_db:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Set baseline
    success = DriftDetectionService.set_baseline(db, device_id, request.backup_id)

    if not success:
        raise HTTPException(status_code=400, detail=f"Backup not found for device {device_id}. Please create a config backup first.")

    return {
        "message": f"Baseline set for device {device_id}",
        "device_id": device_id,
        "backup_id": request.backup_id
    }


@router.post("/auto-scan")
def trigger_auto_scan(db: Session = Depends(get_db)):
    """Trigger automatic drift detection and notifications"""
    try:
        DriftDetectionService.auto_detect_and_notify(db)
        return {"message": "Auto drift detection completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
