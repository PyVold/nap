"""
License Manager - Validation and Feature Gating

Handles:
- License key validation and decryption
- Feature access checks
- Quota enforcement
- Tier-based module access
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# License Tier Definitions
# ============================================================================

LICENSE_TIERS = {
    "starter": {
        "name": "Starter",
        "max_devices": 10,
        "max_users": 2,
        "max_storage_gb": 5,
        "modules": [
            "devices", "manual_audits", "basic_rules", "health_checks"
        ]
    },
    "professional": {
        "name": "Professional",
        "max_devices": 100,
        "max_users": 10,
        "max_storage_gb": 50,
        "modules": [
            "devices", "device_groups", "device_import", "discovery",
            "manual_audits", "scheduled_audits", "basic_rules", "rule_templates",
            "config_backups", "drift_detection", "webhooks",
            "health_checks", "hardware_inventory", "api_access"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "max_devices": 999999,  # Unlimited
        "max_users": 999999,
        "max_storage_gb": 999999,
        "modules": ["all"]  # All features
    }
}

# Module display names for UI
MODULE_DISPLAY_NAMES = {
    "devices": "Device Management",
    "device_groups": "Device Groups",
    "device_import": "Device Import",
    "discovery": "Device Discovery",
    "manual_audits": "Manual Audits",
    "scheduled_audits": "Scheduled Audits",
    "basic_rules": "Basic Audit Rules",
    "rule_templates": "Rule Templates",
    "api_access": "API Access",
    "config_backups": "Configuration Backups",
    "drift_detection": "Drift Detection",
    "webhooks": "Webhook Notifications",
    "health_checks": "Health Monitoring",
    "hardware_inventory": "Hardware Inventory",
    "workflow_automation": "Workflow Automation",
    "topology": "Network Topology Maps",
    "ai_features": "AI-Powered Features",
    "integrations": "Advanced Integrations",
    "sso": "SSO & SAML Authentication",
    "analytics": "Analytics & Reporting",
    "remediation": "Remediation Tasks"
}


# ============================================================================
# License Manager Class
# ============================================================================

class LicenseManager:
    """Manages license validation and feature gating"""
    
    def __init__(self):
        """Initialize license manager with encryption key"""
        # Get encryption key from environment
        key = os.getenv("LICENSE_ENCRYPTION_KEY")
        
        # List of invalid default values
        invalid_defaults = [
            "GENERATE_SECURE_KEY_BEFORE_PRODUCTION",
            "change-me",
            "secret",
            "your-secret-key"
        ]
        
        # Check if key is missing or set to an invalid default
        if not key or key in invalid_defaults:
            if key:
                logger.warning(f"LICENSE_ENCRYPTION_KEY is set to an insecure default value: {key}")
            else:
                logger.warning("LICENSE_ENCRYPTION_KEY not set")
            
            # Generate a valid temporary key for development
            key = Fernet.generate_key().decode()
            logger.info("Generated temporary Fernet key for this session")
            logger.info("To generate a permanent key, run:")
            logger.info("  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        
        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"Failed to initialize cipher: {e}")
            # Fallback to a valid key for dev
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            logger.info("Fallback: Generated new temporary Fernet key")
        
        self.secret_salt = os.getenv("LICENSE_SECRET_SALT", "network-audit-platform-salt-2025")
    
    def validate_license(self, license_key: str) -> Dict:
        """
        Validate and decode a license key
        
        Returns:
            {
                "valid": bool,
                "reason": str,  # valid, expired, invalid, tampered
                "message": str,
                "data": dict or None  # License payload if valid
            }
        """
        try:
            # Decrypt the license key
            decrypted = self.cipher.decrypt(license_key.encode())
            data = json.loads(decrypted.decode())
            
            # Verify signature to prevent tampering
            signature = data.pop("signature", None)
            if not signature:
                return {
                    "valid": False,
                    "reason": "invalid",
                    "message": "License signature missing",
                    "data": None
                }
            
            # Recalculate signature
            data_str = json.dumps(data, sort_keys=True)
            expected_sig = hashlib.sha256(f"{data_str}{self.secret_salt}".encode()).hexdigest()
            
            if signature != expected_sig:
                logger.warning("License signature mismatch - possible tampering")
                return {
                    "valid": False,
                    "reason": "tampered",
                    "message": "License signature invalid - possible tampering detected",
                    "data": None
                }
            
            # Check expiration
            expires_at_str = data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.utcnow() > expires_at:
                    return {
                        "valid": False,
                        "reason": "expired",
                        "message": f"License expired on {expires_at.date()}",
                        "data": data
                    }
            
            # License is valid
            return {
                "valid": True,
                "reason": "valid",
                "message": "License is valid and active",
                "data": data
            }
        
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return {
                "valid": False,
                "reason": "invalid",
                "message": f"Invalid license format: {str(e)}",
                "data": None
            }
    
    def has_module(self, license_data: Dict, module_name: str) -> bool:
        """
        Check if license has access to a specific module
        
        Args:
            license_data: Decoded license payload
            module_name: Module to check (e.g., "scheduled_audits")
        
        Returns:
            True if module is enabled, False otherwise
        """
        if not license_data:
            return False
        
        tier = license_data.get("tier", "starter").lower()
        
        # Enterprise has access to everything
        if tier == "enterprise":
            return True
        
        # Check tier definitions
        tier_config = LICENSE_TIERS.get(tier, {})
        allowed_modules = tier_config.get("modules", [])
        
        # Check if "all" is in modules (enterprise shortcut)
        if "all" in allowed_modules:
            return True
        
        # Check if specific module is enabled
        return module_name in allowed_modules
    
    def check_quota(
        self,
        license_data: Dict,
        quota_type: str,
        current_value: int
    ) -> Tuple[bool, int, str]:
        """
        Check if within quota limits
        
        Args:
            license_data: Decoded license payload
            quota_type: Type of quota (devices, users, storage_gb)
            current_value: Current usage
        
        Returns:
            (within_quota, max_allowed, message)
        """
        if not license_data:
            return False, 0, "No valid license"
        
        tier = license_data.get("tier", "starter").lower()
        tier_config = LICENSE_TIERS.get(tier, {})
        
        # Get max quota from license data or tier defaults
        quota_key = f"max_{quota_type}"
        max_allowed = license_data.get(quota_key) or tier_config.get(quota_key, 0)
        
        # Check if within quota
        within_quota = current_value < max_allowed
        
        if within_quota:
            message = f"Within quota: {current_value}/{max_allowed}"
        else:
            message = f"Quota exceeded: {current_value}/{max_allowed} - Upgrade required"
        
        return within_quota, max_allowed, message
    
    def get_tier_info(self, tier: str) -> Dict:
        """Get information about a license tier"""
        return LICENSE_TIERS.get(tier.lower(), LICENSE_TIERS["starter"])
    
    def get_all_tiers(self) -> Dict:
        """Get all available license tiers"""
        return LICENSE_TIERS
    
    def get_module_display_name(self, module_name: str) -> str:
        """Get human-readable name for a module"""
        return MODULE_DISPLAY_NAMES.get(module_name, module_name.replace("_", " ").title())
    
    def get_tier_modules(self, tier: str) -> List[str]:
        """Get list of modules available in a tier"""
        tier_config = self.get_tier_info(tier)
        modules = tier_config.get("modules", [])
        
        if "all" in modules:
            # Return all available modules
            return list(MODULE_DISPLAY_NAMES.keys())
        
        return modules
    
    def calculate_days_until_expiry(self, license_data: Dict) -> Optional[int]:
        """Calculate days until license expires"""
        if not license_data:
            return None
        
        expires_at_str = license_data.get("expires_at")
        if not expires_at_str:
            return None
        
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            delta = expires_at - datetime.utcnow()
            return max(0, delta.days)
        except Exception:
            return None


# ============================================================================
# Singleton Instance
# ============================================================================

license_manager = LicenseManager()


# ============================================================================
# Helper Functions
# ============================================================================

def require_module(module_name: str):
    """
    Decorator to require a specific module for an API endpoint
    
    Usage:
        @router.get("/schedules")
        @require_module("scheduled_audits")
        async def get_schedules():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            from fastapi import HTTPException, Request
            
            # Try to get license from request state
            request = kwargs.get("request") or args[0] if args else None
            if not request or not isinstance(request, Request):
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Request object not found"
                )
            
            license_data = getattr(request.state, "license", None)
            if not license_data:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "No active license",
                        "module": module_name,
                        "action": "activate_license"
                    }
                )
            
            if not license_manager.has_module(license_data, module_name):
                tier = license_data.get("tier", "unknown")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Module not available in your license",
                        "module": module_name,
                        "current_tier": tier,
                        "action": "upgrade_license"
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_quota(quota_type: str, buffer: int = 0):
    """
    Decorator to check quota before allowing an action
    
    Usage:
        @router.post("/devices")
        @require_quota("devices", buffer=1)  # Check if we can add 1 more device
        async def add_device():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            from fastapi import HTTPException, Request
            from database import get_db
            import db_models
            
            # Get request object
            request = kwargs.get("request") or args[0] if args else None
            if not request or not isinstance(request, Request):
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Request object not found"
                )
            
            license_data = getattr(request.state, "license", None)
            if not license_data:
                raise HTTPException(
                    status_code=402,
                    detail={"error": "No active license", "action": "activate_license"}
                )
            
            # Get current usage from database
            db = next(get_db())
            
            if quota_type == "devices":
                current_count = db.query(db_models.DeviceDB).count()
            elif quota_type == "users":
                current_count = db.query(db_models.UserDB).count()
            else:
                current_count = 0
            
            # Check if adding 'buffer' items would exceed quota
            within_quota, max_allowed, message = license_manager.check_quota(
                license_data,
                quota_type,
                current_count + buffer
            )
            
            if not within_quota:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Quota exceeded",
                        "quota_type": quota_type,
                        "current": current_count,
                        "max": max_allowed,
                        "action": "upgrade_license"
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
