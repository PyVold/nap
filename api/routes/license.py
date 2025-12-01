"""
License Management API

Endpoints for:
- Activating licenses
- Checking license status
- Viewing quotas and usage
- Deactivating/changing licenses
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

from database import get_db
import db_models
from shared.license_manager import license_manager, LICENSE_TIERS, MODULE_DISPLAY_NAMES, ROUTE_MODULE_MAP, get_module_for_route
from services.license_enforcement_service import license_enforcement_service
from utils.logger import setup_logger

logger = setup_logger(__name__)


router = APIRouter(prefix="/license", tags=["License Management"])


# ============================================================================
# Request/Response Models
# ============================================================================

class LicenseActivateRequest(BaseModel):
    """Request to activate a license key"""
    license_key: str = Field(..., description="License key to activate")


class LicenseStatusResponse(BaseModel):
    """License status and usage information"""
    valid: bool
    tier: str
    tier_display: str
    expires_at: Optional[str]
    days_until_expiry: Optional[int]
    is_active: bool
    
    # Quotas
    quotas: Dict[str, Dict]
    
    # Enabled modules
    enabled_modules: List[str]
    module_details: List[Dict]
    
    # Metadata
    customer_name: Optional[str]
    activated_at: Optional[str]
    last_validated: Optional[str]


class LicenseActivateResponse(BaseModel):
    """Response after activating a license"""
    success: bool
    message: str
    license_status: Optional[LicenseStatusResponse]


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/activate", response_model=LicenseActivateResponse)
async def activate_license(
    request: LicenseActivateRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Activate a license key
    
    This will:
    1. Validate the license key
    2. Check if it's not expired
    3. Store it in the database
    4. Deactivate any existing licenses
    """
    try:
        # Validate the license key
        validation = license_manager.validate_license(request.license_key)
        
        if not validation["valid"]:
            logger.warning(f"License activation failed: {validation['message']}")
            
            # Log failed attempt
            log = db_models.LicenseValidationLogDB(
                license_key_attempted=request.license_key[:50],  # Only store prefix
                validation_result=validation["reason"],
                validation_message=validation["message"],
                ip_address=req.client.host if req.client else "unknown"
            )
            db.add(log)
            db.commit()
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid license key",
                    "reason": validation["reason"],
                    "message": validation["message"]
                }
            )
        
        # Extract license data
        license_data = validation["data"]
        
        # Check if this license already exists
        existing_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.license_key == request.license_key
        ).first()
        
        if existing_license:
            # Reactivate existing license
            existing_license.is_active = True
            existing_license.last_validated = datetime.utcnow()
            db.commit()
            
            logger.info(f"Reactivated existing license for {existing_license.customer_email}")
        else:
            # Deactivate all other licenses (single license mode)
            db.query(db_models.LicenseDB).update({"is_active": False})
            
            # Create new license record
            new_license = db_models.LicenseDB(
                customer_name=license_data.get("customer_name", "Unknown"),
                customer_email=license_data.get("customer_email", "unknown@example.com"),
                company_name=license_data.get("company_name"),
                license_key=request.license_key,
                license_tier=license_data.get("tier", "starter"),
                is_active=True,
                activated_at=datetime.utcnow(),
                issued_at=datetime.fromisoformat(license_data.get("issued_at")),
                expires_at=datetime.fromisoformat(license_data.get("expires_at")),
                max_devices=license_data.get("max_devices", 10),
                max_users=license_data.get("max_users", 2),
                max_storage_gb=license_data.get("max_storage_gb", 5),
                enabled_modules=license_data.get("modules", []),
                last_validated=datetime.utcnow()
            )
            
            db.add(new_license)
            db.commit()
            db.refresh(new_license)
            
            logger.info(f"Activated new {new_license.license_tier} license for {new_license.customer_email}")
        
        # Log successful activation
        log = db_models.LicenseValidationLogDB(
            license_id=existing_license.id if existing_license else new_license.id,
            license_key_attempted=request.license_key[:50],
            validation_result="activated",
            validation_message="License successfully activated",
            ip_address=req.client.host if req.client else "unknown"
        )
        db.add(log)
        db.commit()
        
        # Get updated license status
        status = await get_license_status(db)
        
        return LicenseActivateResponse(
            success=True,
            message="License activated successfully",
            license_status=status
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating license: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate license: {str(e)}"
        )


@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(db: Session = Depends(get_db)):
    """
    Get current license status and usage
    
    Returns:
    - License validity and expiration
    - Current quotas and usage
    - Enabled modules
    """
    try:
        # Get active license
        active_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.is_active == True
        ).first()
        
        if not active_license:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "No active license found",
                    "action": "activate_license",
                    "message": "Please activate a license to use this platform"
                }
            )
        
        # Validate the license
        validation = license_manager.validate_license(active_license.license_key)
        
        if not validation["valid"]:
            logger.warning(f"Active license is invalid: {validation['message']}")
            # Deactivate invalid license
            active_license.is_active = False
            db.commit()
            
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "License invalid or expired",
                    "reason": validation["reason"],
                    "message": validation["message"],
                    "action": "renew_license"
                }
            )
        
        # Update last validated timestamp
        active_license.last_validated = datetime.utcnow()
        db.commit()
        
        # Update all current usage stats including storage
        # This ensures the UI shows the most recent usage data
        license_enforcement_service.enforcer.update_license_usage(db)
        
        # Refresh the license object to get updated values
        db.refresh(active_license)
        
        # Get current usage (already updated above, but keep for clarity)
        device_count = active_license.current_devices
        user_count = active_license.current_users
        
        # Calculate quotas
        quotas = {
            "devices": {
                "current": device_count,
                "max": active_license.max_devices,
                "percentage": round((device_count / active_license.max_devices * 100), 1) if active_license.max_devices > 0 else 0,
                "within_quota": device_count < active_license.max_devices
            },
            "users": {
                "current": user_count,
                "max": active_license.max_users,
                "percentage": round((user_count / active_license.max_users * 100), 1) if active_license.max_users > 0 else 0,
                "within_quota": user_count < active_license.max_users
            },
            "storage_gb": {
                "current": active_license.current_storage_gb,
                "max": active_license.max_storage_gb,
                "percentage": round((active_license.current_storage_gb / active_license.max_storage_gb * 100), 1) if active_license.max_storage_gb > 0 else 0,
                "within_quota": active_license.current_storage_gb < active_license.max_storage_gb
            }
        }
        
        # Get enabled modules from the stored license (not tier defaults)
        # This ensures that custom licenses with specific module restrictions are respected
        stored_modules = active_license.enabled_modules or []
        
        # If the license has "all" or is empty (legacy), fall back to tier defaults
        if not stored_modules or "all" in stored_modules:
            tier_modules = license_manager.get_tier_modules(active_license.license_tier)
        else:
            tier_modules = stored_modules
        
        module_details = []
        for module in tier_modules:
            module_details.append({
                "key": module,
                "name": license_manager.get_module_display_name(module),
                "enabled": True
            })
        
        # Calculate days until expiry
        days_until_expiry = license_manager.calculate_days_until_expiry(validation["data"])
        
        # Get tier display name
        tier_info = license_manager.get_tier_info(active_license.license_tier)
        
        return LicenseStatusResponse(
            valid=True,
            tier=active_license.license_tier,
            tier_display=tier_info.get("name", active_license.license_tier.title()),
            expires_at=active_license.expires_at.isoformat(),
            days_until_expiry=days_until_expiry,
            is_active=True,
            quotas=quotas,
            enabled_modules=tier_modules,
            module_details=module_details,
            customer_name=active_license.customer_name,
            activated_at=active_license.activated_at.isoformat() if active_license.activated_at else None,
            last_validated=active_license.last_validated.isoformat() if active_license.last_validated else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting license status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get license status: {str(e)}"
        )


@router.post("/deactivate")
async def deactivate_license(db: Session = Depends(get_db)):
    """
    Deactivate current license
    
    This will disable the current license, requiring a new one to be activated
    """
    try:
        # Deactivate all licenses
        updated = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.is_active == True
        ).update({"is_active": False})
        
        db.commit()
        
        if updated > 0:
            logger.info(f"Deactivated {updated} license(s)")
            return {
                "success": True,
                "message": f"Deactivated {updated} license(s)"
            }
        else:
            return {
                "success": True,
                "message": "No active licenses to deactivate"
            }
    
    except Exception as e:
        logger.error(f"Error deactivating license: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate license: {str(e)}"
        )


@router.get("/tiers")
async def get_license_tiers():
    """
    Get all available license tiers with their features and pricing
    
    Useful for displaying upgrade options in the UI
    """
    try:
        tiers_info = []
        
        for tier_key, tier_config in LICENSE_TIERS.items():
            modules = tier_config.get("modules", [])
            if "all" in modules:
                modules = list(MODULE_DISPLAY_NAMES.keys())
            
            module_list = [
                {
                    "key": module,
                    "name": license_manager.get_module_display_name(module)
                }
                for module in modules
            ]
            
            tiers_info.append({
                "key": tier_key,
                "name": tier_config.get("name", tier_key.title()),
                "max_devices": tier_config.get("max_devices"),
                "max_users": tier_config.get("max_users"),
                "max_storage_gb": tier_config.get("max_storage_gb"),
                "modules": module_list,
                "module_count": len(module_list)
            })
        
        return {
            "tiers": tiers_info
        }
    
    except Exception as e:
        logger.error(f"Error getting license tiers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get license tiers: {str(e)}"
        )


@router.get("/check-module/{module_name}")
async def check_module_access(module_name: str, db: Session = Depends(get_db)):
    """
    Check if current license has access to a specific module
    
    Args:
        module_name: Name of the module to check (e.g., "scheduled_audits")
    
    Returns:
        {
            "has_access": bool,
            "module": str,
            "current_tier": str,
            "required_tier": str (if not accessible)
        }
    """
    try:
        # Get active license
        active_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.is_active == True
        ).first()
        
        if not active_license:
            return {
                "has_access": False,
                "module": module_name,
                "current_tier": "none",
                "message": "No active license"
            }
        
        # Validate license
        validation = license_manager.validate_license(active_license.license_key)
        
        if not validation["valid"]:
            return {
                "has_access": False,
                "module": module_name,
                "current_tier": active_license.license_tier,
                "message": f"License {validation['reason']}: {validation['message']}"
            }
        
        # Check module access
        has_access = license_manager.has_module(validation["data"], module_name)
        
        response = {
            "has_access": has_access,
            "module": module_name,
            "module_display": license_manager.get_module_display_name(module_name),
            "current_tier": active_license.license_tier
        }
        
        if not has_access:
            # Find which tier includes this module
            for tier_key, tier_config in LICENSE_TIERS.items():
                modules = tier_config.get("modules", [])
                if "all" in modules or module_name in modules:
                    response["required_tier"] = tier_key
                    response["required_tier_display"] = tier_config.get("name")
                    break
            
            response["message"] = f"Module not available in {active_license.license_tier} tier"
        
        return response
    
    except Exception as e:
        logger.error(f"Error checking module access: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check module access: {str(e)}"
        )


@router.get("/module-mappings")
async def get_module_mappings():
    """
    Get route-to-module mappings for frontend

    This endpoint returns the mapping of frontend routes/menu items
    to their corresponding license modules. The frontend should use this
    to determine which license module to check for each feature.

    Returns:
        {
            "mappings": dict,  # route_name -> module_name
            "modules": dict    # module_name -> display_name
        }
    """
    try:
        return {
            "mappings": ROUTE_MODULE_MAP,
            "modules": MODULE_DISPLAY_NAMES,
            "tiers": LICENSE_TIERS
        }
    except Exception as e:
        logger.error(f"Error getting module mappings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get module mappings: {str(e)}"
        )


@router.post("/upgrade")
async def handle_license_upgrade(db: Session = Depends(get_db)):
    """
    Handle license upgrade scenario
    
    This endpoint should be called after activating a new license with a higher tier.
    It will:
    1. Detect tier changes
    2. Log the upgrade
    3. Update module availability
    """
    try:
        # Get current active license
        active_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.is_active == True
        ).first()
        
        if not active_license:
            raise HTTPException(
                status_code=404,
                detail="No active license found"
            )
        
        # Check if this is an upgrade (compare with previous tier if available)
        # For now, just handle the current license
        current_tier = active_license.license_tier
        
        # Call upgrade handler
        upgrade_result = license_enforcement_service.handle_license_upgrade(
            db,
            old_tier=current_tier,  # In real scenario, get from history
            new_tier=current_tier
        )
        
        logger.info(f"License upgrade processed: {upgrade_result['message']}")
        
        return {
            "success": True,
            "current_tier": current_tier,
            "changes": upgrade_result.get("changes", []),
            "message": "License upgrade processed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling license upgrade: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to handle license upgrade: {str(e)}"
        )


@router.post("/renew")
async def handle_license_renewal(db: Session = Depends(get_db)):
    """
    Handle license renewal
    
    This refreshes license validation and updates timestamps.
    """
    try:
        renewal_result = license_enforcement_service.handle_license_renewal(db)
        
        if not renewal_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=renewal_result["message"]
            )
        
        return {
            "success": True,
            "message": renewal_result["message"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling license renewal: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to handle license renewal: {str(e)}"
        )


@router.get("/validation-logs")
async def get_validation_logs(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent license validation log entries
    
    Useful for security auditing and troubleshooting
    """
    try:
        logs = db.query(db_models.LicenseValidationLogDB).order_by(
            db_models.LicenseValidationLogDB.checked_at.desc()
        ).limit(limit).all()
        
        return {
            "logs": [
                {
                    "id": log.id,
                    "result": log.validation_result,
                    "message": log.validation_message,
                    "ip_address": log.ip_address,
                    "timestamp": log.checked_at.isoformat()
                }
                for log in logs
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting validation logs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get validation logs: {str(e)}"
        )
