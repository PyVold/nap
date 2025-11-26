# ============================================================================
# shared/deps.py - API Dependencies (shared across microservices)
# ============================================================================

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from shared.database import get_db as database_get_db, SessionLocal
from shared.auth import SECRET_KEY, ALGORITHM
from db_models import UserDB

security = HTTPBearer(auto_error=False)


def get_db() -> Generator:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user from JWT token

    Returns:
        dict: User data with username, role, user_id
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: int = payload.get("user_id")

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        return {"username": username, "role": role, "user_id": user_id}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


def require_role(*allowed_roles: str):
    """
    Dependency to check if user has one of the allowed roles

    Args:
        *allowed_roles: Roles that are allowed (admin, operator, viewer)

    Usage:
        @router.post("/")
        def create_item(current_user: dict = Depends(require_role("admin", "operator"))):
            ...
    """
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


# Convenience role dependencies
require_admin = require_role("admin")
require_admin_or_operator = require_role("admin", "operator")
require_any_authenticated = get_current_user


# ============================================================================
# Permission-based dependencies (granular RBAC)
# ============================================================================

def get_current_user_db(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserDB:
    """
    Get current authenticated user from database with full user object

    Returns:
        UserDB: Full user database object
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )

    db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return db_user


def require_permission(permission: str):
    """
    Dependency to check if user has a specific permission

    Args:
        permission: Permission name (e.g., 'run_audits', 'modify_rules')

    Usage:
        @router.post("/audit")
        def run_audit(current_user: UserDB = Depends(require_permission("run_audits"))):
            ...
    """
    def permission_checker(
        db_user: UserDB = Depends(get_current_user_db),
        db: Session = Depends(get_db)
    ) -> UserDB:
        # Superusers have all permissions
        if db_user.is_superuser:
            return db_user

        # TODO: Implement granular permission checking with user groups
        # For now, all authenticated users have basic permissions
        # Full RBAC is handled by admin-service
        return db_user

    return permission_checker


def require_any_permission(*permissions: str):
    """
    Dependency to check if user has at least one of the specified permissions

    Args:
        *permissions: List of permission names

    Usage:
        @router.get("/rules")
        def get_rules(current_user: UserDB = Depends(require_any_permission("view_rules", "modify_rules"))):
            ...
    """
    def permission_checker(
        db_user: UserDB = Depends(get_current_user_db),
        db: Session = Depends(get_db)
    ) -> UserDB:
        # Superusers have all permissions
        if db_user.is_superuser:
            return db_user

        # TODO: Implement granular permission checking with user groups
        # For now, all authenticated users have basic permissions
        return db_user

    return permission_checker


def require_module_access(module_name: str):
    """
    Dependency to check if user can access a specific module

    Args:
        module_name: Module name (e.g., 'devices', 'audit', 'rules')

    Usage:
        @router.get("/analytics/")
        def get_analytics(current_user: UserDB = Depends(require_module_access("analytics"))):
            ...
    """
    def module_checker(
        db_user: UserDB = Depends(get_current_user_db),
        db: Session = Depends(get_db)
    ) -> UserDB:
        # Superusers have access to all modules
        if db_user.is_superuser:
            return db_user

        # TODO: Implement module-level access control with user groups
        # For now, all authenticated users have access to all modules
        return db_user

    return module_checker


# Convenience permission dependencies for common operations
require_run_audits = require_permission("run_audits")
require_view_audits = require_permission("view_audits")
require_modify_rules = require_permission("modify_rules")
require_view_rules = require_permission("view_rules")
require_delete_rules = require_permission("delete_rules")
require_modify_templates = require_permission("modify_templates")
require_view_templates = require_permission("view_templates")
require_deploy_templates = require_permission("deploy_templates")
require_apply_fix = require_permission("apply_fix")
require_view_remediation = require_permission("view_remediation")
require_create_users = require_permission("create_users")
require_modify_users = require_permission("modify_users")
require_delete_users = require_permission("delete_users")
require_view_users = require_permission("view_users")
require_create_groups = require_permission("create_groups")
require_modify_groups = require_permission("modify_groups")
require_delete_groups = require_permission("delete_groups")
require_view_groups = require_permission("view_groups")
require_create_devices = require_permission("create_devices")
require_modify_devices = require_permission("modify_devices")
require_delete_devices = require_permission("delete_devices")
require_view_devices = require_permission("view_devices")
require_create_backups = require_permission("create_backups")
require_view_backups = require_permission("view_backups")
require_restore_backups = require_permission("restore_backups")
require_manage_system = require_permission("manage_system")
require_view_logs = require_permission("view_logs")


__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_db",
    "require_role",
    "require_admin",
    "require_admin_or_operator",
    "require_any_authenticated",
    "require_permission",
    "require_any_permission",
    "require_module_access",
    # Convenience permission dependencies
    "require_run_audits",
    "require_view_audits",
    "require_modify_rules",
    "require_view_rules",
    "require_delete_rules",
    "require_modify_templates",
    "require_view_templates",
    "require_deploy_templates",
    "require_apply_fix",
    "require_view_remediation",
    "require_create_users",
    "require_modify_users",
    "require_delete_users",
    "require_view_users",
    "require_create_groups",
    "require_modify_groups",
    "require_delete_groups",
    "require_view_groups",
    "require_create_devices",
    "require_modify_devices",
    "require_delete_devices",
    "require_view_devices",
    "require_create_backups",
    "require_view_backups",
    "require_restore_backups",
    "require_manage_system",
    "require_view_logs",
]
