"""
Backup Service - FastAPI Microservice
Port: 3003
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append('../../..')
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config_backups.router, tags=["Config Backups"])
app.include_router(drift_detection.router, tags=["Drift Detection"])


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
