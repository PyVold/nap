"""
License Enforcement Service

High-level service for license enforcement operations:
- Device limit enforcement with queue management
- User creation limits
- Storage management
- License upgrade handling
- Admin module permission management
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime

import db_models
from shared.license_middleware import license_enforcer
from shared.license_manager import license_manager, MODULE_DISPLAY_NAMES
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LicenseEnforcementService:
    """Service for license enforcement operations"""
    
    def __init__(self):
        self.enforcer = license_enforcer
        self.manager = license_manager
    
    # ============================================================================
    # Module Permission Management (Admin Controls)
    # ============================================================================
    
    def set_group_module_access(
        self,
        db: Session,
        group_id: int,
        module_permissions: Dict[str, bool]
    ) -> bool:
        """
        Set module access permissions for a user group
        
        Args:
            db: Database session
            group_id: User group ID
            module_permissions: Dict mapping module names to access boolean
                               e.g., {"scheduled_audits": True, "api_access": False}
        
        Returns:
            True if successful
        
        Raises:
            ValueError: If module not available in current license tier
        """
        # Verify group exists
        group = db.query(db_models.UserGroupDB).filter(
            db_models.UserGroupDB.id == group_id
        ).first()
        
        if not group:
            raise ValueError(f"User group {group_id} not found")
        
        # Get current license data
        license_data = self.enforcer.get_active_license_data(db)
        
        if not license_data:
            raise ValueError("No active license found")
        
        # Validate each module is in the license tier
        for module_name, access_granted in module_permissions.items():
            if access_granted:
                # Only check if we're granting access
                if not self.manager.has_module(license_data, module_name):
                    tier = license_data.get("tier", "unknown")
                    raise ValueError(
                        f"Module '{module_name}' is not available in {tier} tier. "
                        "Please upgrade license first."
                    )
        
        # Remove existing module access for this group
        db.query(db_models.GroupModuleAccessDB).filter(
            db_models.GroupModuleAccessDB.group_id == group_id
        ).delete()
        
        # Add new module access records
        for module_name, can_access in module_permissions.items():
            module_access = db_models.GroupModuleAccessDB(
                group_id=group_id,
                module_name=module_name,
                can_access=can_access
            )
            db.add(module_access)
        
        db.commit()
        
        logger.info(f"Updated module access for group {group_id}: {module_permissions}")
        return True
    
    def get_available_modules_for_license(self, db: Session) -> List[Dict]:
        """
        Get all modules available in the current license tier
        
        Returns:
            List of dicts with module info:
            [
                {
                    "key": "scheduled_audits",
                    "name": "Scheduled Audits",
                    "available": True
                },
                ...
            ]
        """
        license_data = self.enforcer.get_active_license_data(db)
        
        if not license_data:
            return []
        
        tier = license_data.get("tier", "starter")
        tier_modules = self.manager.get_tier_modules(tier)
        
        result = []
        for module_key, module_name in MODULE_DISPLAY_NAMES.items():
            available = module_key in tier_modules or "all" in tier_modules
            result.append({
                "key": module_key,
                "name": module_name,
                "available": available
            })
        
        return result
    
    def get_group_module_access(self, db: Session, group_id: int) -> Dict[str, bool]:
        """
        Get module access permissions for a user group
        
        Returns:
            Dict mapping module names to access boolean
        """
        module_access_records = db.query(db_models.GroupModuleAccessDB).filter(
            db_models.GroupModuleAccessDB.group_id == group_id
        ).all()
        
        return {
            record.module_name: record.can_access
            for record in module_access_records
        }
    
    # ============================================================================
    # Device Limit Enforcement
    # ============================================================================
    
    def check_can_add_devices(self, db: Session, count: int = 1) -> Dict:
        """
        Check if devices can be added within license limits
        
        Returns:
            {
                "allowed": bool,
                "current": int,
                "max": int,
                "available_slots": int,
                "message": str
            }
        """
        result = self.enforcer.check_quota(db, "devices", count)
        
        available_slots = result["max"] - result["current"]
        
        return {
            "allowed": result["allowed"],
            "current": result["current"],
            "max": result["max"],
            "available_slots": available_slots,
            "message": result.get("reason", "")
        }
    
    def enforce_device_limit_on_discovery(
        self,
        db: Session,
        discovered_devices: List[Dict]
    ) -> Dict:
        """
        Enforce device limits during discovery
        
        If more devices discovered than allowed:
        - Take first N devices (FIFO queue)
        - Log warning about remaining devices
        
        Args:
            db: Database session
            discovered_devices: List of discovered device data
        
        Returns:
            {
                "accepted": List[Dict],  # Devices that can be added
                "rejected": List[Dict],  # Devices that exceeded quota
                "message": str
            }
        """
        # Check current quota
        check_result = self.check_can_add_devices(db, len(discovered_devices))
        
        if check_result["allowed"]:
            # All devices can be added
            return {
                "accepted": discovered_devices,
                "rejected": [],
                "message": f"All {len(discovered_devices)} devices within quota"
            }
        
        # Some devices need to be rejected
        available_slots = check_result["available_slots"]
        
        if available_slots <= 0:
            logger.warning(
                f"Device quota exceeded. Cannot add any of {len(discovered_devices)} "
                f"discovered devices. Current: {check_result['current']}/{check_result['max']}"
            )
            return {
                "accepted": [],
                "rejected": discovered_devices,
                "message": f"Device quota exceeded ({check_result['current']}/{check_result['max']}). "
                          f"Upgrade license to add more devices."
            }
        
        # Take first N devices
        accepted = discovered_devices[:available_slots]
        rejected = discovered_devices[available_slots:]
        
        logger.warning(
            f"Device quota limit reached. Accepting {len(accepted)} of {len(discovered_devices)} "
            f"discovered devices. {len(rejected)} devices rejected. "
            f"License allows {check_result['max']} devices total."
        )
        
        return {
            "accepted": accepted,
            "rejected": rejected,
            "message": f"Device limit reached. Added {len(accepted)} devices, "
                      f"rejected {len(rejected)} devices. Upgrade license for more capacity."
        }
    
    # ============================================================================
    # User Creation Limits
    # ============================================================================
    
    def check_can_create_user(self, db: Session) -> Dict:
        """
        Check if a new user can be created
        
        Returns:
            {
                "allowed": bool,
                "current": int,
                "max": int,
                "message": str
            }
        """
        result = self.enforcer.check_quota(db, "users", 1)
        
        return {
            "allowed": result["allowed"],
            "current": result["current"],
            "max": result["max"],
            "message": "Can create user" if result["allowed"] else 
                      f"User limit reached ({result['current']}/{result['max']}). Upgrade license."
        }
    
    def enforce_user_creation_limit(self, db: Session):
        """
        Enforce user creation limit (raises exception if exceeded)
        
        Raises:
            ValueError: If user limit reached
        """
        check_result = self.check_can_create_user(db)
        
        if not check_result["allowed"]:
            raise ValueError(
                f"Cannot create user: License limit reached "
                f"({check_result['current']}/{check_result['max']}). "
                "Please upgrade your license to add more users."
            )
    
    # ============================================================================
    # Storage Management
    # ============================================================================
    
    def check_storage_quota(self, db: Session, additional_gb: int = 0) -> Dict:
        """
        Check storage quota status
        
        Args:
            db: Database session
            additional_gb: Additional GB to check (default 0)
        
        Returns:
            {
                "allowed": bool,
                "current_gb": int,
                "max_gb": int,
                "used_percentage": float,
                "message": str
            }
        """
        result = self.enforcer.check_quota(db, "storage_gb", additional_gb)
        
        used_percentage = (result["current"] / result["max"] * 100) if result["max"] > 0 else 0
        
        return {
            "allowed": result["allowed"],
            "current_gb": result["current"],
            "max_gb": result["max"],
            "used_percentage": round(used_percentage, 1),
            "message": "Within storage quota" if result["allowed"] else 
                      f"Storage quota exceeded ({result['current']} GB / {result['max']} GB)"
        }
    
    def enforce_storage_limit(self, db: Session, backup_size_bytes: int):
        """
        Enforce storage limit before creating backup
        
        Args:
            db: Database session
            backup_size_bytes: Size of backup to be created
        
        Raises:
            ValueError: If storage limit would be exceeded
        """
        # Convert bytes to GB (round up)
        backup_size_gb = (backup_size_bytes / (1024 * 1024 * 1024))
        backup_size_gb = int(backup_size_gb) + (1 if backup_size_gb % 1 > 0 else 0)
        
        check_result = self.check_storage_quota(db, backup_size_gb)
        
        if not check_result["allowed"]:
            raise ValueError(
                f"Cannot create backup: Storage quota exceeded. "
                f"Current: {check_result['current_gb']} GB, "
                f"Max: {check_result['max_gb']} GB. "
                f"Backup size: {backup_size_gb} GB. "
                "Please upgrade your license for more storage."
            )
    
    def cleanup_old_backups_if_needed(self, db: Session) -> Dict:
        """
        Clean up old backups if storage quota is exceeded
        
        Returns:
            {
                "cleaned": int,  # Number of backups deleted
                "freed_gb": int,  # Storage freed
                "message": str
            }
        """
        check_result = self.check_storage_quota(db)
        
        if check_result["allowed"]:
            return {
                "cleaned": 0,
                "freed_gb": 0,
                "message": "Storage within quota, no cleanup needed"
            }
        
        # Get oldest backups (keep at least 1 per device)
        from sqlalchemy import func
        
        # Find devices with multiple backups
        devices_with_backups = db.query(
            db_models.ConfigBackupDB.device_id,
            func.count(db_models.ConfigBackupDB.id).label('backup_count')
        ).group_by(
            db_models.ConfigBackupDB.device_id
        ).having(
            func.count(db_models.ConfigBackupDB.id) > 1
        ).all()
        
        total_deleted = 0
        total_freed_bytes = 0
        
        for device_id, backup_count in devices_with_backups:
            # Get oldest backups for this device (keep most recent)
            old_backups = db.query(db_models.ConfigBackupDB).filter(
                db_models.ConfigBackupDB.device_id == device_id
            ).order_by(
                db_models.ConfigBackupDB.timestamp.asc()
            ).limit(backup_count - 1).all()
            
            for backup in old_backups:
                total_freed_bytes += backup.size_bytes or 0
                db.delete(backup)
                total_deleted += 1
            
            # Check if we're back within quota
            db.commit()
            check_result = self.check_storage_quota(db)
            if check_result["allowed"]:
                break
        
        total_freed_gb = total_freed_bytes / (1024 * 1024 * 1024)
        
        logger.info(
            f"Cleaned up {total_deleted} old backups, "
            f"freed {total_freed_gb:.2f} GB"
        )
        
        return {
            "cleaned": total_deleted,
            "freed_gb": round(total_freed_gb, 2),
            "message": f"Deleted {total_deleted} old backups to free up space"
        }
    
    # ============================================================================
    # License Upgrade/Renewal Handling
    # ============================================================================
    
    def handle_license_upgrade(self, db: Session, old_tier: str, new_tier: str) -> Dict:
        """
        Handle license upgrade - update permissions and quotas
        
        Args:
            db: Database session
            old_tier: Previous license tier
            new_tier: New license tier
        
        Returns:
            {
                "success": bool,
                "changes": List[str],
                "message": str
            }
        """
        changes = []
        
        # Get old and new tier configs
        old_config = self.manager.get_tier_info(old_tier)
        new_config = self.manager.get_tier_info(new_tier)
        
        # Check module additions
        old_modules = set(self.manager.get_tier_modules(old_tier))
        new_modules = set(self.manager.get_tier_modules(new_tier))
        added_modules = new_modules - old_modules
        
        if added_modules:
            changes.append(
                f"Added modules: {', '.join(added_modules)}"
            )
        
        # Check quota increases
        for quota_type in ["max_devices", "max_users", "max_storage_gb"]:
            old_quota = old_config.get(quota_type, 0)
            new_quota = new_config.get(quota_type, 0)
            
            if new_quota > old_quota:
                quota_name = quota_type.replace("max_", "").replace("_", " ").title()
                if new_quota >= 999999:
                    changes.append(f"{quota_name}: {old_quota} → Unlimited")
                else:
                    changes.append(f"{quota_name}: {old_quota} → {new_quota}")
        
        # Update license usage
        self.enforcer.update_license_usage(db)
        
        logger.info(f"License upgraded from {old_tier} to {new_tier}. Changes: {changes}")
        
        return {
            "success": True,
            "changes": changes,
            "message": f"License successfully upgraded from {old_tier} to {new_tier}"
        }
    
    def handle_license_renewal(self, db: Session) -> Dict:
        """
        Handle license renewal - validate and update timestamps
        
        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        # Update license usage stats
        self.enforcer.update_license_usage(db)
        
        # Get active license
        active_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.is_active == True
        ).first()
        
        if not active_license:
            return {
                "success": False,
                "message": "No active license found"
            }
        
        # Update last validated timestamp
        active_license.last_validated = datetime.utcnow()
        db.commit()
        
        logger.info(f"License renewed for {active_license.customer_email}")
        
        return {
            "success": True,
            "message": "License renewed successfully"
        }


# Singleton instance
license_enforcement_service = LicenseEnforcementService()
