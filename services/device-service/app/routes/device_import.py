# ============================================================================
# api/routes/device_import.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from shared.deps import get_db
from services.device_import_service import DeviceImportService

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
def download_import_template():
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
def validate_csv(csv_content: str):
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
    db: Session = Depends(get_db)
):
    """Upload and import devices from CSV file"""
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

        # Import devices
        created, updated, import_errors = DeviceImportService.import_devices(
            db, devices, update_existing
        )

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
    db: Session = Depends(get_db)
):
    """Import devices from CSV content (JSON payload)"""
    try:
        # Parse CSV
        devices, parse_errors = DeviceImportService.parse_csv(request.csv_content)

        if parse_errors:
            return ImportResult(created=0, updated=0, errors=parse_errors)

        # Import devices
        created, updated, import_errors = DeviceImportService.import_devices(
            db, devices, request.update_existing
        )

        return ImportResult(
            created=created,
            updated=updated,
            errors=import_errors
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
def export_devices(db: Session = Depends(get_db)):
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
