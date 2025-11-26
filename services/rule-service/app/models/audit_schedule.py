# ============================================================================
# models/audit_schedule.py
# ============================================================================

from pydantic import BaseModel
from typing import Optional, List


class AuditSchedule(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    device_group_id: Optional[int] = None
    device_ids: Optional[List[int]] = None  # Alternative to device_group_id
    rule_ids: Optional[List[int]] = None  # null = all enabled rules
    schedule_enabled: bool = False
    cron_expression: Optional[str] = None  # e.g., "0 2 * * *" for 2am daily
    schedule_interval: Optional[int] = None  # Minutes (alternative to cron)
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AuditScheduleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    device_group_id: Optional[int] = None
    device_ids: Optional[List[int]] = None
    rule_ids: Optional[List[int]] = None
    schedule_enabled: bool = False
    cron_expression: Optional[str] = None
    schedule_interval: Optional[int] = None


class AuditScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    device_group_id: Optional[int] = None
    device_ids: Optional[List[int]] = None
    rule_ids: Optional[List[int]] = None
    schedule_enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    schedule_interval: Optional[int] = None
    active: Optional[bool] = None
