# Network Audit Platform - Microservices Edition

> A modern, cloud-native network compliance and audit platform built with microservices architecture.

## 🎯 What's New

The platform has been refactored from a monolithic application into a **microservices architecture** with:

- ✅ **6 Independent Services** - Each service can be deployed, scaled, and maintained separately
- ✅ **API Gateway** - Centralized routing and service discovery
- ✅ **Dynamic Frontend** - Automatically discovers and adapts to available services
- ✅ **Docker Support** - Full containerization with Docker Compose
- ✅ **Service Discovery** - Frontend dynamically loads modules based on available services
- ✅ **Health Monitoring** - Real-time service health checks
- ✅ **Scalable** - Scale individual services based on load

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│          http://localhost:8080                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                     API Gateway :3000                           │
│              Service Discovery & Routing                        │
└─────┬────────┬────────┬────────┬────────┬──────────────────────┘
      │        │        │        │        │
   ┌──▼──┐  ┌─▼──┐  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐
   │Dev  │  │Rule│  │Back │  │Inv  │  │Admin│
   │:3001│  │:3002│  │:3003│  │:3004│  │:3005│
   └──┬──┘  └─┬──┘  └──┬──┘  └──┬──┘  └──┬──┘
      │       │        │        │        │
      └───────┴────────┴────────┴────────┘
                      │
              ┌───────▼────────┐
              │  PostgreSQL    │
              │    :5432       │
              └────────────────┘
```

## 📦 Services

| Service | Port | Responsibility | Key Features |
|---------|------|----------------|--------------|
| **API Gateway** | 3000 | Routing, Discovery | Service registry, health checks, request proxying |
| **Device Service** | 3001 | Device Management | CRUD, discovery, groups, health monitoring, imports |
| **Rule Service** | 3002 | Compliance | Rules, templates, audits, schedules, compliance reports |
| **Backup Service** | 3003 | Config Management | Backups, drift detection, versioning, baselines |
| **Inventory Service** | 3004 | Asset Tracking | Hardware inventory, software versions, components |
| **Admin Service** | 3005 | Administration | Users, RBAC, integrations, notifications, monitoring |

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Start all services
docker-compose up --build

# 2. Access the application
# Frontend: http://localhost:8080
# API Gateway: http://localhost:3000
# Services: http://localhost:3001-3005
```

### Option 2: Manual Setup

```bash
# 1. Start PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=nap_db \
  -e POSTGRES_USER=nap_user \
  -e POSTGRES_PASSWORD=nap_password \
  postgres:15

# 2. Set environment variable
export DATABASE_URL="postgresql://nap_user:nap_password@localhost:5432/nap_db"

# 3. Start each service
cd services/device-service && python app/main.py &  # Port 3001
cd services/rule-service && python app/main.py &    # Port 3002
cd services/backup-service && python app/main.py &  # Port 3003
cd services/inventory-service && python app/main.py & # Port 3004
cd services/admin-service && python app/main.py &   # Port 3005
cd services/api-gateway && python app/main.py &     # Port 3000

# 4. Start frontend
cd frontend && npm install && npm start
```

## 📚 Documentation

- **[Microservices Architecture](./MICROSERVICES_ARCHITECTURE.md)** - Detailed architecture documentation
- **[Deployment Guide](./MICROSERVICES_DEPLOYMENT.md)** - Complete deployment instructions
- **[API Gateway Code](./services/api-gateway/app/main.py)** - Gateway implementation
- **[Service Discovery Client](./frontend/src/services/serviceDiscovery.js)** - Frontend discovery

## 🔧 Development

### Running Individual Services

```bash
# Device Service
cd services/device-service
pip install -r requirements.txt
python app/main.py

# Rule Service
cd services/rule-service
pip install -r requirements.txt
python app/main.py
```

### Hot Reload Mode

```bash
cd services/device-service
uvicorn app.main:app --reload --port 3001
```

### Frontend Development

```bash
cd frontend
npm install
npm start  # Dev server on http://localhost:3000
```

## 🧪 Testing

### Check Service Health

```bash
# All services
curl http://localhost:3000/health

# Individual service
curl http://localhost:3001/health  # Device service
curl http://localhost:3002/health  # Rule service
```

### Discover Services

```bash
# Get list of available services
curl http://localhost:3000/api/services

# Response:
# [
#   {
#     "id": "device-service",
#     "name": "Device Management",
#     "enabled": true,
#     "ui_routes": ["devices", "discovery", "health"]
#   },
#   ...
# ]
```

## 🎯 Key Features

### Dynamic Service Discovery

The frontend automatically discovers available services:

1. On startup, calls `/api/services` endpoint
2. Builds navigation menu dynamically
3. Renders only available modules
4. Adapts UI based on service availability

### API Gateway Routing

All API requests go through the gateway which routes to appropriate services:

```
GET /devices/123           → device-service:3001/devices/123
POST /rules               → rule-service:3002/rules
GET /config-backups       → backup-service:3003/config-backups
```

### Independent Scaling

Scale services individually based on load:

```bash
# Scale device service to 3 instances
docker-compose up -d --scale device-service=3

# Scale rule service to 2 instances
docker-compose up -d --scale rule-service=2
```

## 📊 Monitoring

### Health Checks

```bash
# Gateway health
curl http://localhost:3000/health

# Individual service health
curl http://localhost:3001/health
```

### Service Discovery

```bash
# List all services
curl http://localhost:3000/api/services
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f device-service

# Last 100 lines
docker-compose logs --tail=100 rule-service
```

## 🗄️ Database

### Connection

All services connect to shared PostgreSQL database:

```
postgresql://nap_user:nap_password@database:5432/nap_db
```

### Access Database

```bash
docker-compose exec database psql -U nap_user -d nap_db
```

### Backup/Restore

```bash
# Backup
docker-compose exec database pg_dump -U nap_user nap_db > backup.sql

# Restore
cat backup.sql | docker-compose exec -T database psql -U nap_user -d nap_db
```

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs
docker-compose logs -f

# Restart service
docker-compose restart device-service

# Rebuild service
docker-compose up -d --build device-service
```

## 🔐 Security

### Production Checklist

- [ ] Change default database credentials in `docker-compose.yml`
- [ ] Set strong `JWT_SECRET` in admin-service
- [ ] Enable HTTPS with SSL certificates
- [ ] Implement rate limiting on API Gateway
- [ ] Add authentication to all endpoints
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Run security scans on Docker images
- [ ] Set up audit logging
- [ ] Implement network policies

## 🚢 Deployment

### Docker Swarm

```bash
docker swarm init
docker stack deploy -c docker-compose.yml nap
```

### Kubernetes

```bash
# Convert to K8s manifests
kompose convert -f docker-compose.yml

# Apply
kubectl apply -f ./
```

### Cloud Providers

- **AWS**: ECS, EKS, or App Runner
- **Azure**: Container Instances or AKS
- **GCP**: Cloud Run or GKE

## 🛠️ Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs service-name

# Rebuild
docker-compose up -d --build --force-recreate service-name
```

### Can't Connect to Database

```bash
# Check database status
docker-compose ps database

# Restart database
docker-compose restart database
```

### Frontend Can't Reach Services

```bash
# Check gateway is running
curl http://localhost:3000/health

# Check service discovery
curl http://localhost:3000/api/services
```

## 📝 Migration from Monolith

The codebase was migrated using `migrate_to_microservices.py`:

1. ✅ Removed unused code (config templates, workflows)
2. ✅ Created shared libraries
3. ✅ Split routes/services into microservices
4. ✅ Created API Gateway with service registry
5. ✅ Containerized all services
6. ✅ Updated frontend for dynamic discovery

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

[Your License]

## 🆘 Support

- **Documentation**: See `MICROSERVICES_ARCHITECTURE.md` and `MICROSERVICES_DEPLOYMENT.md`
- **Issues**: Check logs with `docker-compose logs -f`
- **Health**: Check `http://localhost:3000/health`
- **Discovery**: Check `http://localhost:3000/api/services`

## 🎉 What's Next?

- [ ] Implement message queue (RabbitMQ/Kafka) for async communication
- [ ] Add API rate limiting
- [ ] Implement circuit breakers
- [ ] Add distributed tracing (Jaeger/Zipkin)
- [ ] Set up centralized logging (ELK stack)
- [ ] Add Prometheus metrics
- [ ] Implement GraphQL gateway
- [ ] Add service mesh (Istio/Linkerd)
