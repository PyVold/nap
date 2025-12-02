"""
Admin Settings API Routes

Provides endpoints for:
- System configuration
- Backup configuration
- Email/SMTP settings
- General admin controls
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import time

from deps import get_db, get_current_user
import db_models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Settings"])


# ============================================================================
# Request/Response Models
# ============================================================================

class BackupConfigRequest(BaseModel):
    """Configuration for automatic config backups"""
    enabled: bool = True
    scheduleType: str = Field(..., pattern="^(hourly|every6hours|every12hours|daily|weekly|monthly)$")
    scheduleTime: str = Field(..., description="Time in HH:MM format")
    retentionDays: int = Field(30, ge=1, le=365)
    maxBackupsPerDevice: int = Field(10, ge=1, le=100)
    compressBackups: bool = True
    notifyOnFailure: bool = True


class BackupConfigResponse(BaseModel):
    """Current backup configuration"""
    enabled: bool
    scheduleType: str
    scheduleTime: str
    retentionDays: int
    maxBackupsPerDevice: int
    compressBackups: bool
    notifyOnFailure: bool


class SystemSettingsRequest(BaseModel):
    """General system settings"""
    platformName: str = Field("Network Audit Platform", max_length=100)
    smtpEnabled: bool = False
    smtpServer: Optional[str] = None
    smtpPort: int = Field(587, ge=1, le=65535)
    smtpUsername: Optional[str] = None
    smtpPassword: Optional[str] = None
    defaultSessionTimeout: int = Field(3600, ge=300, le=86400)
    enableAuditLogs: bool = True
    maxFailedLogins: int = Field(5, ge=1, le=20)


class SystemSettingsResponse(BaseModel):
    """Current system settings"""
    platformName: str
    smtpEnabled: bool
    smtpServer: Optional[str]
    smtpPort: int
    smtpUsername: Optional[str]
    smtpPassword: Optional[str] = None  # Never return actual password
    defaultSessionTimeout: int
    enableAuditLogs: bool
    maxFailedLogins: int


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/backup-config", response_model=BackupConfigResponse)
async def get_backup_config(
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_user)
):
    """
    Get current backup configuration

    Returns the current settings for automatic config backups
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get config from database (stored in a settings table)
    config = db.query(db_models.SystemConfigDB).filter(
        db_models.SystemConfigDB.key == "backup_config"
    ).first()

    if not config:
        # Return defaults if not configured yet
        return BackupConfigResponse(
            enabled=True,
            scheduleType="daily",
            scheduleTime="02:00",
            retentionDays=30,
            maxBackupsPerDevice=10,
            compressBackups=True,
            notifyOnFailure=True
        )

    import json
    settings = json.loads(config.value)
    return BackupConfigResponse(**settings)


@router.post("/backup-config", response_model=BackupConfigResponse)
async def save_backup_config(
    request: BackupConfigRequest,
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_user)
):
    """
    Save backup configuration

    Updates the automatic backup settings
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    import json

    # Get or create config entry
    config = db.query(db_models.SystemConfigDB).filter(
        db_models.SystemConfigDB.key == "backup_config"
    ).first()

    config_dict = request.dict()

    if config:
        config.value = json.dumps(config_dict)
    else:
        config = db_models.SystemConfigDB(
            key="backup_config",
            value=json.dumps(config_dict),
            description="Automatic backup configuration"
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    logger.info(f"Backup config updated by {current_user.username}")

    # Reload backup scheduler with new settings
    try:
        import sys
        sys.path.insert(0, '/app')
        from shared.backup_scheduler import backup_scheduler
        backup_scheduler.load_and_update_schedule(db)
        logger.info("✅ Backup scheduler reloaded with new configuration")
    except Exception as e:
        logger.error(f"❌ Error reloading backup scheduler: {e}")
        # Don't fail the request if scheduler reload fails

    return BackupConfigResponse(**config_dict)


@router.get("/system-settings", response_model=SystemSettingsResponse)
async def get_system_settings(
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_user)
):
    """
    Get current system settings

    Returns general system configuration
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    config = db.query(db_models.SystemConfigDB).filter(
        db_models.SystemConfigDB.key == "system_settings"
    ).first()

    if not config:
        # Return defaults
        return SystemSettingsResponse(
            platformName="Network Audit Platform",
            smtpEnabled=False,
            smtpServer=None,
            smtpPort=587,
            smtpUsername=None,
            smtpPassword=None,
            defaultSessionTimeout=3600,
            enableAuditLogs=True,
            maxFailedLogins=5
        )

    import json
    settings = json.loads(config.value)

    # Don't return actual password
    if 'smtpPassword' in settings:
        settings['smtpPassword'] = '********' if settings['smtpPassword'] else None

    return SystemSettingsResponse(**settings)


@router.post("/system-settings", response_model=SystemSettingsResponse)
async def save_system_settings(
    request: SystemSettingsRequest,
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_user)
):
    """
    Save system settings

    Updates general system configuration
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    import json

    config = db.query(db_models.SystemConfigDB).filter(
        db_models.SystemConfigDB.key == "system_settings"
    ).first()

    config_dict = request.dict()

    # Handle password specially - only update if not placeholder
    if config:
        existing = json.loads(config.value)
        if config_dict.get('smtpPassword') == '********':
            # Don't update password if it's the placeholder
            config_dict['smtpPassword'] = existing.get('smtpPassword')

    if config:
        config.value = json.dumps(config_dict)
    else:
        config = db_models.SystemConfigDB(
            key="system_settings",
            value=json.dumps(config_dict),
            description="General system settings"
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    logger.info(f"System settings updated by {current_user.username}")

    # Return without actual password
    config_dict['smtpPassword'] = '********' if config_dict.get('smtpPassword') else None

    return SystemSettingsResponse(**config_dict)


@router.post("/test-email")
async def test_email_config(
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_user)
):
    """
    Test SMTP email configuration

    Sends a test email to verify settings
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get SMTP settings
    config = db.query(db_models.SystemConfigDB).filter(
        db_models.SystemConfigDB.key == "system_settings"
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="SMTP not configured")

    import json
    settings = json.loads(config.value)

    if not settings.get('smtpEnabled'):
        raise HTTPException(status_code=400, detail="SMTP is not enabled")

    # Send test email using notification service
    try:
        import sys
        sys.path.insert(0, '/app')
        from shared.notification_service import notification_service

        result = notification_service.send_test_email(current_user.email, db)

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

# ============================================================================
# Notification Settings
# ============================================================================

class NotificationSettingsRequest(BaseModel):
    """Email notification settings"""
    emailEnabled: bool = True
    emailRecipients: List[EmailStr] = []
    notifyOnBackupFailure: bool = True
    notifyOnLicenseExpiry: bool = True
    notifyOnQuotaExceeded: bool = True
    notifyOnAuditFailure: bool = True


class NotificationSettingsResponse(BaseModel):
    """Current notification settings"""
    emailEnabled: bool
    emailRecipients: List[str]
    notifyOnBackupFailure: bool
    notifyOnLicenseExpiry: bool
    notifyOnQuotaExceeded: bool
    notifyOnAuditFailure: bool


@router.get("/notification-settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_user)
):
    """
    Get current notification settings

    Returns email notification configuration
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    config = db.query(db_models.SystemConfigDB).filter(
        db_models.SystemConfigDB.key == "notification_settings"
    ).first()

    if not config:
        # Return defaults
        return NotificationSettingsResponse(
            emailEnabled=True,
            emailRecipients=[],
            notifyOnBackupFailure=True,
            notifyOnLicenseExpiry=True,
            notifyOnQuotaExceeded=True,
            notifyOnAuditFailure=True
        )

    import json
    settings = json.loads(config.value)
    return NotificationSettingsResponse(**settings)


@router.post("/notification-settings", response_model=NotificationSettingsResponse)
async def save_notification_settings(
    request: NotificationSettingsRequest,
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_user)
):
    """
    Save notification settings

    Updates email notification configuration
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    import json

    config = db.query(db_models.SystemConfigDB).filter(
        db_models.SystemConfigDB.key == "notification_settings"
    ).first()

    config_dict = request.dict()

    if config:
        config.value = json.dumps(config_dict)
    else:
        config = db_models.SystemConfigDB(
            key="notification_settings",
            value=json.dumps(config_dict),
            description="Email notification settings"
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    logger.info(f"Notification settings updated by {current_user.username}")

    return NotificationSettingsResponse(**config_dict)
