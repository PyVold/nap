"""
License Enforcement Middleware for API Gateway

Blocks requests to modules that are not included in the active license tier.
"""

import sys
sys.path.append('/workspace')

from typing import Dict, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import db_models
from shared.license_manager import license_manager
from shared.logger import setup_logger

logger = setup_logger(__name__)


# Module to route prefix mapping
MODULE_TO_ROUTE_MAPPING = {
    # Device Management
    "devices": ["/devices", "/device-groups", "/device-import", "/health"],
    "device_groups": ["/device-groups"],
    "discovery": ["/discovery-groups"],
    "device_import": ["/device-import"],
    
    # Audits & Rules
    "manual_audits": ["/audit"],
    "scheduled_audits": ["/audit-schedules"],
    "basic_rules": ["/rules"],
    "rule_templates": ["/rule-templates"],
    
    # Configuration Management
    "config_backups": ["/config-backups"],
    "drift_detection": ["/drift-detection"],
    
    # Notifications & Webhooks
    "webhooks": ["/notifications"],
    
    # Hardware & Health
    "health_checks": ["/health"],
    "hardware_inventory": ["/hardware-inventory", "/hardware"],
    
    # Integrations & Automation
    "integrations": ["/integrations"],
    "workflow_automation": ["/workflows"],
    
    # Analytics
    "analytics": ["/analytics"],
    
    # Remediation
    "remediation": ["/remediation"],
}


class LicenseGatewayMiddleware:
    """License enforcement for API Gateway"""
    
    def __init__(self):
        self.license_manager = license_manager
        
    def get_active_license_data(self, db: Session) -> Optional[dict]:
        """Get active license data from database"""
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
    
    def get_required_module_for_path(self, path: str) -> Optional[str]:
        """
        Determine which license module is required for a given path
        
        Args:
            path: Request path (e.g., "/devices", "/audit-schedules")
            
        Returns:
            Module name or None if no specific module required
        """
        # Paths that don't require license checks (always accessible)
        public_paths = [
            "/", "/health", "/api/services",
            "/login", "/me", "/license"
        ]
        
        # Check if path is public
        normalized_path = f"/{path.strip('/')}"
        for public_path in public_paths:
            if normalized_path == public_path or normalized_path.startswith(f"{public_path}/"):
                return None
        
        # Check which module this path belongs to
        for module_name, route_prefixes in MODULE_TO_ROUTE_MAPPING.items():
            for prefix in route_prefixes:
                if normalized_path == prefix or normalized_path.startswith(f"{prefix}/"):
                    return module_name
        
        # Admin and user management routes - don't require specific module (authenticated only)
        if normalized_path.startswith("/admin") or normalized_path.startswith("/user-management"):
            return None
        
        # Unknown paths are allowed by default (they'll hit 404 if invalid)
        logger.debug(f"No module requirement found for path: {normalized_path}")
        return None
    
    def check_license_for_request(self, path: str) -> None:
        """
        Check if the request path is allowed by the active license
        
        Raises:
            HTTPException: If license check fails
        """
        # Determine required module
        required_module = self.get_required_module_for_path(path)
        
        # If no module required, allow request
        if not required_module:
            return
        
        # Get license data
        db = SessionLocal()
        try:
            license_data = self.get_active_license_data(db)
            
            if not license_data:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "No active license",
                        "message": "Please activate a valid license to use this feature",
                        "required_module": required_module,
                        "action": "activate_license"
                    }
                )
            
            # Check if license has the required module
            has_module = self.license_manager.has_module(license_data, required_module)
            
            if not has_module:
                tier = license_data.get("tier", "unknown")
                module_display = self.license_manager.get_module_display_name(required_module)
                
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Module not available in license",
                        "message": f"The module '{module_display}' is not available in your {tier} tier",
                        "required_module": required_module,
                        "current_tier": tier,
                        "action": "upgrade_license"
                    }
                )
            
            # License check passed
            logger.debug(f"License check passed for path {path} (module: {required_module})")
            
        finally:
            db.close()


# Singleton instance
license_gateway_middleware = LicenseGatewayMiddleware()
