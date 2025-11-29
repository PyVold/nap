"""
License Enforcement Middleware

Provides middleware and dependency injection for license enforcement:
- Module access control based on license tier
- User module permissions (admin-controlled)
- Quota enforcement (devices, users, storage)
- License upgrade/renewal handling
"""

from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, Callable
from functools import wraps

from database import get_db
import db_models
from shared.license_manager import license_manager
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LicenseEnforcer:
    """Centralized license enforcement"""
    
    def __init__(self):
        self.license_manager = license_manager
    
    def get_active_license_data(self, db: Session) -> Optional[dict]:
        """
        Get active license data from database
        
        Returns:
            Decoded license data or None if no active license
        """
        active_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.is_active == True
        ).first()
        
        if not active_license:
            return None
        
        # Validate the license
        validation = self.license_manager.validate_license(active_license.license_key)
        
        if not validation["valid"]:
            logger.warning(f"Active license is invalid: {validation['message']}")
            # Deactivate invalid license
            active_license.is_active = False
            db.commit()
            return None
        
        return validation["data"]
    
    def check_module_access(
        self,
        db: Session,
        module_name: str,
        user_id: Optional[int] = None
    ) -> dict:
        """
        Check if module is accessible based on license tier and user permissions
        
        Args:
            db: Database session
            module_name: Module to check
            user_id: User ID (optional, for user-specific permissions)
        
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "license_tier": str,
                "user_has_access": bool (if user_id provided)
            }
        """
        # Get active license
        license_data = self.get_active_license_data(db)
        
        if not license_data:
            return {
                "allowed": False,
                "reason": "no_license",
                "message": "No active license found"
            }
        
        tier = license_data.get("tier", "starter")
        
        # Check if license tier includes this module
        tier_has_module = self.license_manager.has_module(license_data, module_name)
        
        if not tier_has_module:
            return {
                "allowed": False,
                "reason": "module_not_in_tier",
                "license_tier": tier,
                "message": f"Module '{module_name}' not available in {tier} tier"
            }
        
        # If user_id provided, check user-specific permissions
        if user_id:
            user_has_access = self._user_can_access_module(db, user_id, module_name)
            
            if not user_has_access:
                return {
                    "allowed": False,
                    "reason": "user_permission_denied",
                    "license_tier": tier,
                    "user_has_access": False,
                    "message": f"User does not have access to module '{module_name}'"
                }
        
        return {
            "allowed": True,
            "reason": "granted",
            "license_tier": tier,
            "user_has_access": True if user_id else None
        }
    
    def _user_can_access_module(self, db: Session, user_id: int, module_name: str) -> bool:
        """
        Check if user has permission to access a specific module
        
        This checks:
        1. Superuser status (always has access)
        2. Group-based module access permissions
        """
        # Get user
        user = db.query(db_models.UserDB).filter(db_models.UserDB.id == user_id).first()
        
        if not user:
            return False
        
        # Superusers have access to all modules
        if user.is_superuser:
            return True
        
        # Get user's groups
        memberships = db.query(db_models.UserGroupMembershipDB).filter(
            db_models.UserGroupMembershipDB.user_id == user_id
        ).all()
        
        if not memberships:
            # No groups = no access (except superusers handled above)
            return False
        
        # Check module access in any of the user's groups
        for membership in memberships:
            group_id = membership.group_id
            
            # Check if group has module access
            module_access = db.query(db_models.GroupModuleAccessDB).filter(
                db_models.GroupModuleAccessDB.group_id == group_id,
                db_models.GroupModuleAccessDB.module_name == module_name
            ).first()
            
            # If found and can_access is True, grant access
            if module_access and module_access.can_access:
                return True
        
        # No group granted access
        return False
    
    def check_quota(
        self,
        db: Session,
        quota_type: str,
        requested_amount: int = 1
    ) -> dict:
        """
        Check if action would exceed quota limits
        
        Args:
            db: Database session
            quota_type: 'devices', 'users', or 'storage_gb'
            requested_amount: Amount to add (default 1)
        
        Returns:
            {
                "allowed": bool,
                "current": int,
                "max": int,
                "after_action": int,
                "reason": str
            }
        """
        license_data = self.get_active_license_data(db)
        
        if not license_data:
            return {
                "allowed": False,
                "current": 0,
                "max": 0,
                "after_action": 0,
                "reason": "no_license"
            }
        
        # Get current usage
        if quota_type == "devices":
            current = db.query(db_models.DeviceDB).count()
        elif quota_type == "users":
            current = db.query(db_models.UserDB).count()
        elif quota_type == "storage_gb":
            # Calculate storage from config backups
            current = self._calculate_storage_usage(db)
        else:
            return {
                "allowed": False,
                "current": 0,
                "max": 0,
                "after_action": 0,
                "reason": "invalid_quota_type"
            }
        
        # Get max allowed from license
        tier = license_data.get("tier", "starter")
        tier_config = self.license_manager.get_tier_info(tier)
        max_allowed = tier_config.get(f"max_{quota_type}", 0)
        
        # Check if after action would exceed
        after_action = current + requested_amount
        allowed = after_action <= max_allowed
        
        return {
            "allowed": allowed,
            "current": current,
            "max": max_allowed,
            "after_action": after_action,
            "reason": "within_quota" if allowed else "quota_exceeded"
        }
    
    def _calculate_storage_usage(self, db: Session) -> int:
        """
        Calculate total storage usage in GB
        
        Returns:
            Storage usage in GB (rounded up)
        """
        from sqlalchemy import func
        
        # Sum all config backup sizes
        total_bytes = db.query(
            func.coalesce(func.sum(db_models.ConfigBackupDB.size_bytes), 0)
        ).scalar()
        
        # Convert to GB (rounded up)
        total_gb = (total_bytes / (1024 * 1024 * 1024))
        
        return int(total_gb) + (1 if total_gb % 1 > 0 else 0)
    
    def update_license_usage(self, db: Session):
        """
        Update current usage stats in license record
        
        Should be called periodically or after significant changes
        """
        active_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.is_active == True
        ).first()
        
        if not active_license:
            return
        
        # Update counts
        active_license.current_devices = db.query(db_models.DeviceDB).count()
        active_license.current_users = db.query(db_models.UserDB).count()
        active_license.current_storage_gb = self._calculate_storage_usage(db)
        
        db.commit()
        logger.debug(f"Updated license usage: {active_license.current_devices} devices, "
                    f"{active_license.current_users} users, {active_license.current_storage_gb} GB")


# Singleton instance
license_enforcer = LicenseEnforcer()


# ============================================================================
# FastAPI Dependencies
# ============================================================================

def require_license_module(module_name: str):
    """
    Dependency to enforce module access based on license
    
    Usage:
        @router.get("/schedules")
        def get_schedules(
            db: Session = Depends(get_db),
            _: None = Depends(require_license_module("scheduled_audits"))
        ):
            ...
    """
    def dependency(db: Session = Depends(get_db)):
        result = license_enforcer.check_module_access(db, module_name)
        
        if not result["allowed"]:
            if result["reason"] == "no_license":
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "No active license",
                        "message": "Please activate a license to use this feature",
                        "action": "activate_license"
                    }
                )
            elif result["reason"] == "module_not_in_tier":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Module not available",
                        "module": module_name,
                        "current_tier": result.get("license_tier"),
                        "message": result.get("message"),
                        "action": "upgrade_license"
                    }
                )
        
        return None
    
    return dependency


def require_license_module_and_user_access(module_name: str):
    """
    Dependency to enforce both license tier AND user-specific module access
    
    Usage:
        @router.get("/schedules")
        def get_schedules(
            db: Session = Depends(get_db),
            current_user: dict = Depends(get_current_user),
            _: None = Depends(require_license_module_and_user_access("scheduled_audits"))
        ):
            ...
    """
    def dependency(
        db: Session = Depends(get_db),
        current_user: dict = Depends(lambda: None)  # Will be injected
    ):
        user_id = current_user.get("user_id") if current_user else None
        result = license_enforcer.check_module_access(db, module_name, user_id)
        
        if not result["allowed"]:
            if result["reason"] == "no_license":
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "No active license",
                        "message": "Please activate a license to use this feature",
                        "action": "activate_license"
                    }
                )
            elif result["reason"] == "module_not_in_tier":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Module not available in license",
                        "module": module_name,
                        "current_tier": result.get("license_tier"),
                        "message": result.get("message"),
                        "action": "upgrade_license"
                    }
                )
            elif result["reason"] == "user_permission_denied":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Access denied",
                        "module": module_name,
                        "message": result.get("message"),
                        "action": "contact_admin"
                    }
                )
        
        return None
    
    return dependency


def enforce_quota(quota_type: str, amount: int = 1):
    """
    Dependency to enforce quota limits before action
    
    Usage:
        @router.post("/devices")
        def create_device(
            device_data: DeviceCreate,
            db: Session = Depends(get_db),
            _: None = Depends(enforce_quota("devices", 1))
        ):
            ...
    """
    def dependency(db: Session = Depends(get_db)):
        result = license_enforcer.check_quota(db, quota_type, amount)
        
        if not result["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Quota exceeded",
                    "quota_type": quota_type,
                    "current": result["current"],
                    "max": result["max"],
                    "requested": amount,
                    "message": f"Cannot add {amount} more {quota_type}. "
                              f"Current: {result['current']}/{result['max']}",
                    "action": "upgrade_license"
                }
            )
        
        return None
    
    return dependency


__all__ = [
    "license_enforcer",
    "LicenseEnforcer",
    "require_license_module",
    "require_license_module_and_user_access",
    "enforce_quota"
]
