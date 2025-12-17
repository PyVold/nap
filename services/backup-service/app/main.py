"""
Backup Service - FastAPI Microservice
Port: 3003
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
from shared.monitoring import router as monitoring_router
from routes import config_backups, drift_detection

logger = setup_logger(__name__)

app = FastAPI(
    title="Backup Service",
    version="1.0.0",
    description="Network Audit Platform - Backup Service"
)

# Initialize database
init_db()
logger.info("Database initialized")

# CORS configuration from environment
import os
cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:3000")
if cors_origins_str == "*":
    cors_origins = ["*"]
    logger.warning("CORS configured with wildcard '*' - not recommended for production!")
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if cors_origins_str != "*" else False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Include routers
app.include_router(config_backups.router, tags=["Config Backups"])
app.include_router(drift_detection.router, tags=["Drift Detection"])
app.include_router(monitoring_router, tags=["Monitoring"])


@app.get("/")
async def root():
    """Service health check"""
    return {
        "service": "backup-service",
        "status": "online",
        "version": "1.0.0",
        "port": 3003
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "backup-service",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting backup-service on port 3003")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3003,
        log_level="info"
    )
