
# ============================================================================
# main.py - FastAPI Application
# ============================================================================

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import get_db, init_db
from api.routes import devices, rules, audits, health, discovery_groups, device_groups, audit_schedules, config_backups, notifications, device_import, drift_detection, rule_templates, integrations, admin, remediation, user_management, hardware_inventory, license
from config import settings
from utils.logger import setup_logger
from scheduler.background_scheduler import get_scheduler

logger = setup_logger(__name__)

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Network Audit Platform with scheduled discovery, device groups, and automated audits"
)

# Initialize database
init_db()
logger.info("Database initialized")

# Start background scheduler
scheduler = get_scheduler()


@app.on_event("startup")
async def startup_event():
    """Start background scheduler and initialize system modules on application startup"""
    # Initialize system modules if empty
    from db_models import SystemModuleDB
    db = next(get_db())
    try:
        module_count = db.query(SystemModuleDB).count()
        if module_count == 0:
            logger.info("Initializing system modules with default configuration")
            default_modules = [
                {'module_name': 'devices', 'display_name': 'Device Management', 'enabled': True},
                {'module_name': 'device_groups', 'display_name': 'Device Groups', 'enabled': True},
                {'module_name': 'discovery_groups', 'display_name': 'Discovery Groups', 'enabled': True},
                {'module_name': 'device_import', 'display_name': 'Device Import', 'enabled': True},
                {'module_name': 'audit', 'display_name': 'Audit Results', 'enabled': True},
                {'module_name': 'audit_schedules', 'display_name': 'Audit Schedules', 'enabled': True},
                {'module_name': 'rules', 'display_name': 'Rule Management', 'enabled': True},
                {'module_name': 'rule_templates', 'display_name': 'Rule Templates', 'enabled': True},
                {'module_name': 'config_backups', 'display_name': 'Config Backups', 'enabled': True},
                {'module_name': 'drift_detection', 'display_name': 'Drift Detection', 'enabled': True},
                {'module_name': 'notifications', 'display_name': 'Notifications', 'enabled': True},
                {'module_name': 'health', 'display_name': 'Device Health', 'enabled': True},
                {'module_name': 'hardware_inventory', 'display_name': 'Hardware Inventory', 'enabled': True},
                {'module_name': 'integrations', 'display_name': 'Integration Hub', 'enabled': True},
            ]

            for module_data in default_modules:
                module = SystemModuleDB(**module_data)
                db.add(module)

            db.commit()
            logger.info(f"Initialized {len(default_modules)} system modules")
        else:
            logger.info(f"System modules already configured ({module_count} modules)")
    except Exception as e:
        logger.error(f"Failed to initialize system modules: {e}")
        db.rollback()
    finally:
        db.close()

    # Start background scheduler
    scheduler.start()
    logger.info("Application started with background scheduler")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background scheduler on application shutdown"""
    scheduler.shutdown()
    logger.info("Application shutdown complete")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/devices", tags=["Devices"])
app.include_router(rules.router, prefix="/rules", tags=["Rules"])
app.include_router(audits.router, prefix="/audit", tags=["Audits"])
app.include_router(health.router, tags=["Health"])
app.include_router(discovery_groups.router, prefix="/discovery-groups", tags=["Discovery Groups"])
app.include_router(device_groups.router, prefix="/device-groups", tags=["Device Groups"])
app.include_router(audit_schedules.router, prefix="/audit-schedules", tags=["Audit Schedules"])
# These routers already have prefixes defined in their files
app.include_router(config_backups.router, tags=["Config Backups"])
app.include_router(notifications.router, tags=["Notifications"])
app.include_router(device_import.router, tags=["Device Import"])
app.include_router(drift_detection.router, tags=["Drift Detection"])
app.include_router(rule_templates.router, tags=["Rule Templates"])
# Advanced features
app.include_router(integrations.router, tags=["Integrations"])
# Admin panel
app.include_router(admin.router, tags=["Admin"])
# User Management
app.include_router(user_management.router, prefix="/user-management", tags=["User Management"])
# Remediation
app.include_router(remediation.router, tags=["Remediation"])
# Hardware Inventory
app.include_router(hardware_inventory.router, tags=["Hardware Inventory"])
# License Management
app.include_router(license.router, tags=["License"])

# Mount frontend static files (if they exist)
try:
    app.mount("/app", StaticFiles(directory="frontend/build", html=True), name="frontend")
    logger.info("Frontend static files mounted at /app")
except Exception as e:
    logger.warning(f"Frontend not found or could not be mounted: {e}")

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "online",
        "service": settings.api_title,
        "version": settings.api_version,
        "features": [
            "subnet-based device discovery",
            "automatic vendor & hostname detection",
            "scheduled discovery groups",
            "device grouping",
            "scheduled audits with cron support",
            "dynamic rules management",
            "rule templates library (CIS, PCI-DSS, NIST)",
            "compliance framework automation",
            "NETCONF connectivity (Cisco XR, Nokia SROS)",
            "pysros integration for Nokia devices",
            "configuration backup & versioning",
            "configuration change detection",
            "configuration drift detection",
            "baseline configuration management",
            "webhook notifications (Slack, Teams, Discord)",
            "bulk device import/export (CSV)",
            "integration hub (NetBox, Git, Ansible, ServiceNow, Prometheus)",
            "hardware inventory tracking",
            "microservices architecture",
            "database persistence",
            "health monitoring",
            "ping and netconf checks",
            "configuration retention",
            "detailed audit reports"
        ]
    }

@app.get("/api/health-check")
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check with database stats"""
    from services.device_service import DeviceService
    from services.rule_service import RuleService
    from services.audit_service import AuditService
    from engine.audit_engine import AuditEngine
    from datetime import datetime

    device_service = DeviceService()
    rule_service = RuleService()
    audit_service = AuditService(AuditEngine())

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "devices": len(device_service.get_all_devices(db)),
        "rules": len(rule_service.get_all_rules(db)),
        "enabled_rules": len(rule_service.get_enabled_rules(db)),
        "audit_results": len(audit_service.get_all_results(db))
    }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Listening on {settings.api_host}:{settings.api_port}")

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
