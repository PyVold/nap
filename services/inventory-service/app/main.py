"""
Inventory Service - FastAPI Microservice
Port: 3004
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
from routes import hardware_inventory

logger = setup_logger(__name__)

app = FastAPI(
    title="Inventory Service",
    version="1.0.0",
    description="Network Audit Platform - Inventory Service"
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
app.include_router(hardware_inventory.router, tags=["Hardware Inventory"])


@app.get("/")
async def root():
    """Service health check"""
    return {
        "service": "inventory-service",
        "status": "online",
        "version": "1.0.0",
        "port": 3004
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "inventory-service",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting inventory-service on port 3004")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3004,
        log_level="info"
    )
