# ============================================================================
# models/discovery_group.py
# ============================================================================

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime as dt


class DiscoveryGroup(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    subnet: str = Field(..., description="Subnet in CIDR notation (e.g., 192.168.1.0/24)")
    excluded_ips: Optional[List[str]] = Field(default_factory=list, description="List of IP addresses to exclude from discovery")
    username: str
    password: str  # Will be encrypted before storage
    port: int = 830
    schedule_enabled: bool = False
    schedule_interval: int = 60  # minutes
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DiscoveryGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subnet: str = Field(..., description="Subnet in CIDR notation")
    excluded_ips: Optional[List[str]] = Field(default_factory=list, description="IP addresses to exclude (e.g., ['192.168.1.1', '192.168.1.254'])")
    username: str
    password: str
    port: int = 830
    schedule_enabled: bool = False
    schedule_interval: int = 60  # minutes


class DiscoveryGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subnet: Optional[str] = None
    excluded_ips: Optional[List[str]] = None
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[int] = None
    schedule_enabled: Optional[bool] = None
    schedule_interval: Optional[int] = None
    active: Optional[bool] = None
