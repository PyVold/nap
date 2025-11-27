# ============================================================================
# routes/workflows.py - Workflow API (Stub)
# ============================================================================

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("/")
async def get_workflows():
    """Get all workflows (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Workflow module is not yet implemented"
    )


@router.get("/executions/")
async def get_workflow_executions():
    """Get workflow executions (stub - not implemented)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Workflow module is not yet implemented"
    )
