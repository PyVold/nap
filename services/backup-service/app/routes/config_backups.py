# ============================================================================
# api/routes/config_backups.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from shared.deps import get_db
from db_models import DeviceDB, ConfigBackupDB, ConfigChangeEventDB
from services.config_backup_service import ConfigBackupService
from models.device import Device
from models.enums import VendorType

router = APIRouter(prefix="/config-backups", tags=["config-backups"])


# ============================================================================
# Pydantic Models
# ============================================================================

class BackupResponse(BaseModel):
    id: int
    device_id: int
    config_hash: str
    backup_type: str
    timestamp: datetime
    triggered_by: Optional[str] = None
    size_bytes: Optional[int] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class BackupDetailResponse(BackupResponse):
    config_data: str


class ChangeEventResponse(BaseModel):
    id: int
    device_id: int
    timestamp: datetime  # Fixed: was detected_at, but DB field is timestamp
    change_type: str
    severity: str
    diff_text: Optional[str] = None

    class Config:
        from_attributes = True


class BackupCompareResponse(BaseModel):
    backup1: BackupResponse
    backup2: BackupResponse
    diff: str
    summary: dict


class CreateBackupRequest(BaseModel):
    device_id: int
    backup_type: str = "manual"
    created_by: Optional[str] = None


class DeviceBackupSummary(BaseModel):
    device_id: int
    device_name: str
    device_ip: Optional[str] = None
    vendor: str
    total_backups: int
    latest_backup: Optional[BackupResponse] = None
    oldest_backup: Optional[BackupResponse] = None

    class Config:
        from_attributes = True


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/", response_model=List[BackupResponse])
def list_all_backups(
    limit: int = Query(100, ge=1, le=500),
    device_id: Optional[int] = None,
    include_auto: bool = Query(False, description="Include auto/pre_remediation/pre_template backups"),
    db: Session = Depends(get_db)
):
    """
    List all configuration backups (optionally filtered by device)

    By default, excludes automatic backups (auto, pre_remediation, pre_template).
    Set include_auto=True to include all backup types.
    """
    try:
        query = db.query(ConfigBackupDB)

        # Filter out automatic backups by default
        if not include_auto:
            query = query.filter(
                ConfigBackupDB.backup_type.notin_(['auto', 'pre_remediation', 'pre_template'])
            )

        if device_id:
            query = query.filter(ConfigBackupDB.device_id == device_id)

        backups = query.order_by(desc(ConfigBackupDB.timestamp)).limit(limit).all()
        return backups

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/summary", response_model=List[DeviceBackupSummary])
def list_devices_with_backups(
    include_auto: bool = Query(False, description="Include auto/pre_remediation/pre_template backups in counts"),
    db: Session = Depends(get_db)
):
    """
    List all devices with their backup statistics (scalable device-per-device view)

    Returns a summary of each device with:
    - Total backup count
    - Latest backup info
    - Oldest backup info

    By default, excludes automatic backups from counts.
    Set include_auto=True to include all backup types.
    """
    try:
        from sqlalchemy import func

        # Get all devices
        devices = db.query(DeviceDB).all()

        result = []
        for device in devices:
            # Build query for this device's backups
            backup_query = db.query(ConfigBackupDB).filter(
                ConfigBackupDB.device_id == device.id
            )

            # Filter out automatic backups if requested
            if not include_auto:
                backup_query = backup_query.filter(
                    ConfigBackupDB.backup_type.notin_(['auto', 'pre_remediation', 'pre_template'])
                )

            # Get count
            total_backups = backup_query.count()

            # Get latest and oldest backups (may be None if no backups exist)
            latest_backup = backup_query.order_by(desc(ConfigBackupDB.timestamp)).first()
            oldest_backup = backup_query.order_by(ConfigBackupDB.timestamp).first()

            # Include all devices, even those with no backups
            result.append(DeviceBackupSummary(
                device_id=device.id,
                device_name=device.hostname,
                device_ip=device.ip,
                vendor=device.vendor.value if hasattr(device.vendor, 'value') else str(device.vendor),
                total_backups=total_backups,
                latest_backup=BackupResponse.model_validate(latest_backup) if latest_backup else None,
                oldest_backup=BackupResponse.model_validate(oldest_backup) if oldest_backup else None
            ))

        # Sort by device name
        result.sort(key=lambda x: x.device_name)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backup_id}", response_model=BackupDetailResponse)
def get_backup(
    backup_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific backup with full configuration data"""
    backup = db.query(ConfigBackupDB).filter(ConfigBackupDB.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")

    return backup


@router.post("/", response_model=BackupResponse)
def create_backup(
    request: CreateBackupRequest,
    db: Session = Depends(get_db)
):
    """Manually trigger a configuration backup for a device"""
    try:
        # Get device from database
        stmt = select(DeviceDB).where(DeviceDB.id == request.device_id)
        result = db.execute(stmt)
        device_db = result.scalar_one_or_none()

        if not device_db:
            raise HTTPException(status_code=404, detail=f"Device {request.device_id} not found")

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

        # Create backup using async method (run in event loop)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            backup = loop.run_until_complete(
                ConfigBackupService.backup_device(
                    db=db,
                    device=device,
                    backup_type=request.backup_type,
                    created_by=request.created_by
                )
            )
            return backup
        finally:
            loop.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/{device_id}/history", response_model=List[BackupResponse])
def get_device_backup_history(
    device_id: int,
    limit: int = Query(50, ge=1, le=200),
    include_auto: bool = Query(False, description="Include auto/pre_remediation/pre_template backups"),
    db: Session = Depends(get_db)
):
    """
    Get backup history for a specific device

    By default, excludes automatic backups (auto, pre_remediation, pre_template).
    Set include_auto=True to include all backup types.
    """
    try:
        query = db.query(ConfigBackupDB).filter(ConfigBackupDB.device_id == device_id)

        # Filter out automatic backups by default
        if not include_auto:
            query = query.filter(
                ConfigBackupDB.backup_type.notin_(['auto', 'pre_remediation', 'pre_template'])
            )

        backups = query.order_by(desc(ConfigBackupDB.timestamp)).limit(limit).all()
        return backups

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/{device_id}/changes", response_model=List[ChangeEventResponse])
def get_device_change_history(
    device_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get configuration change history for a device"""
    try:
        changes = db.query(ConfigChangeEventDB).filter(
            ConfigChangeEventDB.device_id == device_id
        ).order_by(desc(ConfigChangeEventDB.timestamp)).limit(limit).all()
        return changes

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare/{backup_id_1}/{backup_id_2}", response_model=BackupCompareResponse)
def compare_backups(
    backup_id_1: int,
    backup_id_2: int,
    db: Session = Depends(get_db)
):
    """Compare two configuration backups"""
    try:
        # Get both backups
        backup1 = db.query(ConfigBackupDB).filter(ConfigBackupDB.id == backup_id_1).first()
        backup2 = db.query(ConfigBackupDB).filter(ConfigBackupDB.id == backup_id_2).first()

        if not backup1:
            raise HTTPException(status_code=404, detail=f"Backup {backup_id_1} not found")
        if not backup2:
            raise HTTPException(status_code=404, detail=f"Backup {backup_id_2} not found")

        # Generate diff
        import difflib
        diff_lines = list(difflib.unified_diff(
            backup1.config_data.splitlines(keepends=True),
            backup2.config_data.splitlines(keepends=True),
            fromfile=f"backup_{backup_id_1}",
            tofile=f"backup_{backup_id_2}"
        ))
        diff = ''.join(diff_lines)

        # Calculate summary statistics
        lines_added = diff.count('\n+')
        lines_removed = diff.count('\n-')
        lines_changed = lines_added + lines_removed

        return BackupCompareResponse(
            backup1=BackupResponse.model_validate(backup1),
            backup2=BackupResponse.model_validate(backup2),
            diff=diff,
            summary={
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "lines_changed": lines_changed,
                "time_diff_seconds": (backup2.timestamp - backup1.timestamp).total_seconds()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{backup_id}")
def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db)
):
    """Delete a configuration backup"""
    try:
        backup = db.query(ConfigBackupDB).filter(ConfigBackupDB.id == backup_id).first()

        if not backup:
            raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")

        db.delete(backup)
        db.commit()

        return {"message": f"Backup {backup_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
