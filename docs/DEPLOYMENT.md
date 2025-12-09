# Network Audit Platform - Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [Monitoring](#monitoring)
6. [Security Hardening](#security-hardening)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- Docker 20.10+ and Docker Compose 2.0+
- Minimum 4GB RAM (8GB recommended for production)
- 20GB+ disk space for data storage
- Linux (Ubuntu 20.04+ recommended) or Windows with WSL2

### Network Requirements
- Port 80/443 for web interface
- Port 830 for NETCONF connections to devices
- Outbound access to network devices

---

## Quick Start

### Development Environment
```bash
# Clone the repository
git clone https://github.com/your-org/nap.git
cd nap

# Start development stack
docker-compose up -d

# Access the application
open http://localhost:3000
```

Default credentials: `admin` / `admin`

---

## Production Deployment

### 1. Run Setup Script
```bash
chmod +x scripts/setup-production.sh
./scripts/setup-production.sh
```

This script will:
- Generate secure secrets
- Create `.env.prod` configuration file
- Set up monitoring configurations
- Configure proper file permissions

### 2. Configure Environment
```bash
# Review and update configuration
nano .env.prod

# Required settings to update:
# - API_URL: Your public domain
# - POSTGRES_PASSWORD: Strong database password
# - JWT_SECRET_KEY: Secure JWT signing key
# - ENCRYPTION_KEY: Device credential encryption key
```

### 3. SSL/TLS Setup
```bash
# Create SSL directory
mkdir -p nginx/ssl

# Option A: Let's Encrypt (recommended)
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/

# Option B: Self-signed (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem
```

### 4. Start Production Stack
```bash
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. Initialize Admin User
```bash
# Change default admin password immediately
curl -X POST http://localhost:3000/api/users/admin/password \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "YourSecurePassword123!"}'
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `nap_db` |
| `POSTGRES_USER` | Database username | `nap_user` |
| `POSTGRES_PASSWORD` | Database password | *required* |
| `JWT_SECRET_KEY` | JWT signing key | *required* |
| `ENCRYPTION_KEY` | Device credential encryption key | *required* |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `100` |
| `RATE_LIMIT_WINDOW` | Rate limit window (seconds) | `60` |
| `LOG_LEVEL` | Logging level | `info` |

### Service Ports

| Service | Internal Port | Description |
|---------|--------------|-------------|
| API Gateway | 3000 | Main API endpoint |
| Device Service | 3001 | Device management |
| Rule Service | 3002 | Audit rules |
| Backup Service | 3003 | Configuration backups |
| Admin Service | 3006 | User/system management |
| Analytics Service | 3007 | Reporting & analytics |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| Prometheus | 9090 | Metrics |
| Grafana | 3030 | Dashboards |

---

## Monitoring

### Accessing Dashboards
- **Grafana**: http://localhost:3030 (admin / see .env.prod)
- **Prometheus**: http://localhost:9090

### Health Endpoints
```bash
# Application health
curl http://localhost:3000/health

# Readiness check
curl http://localhost:3000/ready

# Liveness check
curl http://localhost:3000/live

# Prometheus metrics
curl http://localhost:3000/metrics
```

### Key Metrics to Monitor
- `nap_http_requests_total` - Request count by endpoint
- `nap_http_request_duration_ms` - Request latency
- `nap_http_errors_total` - Error count by status code
- `nap_process_memory_bytes` - Memory usage
- `nap_system_cpu_percent` - CPU usage

### Alerting
Configure alerts in Grafana for:
- High error rate (>1% 5xx errors)
- High latency (p95 > 2s)
- Memory usage (>80%)
- Disk space (<20% free)

---

## Security Hardening

### Checklist
- [ ] Change all default passwords
- [ ] Configure SSL/TLS with valid certificates
- [ ] Enable rate limiting
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Enable audit logging
- [ ] Configure CORS properly
- [ ] Review and restrict network access

### Firewall Rules
```bash
# Allow only necessary ports
ufw allow 80/tcp    # HTTP (redirect to HTTPS)
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH (restrict to admin IPs)
ufw enable
```

### Database Security
```bash
# Ensure database is not exposed externally
# In docker-compose.prod.yml, database ports are bound to 127.0.0.1

# Regular backups
docker exec nap_database pg_dump -U nap_user nap_db > backup.sql
```

---

## Backup & Recovery

### Automated Backups
```bash
# Add to crontab
0 2 * * * /path/to/nap/scripts/backup.sh

# backup.sh content
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec nap_database pg_dump -U nap_user nap_db > /backups/db_$DATE.sql
docker exec nap_database pg_dump -U nap_user nap_db | gzip > /backups/db_$DATE.sql.gz
find /backups -name "*.sql.gz" -mtime +30 -delete
```

### Recovery Procedure
```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore database
gunzip -c /backups/db_20240101_020000.sql.gz | \
  docker exec -i nap_database psql -U nap_user nap_db

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs <service-name>

# Check resource usage
docker stats

# Verify database connectivity
docker exec nap_device-service python -c "from shared.database import engine; engine.connect()"
```

#### Database Connection Errors
```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps database

# Test connection
docker exec nap_database psql -U nap_user -d nap_db -c "SELECT 1"
```

#### High Memory Usage
```bash
# Identify memory hogs
docker stats --no-stream

# Restart specific service
docker-compose -f docker-compose.prod.yml restart <service-name>
```

#### API Errors
```bash
# Check API logs
docker-compose -f docker-compose.prod.yml logs -f api-gateway

# Test endpoint
curl -v http://localhost:3000/health
```

### Getting Help
- Check logs: `docker-compose logs -f`
- GitHub Issues: https://github.com/your-org/nap/issues
- Documentation: https://docs.your-org.com/nap

---

## Upgrading

### Version Upgrade Process
```bash
# 1. Backup database
./scripts/backup.sh

# 2. Pull latest code
git pull origin main

# 3. Stop services
docker-compose -f docker-compose.prod.yml down

# 4. Rebuild images
docker-compose -f docker-compose.prod.yml build

# 5. Run migrations
docker-compose -f docker-compose.prod.yml run --rm admin-service alembic upgrade head

# 6. Start services
docker-compose -f docker-compose.prod.yml up -d

# 7. Verify health
curl http://localhost:3000/health
```
