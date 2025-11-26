"""
Configuration Templates Library Models
Pre-built and custom configuration templates for devices
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text, Enum
from sqlalchemy.sql import func
from database import Base
import enum


class TemplateCategory(str, enum.Enum):
    SECURITY = "security"
    QOS = "qos"
    ROUTING = "routing"
    INTERFACES = "interfaces"
    SYSTEM = "system"
    MPLS = "mpls"
    BGP = "bgp"
    ISIS = "isis"
    OSPF = "ospf"
    VLAN = "vlan"
    ACL = "acl"
    LOGGING = "logging"
    SNMP = "snmp"


class ConfigTemplate(Base):
    __tablename__ = "config_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    category = Column(Enum(TemplateCategory), nullable=False, index=True)
    vendor = Column(String, nullable=False, index=True)  # CISCO_XR, NOKIA_SROS, etc.

    # Template content with variable placeholders
    template_content = Column(Text, nullable=False)

    # XPath for Nokia SROS templates (optional)
    xpath = Column(String, nullable=True)  # XPath for pysros candidate.set()

    # Variables that can be substituted
    variables = Column(JSON)  # [{name, type, description, default, required}]

    # Validation rules
    validation_rules = Column(JSON)  # Rules to validate generated config

    # Pre/Post conditions
    pre_checks = Column(JSON)  # Commands to run before applying
    post_checks = Column(JSON)  # Commands to run after applying

    # Template metadata
    is_builtin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    version = Column(String, default="1.0.0")
    tags = Column(JSON)  # Searchable tags

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String)


class TemplateDeployment(Base):
    __tablename__ = "template_deployments"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, nullable=False)
    device_id = Column(Integer, nullable=False)

    # Deployment details
    variables_used = Column(JSON)  # Actual values used for variables
    generated_config = Column(Text)  # Final config generated from template

    # Deployment status
    status = Column(String, nullable=False)  # pending, success, failed, rolled_back
    error_message = Column(Text)

    # Backup before deployment
    backup_id = Column(Integer)  # Reference to config backup before change

    # Deployment metadata
    deployed_at = Column(DateTime(timezone=True))
    deployed_by = Column(String)
    rollback_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
