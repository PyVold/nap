# ============================================================================
# models/device_group.py
# ============================================================================

from pydantic import BaseModel
from typing import Optional, List


class DeviceGroup(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    device_ids: List[int] = []  # List of device IDs in this group
    device_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DeviceGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    device_ids: List[int] = []


class DeviceGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    device_ids: Optional[List[int]] = None
