# ============================================================================
# api/routes/device_groups.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.device_group import DeviceGroup, DeviceGroupCreate, DeviceGroupUpdate
from services.device_group_service import DeviceGroupService
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

device_group_service = DeviceGroupService()


@router.get("/", response_model=List[DeviceGroup])
async def get_all_device_groups(db: Session = Depends(get_db)):
    """Get all device groups"""
    return device_group_service.get_all_groups(db)


@router.get("/{group_id}", response_model=DeviceGroup)
async def get_device_group(group_id: int, db: Session = Depends(get_db)):
    """Get a specific device group by ID"""
    group = device_group_service.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device group with ID {group_id} not found"
        )
    return group


@router.post("/", response_model=DeviceGroup, status_code=status.HTTP_201_CREATED)
async def create_device_group(
    group_create: DeviceGroupCreate,
    db: Session = Depends(get_db)
):
    """Create a new device group"""
    try:
        return device_group_service.create_group(db, group_create)
    except Exception as e:
        logger.error(f"Error creating device group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{group_id}", response_model=DeviceGroup)
async def update_device_group(
    group_id: int,
    group_update: DeviceGroupUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing device group"""
    try:
        return device_group_service.update_group(db, group_id, group_update)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating device group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_group(group_id: int, db: Session = Depends(get_db)):
    """Delete a device group"""
    try:
        device_group_service.delete_group(db, group_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{group_id}/devices/{device_id}")
async def add_device_to_group(
    group_id: int,
    device_id: int,
    db: Session = Depends(get_db)
):
    """Add a device to a group"""
    try:
        success = device_group_service.add_device_to_group(db, group_id, device_id)
        if success:
            return {"status": "success", "message": f"Device {device_id} added to group {group_id}"}
        else:
            return {"status": "already_exists", "message": f"Device {device_id} already in group {group_id}"}
    except Exception as e:
        logger.error(f"Error adding device to group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{group_id}/devices/{device_id}")
async def remove_device_from_group(
    group_id: int,
    device_id: int,
    db: Session = Depends(get_db)
):
    """Remove a device from a group"""
    try:
        success = device_group_service.remove_device_from_group(db, group_id, device_id)
        if success:
            return {"status": "success", "message": f"Device {device_id} removed from group {group_id}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found in group {group_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing device from group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{group_id}/devices", response_model=List[int])
async def get_group_devices(group_id: int, db: Session = Depends(get_db)):
    """Get all device IDs in a group"""
    return device_group_service.get_group_devices(db, group_id)
