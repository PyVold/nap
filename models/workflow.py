# ============================================================================
# models/workflow.py
# Pydantic models for Workflow Manager
# ============================================================================

from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime


class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    workflow_yaml: str
    execution_mode: str = "sequential"  # sequential, dag, hybrid
    is_active: bool = True


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workflow_yaml: Optional[str] = None
    execution_mode: Optional[str] = None
    is_active: Optional[bool] = None


class Workflow(WorkflowBase):
    id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowExecutionRequest(BaseModel):
    workflow_id: int
    device_ids: List[int]
    trigger_type: str = "manual"
    override_vars: Optional[Dict[str, Any]] = None


class WorkflowExecution(BaseModel):
    id: int
    workflow_id: int
    device_id: int
    trigger_type: str
    status: str
    current_step: Optional[str] = None
    step_results: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_by: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowStepLog(BaseModel):
    id: int
    execution_id: int
    step_name: str
    step_type: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class WorkflowScheduleBase(BaseModel):
    workflow_id: int
    device_group_id: Optional[int] = None
    cron_expression: str
    is_active: bool = True


class WorkflowScheduleCreate(WorkflowScheduleBase):
    pass


class WorkflowSchedule(WorkflowScheduleBase):
    id: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowTriggerBase(BaseModel):
    workflow_id: int
    trigger_event: str
    condition: Optional[Dict[str, Any]] = None
    is_active: bool = True


class WorkflowTriggerCreate(WorkflowTriggerBase):
    pass


class WorkflowTrigger(WorkflowTriggerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
