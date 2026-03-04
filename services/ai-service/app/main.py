"""
AI Service - FastAPI Microservice
Port: 3007
Provides AI-powered features: rule builder, chat, remediation advisor,
report generation, anomaly detection, MCP server, and MCP hub.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.database import init_db
from shared.logger import setup_logger
from shared.monitoring import router as monitoring_router
from routes.ai import router as ai_router
from routes.mcp import router as mcp_router

logger = setup_logger(__name__)

app = FastAPI(
    title="AI Service",
    version="1.0.0",
    description="Network Audit Platform - AI & MCP Service"
)

# Initialize database
init_db()
logger.info("AI Service database initialized")

# CORS configuration
cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:3000")
if cors_origins_str == "*":
    cors_origins = ["*"]
    logger.warning("CORS configured with wildcard '*' - not recommended for production!")
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if cors_origins_str != "*" else False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Include routers
app.include_router(ai_router, tags=["AI"])
app.include_router(mcp_router, tags=["MCP"])
app.include_router(monitoring_router, tags=["Monitoring"])


@app.get("/")
async def root():
    """Service health check"""
    return {
        "service": "ai-service",
        "status": "online",
        "version": "1.0.0",
        "port": 3007,
        "features": [
            "natural_language_rule_builder",
            "ai_chat_query",
            "remediation_advisor",
            "compliance_report_generator",
            "anomaly_detection",
            "mcp_server",
            "mcp_integration_hub",
        ],
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    from services.llm_adapter import get_available_providers, get_default_provider

    providers = get_available_providers()
    default = get_default_provider()

    return {
        "status": "healthy",
        "service": "ai-service",
        "database": "connected",
        "ai_providers": [p.value for p in providers],
        "default_provider": default.value,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVICE_PORT", "3007"))
    logger.info(f"Starting ai-service on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
