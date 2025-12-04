"""
Device Service - FastAPI Microservice
Port: 3001
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
from routes import devices, device_groups, discovery_groups, device_import, health
from scheduler import get_scheduler

logger = setup_logger(__name__)

app = FastAPI(
    title="Device Service",
    version="1.0.0",
    description="Network Audit Platform - Device Service"
)

# Initialize database
init_db()
logger.info("Database initialized")

# Get scheduler instance (will be started on app startup)
scheduler = get_scheduler()

# CORS configuration from settings
# Default to "*" for backward compatibility, but allow restriction via CORS_ALLOWED_ORIGINS env var
cors_origins_str = settings.cors_allowed_origins
if cors_origins_str == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/devices", tags=["Devices"])
app.include_router(device_groups.router, prefix="/device-groups", tags=["Device Groups"])
app.include_router(discovery_groups.router, prefix="/discovery-groups", tags=["Discovery Groups"])
app.include_router(device_import.router, prefix="/device-import", tags=["Device Import"])
app.include_router(health.router, tags=["Health"])  # Already has /health prefix


@app.on_event("startup")
async def startup_event():
    """Start background scheduler on application startup"""
    scheduler.start()
    logger.info("Device service started with background scheduler (health checks & scheduled discoveries)")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background scheduler on application shutdown"""
    scheduler.shutdown()
    logger.info("Device service shutdown complete")


@app.get("/")
async def root():
    """Service health check"""
    return {
        "service": "device-service",
        "status": "online",
        "version": "1.0.0",
        "port": 3001,
        "features": [
            "device management",
            "device discovery",
            "health monitoring (periodic)",
            "device groups",
            "scheduled discoveries"
        ]
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "device-service",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting device-service on port 3001")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3001,
        log_level="info",
        timeout_keep_alive=75,  # Increase keep-alive timeout
        limit_concurrency=100,  # Limit concurrent connections
        backlog=2048  # Increase connection backlog
    )
