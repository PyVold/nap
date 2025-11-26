"""
Hardware Inventory API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from api.deps import get_db
from db_models import HardwareInventoryDB, DeviceDB
from services.hardware_inventory_service import HardwareInventoryService

router = APIRouter(prefix="/hardware", tags=["hardware"])


# ============================================================================
# Pydantic Models
# ============================================================================

class HardwareComponent(BaseModel):
    id: int
    device_id: int
    component_type: str
    component_name: str
    slot_number: Optional[str] = None
    parent_id: Optional[int] = None
    part_number: Optional[str] = None
    serial_number: Optional[str] = None
    hardware_revision: Optional[str] = None
    firmware_version: Optional[str] = None
    model_name: Optional[str] = None
    description: Optional[str] = None
    operational_state: Optional[str] = None
    admin_state: Optional[str] = None
    manufacturing_date: Optional[str] = None
    clei_code: Optional[str] = None
    is_fru: bool
    last_discovered: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceInventorySummary(BaseModel):
    device_id: int
    device_name: str
    device_ip: Optional[str]
    vendor: str
    chassis_model: Optional[str]
    total_components: int
    cards_count: int
    power_count: int
    fans_count: int
    last_scan: Optional[datetime]


class ChassisModelSummary(BaseModel):
    vendor: str
    chassis_model: str
    device_count: int
    devices: List[dict]


class ScanResponse(BaseModel):
    success: bool
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    components_found: Optional[int] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/inventory", response_model=List[DeviceInventorySummary])
def list_inventory_summary(
    vendor: Optional[str] = Query(None, description="Filter by vendor (nokia, cisco)"),
    chassis_model: Optional[str] = Query(None, description="Filter by chassis model"),
    db: Session = Depends(get_db)
):
    """
    Get inventory summary for all devices with filtering

    Returns a list of devices with their hardware inventory statistics
    """
    try:
        # Build query
        query = db.query(DeviceDB)

        # Apply vendor filter
        if vendor:
            query = query.filter(DeviceDB.vendor == vendor)

        devices = query.all()
        summaries = []

        for device in devices:
            # Get all components for this device
            components = db.query(HardwareInventoryDB).filter(
                HardwareInventoryDB.device_id == device.id
            ).all()

            # Get chassis model
            chassis = next((c for c in components if c.component_type == 'chassis'), None)
            chassis_model_name = chassis.model_name if chassis else None

            # Apply chassis model filter
            if chassis_model and chassis_model_name != chassis_model:
                continue

            # Count by type
            cards = [c for c in components if c.component_type in ('card', 'mda', 'rp')]
            power = [c for c in components if c.component_type == 'power']
            fans = [c for c in components if c.component_type == 'fan']

            # Get last scan time
            last_scan = max((c.last_discovered for c in components), default=None) if components else None

            summaries.append(DeviceInventorySummary(
                device_id=device.id,
                device_name=device.hostname,
                device_ip=device.ip,
                vendor=device.vendor.value if hasattr(device.vendor, 'value') else str(device.vendor),
                chassis_model=chassis_model_name,
                total_components=len(components),
                cards_count=len(cards),
                power_count=len(power),
                fans_count=len(fans),
                last_scan=last_scan
            ))

        # Sort by device name
        summaries.sort(key=lambda x: x.device_name)

        return summaries

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chassis-models", response_model=List[ChassisModelSummary])
def list_chassis_models(
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    db: Session = Depends(get_db)
):
    """
    Get list of chassis models with device counts

    Groups devices by vendor and chassis model
    """
    try:
        # Query devices with chassis information
        query = db.query(DeviceDB)

        if vendor:
            query = query.filter(DeviceDB.vendor == vendor)

        devices = query.all()

        # Group by chassis model
        chassis_map = {}

        for device in devices:
            chassis = db.query(HardwareInventoryDB).filter(
                HardwareInventoryDB.device_id == device.id,
                HardwareInventoryDB.component_type == 'chassis'
            ).first()

            if not chassis:
                continue

            vendor_name = device.vendor.value if hasattr(device.vendor, 'value') else str(device.vendor)
            model = chassis.model_name or 'Unknown'
            key = f"{vendor_name}:{model}"

            if key not in chassis_map:
                chassis_map[key] = {
                    'vendor': vendor_name,
                    'chassis_model': model,
                    'devices': []
                }

            chassis_map[key]['devices'].append({
                'id': device.id,
                'hostname': device.hostname,
                'ip': device.ip
            })

        # Convert to list
        result = [
            ChassisModelSummary(
                vendor=v['vendor'],
                chassis_model=v['chassis_model'],
                device_count=len(v['devices']),
                devices=v['devices']
            )
            for v in chassis_map.values()
        ]

        # Sort by vendor, then model
        result.sort(key=lambda x: (x.vendor, x.chassis_model))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inventory/{device_id}", response_model=List[HardwareComponent])
def get_device_inventory(
    device_id: int,
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    db: Session = Depends(get_db)
):
    """Get detailed hardware inventory for a specific device"""
    try:
        query = db.query(HardwareInventoryDB).filter(
            HardwareInventoryDB.device_id == device_id
        )

        if component_type:
            query = query.filter(HardwareInventoryDB.component_type == component_type)

        components = query.order_by(HardwareInventoryDB.slot_number).all()

        return components

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/{device_id}", response_model=ScanResponse)
async def scan_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Trigger a hardware inventory scan for a specific device"""
    try:
        result = await HardwareInventoryService.scan_device(db, device_id)
        return ScanResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan-all")
async def scan_all_devices(db: Session = Depends(get_db)):
    """Trigger hardware inventory scan for all devices"""
    try:
        devices = db.query(DeviceDB).all()
        results = []

        for device in devices:
            result = await HardwareInventoryService.scan_device(db, device.id)
            results.append(result)

        successful = sum(1 for r in results if r.get('success'))

        return {
            "success": True,
            "total_devices": len(devices),
            "successful_scans": successful,
            "failed_scans": len(devices) - successful,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
