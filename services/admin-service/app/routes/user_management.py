# ============================================================================
# api/routes/user_management.py
# User and Group Management API Endpoints
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from deps import (
    get_db, get_current_user_db,
    require_view_groups, require_create_groups, require_modify_groups, require_delete_groups,
    require_view_users, require_create_users, require_modify_users, require_delete_users
)
from db_models import UserDB
from services.user_group_service import UserGroupService
from models.user_group import (
    UserGroup, UserGroupCreate, UserGroupUpdate,
    User, UserCreate, UserUpdate,
    PermissionAssignment, ModuleAccessAssignment,
    GroupMemberUpdate, Permission
)
from shared.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

user_group_service = UserGroupService()


# ============================================================================
# User Group Endpoints
# ============================================================================

@router.get("/groups", response_model=List[UserGroup])
def get_all_user_groups(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_view_groups)
):
    """Get all user groups (requires view_groups permission)"""
    try:
        return user_group_service.get_all_groups(db)
    except Exception as e:
        logger.error(f"Error fetching user groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/{group_id}", response_model=UserGroup)
def get_user_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_view_groups)
):
    """Get user group by ID (requires view_groups permission)"""
    try:
        group = user_group_service.get_group_by_id(db, group_id)
        if not group:
            raise HTTPException(status_code=404, detail=f"User group {group_id} not found")
        return group
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user group {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/groups", response_model=UserGroup, status_code=status.HTTP_201_CREATED)
def create_user_group(
    group_create: UserGroupCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_create_groups)
):
    """Create a new user group (requires create_groups permission)"""
    try:
        return user_group_service.create_group(db, group_create, created_by=current_user.username)
    except Exception as e:
        logger.error(f"Error creating user group: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/groups/{group_id}", response_model=UserGroup)
def update_user_group(
    group_id: int,
    group_update: UserGroupUpdate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_modify_groups)
):
    """Update user group (requires modify_groups permission)"""
    try:
        return user_group_service.update_group(db, group_id, group_update)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user group {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_delete_groups)
):
    """Delete user group (requires delete_groups permission)"""
    try:
        user_group_service.delete_group(db, group_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user group {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Group Membership Endpoints
# ============================================================================

@router.post("/groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_user_to_group(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Add a user to a group (Admin only)"""
    try:
        result = user_group_service.add_user_to_group(db, user_id, group_id)
        if not result:
            raise HTTPException(status_code=400, detail="User already in group")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user {user_id} to group {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_group(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Remove a user from a group (Admin only)"""
    try:
        result = user_group_service.remove_user_from_group(db, user_id, group_id)
        if not result:
            raise HTTPException(status_code=404, detail="User not in group")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing user {user_id} from group {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/groups/{group_id}/members", status_code=status.HTTP_204_NO_CONTENT)
def set_group_members(
    group_id: int,
    member_update: GroupMemberUpdate,
    db: Session = Depends(get_db)
):
    """Replace all members in a group (Admin only)"""
    try:
        user_group_service.set_group_members(db, group_id, member_update.user_ids)
    except Exception as e:
        logger.error(f"Error setting members for group {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/{group_id}/members", response_model=List[int])
def get_group_members(group_id: int, db: Session = Depends(get_db)):
    """Get all members of a group"""
    try:
        return user_group_service.get_group_members(db, group_id)
    except Exception as e:
        logger.error(f"Error fetching members for group {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# User Endpoints
# ============================================================================

@router.get("/users", response_model=List[User])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_view_users)
):
    """Get all users (requires view_users permission)"""
    try:
        return user_group_service.get_all_users(db)
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_view_users)
):
    """Get user by ID (requires view_users permission)"""
    try:
        user = user_group_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    user_create: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_create_users)
):
    """Create a new user (requires create_users permission)"""
    try:
        return user_group_service.create_user(db, user_create, created_by="admin")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_modify_users)
):
    """Update user (requires modify_users permission)"""
    try:
        return user_group_service.update_user(db, user_id, user_update)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_delete_users)
):
    """Delete user (requires delete_users permission)"""
    try:
        user_group_service.delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Permission Endpoints
# ============================================================================

@router.get("/permissions", response_model=List[str])
def get_available_permissions():
    """Get all available permissions in the system"""
    return Permission.all_permissions()


@router.get("/users/{user_id}/permissions", response_model=List[str])
def get_user_permissions(user_id: int, db: Session = Depends(get_db)):
    """Get all permissions for a specific user"""
    try:
        permissions = user_group_service.get_user_permissions(db, user_id)
        return list(permissions)
    except Exception as e:
        logger.error(f"Error fetching permissions for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/modules", response_model=List[str])
def get_user_modules(user_id: int, db: Session = Depends(get_db)):
    """Get all accessible modules for a specific user"""
    try:
        modules = user_group_service.get_user_modules(db, user_id)
        return list(modules)
    except Exception as e:
        logger.error(f"Error fetching modules for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/has-permission/{permission}", response_model=bool)
def check_user_permission(user_id: int, permission: str, db: Session = Depends(get_db)):
    """Check if user has a specific permission"""
    try:
        return user_group_service.user_has_permission(db, user_id, permission)
    except Exception as e:
        logger.error(f"Error checking permission {permission} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/can-access/{module}", response_model=bool)
def check_module_access(user_id: int, module: str, db: Session = Depends(get_db)):
    """Check if user can access a specific module"""
    try:
        return user_group_service.user_can_access_module(db, user_id, module)
    except Exception as e:
        logger.error(f"Error checking module access {module} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
