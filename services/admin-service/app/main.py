"""
Admin Service - FastAPI Microservice
Port: 3005
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append('../../..')
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
from routes import admin, user_management, integrations, notifications, remediation

logger = setup_logger(__name__)

app = FastAPI(
    title="Admin Service",
    version="1.0.0",
    description="Network Audit Platform - Admin Service"
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
app.include_router(admin.router, tags=["Admin"])
app.include_router(user_management.router, tags=["User Management"])
app.include_router(integrations.router, tags=["Integrations"])
app.include_router(notifications.router, tags=["Notifications"])
app.include_router(remediation.router, tags=["Remediation"])


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
