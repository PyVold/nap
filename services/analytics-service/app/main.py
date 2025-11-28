"""
Analytics Service - FastAPI Microservice
Port: 3006
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.database import init_db
from shared.logger import setup_logger
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics.router, tags=["Analytics"])


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
