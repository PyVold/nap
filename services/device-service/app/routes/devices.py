# ============================================================================
# api/routes/devices.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from shared.deps import get_db, require_admin_or_operator
from models.device import Device, DeviceCreate, DeviceUpdate, DiscoveryRequest
from services.device_service import DeviceService
from services.discovery_service import DiscoveryService
from shared.exceptions import DeviceNotFoundError

router = APIRouter()

device_service = DeviceService()
discovery_service = DiscoveryService()

@router.get("/", response_model=List[Device])
async def get_all_devices(db: Session = Depends(get_db)):
    """Get all devices"""
    return device_service.get_all_devices(db)

@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: int, db: Session = Depends(get_db)):
    """Get a specific device by ID"""
    device = device_service.get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID {device_id} not found"
        )
    return device

@router.post("/", response_model=Device, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_create: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Create a new device (requires admin or operator role)"""
    try:
        return device_service.create_device(db, device_create)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{device_id}", response_model=Device)
async def update_device(
    device_id: int,
    device_update: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Update an existing device (requires admin or operator role)"""
    try:
        return device_service.update_device(db, device_id, device_update)
    except DeviceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Delete a device (requires admin or operator role)"""
    try:
        device_service.delete_device(db, device_id)
    except DeviceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/discover")
async def discover_devices(
    discovery_request: DiscoveryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Discover devices via subnet scanning (requires admin or operator role)"""
    try:
        discovered = await discovery_service.discover_subnet(
            subnet=discovery_request.subnet,
            username=discovery_request.username,
            password=discovery_request.password,
            port=discovery_request.port
        )
        added_count = device_service.merge_discovered_devices(db, discovered)

        return {
            "status": "success",
            "discovered": len(discovered),
            "added": added_count,
            "total_devices": len(device_service.get_all_devices(db))
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery failed: {str(e)}"
        )

@router.get("/vendor/{vendor}", response_model=List[Device])
async def get_devices_by_vendor(vendor: str, db: Session = Depends(get_db)):
    """Get devices filtered by vendor"""
    return device_service.get_devices_by_vendor(db, vendor)
