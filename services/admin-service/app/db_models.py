from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, DateTime, Text, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database import Base
from models.enums import VendorType, DeviceStatus, SeverityLevel, AuditStatus
import enum

class DeviceDB(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), unique=True, index=True, nullable=False)
    vendor = Column(SQLEnum(VendorType), nullable=False)
    ip = Column(String(45), unique=True, index=True, nullable=True)  # Unique constraint on IP
    port = Column(Integer, default=830)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.DISCOVERED)
    last_audit = Column(DateTime, nullable=True)
    compliance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Exponential backoff tracking
    consecutive_failures = Column(Integer, default=0)
    last_check_attempt = Column(DateTime, nullable=True)
    next_check_due = Column(DateTime, nullable=True)

    audit_results = relationship("AuditResultDB", back_populates="device", cascade="all, delete-orphan")
    health_checks = relationship("HealthCheckDB", back_populates="device", cascade="all, delete-orphan")
    hardware_inventory = relationship("HardwareInventoryDB", back_populates="device", cascade="all, delete-orphan")


class HardwareInventoryDB(Base):
    """Hardware inventory for device components"""
    __tablename__ = "hardware_inventory"
    __table_args__ = (
        Index('ix_hardware_device_type', 'device_id', 'component_type'),
        Index('ix_hardware_device_slot', 'device_id', 'slot_number'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), index=True, nullable=False)

    # Component identification
    component_type = Column(String(50), index=True, nullable=False)  # chassis, card, power, fan, mda
    component_name = Column(String(255), nullable=False)  # User-friendly name
    slot_number = Column(String(50), nullable=True)  # Slot/location identifier
    parent_id = Column(Integer, ForeignKey('hardware_inventory.id', ondelete='CASCADE'), nullable=True)  # For nested components

    # Hardware details
    part_number = Column(String(100), nullable=True)  # PID for Cisco, part-number for Nokia
    serial_number = Column(String(100), nullable=True)
    hardware_revision = Column(String(50), nullable=True)  # VID for Cisco
    firmware_version = Column(String(100), nullable=True)
    model_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Status
    operational_state = Column(String(50), nullable=True)  # up, down, diagnosing
    admin_state = Column(String(50), nullable=True)  # in-service, out-of-service

    # Additional metadata
    manufacturing_date = Column(String(50), nullable=True)
    clei_code = Column(String(50), nullable=True)  # Nokia specific
    is_fru = Column(Boolean, default=False)  # Field Replaceable Unit

    # Timestamps
    last_discovered = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    device = relationship("DeviceDB", back_populates="hardware_inventory")
    children = relationship("HardwareInventoryDB", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("HardwareInventoryDB", remote_side=[id], back_populates="children")


class AuditRuleDB(Base):
    __tablename__ = "audit_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.MEDIUM)
    category = Column(String(100), index=True, nullable=True)
    enabled = Column(Boolean, default=True)
    vendors = Column(JSON, nullable=False)  # List of VendorType
    checks = Column(JSON, nullable=False)  # List of RuleCheck dictionaries
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditResultDB(Base):
    __tablename__ = "audit_results"
    __table_args__ = (
        Index('ix_audit_results_device_timestamp', 'device_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), index=True, nullable=False)
    device_name = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    findings = Column(JSON, nullable=False)  # List of AuditFinding dictionaries
    compliance = Column(Float, default=0.0)
    status = Column(String(50), default="completed")

    device = relationship("DeviceDB", back_populates="audit_results")


class HealthCheckDB(Base):
    __tablename__ = "health_checks"
    __table_args__ = (
        Index('ix_health_checks_device_timestamp', 'device_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ping_status = Column(Boolean, default=False)
    ping_latency = Column(Float, nullable=True)
    netconf_status = Column(Boolean, default=False)
    netconf_message = Column(Text, nullable=True)
    ssh_status = Column(Boolean, default=False)
    ssh_message = Column(Text, nullable=True)
    overall_status = Column(String(50), default="unknown")

    device = relationship("DeviceDB", back_populates="health_checks")


class DiscoveryGroupDB(Base):
    __tablename__ = "discovery_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    subnet = Column(String(100), nullable=False)  # CIDR notation
    excluded_ips = Column(JSON, nullable=True, default=list)  # List of IPs to exclude
    username = Column(String(255), nullable=False)
    password = Column(String(512), nullable=False)  # Encrypted
    port = Column(Integer, default=830)
    schedule_enabled = Column(Boolean, default=False)
    schedule_interval = Column(Integer, default=60)  # minutes
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeviceGroupDB(Base):
    __tablename__ = "device_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    devices = relationship("DeviceGroupMembershipDB", back_populates="group", cascade="all, delete-orphan")


class DeviceGroupMembershipDB(Base):
    __tablename__ = "device_group_memberships"
    __table_args__ = (
        Index('ix_device_group_membership', 'device_id', 'group_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey('device_groups.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("DeviceGroupDB", back_populates="devices")
    device = relationship("DeviceDB")


class AuditScheduleDB(Base):
    __tablename__ = "audit_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    device_group_id = Column(Integer, ForeignKey('device_groups.id', ondelete='CASCADE'), nullable=True)
    device_ids = Column(JSON, nullable=True)  # List of device IDs if not using group
    rule_ids = Column(JSON, nullable=True)  # List of rule IDs (null = all enabled rules)
    schedule_enabled = Column(Boolean, default=False)
    cron_expression = Column(String(100), nullable=True)  # Cron expression
    schedule_interval = Column(Integer, nullable=True)  # Minutes (alternative to cron)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    device_group = relationship("DeviceGroupDB")


# ============================================================================
# Configuration Backup & Versioning
# ============================================================================

class ConfigBackupDB(Base):
    """Stores device configuration backups with versioning"""
    __tablename__ = "config_backups"
    __table_args__ = (
        Index('ix_config_backups_device_timestamp', 'device_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    config_data = Column(Text, nullable=False)  # Full configuration
    config_hash = Column(String(64), index=True)  # SHA256 hash for change detection
    size_bytes = Column(Integer)  # Configuration size
    backup_type = Column(String(50), default="auto")  # auto, manual, audit, discovery
    triggered_by = Column(String(100), nullable=True)  # Event that triggered backup
    notes = Column(Text, nullable=True)

    device = relationship("DeviceDB")


class ConfigChangeEventDB(Base):
    """Tracks configuration changes between versions"""
    __tablename__ = "config_change_events"
    __table_args__ = (
        Index('ix_config_changes_device_timestamp', 'device_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    previous_backup_id = Column(Integer, ForeignKey('config_backups.id', ondelete='SET NULL'), nullable=True)
    current_backup_id = Column(Integer, ForeignKey('config_backups.id', ondelete='SET NULL'), nullable=True)
    change_summary = Column(JSON)  # {'added_lines': 10, 'removed_lines': 5, 'modified_sections': [...]}
    diff_text = Column(Text, nullable=True)  # Unified diff format
    change_type = Column(String(50))  # drift, manual, update, unknown
    severity = Column(String(20))  # critical, high, medium, low
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    device = relationship("DeviceDB")
    previous_backup = relationship("ConfigBackupDB", foreign_keys=[previous_backup_id])
    current_backup = relationship("ConfigBackupDB", foreign_keys=[current_backup_id])


# ============================================================================
# Notifications & Webhooks
# ============================================================================

class NotificationWebhookDB(Base):
    """Webhook configurations for notifications"""
    __tablename__ = "notification_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    webhook_url = Column(String(512), nullable=False)
    webhook_type = Column(String(50))  # slack, teams, discord, generic, email
    enabled = Column(Boolean, default=True)
    events = Column(JSON)  # List of events: audit_failure, compliance_drop, discovery_complete, etc
    filters = Column(JSON, nullable=True)  # Event filtering criteria
    headers = Column(JSON, nullable=True)  # Custom headers
    secret = Column(String(512), nullable=True)  # Webhook secret/token (encrypted)
    retry_count = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=10)
    last_triggered = Column(DateTime, nullable=True)
    last_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationHistoryDB(Base):
    """History of sent notifications"""
    __tablename__ = "notification_history"
    __table_args__ = (
        Index('ix_notification_history_webhook_timestamp', 'webhook_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey('notification_webhooks.id', ondelete='CASCADE'), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(100))
    event_data = Column(JSON)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    webhook = relationship("NotificationWebhookDB")


# ============================================================================
# Rule Templates & Library
# ============================================================================

class RuleTemplateDB(Base):
    """Pre-built rule templates (CIS, PCI-DSS, etc)"""
    __tablename__ = "rule_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    category = Column(String(100), index=True)  # CIS, PCI-DSS, SOC2, Custom
    framework = Column(String(100), nullable=True)  # Framework name/version
    description = Column(Text)
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.MEDIUM)
    vendors = Column(JSON, nullable=False)  # Applicable vendors
    checks = Column(JSON, nullable=False)  # Rule check definitions
    tags = Column(JSON, nullable=True)  # Search tags
    is_public = Column(Boolean, default=True)  # Public template vs custom
    created_by = Column(String(100), nullable=True)
    version = Column(String(20), default="1.0.0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# RBAC & User Management
# ============================================================================

class UserDB(Base):
    """User accounts for RBAC"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="viewer")  # Legacy: admin, auditor, operator, viewer
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    group_memberships = relationship("UserGroupMembershipDB", back_populates="user", cascade="all, delete-orphan")


class UserGroupDB(Base):
    """User groups for organizing users and assigning permissions"""
    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)

    # Relationships
    members = relationship("UserGroupMembershipDB", back_populates="group", cascade="all, delete-orphan")
    permissions = relationship("GroupPermissionDB", back_populates="group", cascade="all, delete-orphan")
    module_access = relationship("GroupModuleAccessDB", back_populates="group", cascade="all, delete-orphan")


class UserGroupMembershipDB(Base):
    """Many-to-many relationship between users and groups"""
    __tablename__ = "user_group_memberships"
    __table_args__ = (
        Index('ix_user_group_membership', 'user_id', 'group_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserDB", back_populates="group_memberships")
    group = relationship("UserGroupDB", back_populates="members")


class GroupPermissionDB(Base):
    """Granular permissions assigned to user groups"""
    __tablename__ = "group_permissions"
    __table_args__ = (
        Index('ix_group_permission', 'group_id', 'permission'),
    )

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False)
    permission = Column(String(100), nullable=False)  # e.g., 'run_audits', 'modify_rules', etc.
    granted = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("UserGroupDB", back_populates="permissions")


class GroupModuleAccessDB(Base):
    """Module visibility per user group"""
    __tablename__ = "group_module_access"
    __table_args__ = (
        Index('ix_group_module_access', 'group_id', 'module_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False)
    module_name = Column(String(100), nullable=False)  # e.g., 'devices', 'audits', 'rules'
    can_access = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("UserGroupDB", back_populates="module_access")


class AuditLogDB(Base):
    """Audit log for user actions"""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('ix_audit_logs_user_timestamp', 'user_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    username = Column(String(100))  # Denormalized for deleted users
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    action = Column(String(100))  # create_device, run_audit, delete_rule, etc
    resource_type = Column(String(50))  # device, rule, audit, etc
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    user = relationship("UserDB")


class SystemModuleDB(Base):
    """System modules that can be enabled/disabled"""
    __tablename__ = "system_modules"

    id = Column(Integer, primary_key=True, index=True)
    module_name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    settings = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)


# ============================================================================
# Integration Hub
# ============================================================================

class IntegrationDB(Base):
    """External system integrations"""
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    integration_type = Column(String(50))  # git, netbox, servicenow, ansible, prometheus
    enabled = Column(Boolean, default=True)
    config = Column(JSON)  # Integration-specific configuration
    credentials = Column(JSON, nullable=True)  # Encrypted credentials
    last_sync = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    sync_interval_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# Remediation & Change Management
# ============================================================================

class RemediationTaskDB(Base):
    """Remediation tasks for audit failures"""
    __tablename__ = "remediation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    audit_result_id = Column(Integer, ForeignKey('audit_results.id', ondelete='SET NULL'), nullable=True)
    rule_name = Column(String(255))
    description = Column(Text)
    remediation_script = Column(Text)  # Generated fix script
    script_type = Column(String(50))  # netconf, ansible, manual
    status = Column(String(50), default="pending")  # pending, approved, in_progress, completed, failed
    priority = Column(String(20))  # critical, high, medium, low
    created_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    executed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_output = Column(Text, nullable=True)
    rollback_script = Column(Text, nullable=True)

    device = relationship("DeviceDB")
    audit_result = relationship("AuditResultDB")


# ============================================================================
# License Management Models
# ============================================================================

class LicenseDB(Base):
    """Software license information"""
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    license_key = Column(Text, unique=True, nullable=False)
    license_tier = Column(String(50), nullable=False)  # starter, professional, enterprise
    is_active = Column(Boolean, default=True)
    
    # Dates
    activated_at = Column(DateTime, nullable=True)
    issued_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_validated = Column(DateTime, nullable=True)
    
    # Quotas
    max_devices = Column(Integer, nullable=False)
    max_users = Column(Integer, nullable=False)
    max_storage_gb = Column(Integer, nullable=False)
    
    # Current usage (tracked)
    current_devices = Column(Integer, default=0)
    current_users = Column(Integer, default=0)
    current_storage_gb = Column(Float, default=0.0)
    
    # Enabled modules (JSON list)
    enabled_modules = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LicenseValidationLogDB(Base):
    """Log of license validation attempts"""
    __tablename__ = "license_validation_logs"
    __table_args__ = (
        Index('ix_license_logs_checked_at', 'checked_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey('licenses.id', ondelete='SET NULL'), nullable=True)
    license_key_attempted = Column(String(100), nullable=True)  # Partial key for security
    validation_result = Column(String(50), nullable=False)  # valid, expired, invalid, etc.
    validation_message = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)

    license = relationship("LicenseDB")


# ============================================================================
# Analytics & Intelligence Models
# ============================================================================

class ComplianceTrendDB(Base):
    """Compliance trend snapshots for analytics"""
    __tablename__ = "compliance_trends"
    __table_args__ = (
        Index('ix_compliance_trends_device_snapshot', 'device_id', 'snapshot_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), nullable=True)  # NULL = overall
    
    # Compliance metrics
    overall_compliance = Column(Float, default=0.0)
    compliance_change = Column(Float, default=0.0)  # Change from previous snapshot
    
    # Device counts
    total_devices = Column(Integer, default=0)
    compliant_devices = Column(Integer, default=0)
    failed_devices = Column(Integer, default=0)
    
    # Check counts
    total_checks = Column(Integer, default=0)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    warning_checks = Column(Integer, default=0)
    
    # Failure breakdown by severity
    critical_failures = Column(Integer, default=0)
    high_failures = Column(Integer, default=0)
    medium_failures = Column(Integer, default=0)
    low_failures = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("DeviceDB")


class ComplianceForecastDB(Base):
    """Compliance forecasts using predictive analytics"""
    __tablename__ = "compliance_forecasts"
    __table_args__ = (
        Index('ix_compliance_forecasts_device_date', 'device_id', 'forecast_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    forecast_date = Column(DateTime, index=True, nullable=False)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), nullable=True)  # NULL = overall
    
    # Predictions
    predicted_compliance = Column(Float, nullable=False)
    confidence_score = Column(Float, default=0.0)  # 0-1 confidence level
    predicted_failures = Column(Integer, default=0)
    
    # Model info
    training_data_points = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("DeviceDB")


class ComplianceAnomalyDB(Base):
    """Detected compliance anomalies"""
    __tablename__ = "compliance_anomalies"
    __table_args__ = (
        Index('ix_compliance_anomalies_device_detected', 'device_id', 'detected_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), nullable=True)  # NULL = overall
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Anomaly details
    anomaly_type = Column(String(100), nullable=False)  # compliance_drop, spike_failures, etc.
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.MEDIUM)
    description = Column(Text, nullable=False)
    
    # Statistical data
    z_score = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    
    # Acknowledgment
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("DeviceDB")


# ============================================================================
# Advanced Models - Using separate model files for reference
# ============================================================================
# Note: Advanced models are defined in separate files for documentation
# but we use the existing DB models in this file to avoid duplicate table definitions
# The separate model files serve as reference for API development

