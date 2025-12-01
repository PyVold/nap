# ============================================================================
# api/routes/device_import.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from api.deps import get_db
from services.device_import_service import DeviceImportService
from shared.license_middleware import require_license_module

router = APIRouter(prefix="/device-import", tags=["device-import"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list


class CSVImportRequest(BaseModel):
    csv_content: str
    update_existing: bool = False


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/template")
def download_import_template(_: None = Depends(require_license_module("devices"))):
    """Download a CSV template for bulk device import"""
    template_csv = DeviceImportService.generate_csv_template()

    return Response(
        content=template_csv,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=device_import_template.csv"
        }
    )


@router.post("/validate")
def validate_csv(
    csv_content: str,
    _: None = Depends(require_license_module("devices"))
):
    """Validate CSV content without importing"""
    devices, errors = DeviceImportService.parse_csv(csv_content)

    return {
        "valid": len(errors) == 0,
        "device_count": len(devices),
        "errors": errors,
        "devices": devices
    }


@router.post("/upload", response_model=ImportResult)
def upload_csv_file(
    file: UploadFile = File(...),
    update_existing: bool = False,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("devices"))
):
    """Upload and import devices from CSV file (enforces device quota)"""
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")

    try:
        # Read file content synchronously
        content = file.file.read()
        csv_content = content.decode('utf-8')

        # Parse CSV
        devices, parse_errors = DeviceImportService.parse_csv(csv_content)

        if parse_errors:
            return ImportResult(created=0, updated=0, errors=parse_errors)

        # Check quota before importing
        # Count how many NEW devices would be created (not updates)
        new_device_count = 0
        if not update_existing:
            # If not updating, all devices are new
            new_device_count = len(devices)
        else:
            # Count only devices that don't exist yet
            for device_data in devices:
                existing = db.query(DeviceDB).filter(
                    DeviceDB.hostname == device_data.get("hostname")
                ).first()
                if not existing:
                    new_device_count += 1

        # Enforce device quota
        from shared.license_middleware import license_enforcer
        quota_result = license_enforcer.check_quota(db, "devices", new_device_count)

        if not quota_result["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Device quota exceeded",
                    "message": f"Cannot import {new_device_count} new devices. "
                              f"Current: {quota_result['current']}/{quota_result['max']}. "
                              f"Available slots: {quota_result['max'] - quota_result['current']}. "
                              "Please upgrade your license to import more devices.",
                    "current": quota_result['current'],
                    "max": quota_result['max'],
                    "requested": new_device_count,
                    "action": "upgrade_license"
                }
            )

        # Import devices
        created, updated, import_errors = DeviceImportService.import_devices(
            db, devices, update_existing
        )

        # Update license usage after import
        from services.license_enforcement_service import license_enforcement_service
        license_enforcement_service.enforcer.update_license_usage(db)

        return ImportResult(
            created=created,
            updated=updated,
            errors=import_errors
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/csv", response_model=ImportResult)
def import_csv_content(
    request: CSVImportRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("devices"))
):
    """Import devices from CSV content (JSON payload, enforces device quota)"""
    try:
        # Parse CSV
        devices, parse_errors = DeviceImportService.parse_csv(request.csv_content)

        if parse_errors:
            return ImportResult(created=0, updated=0, errors=parse_errors)

        # Check quota before importing
        # Count how many NEW devices would be created (not updates)
        new_device_count = 0
        if not request.update_existing:
            # If not updating, all devices are new
            new_device_count = len(devices)
        else:
            # Count only devices that don't exist yet
            for device_data in devices:
                existing = db.query(DeviceDB).filter(
                    DeviceDB.hostname == device_data.get("hostname")
                ).first()
                if not existing:
                    new_device_count += 1

        # Enforce device quota
        from shared.license_middleware import license_enforcer
        quota_result = license_enforcer.check_quota(db, "devices", new_device_count)

        if not quota_result["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Device quota exceeded",
                    "message": f"Cannot import {new_device_count} new devices. "
                              f"Current: {quota_result['current']}/{quota_result['max']}. "
                              f"Available slots: {quota_result['max'] - quota_result['current']}. "
                              "Please upgrade your license to import more devices.",
                    "current": quota_result['current'],
                    "max": quota_result['max'],
                    "requested": new_device_count,
                    "action": "upgrade_license"
                }
            )

        # Import devices
        created, updated, import_errors = DeviceImportService.import_devices(
            db, devices, request.update_existing
        )

        # Update license usage after import
        from services.license_enforcement_service import license_enforcement_service
        license_enforcement_service.enforcer.update_license_usage(db)

        return ImportResult(
            created=created,
            updated=updated,
            errors=import_errors
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
def export_devices(
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("devices"))
):
    """Export all devices to CSV format"""
    try:
        csv_content = DeviceImportService.export_devices_to_csv(db)

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=devices_export.csv"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
