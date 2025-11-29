# ============================================================================
# api/routes/admin.py - Admin panel API
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from api.deps import get_db
from db_models import UserDB, SystemModuleDB, AuditLogDB
from utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin
)
from utils.logger import setup_logger

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = setup_logger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"  # admin, operator, viewer


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModuleResponse(BaseModel):
    id: int
    module_name: str
    display_name: str
    description: Optional[str]
    enabled: bool
    settings: Optional[dict]
    updated_at: datetime
    updated_by: Optional[str]

    class Config:
        from_attributes = True


class ModuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    settings: Optional[dict] = None


class AuditLogResponse(BaseModel):
    id: int
    username: str
    timestamp: datetime
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[dict]

    class Config:
        from_attributes = True




# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/login", response_model=LoginResponse)
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """Admin login"""
    user = db.query(UserDB).filter(UserDB.username == login_request.username).first()

    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )

    # Log the login
    audit_log = AuditLogDB(
        user_id=user.id,
        username=user.username,
        action="login",
        resource_type="auth",
        details={"success": True}
    )
    db.add(audit_log)
    db.commit()

    return LoginResponse(
        access_token=access_token,
        username=user.username,
        role=user.role
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current logged-in user info"""
    user = db.query(UserDB).filter(UserDB.username == current_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(UserDB).all()
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_create: UserCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)"""
    # Check if username exists
    if db.query(UserDB).filter(UserDB.username == user_create.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if email exists
    if db.query(UserDB).filter(UserDB.email == user_create.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create user
    db_user = UserDB(
        username=user_create.username,
        email=user_create.email,
        full_name=user_create.full_name,
        hashed_password=get_password_hash(user_create.password),
        role=user_create.role,
        is_active=True
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Log the action
    audit_log = AuditLogDB(
        user_id=current_user["user_id"],
        username=current_user["sub"],
        action="user_created",
        resource_type="user",
        resource_id=db_user.id,
        details={"username": db_user.username, "role": db_user.role}
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User created: {db_user.username} by {current_user['sub']}")
    return db_user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Log the action
    audit_log = AuditLogDB(
        user_id=current_user["user_id"],
        username=current_user["sub"],
        action="user_updated",
        resource_type="user",
        resource_id=user.id,
        details=update_data
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User updated: {user.username} by {current_user['sub']}")
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if user.id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Log before deletion
    audit_log = AuditLogDB(
        user_id=current_user["user_id"],
        username=current_user["sub"],
        action="user_deleted",
        resource_type="user",
        resource_id=user.id,
        details={"username": user.username}
    )
    db.add(audit_log)

    db.delete(user)
    db.commit()

    logger.info(f"User deleted: {user.username} by {current_user['sub']}")
    return None


# ============================================================================
# Module Management Endpoints
# ============================================================================

@router.get("/modules", response_model=List[ModuleResponse])
def list_modules(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all system modules (admin only)"""
    modules = db.query(SystemModuleDB).all()
    return modules


@router.get("/modules/enabled", response_model=List[str])
def get_enabled_modules(db: Session = Depends(get_db)):
    """
    Get list of enabled module names (public endpoint for UI visibility)

    Returns list of module_name values for enabled modules
    """
    enabled_modules = db.query(SystemModuleDB.module_name).filter(
        SystemModuleDB.enabled == True
    ).all()
    return [module[0] for module in enabled_modules]


@router.get("/modules/{module_id}", response_model=ModuleResponse)
def get_module(
    module_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get module by ID (admin only)"""
    module = db.query(SystemModuleDB).filter(SystemModuleDB.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


@router.put("/modules/{module_id}", response_model=ModuleResponse)
def update_module(
    module_id: int,
    module_update: ModuleUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update module settings (admin only)"""
    module = db.query(SystemModuleDB).filter(SystemModuleDB.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Update fields
    update_data = module_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value)

    module.updated_at = datetime.utcnow()
    module.updated_by = current_user["sub"]
    db.commit()
    db.refresh(module)

    # Log the action
    audit_log = AuditLogDB(
        user_id=current_user["user_id"],
        username=current_user["sub"],
        action="module_updated",
        resource_type="module",
        resource_id=module.id,
        details={
            "module_name": module.module_name,
            "enabled": module.enabled,
            **update_data
        }
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Module updated: {module.module_name} by {current_user['sub']}")
    return module


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    limit: int = 100,
    skip: int = 0,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List audit logs (admin only)"""
    logs = db.query(AuditLogDB).order_by(
        AuditLogDB.timestamp.desc()
    ).offset(skip).limit(limit).all()
    return logs


# ============================================================================
# System Statistics
# ============================================================================

@router.get("/stats")
def get_admin_stats(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    from db_models import DeviceDB, AuditRuleDB, AuditResultDB

    total_users = db.query(UserDB).count()
    active_users = db.query(UserDB).filter(UserDB.is_active == True).count()
    total_devices = db.query(DeviceDB).count()
    total_rules = db.query(AuditRuleDB).count()
    total_audits = db.query(AuditResultDB).count()
    enabled_modules = db.query(SystemModuleDB).filter(SystemModuleDB.enabled == True).count()
    total_modules = db.query(SystemModuleDB).count()

    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "system": {
            "total_devices": total_devices,
            "total_rules": total_rules,
            "total_audits": total_audits,
            "enabled_modules": enabled_modules,
            "total_modules": total_modules
        }
    }


