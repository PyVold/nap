"""
Admin Service - FastAPI Microservice
Port: 3005
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
from routes import (
    admin, user_management, integrations, notifications, remediation,
    analytics, workflows, config_templates, licensing
)

logger = setup_logger(__name__)

# Security warning for default credentials
def check_security_configuration():
    """Check for insecure configurations and log warnings"""
    warnings = []
    
    # Check JWT secret
    jwt_secret = os.getenv("JWT_SECRET", "")
    if not jwt_secret or jwt_secret in ["GENERATE_SECURE_KEY_BEFORE_PRODUCTION", "change-me", "secret"]:
        warnings.append("⚠️  WARNING: JWT_SECRET is not set or using default value!")
    
    # Check encryption key
    encryption_key = os.getenv("ENCRYPTION_KEY", "")
    if not encryption_key or encryption_key in ["GENERATE_SECURE_KEY_BEFORE_PRODUCTION", "change-me", "secret"]:
        warnings.append("⚠️  WARNING: ENCRYPTION_KEY is not set or using default value!")
    
    if warnings:
        logger.warning("=" * 80)
        logger.warning("🔒 SECURITY CONFIGURATION WARNINGS")
        logger.warning("=" * 80)
        for warning in warnings:
            logger.warning(warning)
        logger.warning("")
        logger.warning("Generate secure keys with:")
        logger.warning("  python -c 'import secrets; print(secrets.token_urlsafe(32))'")
        logger.warning("")
        logger.warning("See SECURITY_SETUP_GUIDE.md for complete setup instructions.")
        logger.warning("=" * 80)

app = FastAPI(
    title="Admin Service",
    version="1.0.0",
    description="Network Audit Platform - Admin Service"
)

# Initialize database
init_db()
logger.info("Database initialized")

# Create default users on startup
@app.on_event("startup")
async def startup_event():
    """Initialize default users for all roles on startup"""
    from passlib.context import CryptContext
    import db_models

    # Check security configuration
    check_security_configuration()

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = next(get_db())

    created_users = []

    try:
        # Create default admin user if not exists
        admin_user = db.query(db_models.UserDB).filter(
            db_models.UserDB.username == "admin"
        ).first()

        if not admin_user:
            created_users.append("admin")
            hashed_password = pwd_context.hash("admin")
            admin_user = db_models.UserDB(
                username="admin",
                email="admin@example.com",
                full_name="System Administrator",
                hashed_password=hashed_password,
                role="admin",
                is_active=True,
                is_superuser=True
            )
            db.add(admin_user)
            logger.info("✅ Default admin user created (username: admin, password: admin)")
        else:
            logger.info("✅ Admin user already exists")

        # Create default operator user if not exists
        operator_user = db.query(db_models.UserDB).filter(
            db_models.UserDB.username == "operator"
        ).first()

        if not operator_user:
            created_users.append("operator")
            hashed_password = pwd_context.hash("operator")
            operator_user = db_models.UserDB(
                username="operator",
                email="operator@example.com",
                full_name="Network Operator",
                hashed_password=hashed_password,
                role="operator",
                is_active=True,
                is_superuser=False
            )
            db.add(operator_user)
            logger.info("✅ Default operator user created (username: operator, password: operator)")
        else:
            logger.info("✅ Operator user already exists")

        # Create default viewer user if not exists
        viewer_user = db.query(db_models.UserDB).filter(
            db_models.UserDB.username == "viewer"
        ).first()

        if not viewer_user:
            created_users.append("viewer")
            hashed_password = pwd_context.hash("viewer")
            viewer_user = db_models.UserDB(
                username="viewer",
                email="viewer@example.com",
                full_name="Network Viewer",
                hashed_password=hashed_password,
                role="viewer",
                is_active=True,
                is_superuser=False
            )
            db.add(viewer_user)
            logger.info("✅ Default viewer user created (username: viewer, password: viewer)")
        else:
            logger.info("✅ Viewer user already exists")

        db.commit()
        
        # Show security warning if any default users were created
        if created_users:
            logger.warning("=" * 80)
            logger.warning("🚨 SECURITY ALERT: DEFAULT TEST USERS CREATED")
            logger.warning("=" * 80)
            logger.warning("")
            logger.warning(f"Created {len(created_users)} default user(s) with DEFAULT PASSWORDS:")
            for username in created_users:
                logger.warning(f"  • Username: {username} / Password: {username}")
            logger.warning("")
            logger.warning("⚠️  CRITICAL: Change these passwords immediately!")
            logger.warning("⚠️  CRITICAL: Delete or disable these accounts in production!")
            logger.warning("")
            logger.warning("See SECURITY_SETUP_GUIDE.md for instructions.")
            logger.warning("=" * 80)
        else:
            logger.warning("⚠️  Change default passwords immediately in production!")
    except Exception as e:
        logger.error(f"❌ Error creating default users: {e}")
        db.rollback()
    finally:
        db.close()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin.router, tags=["Admin"])
app.include_router(user_management.router, prefix="/user-management", tags=["User Management"])
app.include_router(integrations.router, tags=["Integrations"])
app.include_router(notifications.router, tags=["Notifications"])
app.include_router(remediation.router, tags=["Remediation"])
# Stub routes for unimplemented features
app.include_router(analytics.router, tags=["Analytics"])
app.include_router(workflows.router, tags=["Workflows"])
app.include_router(config_templates.router, tags=["Config Templates"])
app.include_router(licensing.router, tags=["Licensing"])


@app.get("/")
async def root():
    """Service health check"""
    return {
        "service": "admin-service",
        "status": "online",
        "version": "1.0.0",
        "port": 3005
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "admin-service",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting admin-service on port 3005")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3005,
        log_level="info"
    )
