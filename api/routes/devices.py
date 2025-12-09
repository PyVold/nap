# ============================================================================
# api/routes/devices.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from api.deps import get_db, require_admin_or_operator
from models.device import Device, DeviceCreate, DeviceUpdate, DiscoveryRequest
from services.device_service import DeviceService
from services.discovery_service import DiscoveryService
from services.license_enforcement_service import license_enforcement_service
from shared.license_middleware import require_license_module, enforce_quota
from utils.exceptions import DeviceNotFoundError
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

device_service = DeviceService()
discovery_service = DiscoveryService()

@router.get("/", response_model=List[Device])
async def get_all_devices(
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("devices"))
):
    """Get all devices (requires 'devices' module in license)"""
    return device_service.get_all_devices(db)


@router.get("/metadata/overlaps")
async def get_metadata_overlaps(db: Session = Depends(get_db)):
    """
    Detect overlapping metadata values across devices.

    Returns devices with duplicate:
    - ISIS NET addresses
    - System/Loopback0 addresses
    - BGP router-ids
    """
    return device_service.detect_metadata_overlaps(db)


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
    current_user: dict = Depends(require_admin_or_operator),
    _license: None = Depends(require_license_module("devices")),
    _quota: None = Depends(enforce_quota("devices", 1))
):
    """Create a new device (requires admin or operator role, enforces device quota)"""
    try:
        device = device_service.create_device(db, device_create)
        
        # Update license usage after creating device
        license_enforcement_service.enforcer.update_license_usage(db)
        
        return device
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
    current_user: dict = Depends(require_admin_or_operator),
    _license: None = Depends(require_license_module("discovery"))
):
    """Discover devices via subnet scanning with license quota enforcement"""
    try:
        discovered = await discovery_service.discover_subnet(
            subnet=discovery_request.subnet,
            username=discovery_request.username,
            password=discovery_request.password,
            port=discovery_request.port
        )
        
        # Enforce device limits on discovered devices
        enforcement_result = license_enforcement_service.enforce_device_limit_on_discovery(
            db, discovered
        )
        
        # Only add accepted devices
        accepted_devices = enforcement_result["accepted"]
        rejected_devices = enforcement_result["rejected"]
        
        added_count = 0
        if accepted_devices:
            added_count = device_service.merge_discovered_devices(db, accepted_devices)
            
            # Update license usage after adding devices
            license_enforcement_service.enforcer.update_license_usage(db)
        
        # Log warning if devices were rejected
        if rejected_devices:
            logger.warning(
                f"Discovery quota limit: {len(rejected_devices)} devices rejected. "
                f"License upgrade required."
            )

        return {
            "status": "success" if not rejected_devices else "partial",
            "discovered": len(discovered),
            "added": added_count,
            "rejected": len(rejected_devices),
            "message": enforcement_result["message"],
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
