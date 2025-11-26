
# ============================================================================
# api/routes/health.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db, SessionLocal
from services.health_service import HealthService
from services.device_service import DeviceService
from utils.logger import setup_logger

router = APIRouter(prefix="/health", tags=["health"])
logger = setup_logger(__name__)

health_service = HealthService()
device_service = DeviceService()


@router.post("/check/{device_id}")
async def check_device_health(
    device_id: int,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Perform health check on a specific device

    Args:
        device_id: Device ID to check
        force: If true, bypass backoff and check immediately
    """
    try:
        device = device_service.get_device_by_id(db, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        result = await health_service.check_device_health(db, device, force=force)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/check-all")
async def check_all_devices_health(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Perform health check on all devices"""
    devices = device_service.get_all_devices(db)

    if not devices:
        return {"message": "No devices to check", "results": []}

    # Run health checks in background - create new session in background task
    async def run_checks():
        db = SessionLocal()
        try:
            await health_service.check_all_devices_health(db, devices)
        except Exception as e:
            logger.error(f"Background health check failed: {e}")
        finally:
            db.close()

    background_tasks.add_task(run_checks)

    return {
        "message": f"Health check started for {len(devices)} devices",
        "device_count": len(devices)
    }


@router.get("/history/{device_id}")
def get_device_health_history(
    device_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get health check history for a device"""
    device = device_service.get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    history = health_service.get_device_health_history(db, device_id, limit)
    return {
        "device_id": device_id,
        "device_name": device.hostname,
        "history": history
    }


@router.get("/summary")
def get_health_summary(db: Session = Depends(get_db)):
    """Get overall health summary for all devices"""
    summary = health_service.get_health_summary(db)
    return summary
