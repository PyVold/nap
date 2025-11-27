# ============================================================================
# routes/config_templates.py - Configuration Template API (Stub)
# ============================================================================

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/config-templates", tags=["Config Templates"])


@router.post("/initialize")
async def initialize_templates():
    """Initialize templates (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Configuration template module is not yet implemented"
    )


@router.get("/categories/list")
async def get_template_categories():
    """Get template categories (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Configuration template module is not yet implemented"
    )


@router.get("/")
async def get_templates():
    """Get all templates (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Configuration template module is not yet implemented"
    )
