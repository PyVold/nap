# ============================================================================
# admin-service deps.py - Local dependencies with RBAC support
# ============================================================================

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from shared.database import get_db as database_get_db, SessionLocal
from shared.auth import SECRET_KEY, ALGORITHM
from services.user_group_service import UserGroupService
from db_models import UserDB

security = HTTPBearer(auto_error=False)
user_group_service = UserGroupService()


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
    """
    def permission_checker(
        db_user: UserDB = Depends(get_current_user_db),
        db: Session = Depends(get_db)
    ) -> UserDB:
        # Superusers have all permissions
        if db_user.is_superuser:
            return db_user

        # Check if user has the required permission
        if not user_group_service.user_has_permission(db, db_user.id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission}",
            )

        return db_user

    return permission_checker


# Convenience permission dependencies for user/group management
require_create_users = require_permission("create_users")
require_modify_users = require_permission("modify_users")
require_delete_users = require_permission("delete_users")
require_view_users = require_permission("view_users")
require_create_groups = require_permission("create_groups")
require_modify_groups = require_permission("modify_groups")
require_delete_groups = require_permission("delete_groups")
require_view_groups = require_permission("view_groups")

# Remediation permission dependencies
require_apply_fix = require_permission("apply_fix")
require_view_remediation = require_permission("view_remediation")
