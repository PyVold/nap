# Microservices Deployment Guide

## 🏗️ Architecture Overview

The Network Audit Platform has been refactored into a microservices architecture with 6 services:

1. **API Gateway** (port 3000) - Main entry point, service routing
2. **Device Service** (port 3001) - Device management, discovery, health checks
3. **Rule Service** (port 3002) - Rules, audits, compliance checking
4. **Backup Service** (port 3003) - Config backups, drift detection
5. **Inventory Service** (port 3004) - Hardware inventory tracking
6. **Admin Service** (port 3005) - User management, integrations, monitoring

## 📁 Project Structure

```
nap/
├── services/
│   ├── api-gateway/          # API Gateway service
│   │   ├── app/
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── device-service/       # Device management service
│   │   ├── app/
│   │   │   ├── routes/       # API routes
│   │   │   ├── services/     # Business logic
│   │   │   ├── models/       # Data models
│   │   │   ├── connectors/   # Device connectors
│   │   │   ├── db_models.py
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── rule-service/         # Rule & audit service
│   ├── backup-service/       # Config backup service
│   ├── inventory-service/    # Hardware inventory service
│   └── admin-service/        # Admin & user management service
├── shared/                   # Shared libraries
│   ├── database.py
│   ├── config.py
│   ├── auth.py
│   ├── logger.py
│   └── ...
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── services/
│   │   │   └── serviceDiscovery.js  # Dynamic service discovery
│   │   └── ...
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml        # Orchestration file
└── MICROSERVICES_ARCHITECTURE.md  # Architecture documentation
```

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM (minimum)
- Ports 3000-3005, 5432, 8080 available

### 1. Clone and Navigate

```bash
cd /path/to/nap
```

### 2. Build and Start All Services

```bash
docker-compose up --build
```

This will:
- Build all 6 microservices
- Start PostgreSQL database
- Start frontend (React + Nginx)
- Set up networking between services

### 3. Access the Application

- **Frontend**: http://localhost:8080
- **API Gateway**: http://localhost:3000
- **Service Discovery**: http://localhost:3000/api/services
- **Health Check**: http://localhost:3000/health

### 4. Individual Service Endpoints

- **Device Service**: http://localhost:3001
- **Rule Service**: http://localhost:3002
- **Backup Service**: http://localhost:3003
- **Inventory Service**: http://localhost:3004
- **Admin Service**: http://localhost:3005

## 🔧 Development Mode

### Run Individual Services

```bash
# Run device service only
cd services/device-service
pip install -r requirements.txt
python app/main.py
```

### Run with Hot Reload

```bash
# In each service directory
uvicorn app.main:app --reload --port 3001
```

### Frontend Development

```bash
cd frontend
npm install
npm start  # Runs on port 3000 (dev server)
```

## 🐳 Docker Commands

### Build All Services

```bash
docker-compose build
```

### Start Services

```bash
# Foreground (see logs)
docker-compose up

# Background (detached)
docker-compose up -d
```

### Stop Services

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f device-service
docker-compose logs -f api-gateway
```

### Restart Service

```bash
docker-compose restart device-service
```

### Rebuild Single Service

```bash
docker-compose up -d --build device-service
```

## 🗄️ Database Management

### Access Database

```bash
docker-compose exec database psql -U nap_user -d nap_db
```

### Run Migrations

```bash
# From host
docker-compose exec device-service python -c "from app.db_models import Base; from shared.database import engine; Base.metadata.create_all(bind=engine)"
```

### Backup Database

```bash
docker-compose exec database pg_dump -U nap_user nap_db > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker-compose exec -T database psql -U nap_user -d nap_db
```

## 🔍 Service Discovery

The frontend dynamically discovers available services on startup:

```javascript
// Frontend calls on startup
GET /api/services

// Response:
[
  {
    "id": "device-service",
    "name": "Device Management",
    "enabled": true,
    "ui_routes": ["devices", "discovery", "health"],
    "api_routes": ["/devices", "/device-groups", "/discovery-groups"]
  },
  ...
]
```

The frontend then:
1. Builds navigation menu dynamically
2. Renders only available modules
3. Routes API calls through the gateway

## 🏥 Health Monitoring

### Check All Services Health

```bash
curl http://localhost:3000/health
```

Response:
```json
{
  "gateway": "healthy",
  "services": {
    "device-service": {
      "status": "healthy",
      "response_time_ms": 12
    },
    "rule-service": {
      "status": "healthy",
      "response_time_ms": 15
    },
    ...
  }
}
```

### Check Individual Service

```bash
curl http://localhost:3001/health  # Device service
curl http://localhost:3002/health  # Rule service
```

## 🔐 Environment Variables

### Gateway (.env)

```bash
LOG_LEVEL=info
```

### Services (.env)

```bash
DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
SERVICE_PORT=3001
LOG_LEVEL=info
JWT_SECRET=your-secret-key-change-in-production
```

### Frontend (.env)

```bash
REACT_APP_API_URL=http://localhost:3000
```

## 📊 Scaling Services

### Scale Horizontally

```bash
# Run 3 instances of device-service
docker-compose up -d --scale device-service=3
```

### Load Balancing

For production, add a load balancer (Nginx, HAProxy) in front of the API Gateway.

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs device-service

# Check if port is in use
lsof -i :3001

# Rebuild service
docker-compose up -d --build --force-recreate device-service
```

### Database Connection Issues

```bash
# Check database is running
docker-compose ps database

# Check database logs
docker-compose logs database

# Restart database
docker-compose restart database
```

### Frontend Can't Connect to Gateway

```bash
# Check API gateway is running
curl http://localhost:3000/health

# Check nginx config
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# Check browser console for CORS errors
```

### Service Discovery Not Working

```bash
# Check gateway can reach services
docker-compose exec api-gateway ping device-service

# Check service registry
curl http://localhost:3000/api/services

# Check docker network
docker network inspect nap_network
```

## 🚀 Production Deployment

### Using Docker Swarm

```bash
docker swarm init
docker stack deploy -c docker-compose.yml nap
```

### Using Kubernetes

```bash
# Convert docker-compose to K8s manifests
kompose convert -f docker-compose.yml

# Apply manifests
kubectl apply -f ./
```

### Using Cloud Services

- **AWS**: ECS, EKS, or App Runner
- **Azure**: Container Instances or AKS
- **GCP**: Cloud Run or GKE

## 📈 Monitoring & Logging

### Centralized Logging

Add ELK Stack or Loki to `docker-compose.yml`:

```yaml
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"

  grafana:
    image: grafana/grafana:10.0.0
    ports:
      - "3001:3000"
```

### Metrics Collection

Add Prometheus for metrics:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
```

## 🔒 Security

### Production Checklist

- [ ] Change default database credentials
- [ ] Set strong JWT_SECRET
- [ ] Enable HTTPS (add SSL certificates)
- [ ] Implement rate limiting
- [ ] Add authentication to all endpoints
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Enable network policies
- [ ] Run security scans on images
- [ ] Implement API key rotation
- [ ] Set up audit logging

## 📝 Additional Resources

- [Architecture Documentation](./MICROSERVICES_ARCHITECTURE.md)
- [API Gateway Code](./services/api-gateway/app/main.py)
- [Service Discovery Client](./frontend/src/services/serviceDiscovery.js)
- [Docker Compose File](./docker-compose.yml)

## 🆘 Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Check health: `curl http://localhost:3000/health`
3. Review architecture documentation
4. Check individual service logs

## 📄 License

[Your License]
