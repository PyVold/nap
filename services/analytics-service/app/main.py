"""
Analytics Service - FastAPI Microservice
Port: 3006
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.database import init_db
from shared.logger import setup_logger
from shared.monitoring import router as monitoring_router
from routes import analytics

logger = setup_logger(__name__)

app = FastAPI(
    title="Analytics Service",
    version="1.0.0",
    description="Network Audit Platform - Analytics & Intelligence Service"
)

# Initialize database
init_db()
logger.info("Analytics database initialized")

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
app.include_router(analytics.router, tags=["Analytics"])
app.include_router(monitoring_router, tags=["Monitoring"])


@app.get("/")
async def root():
    """Service health check"""
    return {
        "service": "analytics-service",
        "status": "online",
        "version": "1.0.0",
        "port": 3006
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "analytics-service",
        "database": "connected"
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting analytics-service on port 3006")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3006,
        log_level="info"
    )
