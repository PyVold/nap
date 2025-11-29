# ============================================================================
# services/user_group_service.py
# User Group Management Service
# ============================================================================

from typing import List, Optional, Set
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime

from db_models import (
    UserDB, UserGroupDB, UserGroupMembershipDB,
    GroupPermissionDB, GroupModuleAccessDB
)
from models.user_group import (
    UserGroup, UserGroupCreate, UserGroupUpdate,
    User, UserCreate, UserUpdate, Permission
)
from shared.logger import setup_logger
from shared.license_middleware import license_enforcer
from shared.license_manager import license_manager

logger = setup_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserGroupService:
    """Service for user group and permission management"""

    # ============================================================================
    # User Group CRUD
    # ============================================================================

    def get_all_groups(self, db: Session) -> List[UserGroup]:
        """Get all user groups"""
        db_groups = db.query(UserGroupDB).all()
        return [self._group_to_pydantic(db, g) for g in db_groups]

    def get_group_by_id(self, db: Session, group_id: int) -> Optional[UserGroup]:
        """Get user group by ID"""
        db_group = db.query(UserGroupDB).filter(UserGroupDB.id == group_id).first()
        return self._group_to_pydantic(db, db_group) if db_group else None

    def create_group(self, db: Session, group_create: UserGroupCreate, created_by: str = "system") -> UserGroup:
        """Create a new user group"""
        # Create group
        db_group = UserGroupDB(
            name=group_create.name,
            description=group_create.description,
            is_active=group_create.is_active,
            created_by=created_by
        )
        db.add(db_group)
        db.flush()

        # Add permissions
        if group_create.permissions:
            self._update_group_permissions(db, db_group.id, group_create.permissions)

        # Add module access
        if group_create.module_access:
            self._update_group_modules(db, db_group.id, group_create.module_access)

        db.commit()
        db.refresh(db_group)

        logger.info(f"Created user group: {db_group.name} by {created_by}")
        return self._group_to_pydantic(db, db_group)

    def update_group(self, db: Session, group_id: int, group_update: UserGroupUpdate) -> UserGroup:
        """Update an existing user group"""
        db_group = db.query(UserGroupDB).filter(UserGroupDB.id == group_id).first()
        if not db_group:
            raise ValueError(f"User group {group_id} not found")

        update_data = group_update.dict(exclude_unset=True, exclude={'permissions', 'module_access'})

        # Update basic fields
        for field, value in update_data.items():
            setattr(db_group, field, value)

        db_group.updated_at = datetime.utcnow()

        # Update permissions if provided
        if group_update.permissions is not None:
            self._update_group_permissions(db, group_id, group_update.permissions)

        # Update module access if provided
        if group_update.module_access is not None:
            self._update_group_modules(db, group_id, group_update.module_access)

        db.commit()
        db.refresh(db_group)

        logger.info(f"Updated user group: {db_group.name}")
        return self._group_to_pydantic(db, db_group)

    def delete_group(self, db: Session, group_id: int) -> bool:
        """Delete a user group"""
        db_group = db.query(UserGroupDB).filter(UserGroupDB.id == group_id).first()
        if not db_group:
            raise ValueError(f"User group {group_id} not found")

        db.delete(db_group)
        db.commit()

        logger.info(f"Deleted user group ID: {group_id}")
        return True

    # ============================================================================
    # Group Membership
    # ============================================================================

    def add_user_to_group(self, db: Session, user_id: int, group_id: int) -> bool:
        """Add a user to a group"""
        existing = db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.user_id == user_id,
            UserGroupMembershipDB.group_id == group_id
        ).first()

        if existing:
            return False  # Already a member

        membership = UserGroupMembershipDB(user_id=user_id, group_id=group_id)
        db.add(membership)
        db.commit()

        logger.info(f"Added user {user_id} to group {group_id}")
        return True

    def remove_user_from_group(self, db: Session, user_id: int, group_id: int) -> bool:
        """Remove a user from a group"""
        membership = db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.user_id == user_id,
            UserGroupMembershipDB.group_id == group_id
        ).first()

        if not membership:
            return False

        db.delete(membership)
        db.commit()

        logger.info(f"Removed user {user_id} from group {group_id}")
        return True

    def get_group_members(self, db: Session, group_id: int) -> List[int]:
        """Get all user IDs in a group"""
        memberships = db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.group_id == group_id
        ).all()
        return [m.user_id for m in memberships]

    def set_group_members(self, db: Session, group_id: int, user_ids: List[int]):
        """Replace all members in a group"""
        # Remove existing memberships
        db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.group_id == group_id
        ).delete()

        # Add new memberships
        for user_id in user_ids:
            membership = UserGroupMembershipDB(user_id=user_id, group_id=group_id)
            db.add(membership)

        db.commit()

    # ============================================================================
    # User Management
    # ============================================================================

    def create_user(self, db: Session, user_create: UserCreate, created_by: str = "admin") -> User:
        """Create a new user"""
        # Check if username or email already exists
        existing_user = db.query(UserDB).filter(
            (UserDB.username == user_create.username) | (UserDB.email == user_create.email)
        ).first()

        if existing_user:
            raise ValueError("Username or email already exists")

        # Hash password
        hashed_password = pwd_context.hash(user_create.password)

        # Create user
        db_user = UserDB(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=user_create.is_active,
            is_superuser=user_create.is_superuser,
            role="viewer"  # Legacy field
        )
        db.add(db_user)
        db.flush()

        # Add user to groups
        if user_create.group_ids:
            for group_id in user_create.group_ids:
                self.add_user_to_group(db, db_user.id, group_id)

        db.commit()
        db.refresh(db_user)

        logger.info(f"Created user: {db_user.username} by {created_by}")
        return self._user_to_pydantic(db, db_user)

    def update_user(self, db: Session, user_id: int, user_update: UserUpdate) -> User:
        """Update an existing user"""
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            raise ValueError(f"User {user_id} not found")

        update_data = user_update.dict(exclude_unset=True, exclude={'password', 'group_ids'})

        # Update basic fields
        for field, value in update_data.items():
            setattr(db_user, field, value)

        # Update password if provided
        if user_update.password:
            db_user.hashed_password = pwd_context.hash(user_update.password)

        # Update groups if provided
        if user_update.group_ids is not None:
            # Remove from all current groups
            db.query(UserGroupMembershipDB).filter(
                UserGroupMembershipDB.user_id == user_id
            ).delete()

            # Add to new groups
            for group_id in user_update.group_ids:
                self.add_user_to_group(db, user_id, group_id)

        db_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_user)

        logger.info(f"Updated user: {db_user.username}")
        return self._user_to_pydantic(db, db_user)

    def delete_user(self, db: Session, user_id: int) -> bool:
        """Delete a user"""
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            raise ValueError(f"User {user_id} not found")

        db.delete(db_user)
        db.commit()

        logger.info(f"Deleted user ID: {user_id}")
        return True

    def get_all_users(self, db: Session) -> List[User]:
        """Get all users"""
        db_users = db.query(UserDB).all()
        return [self._user_to_pydantic(db, u) for u in db_users]

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        return self._user_to_pydantic(db, db_user) if db_user else None

    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        db_user = db.query(UserDB).filter(UserDB.username == username).first()
        return self._user_to_pydantic(db, db_user) if db_user else None

    # ============================================================================
    # Permission Checking
    # ============================================================================

    def get_user_permissions(self, db: Session, user_id: int) -> Set[str]:
        """Get all permissions for a user (aggregated from all groups)"""
        # Check if superuser
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if db_user and db_user.is_superuser:
            return set(Permission.all_permissions())

        # Get user's groups
        memberships = db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.user_id == user_id
        ).all()
        group_ids = [m.group_id for m in memberships]

        if not group_ids:
            return set()

        # Get all permissions from all groups
        permissions = db.query(GroupPermissionDB).filter(
            GroupPermissionDB.group_id.in_(group_ids),
            GroupPermissionDB.granted == True
        ).all()

        return set(p.permission for p in permissions)

    def get_user_modules(self, db: Session, user_id: int) -> Set[str]:
        """
        Get all accessible modules for a user (aggregated from all groups)
        
        IMPORTANT: This now enforces license restrictions for ALL users including admin/superuser.
        Only modules available in the active license tier will be returned.
        """
        # Get active license data - if no license, no modules available
        license_data = license_enforcer.get_active_license_data(db)
        
        if not license_data:
            logger.warning(f"No active license - user {user_id} has no module access")
            return set()
        
        # Get tier and available modules from license
        tier = license_data.get("tier", "starter")
        tier_modules = license_manager.get_tier_modules(tier)
        
        # Convert to set for easier filtering
        license_modules = set(tier_modules)
        
        # If license has "all" modules, get the full list
        if "all" in license_modules:
            license_modules = set([
                'devices', 'device_groups', 'discovery_groups', 'device_import',
                'audit', 'audit_schedules', 'rules', 'rule_templates',
                'config_backups', 'drift_detection',
                'notifications', 'health', 'hardware_inventory', 'integrations',
                'workflows', 'analytics', 'admin'
            ])
        
        # Map license module names to frontend module names if needed
        # Backend uses names like 'manual_audits', 'scheduled_audits', 'basic_rules'
        # Frontend uses 'audit', 'audit_schedules', 'rules'
        module_mapping = {
            'manual_audits': 'audit',
            'scheduled_audits': 'audit_schedules',
            'basic_rules': 'rules',
            'rule_templates': 'rule_templates',
            'api_access': 'api',
            'config_backups': 'config_backups',
            'drift_detection': 'drift_detection',
            'webhooks': 'notifications',
            'device_groups': 'device_groups',
            'discovery': 'discovery_groups',
            'health_checks': 'health',
            'workflow_automation': 'workflows',
            'topology': 'topology',
            'ai_features': 'ai',
            'integrations': 'integrations',
            'sso': 'sso',
            'devices': 'devices',
            'device_import': 'device_import',
            'hardware_inventory': 'hardware_inventory',
            'analytics': 'analytics',
            'admin': 'admin'
        }
        
        # Convert license modules to frontend module names
        frontend_license_modules = set()
        for license_module in license_modules:
            frontend_module = module_mapping.get(license_module, license_module)
            frontend_license_modules.add(frontend_module)
        
        # Check if superuser - they see ALL modules that are in the license, not just group-assigned ones
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if db_user and db_user.is_superuser:
            # Superusers get all modules that are available in the license
            logger.debug(f"Superuser {user_id} has access to all licensed modules: {frontend_license_modules}")
            return frontend_license_modules

        # For regular users, get their group-based module access
        memberships = db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.user_id == user_id
        ).all()
        group_ids = [m.group_id for m in memberships]

        if not group_ids:
            logger.debug(f"User {user_id} has no groups - no module access")
            return set()

        # Get all module access from all groups
        module_access = db.query(GroupModuleAccessDB).filter(
            GroupModuleAccessDB.group_id.in_(group_ids),
            GroupModuleAccessDB.can_access == True
        ).all()

        user_modules = set(m.module_name for m in module_access)
        
        # Intersect user modules with license-allowed modules
        # User can only access modules that are BOTH in their groups AND in the license
        allowed_modules = user_modules.intersection(frontend_license_modules)
        
        logger.debug(f"User {user_id} modules: group={user_modules}, license={frontend_license_modules}, allowed={allowed_modules}")
        
        return allowed_modules

    def user_has_permission(self, db: Session, user_id: int, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.get_user_permissions(db, user_id)

    def user_can_access_module(self, db: Session, user_id: int, module: str) -> bool:
        """Check if user can access a specific module"""
        return module in self.get_user_modules(db, user_id)

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _update_group_permissions(self, db: Session, group_id: int, permissions: List[str]):
        """Replace all permissions for a group"""
        # Remove existing permissions
        db.query(GroupPermissionDB).filter(
            GroupPermissionDB.group_id == group_id
        ).delete()

        # Add new permissions
        for permission in permissions:
            perm = GroupPermissionDB(group_id=group_id, permission=permission, granted=True)
            db.add(perm)

        db.flush()

    def _update_group_modules(self, db: Session, group_id: int, modules: List[str]):
        """Replace all module access for a group"""
        # Remove existing module access
        db.query(GroupModuleAccessDB).filter(
            GroupModuleAccessDB.group_id == group_id
        ).delete()

        # Add new module access
        for module in modules:
            access = GroupModuleAccessDB(group_id=group_id, module_name=module, can_access=True)
            db.add(access)

        db.flush()

    def _group_to_pydantic(self, db: Session, db_group: UserGroupDB) -> UserGroup:
        """Convert DB group to Pydantic model"""
        # Get permissions
        permissions = db.query(GroupPermissionDB).filter(
            GroupPermissionDB.group_id == db_group.id,
            GroupPermissionDB.granted == True
        ).all()
        permission_list = [p.permission for p in permissions]

        # Get module access
        modules = db.query(GroupModuleAccessDB).filter(
            GroupModuleAccessDB.group_id == db_group.id,
            GroupModuleAccessDB.can_access == True
        ).all()
        module_list = [m.module_name for m in modules]

        # Get member count
        member_count = db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.group_id == db_group.id
        ).count()

        return UserGroup(
            id=db_group.id,
            name=db_group.name,
            description=db_group.description,
            is_active=db_group.is_active,
            permissions=permission_list,
            module_access=module_list,
            member_count=member_count,
            created_at=db_group.created_at,
            updated_at=db_group.updated_at,
            created_by=db_group.created_by
        )

    def _user_to_pydantic(self, db: Session, db_user: UserDB) -> User:
        """Convert DB user to Pydantic model"""
        # Get user's groups
        memberships = db.query(UserGroupMembershipDB).filter(
            UserGroupMembershipDB.user_id == db_user.id
        ).all()
        group_ids = [m.group_id for m in memberships]

        groups = []
        if group_ids:
            db_groups = db.query(UserGroupDB).filter(UserGroupDB.id.in_(group_ids)).all()
            groups = [g.name for g in db_groups]

        # Get aggregated permissions and modules
        permissions = list(self.get_user_permissions(db, db_user.id))
        modules = list(self.get_user_modules(db, db_user.id))

        return User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
            is_superuser=db_user.is_superuser,
            role=db_user.role,
            groups=groups,
            permissions=permissions,
            modules=modules,
            last_login=db_user.last_login,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
