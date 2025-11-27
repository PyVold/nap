# ============================================================================
# routes/licensing.py - Licensing API (Stub)
# ============================================================================

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/licensing", tags=["Licensing"])


@router.get("/")
async def get_licenses():
    """Get all licenses (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Licensing module is not yet implemented"
    )


@router.get("/alerts/")
async def get_license_alerts():
    """Get license alerts (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Licensing module is not yet implemented"
    )


@router.get("/stats/summary")
async def get_license_stats():
    """Get license statistics summary (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Licensing module is not yet implemented"
    )


@router.get("/software/")
async def get_software_licenses():
    """Get software licenses (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Licensing module is not yet implemented"
    )
