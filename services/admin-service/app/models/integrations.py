"""
Integration Hub Models (Pydantic)
Supports NetBox, Git, Ansible, ServiceNow, and Prometheus integrations
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class IntegrationType(str, Enum):
    NETBOX = "netbox"
    GIT = "git"
    ANSIBLE = "ansible"
    SERVICENOW = "servicenow"
    PROMETHEUS = "prometheus"
    SLACK = "slack"
    TEAMS = "teams"


class IntegrationBase(BaseModel):
    name: str
    integration_type: str
    enabled: bool = True
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    sync_interval_minutes: Optional[int] = None


class IntegrationCreate(IntegrationBase):
    pass


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    integration_type: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    sync_interval_minutes: Optional[int] = None


class Integration(IntegrationBase):
    id: int
    last_sync: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
