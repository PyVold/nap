# ============================================================================
# models/audit_policy.py
# Pydantic models for Audit Policy Orchestrator
# ============================================================================

from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime


class AuditPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    protocol: str  # bgp, isis, ospf, interface, etc.
    template_content: str  # YAML template
    default_variables: Optional[Dict[str, Any]] = None
    is_active: bool = True


class AuditPolicyCreate(AuditPolicyBase):
    pass


class AuditPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    protocol: Optional[str] = None
    template_content: Optional[str] = None
    default_variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AuditPolicy(AuditPolicyBase):
    id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceVariableBase(BaseModel):
    policy_id: int
    device_id: int
    variables: Dict[str, Any]
    auto_collected: bool = False


class DeviceVariableCreate(DeviceVariableBase):
    pass


class DeviceVariableUpdate(BaseModel):
    variables: Optional[Dict[str, Any]] = None
    auto_collected: Optional[bool] = None


class DeviceVariable(DeviceVariableBase):
    id: int
    last_collected: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceFactBase(BaseModel):
    device_id: int
    fact_type: str  # bgp_neighbors, isis_adjacencies, ospf_neighbors, interfaces
    fact_data: Dict[str, Any]
    is_current: bool = True


class DeviceFactCreate(DeviceFactBase):
    pass


class DeviceFact(DeviceFactBase):
    id: int
    collected_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Policy Execution Models
# ============================================================================

class PolicyExecutionRequest(BaseModel):
    policy_id: int
    device_ids: Optional[List[int]] = None  # None = all devices with variables
    collect_facts: bool = False  # Whether to collect facts before execution


class PolicyCheck(BaseModel):
    """A single check within a policy"""
    name: str
    command: str
    assertion: str
    loop: Optional[str] = None  # Jinja2 expression for looping
    severity: str = "high"


class PolicyExecutionResult(BaseModel):
    """Result of executing a policy on a device"""
    policy_id: int
    policy_name: str
    device_id: int
    device_name: str
    timestamp: str
    checks_passed: int
    checks_failed: int
    compliance: int
    findings: List[Dict[str, Any]]  # List of check results
