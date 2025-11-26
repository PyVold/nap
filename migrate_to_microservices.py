#!/usr/bin/env python3
"""
Migration script to refactor monolith into microservices
This script creates the directory structure and moves code to appropriate services
"""

import os
import shutil
from pathlib import Path

# Service definitions
SERVICES = {
    'device-service': {
        'port': 3001,
        'routes': ['devices', 'device_groups', 'discovery_groups', 'device_import', 'health'],
        'services': ['device_service', 'device_group_service', 'discovery_group_service', 'device_import_service', 'health_service'],
        'models': ['device', 'device_group', 'discovery_group'],
        'needs_connectors': True,
        'needs_engine': False,
    },
    'rule-service': {
        'port': 3002,
        'routes': ['rules', 'rule_templates', 'audits', 'audit_schedules'],
        'services': ['rule_service', 'rule_template_service', 'audit_service', 'audit_schedule_service'],
        'models': ['rule', 'audit', 'audit_schedule'],
        'needs_connectors': True,
        'needs_engine': True,
    },
    'backup-service': {
        'port': 3003,
        'routes': ['config_backups', 'drift_detection'],
        'services': ['config_backup_service', 'drift_detection_service'],
        'models': [],
        'needs_connectors': True,
        'needs_engine': False,
    },
    'inventory-service': {
        'port': 3004,
        'routes': ['hardware_inventory'],
        'services': ['hardware_inventory_service'],
        'models': [],
        'needs_connectors': True,
        'needs_engine': False,
    },
    'admin-service': {
        'port': 3005,
        'routes': ['admin', 'user_management', 'integrations', 'notifications', 'remediation'],
        'services': ['user_group_service', 'notification_service', 'remediation_service'],
        'models': ['user_group', 'integrations'],
        'needs_connectors': False,
        'needs_engine': False,
    },
}

def create_shared_libraries():
    """Create shared libraries used by all services"""
    print("Creating shared libraries...")

    shared_dir = Path('shared')
    shared_dir.mkdir(exist_ok=True)

    # Copy existing utilities
    shutil.copy('database.py', 'shared/database.py')
    shutil.copy('config.py', 'shared/config.py')
    shutil.copy('utils/auth.py', 'shared/auth.py')
    shutil.copy('utils/logger.py', 'shared/logger.py')
    shutil.copy('utils/exceptions.py', 'shared/exceptions.py')
    shutil.copy('utils/validators.py', 'shared/validators.py')
    shutil.copy('utils/crypto.py', 'shared/crypto.py')

    # Create __init__.py
    (shared_dir / '__init__.py').write_text('')

    print("✅ Shared libraries created")


def create_service_structure(service_name, service_config):
    """Create directory structure for a microservice"""
    print(f"\nCreating {service_name}...")

    service_dir = Path(f'services/{service_name}/app')
    service_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (service_dir / 'routes').mkdir(exist_ok=True)
    (service_dir / 'services').mkdir(exist_ok=True)
    (service_dir / 'models').mkdir(exist_ok=True)

    if service_config['needs_connectors']:
        (service_dir / 'connectors').mkdir(exist_ok=True)

    if service_config['needs_engine']:
        (service_dir / 'engine').mkdir(exist_ok=True)

    # Create __init__.py files
    (service_dir / '__init__.py').write_text('')
    (service_dir / 'routes' / '__init__.py').write_text('')
    (service_dir / 'services' / '__init__.py').write_text('')
    (service_dir / 'models' / '__init__.py').write_text('')

    # Copy routes
    for route_name in service_config['routes']:
        src = f'api/routes/{route_name}.py'
        if os.path.exists(src):
            shutil.copy(src, service_dir / 'routes' / f'{route_name}.py')
            print(f"  ✅ Copied route: {route_name}")

    # Copy services
    for service_file in service_config['services']:
        src = f'services/{service_file}.py'
        if os.path.exists(src):
            shutil.copy(src, service_dir / 'services' / f'{service_file}.py')
            print(f"  ✅ Copied service: {service_file}")

    # Copy models
    for model_name in service_config['models']:
        src = f'models/{model_name}.py'
        if os.path.exists(src):
            shutil.copy(src, service_dir / 'models' / f'{model_name}.py')
            print(f"  ✅ Copied model: {model_name}")

    # Copy connectors if needed
    if service_config['needs_connectors']:
        for connector_file in os.listdir('connectors'):
            if connector_file.endswith('.py'):
                shutil.copy(f'connectors/{connector_file}',
                           service_dir / 'connectors' / connector_file)
        print(f"  ✅ Copied connectors")

    # Copy engine if needed
    if service_config['needs_engine']:
        shutil.copytree('engine', service_dir / 'engine', dirs_exist_ok=True)
        print(f"  ✅ Copied audit engine")

    # Copy db_models.py to each service
    shutil.copy('db_models.py', service_dir / 'db_models.py')

    # Create main.py for the service
    create_service_main(service_name, service_config)

    # Create requirements.txt for the service
    create_service_requirements(service_name, service_config)

    # Create Dockerfile
    create_service_dockerfile(service_name, service_config)

    print(f"✅ {service_name} structure created")


def create_service_main(service_name, service_config):
    """Create main.py for a microservice"""
    routes_imports = ', '.join(service_config['routes'])
    port = service_config['port']

    main_content = f'''"""
{service_name.replace('-', ' ').title()} - FastAPI Microservice
Port: {port}
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append('../../..')
from shared.database import get_db, init_db
from shared.config import settings
from shared.logger import setup_logger
from routes import {routes_imports}

logger = setup_logger(__name__)

app = FastAPI(
    title="{service_name.replace('-', ' ').title()}",
    version="1.0.0",
    description="Network Audit Platform - {service_name.replace('-', ' ').title()}"
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
'''

    for route_name in service_config['routes']:
        main_content += f'app.include_router({route_name}.router, tags=["{route_name.replace("_", " ").title()}"])\n'

    main_content += f'''

@app.get("/")
async def root():
    """Service health check"""
    return {{
        "service": "{service_name}",
        "status": "online",
        "version": "1.0.0",
        "port": {port}
    }}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {{
        "status": "healthy",
        "service": "{service_name}",
        "database": "connected"
    }}

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {service_name} on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port={port},
        log_level="info"
    )
'''

    service_dir = Path(f'services/{service_name}/app')
    (service_dir / 'main.py').write_text(main_content)


def create_service_requirements(service_name, service_config):
    """Create requirements.txt for a microservice"""

    # Base requirements for all services
    requirements = [
        'fastapi==0.104.1',
        'uvicorn[standard]==0.24.0',
        'pydantic==2.5.0',
        'pydantic-settings==2.1.0',
        'sqlalchemy==2.0.23',
        'psycopg2-binary==2.9.9',
        'aiosqlite==0.19.0',
        'python-jose[cryptography]==3.3.0',
        'passlib[bcrypt]==1.7.4',
        'cryptography==41.0.7',
    ]

    # Add connector dependencies if needed
    if service_config['needs_connectors']:
        requirements.extend([
            'ncclient==0.6.15',
            'paramiko==3.3.1',
            'netmiko==4.3.0',
            'lxml==4.9.3',
            'pysros>=24.10.1',
        ])

    # Add scheduler if needed for audit/backup services
    if service_name in ['rule-service', 'backup-service']:
        requirements.append('apscheduler==3.10.4')

    # Add notification dependencies for admin service
    if service_name == 'admin-service':
        requirements.extend([
            'aiohttp==3.9.1',
            'python-multipart==0.0.20',
            'email-validator==2.1.0',
        ])

    service_dir = Path(f'services/{service_name}')
    (service_dir / 'requirements.txt').write_text('\n'.join(requirements) + '\n')


def create_service_dockerfile(service_name, service_config):
    """Create Dockerfile for a microservice"""
    port = service_config['port']

    # Build context is project root, so paths are relative to root
    dockerfile_content = f'''FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/{service_name}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/{service_name}/app /app

# Expose port
EXPOSE {port}

# Run the service
CMD ["python", "main.py"]
'''

    service_dir = Path(f'services/{service_name}')
    (service_dir / 'Dockerfile').write_text(dockerfile_content)


def create_api_gateway():
    """Create API Gateway service"""
    print("\nCreating API Gateway...")

    gateway_dir = Path('services/api-gateway/app')
    gateway_dir.mkdir(parents=True, exist_ok=True)

    # Create API Gateway main.py
    gateway_main = '''"""
API Gateway - Main Entry Point
Handles service discovery and request routing
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import sys
sys.path.append('../../..')
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
        "routes": ["/hardware-inventory"],
        "ui_routes": ["inventory"]
    },
    "admin-service": {
        "url": "http://admin-service:3005",
        "name": "Administration",
        "enabled": True,
        "routes": ["/admin", "/user-management", "/integrations", "/notifications", "/remediation"],
        "ui_routes": ["admin", "users", "integrations"]
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

    # Forward the request
    url = f"{target_service['url']}/{path}"

    try:
        async with httpx.AsyncClient() as client:
            # Forward request with same method, headers, and body
            response = await client.request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                content=await request.body(),
                timeout=30.0
            )

            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code,
                headers=dict(response.headers)
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
'''

    (gateway_dir / 'main.py').write_text(gateway_main)
    (gateway_dir / '__init__.py').write_text('')

    # Create requirements.txt for gateway
    gateway_requirements = '''fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.1
pydantic==2.5.0
'''

    Path('services/api-gateway/requirements.txt').write_text(gateway_requirements)

    # Create Dockerfile for gateway
    # Build context is project root, so paths are relative to root
    gateway_dockerfile = '''FROM python:3.11-slim

WORKDIR /app

COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared /app/shared
COPY services/api-gateway/app /app

EXPOSE 3000

CMD ["python", "main.py"]
'''

    Path('services/api-gateway/Dockerfile').write_text(gateway_dockerfile)

    print("✅ API Gateway created")


def create_docker_compose():
    """Create docker-compose.yml for all services"""
    print("\nCreating docker-compose.yml...")

    docker_compose = '''version: '3.8'

services:
  # Database
  database:
    image: postgres:15
    environment:
      POSTGRES_DB: nap_db
      POSTGRES_USER: nap_user
      POSTGRES_PASSWORD: nap_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nap_user -d nap_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  # API Gateway
  api-gateway:
    build:
      context: .
      dockerfile: services/api-gateway/Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - device-service
      - rule-service
      - backup-service
      - inventory-service
      - admin-service
    environment:
      - LOG_LEVEL=info

  # Device Service
  device-service:
    build:
      context: .
      dockerfile: services/device-service/Dockerfile
    ports:
      - "3001:3001"
    depends_on:
      database:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
      - SERVICE_PORT=3001
      - LOG_LEVEL=info

  # Rule Service
  rule-service:
    build:
      context: .
      dockerfile: services/rule-service/Dockerfile
    ports:
      - "3002:3002"
    depends_on:
      database:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
      - SERVICE_PORT=3002
      - LOG_LEVEL=info

  # Backup Service
  backup-service:
    build:
      context: .
      dockerfile: services/backup-service/Dockerfile
    ports:
      - "3003:3003"
    depends_on:
      database:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
      - SERVICE_PORT=3003
      - DEVICE_SERVICE_URL=http://device-service:3001
      - LOG_LEVEL=info

  # Inventory Service
  inventory-service:
    build:
      context: .
      dockerfile: services/inventory-service/Dockerfile
    ports:
      - "3004:3004"
    depends_on:
      database:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
      - SERVICE_PORT=3004
      - DEVICE_SERVICE_URL=http://device-service:3001
      - LOG_LEVEL=info

  # Admin Service
  admin-service:
    build:
      context: .
      dockerfile: services/admin-service/Dockerfile
    ports:
      - "3005:3005"
    depends_on:
      database:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
      - SERVICE_PORT=3005
      - JWT_SECRET=your-secret-key-change-in-production
      - LOG_LEVEL=info

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "8080:80"
    depends_on:
      - api-gateway
    environment:
      - REACT_APP_API_URL=http://localhost:3000

volumes:
  postgres_data:

networks:
  default:
    name: nap_network
'''

    Path('docker-compose.yml').write_text(docker_compose)
    print("✅ docker-compose.yml created")


def main():
    """Main migration function"""
    print("=" * 60)
    print("Network Audit Platform - Microservices Migration")
    print("=" * 60)

    try:
        # Step 1: Create shared libraries
        create_shared_libraries()

        # Step 2: Create each microservice
        for service_name, service_config in SERVICES.items():
            create_service_structure(service_name, service_config)

        # Step 3: Create API Gateway
        create_api_gateway()

        # Step 4: Create Docker Compose
        create_docker_compose()

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the generated services in ./services/")
        print("2. Update import paths in service files if needed")
        print("3. Test services individually")
        print("4. Run: docker-compose up --build")
        print("5. Update frontend to use service discovery")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
