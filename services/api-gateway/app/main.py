"""
API Gateway - Main Entry Point
Handles service discovery and request routing
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import httpx
import sys
from shared.logger import setup_logger
from typing import Dict, List

logger = setup_logger(__name__)

app = FastAPI(
    title="Network Audit Platform - API Gateway",
    version="1.0.0",
    description="API Gateway for microservices"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service registry (can be moved to database/Redis later)
SERVICES = {
    "device-service": {
        "url": "http://device-service:3001",
        "name": "Device Management",
        "enabled": True,
        "routes": ["/devices", "/device-groups", "/discovery-groups", "/device-import", "/health"],
        "ui_routes": ["devices", "discovery", "health"]
    },
    "rule-service": {
        "url": "http://rule-service:3002",
        "name": "Rule & Audit Management",
        "enabled": True,
        "routes": ["/rules", "/rule-templates", "/audit", "/audit-schedules"],
        "ui_routes": ["rules", "audits"]
    },
    "backup-service": {
        "url": "http://backup-service:3003",
        "name": "Configuration Backup",
        "enabled": True,
        "routes": ["/config-backups", "/drift-detection"],
        "ui_routes": ["backups", "drift"]
    },
    "inventory-service": {
        "url": "http://inventory-service:3004",
        "name": "Hardware Inventory",
        "enabled": True,
        "routes": ["/hardware", "/hardware-inventory"],
        "ui_routes": ["inventory"]
    },
    "admin-service": {
        "url": "http://admin-service:3005",
        "name": "Administration",
        "enabled": True,
        "routes": ["/admin", "/user-management", "/integrations", "/notifications", "/remediation"],
        "ui_routes": ["admin", "users", "integrations"]
    },
    "analytics-service": {
        "url": "http://analytics-service:3006",
        "name": "Analytics",
        "enabled": True,
        "routes": ["/analytics"],
        "ui_routes": ["analytics"]
    },
    "workflow-service": {
        "url": "http://admin-service:3005",  # Temporarily route to admin-service
        "name": "Workflows",
        "enabled": False,  # Disabled until implemented
        "routes": ["/workflows"],
        "ui_routes": ["workflows"]
    },
}

@app.get("/")
async def root():
    """API Gateway root"""
    return {
        "service": "API Gateway",
        "status": "online",
        "version": "1.0.0",
        "services": len(SERVICES)
    }

@app.get("/api/services")
async def get_services():
    """Return list of available services for frontend discovery"""
    services_list = []
    for service_id, service_info in SERVICES.items():
        if service_info["enabled"]:
            services_list.append({
                "id": service_id,
                "name": service_info["name"],
                "enabled": service_info["enabled"],
                "ui_routes": service_info["ui_routes"],
                "api_routes": service_info["routes"]
            })
    return services_list

@app.post("/login")
async def unified_login(request: Request):
    """Unified login endpoint for all users (admin, operator, viewer)"""
    try:
        async with httpx.AsyncClient() as client:
            # Forward login request to admin-service
            response = await client.post(
                "http://admin-service:3005/admin/login",
                headers={"Content-Type": "application/json"},
                content=await request.body(),
                timeout=10.0
            )

            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=502, detail=f"Login service unavailable: {str(e)}")

@app.get("/me")
async def get_current_user(request: Request):
    """Get current authenticated user info"""
    try:
        async with httpx.AsyncClient() as client:
            # Forward request to admin-service with authorization header
            response = await client.get(
                "http://admin-service:3005/admin/me",
                headers=dict(request.headers),
                timeout=10.0
            )

            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=502, detail=f"User service unavailable: {str(e)}")

@app.get("/health")
async def health_check():
    """Aggregate health check for all services"""
    health_status = {"gateway": "healthy", "services": {}}

    async with httpx.AsyncClient() as client:
        for service_id, service_info in SERVICES.items():
            try:
                response = await client.get(f"{service_info['url']}/health", timeout=2.0)
                health_status["services"][service_id] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                }
            except Exception as e:
                health_status["services"][service_id] = {
                    "status": "unreachable",
                    "error": str(e)
                }

    return health_status

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, path: str):
    """Proxy requests to appropriate microservice"""

    # Normalize path - remove trailing slash if present
    original_path = path
    path = path.rstrip('/')

    # Determine which service should handle this request
    target_service = None
    for service_id, service_info in SERVICES.items():
        for route_prefix in service_info["routes"]:
            if f"/{path}".startswith(route_prefix):
                target_service = service_info
                break
        if target_service:
            break

    if not target_service:
        raise HTTPException(status_code=404, detail=f"No service found for path: /{path}")

    # Build the forwarding URL
    # Add trailing slash only for root collection endpoints (exact match to route prefix)
    # Examples:
    # - /devices → /devices/ (collection)
    # - /devices/123 → /devices/123 (detail)
    # - /devices/discover → /devices/discover (action)
    # - /device-groups → /device-groups/ (collection)
    
    # Check if path exactly matches a route prefix (collection endpoint)
    is_collection_endpoint = f"/{path}" in target_service["routes"]
    
    # Add trailing slash for collection endpoints or if original had it
    if original_path.endswith('/') or is_collection_endpoint:
        url = f"{target_service['url']}/{path}/"
    else:
        url = f"{target_service['url']}/{path}"

    # Preserve query string
    if request.url.query:
        url = f"{url}?{request.url.query}"

    try:
        # Don't follow redirects - we're sending the correct URL format
        # Increase timeout for long-running operations like discovery
        request_timeout = 30.0
        if '/discover' in path or '/discovery' in path:
            request_timeout = 120.0  # 2 minutes for discovery operations
        
        async with httpx.AsyncClient(follow_redirects=False) as client:
            # Forward request with same method, headers, and body
            response = await client.request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                content=await request.body(),
                timeout=request_timeout
            )

            # Return the response with proper content type
            if response.content:
                try:
                    # Try to parse as JSON
                    content = response.json()
                    return JSONResponse(
                        content=content,
                        status_code=response.status_code
                    )
                except:
                    # If not JSON, return raw response
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.headers.get('content-type', 'application/octet-stream')
                    )
            else:
                return JSONResponse(
                    content={},
                    status_code=response.status_code
                )
    except Exception as e:
        logger.error(f"Error forwarding request to {url}: {e}")
        raise HTTPException(status_code=502, detail=f"Service unavailable: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting API Gateway on port 3000")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info"
    )
