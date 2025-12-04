# Developer Documentation

Technical documentation for developers working on the Network Audit Platform (NAP).

## Architecture Overview

NAP uses a microservices architecture with the following components:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│                         Port: 80 (nginx)                         │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                       │
│                         Port: 8000                               │
└─────────────────────────────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Device Service │    │   Rule Service  │    │  Admin Service  │
│    Port: 8001   │    │    Port: 8002   │    │    Port: 8003   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                          │
│                         Port: 5432                               │
└─────────────────────────────────────────────────────────────────┘
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| api-gateway | 8000 | Request routing, authentication, rate limiting |
| device-service | 8001 | Device management, discovery, health checks |
| rule-service | 8002 | Audit rules, auditing engine, compliance |
| admin-service | 8003 | Users, licenses, system administration |
| backup-service | 8004 | Configuration backup, drift detection |
| inventory-service | 8005 | Hardware inventory, asset management |
| analytics-service | 8006 | Reporting, analytics, dashboards |
| frontend | 80 | React web interface (nginx) |
| database | 5432 | PostgreSQL database |

## Project Structure

```
nap/
├── services/                    # Microservices
│   ├── api-gateway/            # API Gateway service
│   │   └── app/
│   │       ├── main.py         # FastAPI application
│   │       ├── routes/         # API routes
│   │       └── db_models.py    # Database models
│   ├── device-service/         # Device management
│   │   └── app/
│   │       ├── main.py
│   │       ├── routes/
│   │       │   ├── devices.py
│   │       │   ├── discovery_groups.py
│   │       │   └── health.py
│   │       └── services/
│   │           ├── device_service.py
│   │           ├── discovery_service.py
│   │           └── health_service.py
│   ├── rule-service/           # Audit rules & engine
│   │   └── app/
│   │       ├── routes/
│   │       │   ├── rules.py
│   │       │   └── audits.py
│   │       ├── services/
│   │       └── engine/         # Audit engine
│   │           ├── audit_engine.py
│   │           ├── rule_executor.py
│   │           └── comparators.py
│   └── admin-service/          # Administration
│       └── app/
│           ├── routes/
│           │   ├── users.py
│           │   └── license.py
│           └── services/
├── shared/                      # Shared code
│   ├── deps.py                 # FastAPI dependencies
│   ├── crypto.py               # Encryption utilities
│   ├── validators.py           # Input validation
│   ├── logger.py               # Logging configuration
│   └── device_metadata_collector.py
├── connectors/                  # Device connectors
│   ├── base_connector.py       # Abstract base class
│   ├── netconf_connector.py    # NETCONF (Cisco XR)
│   ├── nokia_sros_connector.py # pysros (Nokia)
│   └── ssh_connector.py        # SSH fallback
├── models/                      # Pydantic models
│   ├── device.py
│   ├── rule.py
│   ├── audit.py
│   └── enums.py
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── contexts/           # React contexts
│   │   ├── api/                # API client
│   │   └── App.js
│   └── public/
├── migrations/                  # Database migrations
├── docker-compose.yml          # Docker orchestration
├── .env                        # Environment variables
└── requirements.txt            # Python dependencies
```

## Development Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- PostgreSQL 14+ (or use Docker)

### Local Development

1. **Clone and setup environment:**
```bash
git clone <repository>
cd nap
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Start database:**
```bash
docker-compose up -d database
```

3. **Run services individually:**
```bash
# Terminal 1 - Device Service
cd services/device-service
uvicorn app.main:app --reload --port 8001

# Terminal 2 - Rule Service
cd services/rule-service
uvicorn app.main:app --reload --port 8002

# Terminal 3 - Admin Service
cd services/admin-service
uvicorn app.main:app --reload --port 8003

# Terminal 4 - API Gateway
cd services/api-gateway
uvicorn app.main:app --reload --port 8000
```

4. **Run frontend:**
```bash
cd frontend
npm install
npm start
```

### Using Docker (Recommended)

```bash
# Build and start all services
docker-compose up --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild specific service
docker-compose up --build device-service
```

## API Documentation

### Authentication

All API requests require JWT authentication (except login):

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# Use token in subsequent requests
curl -X GET http://localhost:8000/devices/ \
  -H "Authorization: Bearer eyJ..."
```

### Main Endpoints

#### Devices
```
GET    /devices/                    # List all devices
POST   /devices/                    # Create device
GET    /devices/{id}                # Get device
PUT    /devices/{id}                # Update device
DELETE /devices/{id}                # Delete device
POST   /devices/discover            # Run discovery
GET    /devices/{id}/metadata       # Get device metadata
```

#### Rules
```
GET    /rules/                      # List all rules
POST   /rules/                      # Create rule
GET    /rules/{id}                  # Get rule
PUT    /rules/{id}                  # Update rule
DELETE /rules/{id}                  # Delete rule
PUT    /rules/{id}/toggle           # Enable/disable rule
```

#### Audits
```
POST   /audit/                      # Run audit
GET    /audit/results               # Get audit results
GET    /audit/results/{id}          # Get specific result
GET    /audit/compliance            # Get compliance summary
```

#### Health
```
POST   /health/check/{device_id}    # Check device health
POST   /health/check-all            # Check all devices
GET    /health/summary              # Health summary
GET    /health/history/{device_id}  # Health history
```

### Interactive API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Schema

### Key Tables

```sql
-- Devices
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    ip VARCHAR(50),
    vendor VARCHAR(50),  -- 'cisco_xr' or 'nokia_sros'
    port INTEGER DEFAULT 830,
    username VARCHAR(255),
    password VARCHAR(255),  -- encrypted
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Audit Rules
CREATE TABLE audit_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20),  -- critical, high, medium, low
    category VARCHAR(50),
    enabled BOOLEAN DEFAULT true,
    vendors JSONB,  -- ['cisco_xr', 'nokia_sros']
    checks JSONB,   -- array of check objects
    created_at TIMESTAMP
);

-- Audit Results
CREATE TABLE audit_results (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id),
    rule_id INTEGER REFERENCES audit_rules(id),
    status VARCHAR(20),  -- pass, fail, error
    message TEXT,
    details JSONB,
    created_at TIMESTAMP
);
```

## Adding New Vendors

1. **Create connector** in `connectors/`:
```python
# connectors/juniper_connector.py
from connectors.base_connector import BaseConnector

class JuniperConnector(BaseConnector):
    async def connect(self) -> bool:
        # Implementation
        pass

    async def get_config(self, filter_data=None) -> str:
        # Implementation
        pass

    async def disconnect(self):
        # Implementation
        pass
```

2. **Add vendor enum** in `models/enums.py`:
```python
class VendorType(str, Enum):
    CISCO_XR = "cisco_xr"
    NOKIA_SROS = "nokia_sros"
    JUNIPER = "juniper"  # Add new vendor
```

3. **Update device service** to use new connector

4. **Update frontend** vendor dropdown

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nap

# Security
JWT_SECRET=your-secret-key-min-32-chars
ENCRYPTION_KEY=your-fernet-key

# Services
DEVICE_SERVICE_URL=http://device-service:8001
RULE_SERVICE_URL=http://rule-service:8002
ADMIN_SERVICE_URL=http://admin-service:8003

# Features
ENABLE_AUTH=true
DEBUG_MODE=false
LOG_LEVEL=INFO
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov-report=html

# Run specific service tests
pytest services/device-service/tests/

# Run frontend tests
cd frontend && npm test
```

## Code Style

- Python: Follow PEP 8, use Black formatter
- JavaScript: Follow ESLint config, use Prettier
- Commits: Use conventional commits (feat:, fix:, docs:, etc.)

```bash
# Format Python code
black services/ shared/ connectors/

# Lint Python
flake8 services/ shared/ connectors/

# Format/Lint frontend
cd frontend && npm run lint && npm run format
```

## Debugging

### View service logs
```bash
docker-compose logs -f device-service
```

### Connect to database
```bash
docker-compose exec database psql -U nap_user -d nap_db
```

### Debug specific service
```bash
# Add to service's main.py
import debugpy
debugpy.listen(("0.0.0.0", 5678))
```

## Known Issues

1. **CORS in development**: Set `allow_origins=["*"]` only for development
2. **pysros connection**: Requires network access to Nokia devices
3. **Large configs**: May timeout for devices with very large configurations

## Contributing

1. Create feature branch from `main`
2. Make changes following code style
3. Add tests for new functionality
4. Submit PR with clear description

## Security Considerations

- Never commit `.env` files with real credentials
- Encrypt device passwords before storing
- Use HTTPS in production
- Implement rate limiting for APIs
- Regular security audits

---

For questions, contact the development team.
