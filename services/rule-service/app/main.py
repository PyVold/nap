"""
Rule Service - FastAPI Microservice
Port: 3002
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
from routes import rules, rule_templates, audits, audit_schedules
from scheduler import get_scheduler

logger = setup_logger(__name__)

app = FastAPI(
    title="Rule Service",
    version="1.0.0",
    description="Network Audit Platform - Rule Service"
)

# Initialize database
init_db()
logger.info("Database initialized")

# Initialize scheduler
scheduler = get_scheduler()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rules.router, prefix="/rules", tags=["Rules"])
app.include_router(rule_templates.router, tags=["Rule Templates"])  # Already has /rule-templates prefix
app.include_router(audits.router, prefix="/audit", tags=["Audits"])
app.include_router(audit_schedules.router, prefix="/audit-schedules", tags=["Audit Schedules"])


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Start background scheduler on application startup"""
    logger.info("Starting rule service...")
    scheduler.start()
    logger.info("Rule service started with background scheduler")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background scheduler on application shutdown"""
    logger.info("Shutting down rule service...")
    scheduler.shutdown()
    logger.info("Rule service stopped")


@app.get("/")
async def root():
    """Service health check"""
    return {
        "service": "rule-service",
        "status": "online",
        "version": "1.0.0",
        "port": 3002
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "rule-service",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting rule-service on port 3002")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3002,
        log_level="info"
    )
