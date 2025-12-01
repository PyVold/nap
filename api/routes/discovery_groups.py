# ============================================================================
# api/routes/discovery_groups.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.discovery_group import DiscoveryGroup, DiscoveryGroupCreate, DiscoveryGroupUpdate
from services.discovery_group_service import DiscoveryGroupService
from services.device_service import DeviceService
from services.discovery_service import DiscoveryService
from utils.logger import setup_logger
from shared.license_middleware import require_license_module

router = APIRouter()
logger = setup_logger(__name__)

discovery_group_service = DiscoveryGroupService()
device_service = DeviceService()
discovery_service = DiscoveryService()


@router.get("/", response_model=List[DiscoveryGroup])
async def get_all_discovery_groups(
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("discovery"))
):
    """Get all discovery groups"""
    return discovery_group_service.get_all_groups(db)


@router.get("/{group_id}", response_model=DiscoveryGroup)
async def get_discovery_group(
    group_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("discovery"))
):
    """Get a specific discovery group by ID"""
    group = discovery_group_service.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery group with ID {group_id} not found"
        )
    return group


@router.post("/", response_model=DiscoveryGroup, status_code=status.HTTP_201_CREATED)
async def create_discovery_group(
    group_create: DiscoveryGroupCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("discovery"))
):
    """Create a new discovery group"""
    try:
        return discovery_group_service.create_group(db, group_create)
    except Exception as e:
        logger.error(f"Error creating discovery group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{group_id}", response_model=DiscoveryGroup)
async def update_discovery_group(
    group_id: int,
    group_update: DiscoveryGroupUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("discovery"))
):
    """Update an existing discovery group"""
    try:
        return discovery_group_service.update_group(db, group_id, group_update)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating discovery group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discovery_group(
    group_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("discovery"))
):
    """Delete a discovery group"""
    try:
        discovery_group_service.delete_group(db, group_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{group_id}/discover")
async def run_discovery_for_group(
    group_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("discovery"))
):
    """Run discovery for a specific group"""
    group = discovery_group_service.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery group with ID {group_id} not found"
        )

    # Get decrypted password
    password = discovery_group_service.get_decrypted_password(db, group_id)

    # Run discovery in background
    async def run_discovery_task():
        from database import SessionLocal
        task_db = SessionLocal()
        try:
            discovered = await discovery_service.discover_subnet(
                subnet=group.subnet,
                username=group.username,
                password=password,
                port=group.port,
                excluded_ips=group.excluded_ips
            )
            added_count = device_service.merge_discovered_devices(task_db, discovered)
            discovery_group_service.update_run_timestamps(task_db, group_id)
            logger.info(f"Discovery group {group_id}: found {len(discovered)}, added {added_count}")
        except Exception as e:
            logger.error(f"Discovery group {group_id} failed: {str(e)}")
        finally:
            task_db.close()

    background_tasks.add_task(run_discovery_task)

    return {
        "status": "started",
        "message": f"Discovery started for group '{group.name}'"
    }
