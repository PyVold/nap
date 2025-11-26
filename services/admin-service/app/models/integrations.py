"""
Integration Hub Models
Supports NetBox, Git, Ansible, ServiceNow, and Prometheus integrations
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text, Enum
from sqlalchemy.sql import func
from shared.database import Base
import enum


class IntegrationType(str, enum.Enum):
    NETBOX = "netbox"
    GIT = "git"
    ANSIBLE = "ansible"
    SERVICENOW = "servicenow"
    PROMETHEUS = "prometheus"
    SLACK = "slack"
    TEAMS = "teams"


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    integration_type = Column(Enum(IntegrationType), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Connection details (encrypted in production)
    config = Column(JSON, nullable=False)  # URL, credentials, API tokens, etc.

    # Sync settings
    auto_sync = Column(Boolean, default=False)
    sync_interval_minutes = Column(Integer, default=60)
    last_sync = Column(DateTime(timezone=True))
    last_sync_status = Column(String)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String)

    # Integration-specific settings
    settings = Column(JSON)  # Custom settings per integration type


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # sync, push, pull, execute
    status = Column(String, nullable=False)  # success, failed, partial
    message = Column(Text)
    details = Column(JSON)
    duration_seconds = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
