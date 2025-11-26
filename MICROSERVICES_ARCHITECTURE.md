# Microservices Architecture

## Overview
Network Audit Platform refactored into microservices for better scalability, maintainability, and deployment flexibility.

## Architecture Diagram
```
                          ┌─────────────────┐
                          │   Frontend      │
                          │  (React App)    │
                          └────────┬────────┘
                                   │
                          ┌────────▼────────┐
                          │  API Gateway    │
                          │  (Port 3000)    │
                          └────────┬────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │           │           │           │           │
    ┌──────▼─────┐ ┌──▼─────┐ ┌──▼──────┐ ┌──▼──────┐ ┌──▼─────┐
    │  Device    │ │  Rule  │ │ Backup  │ │Inventory│ │ Admin  │
    │  Service   │ │Service │ │ Service │ │ Service │ │Service │
    │ (Port 3001)│ │(3002)  │ │ (3003)  │ │ (3004)  │ │(3005)  │
    └──────┬─────┘ └───┬────┘ └────┬────┘ └────┬────┘ └───┬────┘
           │           │           │           │           │
           └───────────┴───────────┴───────────┴───────────┘
                                   │
                          ┌────────▼────────┐
                          │    Database     │
                          │   (PostgreSQL)  │
                          └─────────────────┘
```

## Services

### 1. API Gateway (Port 3000)
**Responsibility:** Main entry point, request routing, service discovery
- Service registry and discovery
- Request routing to appropriate services
- CORS handling
- Authentication middleware
- Health check aggregation

**Endpoints:**
- `GET /api/services` - List available services
- `GET /health` - Overall system health
- `/devices/*` → device-service
- `/rules/*` → rule-service
- `/backups/*` → backup-service
- `/inventory/*` → inventory-service
- `/admin/*` → admin-service

### 2. Device Service (Port 3001)
**Responsibility:** Device management, discovery, and health monitoring
- Device CRUD operations
- Device groups management
- Discovery groups (subnet scanning)
- Device import/export (CSV)
- Health checks (ping, netconf)
- Device connectivity testing

**Technology:** FastAPI, connectors (netconf, ssh, nokia-sros)

**Database Tables:**
- devices
- device_groups
- device_group_members
- discovery_groups
- health_checks

### 3. Rule Service (Port 3002)
**Responsibility:** Rule management and compliance auditing
- Rule CRUD operations
- Rule templates library (CIS, PCI-DSS, NIST)
- Audit execution
- Audit scheduling (cron)
- Audit results and reports

**Technology:** FastAPI, audit engine, rule engine

**Database Tables:**
- rules
- rule_templates
- audit_results
- audit_schedules

### 4. Backup Service (Port 3003)
**Responsibility:** Configuration backup and change tracking
- Configuration backup (scheduled/on-demand)
- Configuration versioning
- Drift detection
- Baseline management
- Change comparison

**Technology:** FastAPI, device connectors

**Database Tables:**
- config_backups
- drift_detections
- config_baselines

### 5. Inventory Service (Port 3004)
**Responsibility:** Hardware inventory tracking
- Hardware component discovery
- Inventory tracking (chassis, cards, ports)
- Serial number tracking
- Software version tracking

**Technology:** FastAPI, device connectors

**Database Tables:**
- hardware_inventory

### 6. Admin Service (Port 3005)
**Responsibility:** System administration and monitoring
- User management (CRUD)
- User groups and RBAC
- Integration hub (NetBox, Git, Ansible, etc.)
- Notification webhooks (Slack, Teams, Discord)
- System modules registry
- Service health dashboard

**Technology:** FastAPI, auth system

**Database Tables:**
- users
- user_groups
- user_group_members
- permissions
- integrations
- notification_webhooks
- notification_logs
- system_modules

## Shared Components

### Shared Libraries (installed in each service)
- **shared/database.py** - Database connection
- **shared/auth.py** - Authentication utilities
- **shared/logger.py** - Logging setup
- **shared/exceptions.py** - Custom exceptions

### Connectors (in device-service, exposed via API)
- netconf_connector
- ssh_connector
- nokia_sros_connector
- device_connector

## Database Strategy

**Shared Database:** All services connect to a single PostgreSQL database with table prefixes for organization.

**Alternative (Future):** Migrate to per-service databases with inter-service communication via REST APIs.

## Service Discovery

### Static Configuration (Initial)
Services register themselves with the API gateway on startup via `/api/register-service` endpoint.

Each service provides:
- `service_name`: Unique identifier
- `display_name`: Human-readable name
- `port`: Service port
- `base_path`: URL path prefix
- `health_endpoint`: Health check URL
- `ui_routes`: Frontend routes this service provides

### Dynamic Discovery (Frontend)
Frontend calls `GET /api/services` on startup to discover available services and dynamically builds:
- Navigation menu
- Routes
- Feature toggles

## Frontend Architecture

### Service Discovery
```javascript
// On app startup
const services = await fetch('/api/services').then(r => r.json());

// Dynamically build navigation
services.forEach(service => {
  if (service.enabled) {
    renderNavItem(service.display_name, service.ui_routes);
  }
});
```

### Module Structure
```
frontend/src/
├── App.js                    # Main app with dynamic routing
├── services/
│   └── serviceDiscovery.js   # Service discovery client
├── modules/
│   ├── devices/              # Device management UI
│   ├── rules/                # Rule management UI
│   ├── backups/              # Backup management UI
│   ├── inventory/            # Inventory UI
│   └── admin/                # Admin UI
└── shared/
    ├── components/           # Shared UI components
    └── utils/                # API client, auth
```

## Deployment

### Docker Compose
All services deployed as Docker containers with docker-compose:

```yaml
services:
  api-gateway:
    build: ./services/api-gateway
    ports: ["3000:3000"]
  
  device-service:
    build: ./services/device-service
    ports: ["3001:3001"]
  
  rule-service:
    build: ./services/rule-service
    ports: ["3002:3002"]
  
  # ... other services
  
  database:
    image: postgres:15
    environment:
      POSTGRES_DB: nap_db
```

### Environment Variables
Each service uses environment variables for configuration:
- `DATABASE_URL` - Database connection string
- `SERVICE_PORT` - Service port
- `API_GATEWAY_URL` - Gateway URL for service registration
- `JWT_SECRET` - Shared JWT secret for auth

## Inter-Service Communication

Services communicate via REST APIs through the API gateway:
- Backup service needs device info → calls `/devices/{id}` via gateway
- Inventory service needs device info → calls `/devices/{id}` via gateway

**Future Enhancement:** Implement message queue (RabbitMQ/Kafka) for async communication.

## Migration Path

1. ✅ Clean up unused code
2. 🔄 Create service directory structure
3. 🔄 Split routes and services into microservices
4. 🔄 Create shared libraries
5. 🔄 Create Dockerfiles and docker-compose
6. 🔄 Implement service registry
7. 🔄 Update frontend for dynamic discovery
8. 🔄 Test and deploy

## Benefits

- **Independent Deployment:** Each service can be deployed separately
- **Scalability:** Scale individual services based on load
- **Technology Flexibility:** Use different tech stacks per service if needed
- **Team Organization:** Teams can own individual services
- **Fault Isolation:** Failure in one service doesn't crash entire system
- **Dynamic Features:** Frontend adapts to available services
