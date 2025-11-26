# ============================================================================
# api/routes/workflows.py
# Workflow Management API Endpoints
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio

from api.deps import get_db, require_admin
from db_models import WorkflowDB, WorkflowExecutionDB, WorkflowStepLogDB, WorkflowScheduleDB, DeviceDB
from models.workflow import (
    Workflow, WorkflowCreate, WorkflowUpdate,
    WorkflowExecution, WorkflowExecutionRequest,
    WorkflowStepLog, WorkflowSchedule, WorkflowScheduleCreate
)
from engine.workflow_engine import WorkflowEngine
from engine.workflow_parser import WorkflowParser
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


# ============================================================================
# Workflow CRUD Endpoints
# ============================================================================

@router.get("/", response_model=List[Workflow])
def list_workflows(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all workflows"""
    query = db.query(WorkflowDB)

    if is_active is not None:
        query = query.filter(WorkflowDB.is_active == is_active)

    workflows = query.offset(skip).limit(limit).all()
    return workflows


@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Get workflow by ID"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post("/", response_model=Workflow, status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow_create: WorkflowCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new workflow (admin only)"""
    # Validate YAML
    parser = WorkflowParser()
    try:
        parser.parse(workflow_create.workflow_yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow YAML: {str(e)}")

    # Check if name already exists
    existing = db.query(WorkflowDB).filter(WorkflowDB.name == workflow_create.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Workflow name already exists")

    # Create workflow
    workflow = WorkflowDB(
        name=workflow_create.name,
        description=workflow_create.description,
        workflow_yaml=workflow_create.workflow_yaml,
        execution_mode=workflow_create.execution_mode,
        is_active=workflow_create.is_active,
        created_by=current_user.get("sub")
    )

    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    logger.info(f"Workflow '{workflow.name}' created by {current_user.get('sub')}")
    return workflow


@router.put("/{workflow_id}", response_model=Workflow)
def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update workflow (admin only)"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Validate YAML if being updated
    if workflow_update.workflow_yaml:
        parser = WorkflowParser()
        try:
            parser.parse(workflow_update.workflow_yaml)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid workflow YAML: {str(e)}")

    # Update fields
    update_data = workflow_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    db.commit()
    db.refresh(workflow)

    logger.info(f"Workflow '{workflow.name}' updated by {current_user.get('sub')}")
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete workflow (admin only)"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db.delete(workflow)
    db.commit()

    logger.info(f"Workflow '{workflow.name}' deleted by {current_user.get('sub')}")


# ============================================================================
# Workflow Execution Endpoints
# ============================================================================

async def execute_workflow_task(
    workflow_id: int,
    device_id: int,
    trigger_type: str,
    started_by: str,
    override_vars: dict,
    db: Session
):
    """Background task to execute workflow"""
    try:
        workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
        device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()

        if not workflow or not device:
            logger.error(f"Workflow {workflow_id} or device {device_id} not found")
            return

        engine = WorkflowEngine(db)
        await engine.execute_workflow(workflow, device, trigger_type, started_by, override_vars)

    except Exception as e:
        logger.error(f"Background workflow execution failed: {e}")


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: int,
    execution_request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Execute a workflow on specified devices"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if not workflow.is_active:
        raise HTTPException(status_code=400, detail="Workflow is not active")

    # Validate devices exist
    devices = db.query(DeviceDB).filter(DeviceDB.id.in_(execution_request.device_ids)).all()
    if len(devices) != len(execution_request.device_ids):
        raise HTTPException(status_code=400, detail="One or more devices not found")

    # Start execution for each device (in background)
    execution_ids = []
    for device in devices:
        # Create execution record immediately
        execution = WorkflowExecutionDB(
            workflow_id=workflow_id,
            device_id=device.id,
            trigger_type=execution_request.trigger_type,
            status="pending",
            started_by=current_user.get("sub")
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        execution_ids.append(execution.id)

        # Queue background task
        background_tasks.add_task(
            execute_workflow_task,
            workflow_id,
            device.id,
            execution_request.trigger_type,
            current_user.get("sub"),
            execution_request.override_vars,
            db
        )

    logger.info(f"Workflow '{workflow.name}' queued for execution on {len(devices)} devices")

    return {
        "message": f"Workflow execution started on {len(devices)} devices",
        "execution_ids": execution_ids
    }


@router.get("/executions/", response_model=List[WorkflowExecution])
def list_all_executions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    workflow_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List all workflow executions"""
    query = db.query(WorkflowExecutionDB)

    if workflow_id:
        query = query.filter(WorkflowExecutionDB.workflow_id == workflow_id)

    if status:
        query = query.filter(WorkflowExecutionDB.status == status)

    executions = query.order_by(WorkflowExecutionDB.start_time.desc()).offset(skip).limit(limit).all()
    return executions


@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecution])
def list_workflow_executions(
    workflow_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List executions for a workflow"""
    query = db.query(WorkflowExecutionDB).filter(WorkflowExecutionDB.workflow_id == workflow_id)

    if status:
        query = query.filter(WorkflowExecutionDB.status == status)

    executions = query.order_by(WorkflowExecutionDB.start_time.desc()).offset(skip).limit(limit).all()
    return executions


@router.get("/executions/{execution_id}", response_model=WorkflowExecution)
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    """Get workflow execution by ID"""
    execution = db.query(WorkflowExecutionDB).filter(WorkflowExecutionDB.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/executions/{execution_id}/steps", response_model=List[WorkflowStepLog])
def get_execution_steps(execution_id: int, db: Session = Depends(get_db)):
    """Get step logs for an execution"""
    steps = db.query(WorkflowStepLogDB).filter(
        WorkflowStepLogDB.execution_id == execution_id
    ).order_by(WorkflowStepLogDB.start_time).all()

    return steps


@router.post("/executions/{execution_id}/cancel")
def cancel_execution(
    execution_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cancel a running workflow execution"""
    execution = db.query(WorkflowExecutionDB).filter(WorkflowExecutionDB.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status not in ["running", "pending"]:
        raise HTTPException(status_code=400, detail="Execution is not running")

    execution.status = "cancelled"
    execution.error_message = f"Cancelled by {current_user.get('sub')}"
    db.commit()

    logger.info(f"Execution {execution_id} cancelled by {current_user.get('sub')}")
    return {"message": "Execution cancelled"}


# ============================================================================
# Workflow Schedule Endpoints
# ============================================================================

@router.get("/{workflow_id}/schedules", response_model=List[WorkflowSchedule])
def list_workflow_schedules(workflow_id: int, db: Session = Depends(get_db)):
    """List schedules for a workflow"""
    schedules = db.query(WorkflowScheduleDB).filter(
        WorkflowScheduleDB.workflow_id == workflow_id
    ).all()
    return schedules


@router.post("/{workflow_id}/schedules", response_model=WorkflowSchedule, status_code=status.HTTP_201_CREATED)
def create_schedule(
    workflow_id: int,
    schedule_create: WorkflowScheduleCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a schedule for workflow execution"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    schedule = WorkflowScheduleDB(
        workflow_id=workflow_id,
        device_group_id=schedule_create.device_group_id,
        cron_expression=schedule_create.cron_expression,
        is_active=schedule_create.is_active,
        created_by=current_user.get("sub")
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    logger.info(f"Schedule created for workflow '{workflow.name}'")
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a workflow schedule"""
    schedule = db.query(WorkflowScheduleDB).filter(WorkflowScheduleDB.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(schedule)
    db.commit()

    logger.info(f"Schedule {schedule_id} deleted by {current_user.get('sub')}")
