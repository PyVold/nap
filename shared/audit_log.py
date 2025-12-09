# ============================================================================
# shared/audit_log.py - Audit logging for compliance and security
# ============================================================================

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.orm import Session
from pydantic import BaseModel

from shared.logger import setup_logger

logger = setup_logger(__name__)


class AuditAction(str, Enum):
    """Types of auditable actions"""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_PASSWORD_CHANGE = "user_password_change"
    USER_ROLE_CHANGE = "user_role_change"

    # Device management
    DEVICE_CREATE = "device_create"
    DEVICE_UPDATE = "device_update"
    DEVICE_DELETE = "device_delete"
    DEVICE_DISCOVER = "device_discover"

    # Configuration
    CONFIG_BACKUP = "config_backup"
    CONFIG_RESTORE = "config_restore"
    CONFIG_DEPLOY = "config_deploy"

    # Audit operations
    AUDIT_RUN = "audit_run"
    AUDIT_SCHEDULE = "audit_schedule"

    # Rules
    RULE_CREATE = "rule_create"
    RULE_UPDATE = "rule_update"
    RULE_DELETE = "rule_delete"

    # System
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"

    # Security events
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditLogEntry(BaseModel):
    """Audit log entry model"""
    timestamp: datetime
    action: AuditAction
    user_id: Optional[int] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    status: str = "success"  # success, failure, error


class AuditLogger:
    """
    Audit logger for tracking security and compliance events.

    Supports multiple backends:
    - Database (default)
    - File-based logging
    - External SIEM integration (via webhooks)
    """

    def __init__(self, db_session_factory=None):
        self.db_session_factory = db_session_factory
        self.log_to_file = os.environ.get("AUDIT_LOG_FILE", "").lower() == "true"
        self.siem_webhook = os.environ.get("AUDIT_SIEM_WEBHOOK")

    def log(
        self,
        action: AuditAction,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        db: Optional[Session] = None
    ):
        """
        Log an auditable event.

        Args:
            action: The type of action being logged
            user_id: ID of user performing action
            username: Username of user performing action
            ip_address: Client IP address
            resource_type: Type of resource affected (device, user, rule, etc.)
            resource_id: ID of affected resource
            details: Additional context about the action
            status: success, failure, or error
            db: Optional database session
        """
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            action=action,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            status=status
        )

        # Log to structured logger
        log_data = entry.dict()
        log_data["timestamp"] = log_data["timestamp"].isoformat()
        log_data["action"] = log_data["action"].value

        if status == "failure" or action in [
            AuditAction.LOGIN_FAILED,
            AuditAction.PERMISSION_DENIED,
            AuditAction.SUSPICIOUS_ACTIVITY
        ]:
            logger.warning(f"AUDIT: {json.dumps(log_data)}")
        else:
            logger.info(f"AUDIT: {json.dumps(log_data)}")

        # Store in database if session provided
        if db:
            self._store_to_db(entry, db)

        # Send to SIEM if configured
        if self.siem_webhook:
            self._send_to_siem(entry)

    def _store_to_db(self, entry: AuditLogEntry, db: Session):
        """Store audit entry in database"""
        try:
            from db_models import AuditLogDB

            db_entry = AuditLogDB(
                timestamp=entry.timestamp,
                action=entry.action.value,
                user_id=entry.user_id,
                username=entry.username,
                ip_address=entry.ip_address,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                details=json.dumps(entry.details) if entry.details else None,
                status=entry.status
            )
            db.add(db_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to store audit log: {e}")
            # Don't let audit logging failures break the application
            db.rollback()

    def _send_to_siem(self, entry: AuditLogEntry):
        """Send audit entry to external SIEM"""
        try:
            import httpx

            payload = entry.dict()
            payload["timestamp"] = payload["timestamp"].isoformat()
            payload["action"] = payload["action"].value

            # Fire and forget - don't block on SIEM response
            httpx.post(
                self.siem_webhook,
                json=payload,
                timeout=5.0
            )
        except Exception as e:
            logger.error(f"Failed to send to SIEM: {e}")

    def log_login_success(
        self,
        user_id: int,
        username: str,
        ip_address: str,
        db: Optional[Session] = None
    ):
        """Log successful login"""
        self.log(
            action=AuditAction.LOGIN_SUCCESS,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            status="success",
            db=db
        )

    def log_login_failed(
        self,
        username: str,
        ip_address: str,
        reason: str = "invalid_credentials",
        db: Optional[Session] = None
    ):
        """Log failed login attempt"""
        self.log(
            action=AuditAction.LOGIN_FAILED,
            username=username,
            ip_address=ip_address,
            details={"reason": reason},
            status="failure",
            db=db
        )

    def log_device_change(
        self,
        action: AuditAction,
        device_id: int,
        user_id: int,
        username: str,
        ip_address: str,
        changes: Optional[Dict] = None,
        db: Optional[Session] = None
    ):
        """Log device-related changes"""
        self.log(
            action=action,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource_type="device",
            resource_id=str(device_id),
            details={"changes": changes} if changes else None,
            db=db
        )

    def log_permission_denied(
        self,
        user_id: Optional[int],
        username: Optional[str],
        ip_address: str,
        resource: str,
        required_permission: str,
        db: Optional[Session] = None
    ):
        """Log permission denied event"""
        self.log(
            action=AuditAction.PERMISSION_DENIED,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details={
                "resource": resource,
                "required_permission": required_permission
            },
            status="failure",
            db=db
        )


# Global audit logger instance
_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance"""
    return _audit_logger


def audit_log(
    action: AuditAction,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status: str = "success",
    db: Optional[Session] = None
):
    """Convenience function for audit logging"""
    _audit_logger.log(
        action=action,
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        status=status,
        db=db
    )
