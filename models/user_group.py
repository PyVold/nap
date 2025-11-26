# ============================================================================
# models/user_group.py
# User Group and Permission Models
# ============================================================================

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ============================================================================
# Permission Enums
# ============================================================================

class Permission:
    """Available permissions in the system"""
    # Audit permissions
    RUN_AUDITS = "run_audits"
    VIEW_AUDITS = "view_audits"

    # Rule permissions
    MODIFY_RULES = "modify_rules"
    VIEW_RULES = "view_rules"
    DELETE_RULES = "delete_rules"

    # Template permissions
    MODIFY_TEMPLATES = "modify_templates"
    VIEW_TEMPLATES = "view_templates"
    DEPLOY_TEMPLATES = "deploy_templates"

    # Remediation permissions
    APPLY_FIX = "apply_fix"
    VIEW_REMEDIATION = "view_remediation"

    # User management permissions
    CREATE_USERS = "create_users"
    MODIFY_USERS = "modify_users"
    DELETE_USERS = "delete_users"
    VIEW_USERS = "view_users"

    # Group management permissions
    CREATE_GROUPS = "create_groups"
    MODIFY_GROUPS = "modify_groups"
    DELETE_GROUPS = "delete_groups"
    VIEW_GROUPS = "view_groups"

    # Device permissions
    CREATE_DEVICES = "create_devices"
    MODIFY_DEVICES = "modify_devices"
    DELETE_DEVICES = "delete_devices"
    VIEW_DEVICES = "view_devices"

    # Backup permissions
    CREATE_BACKUPS = "create_backups"
    VIEW_BACKUPS = "view_backups"
    RESTORE_BACKUPS = "restore_backups"

    # Admin permissions
    MANAGE_SYSTEM = "manage_system"
    VIEW_LOGS = "view_logs"

    @classmethod
    def all_permissions(cls):
        """Get all available permissions"""
        return [
            getattr(cls, attr) for attr in dir(cls)
            if not attr.startswith('_') and isinstance(getattr(cls, attr), str)
        ]


# ============================================================================
# User Group Models
# ============================================================================

class UserGroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class UserGroupCreate(UserGroupBase):
    permissions: List[str] = []
    module_access: List[str] = []


class UserGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = None
    module_access: Optional[List[str]] = None


class UserGroup(UserGroupBase):
    id: int
    permissions: List[str] = []
    module_access: List[str] = []
    member_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# User Models (Enhanced)
# ============================================================================

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    is_active: bool = True
    is_superuser: bool = False
    group_ids: List[int] = []


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    group_ids: Optional[List[int]] = None


class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    role: str  # Legacy field
    groups: List[str] = []  # Group names
    permissions: List[str] = []  # Combined permissions from all groups
    modules: List[str] = []  # Accessible modules
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class UserToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


# ============================================================================
# Permission Assignment Models
# ============================================================================

class PermissionAssignment(BaseModel):
    group_id: int
    permissions: List[str]


class ModuleAccessAssignment(BaseModel):
    group_id: int
    modules: List[str]  # List of module names user group can access


class GroupMemberUpdate(BaseModel):
    user_ids: List[int]  # Users to add to the group
