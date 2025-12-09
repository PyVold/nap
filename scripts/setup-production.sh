#!/bin/bash
# ============================================================================
# Production Setup Script for Network Audit Platform
# ============================================================================
# This script prepares the environment for production deployment.
# Run with: ./scripts/setup-production.sh
# ============================================================================

set -e

echo "========================================"
echo "Network Audit Platform - Production Setup"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}Error: Do not run this script as root${NC}"
   exit 1
fi

# Create directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p secrets monitoring/grafana/dashboards monitoring/grafana/datasources
echo -e "${GREEN}Done${NC}"

# Generate secrets if they don't exist
echo ""
echo -e "${YELLOW}Generating secrets...${NC}"

generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

if [ ! -f "secrets/db_password.txt" ]; then
    generate_secret > secrets/db_password.txt
    echo "  - Generated database password"
else
    echo "  - Database password already exists"
fi

# Create .env.prod if it doesn't exist
if [ ! -f ".env.prod" ]; then
    echo ""
    echo -e "${YELLOW}Creating .env.prod file...${NC}"

    DB_PASSWORD=$(cat secrets/db_password.txt)
    JWT_SECRET=$(generate_secret)
    ENCRYPTION_KEY=$(generate_secret)
    REDIS_PASSWORD=$(generate_secret)
    GRAFANA_PASSWORD=$(generate_secret)

    cat > .env.prod << EOF
# ============================================================================
# Production Environment Configuration
# Generated on $(date)
# ============================================================================

# Database Configuration
POSTGRES_DB=nap_db
POSTGRES_USER=nap_user
POSTGRES_PASSWORD=${DB_PASSWORD}

# Redis Configuration
REDIS_PASSWORD=${REDIS_PASSWORD}

# JWT Configuration
JWT_SECRET_KEY=${JWT_SECRET}

# Encryption Key for device credentials
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Application Settings
APP_VERSION=1.0.0
LOG_LEVEL=info

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Monitoring
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}

# API URL (update with your domain)
API_URL=http://localhost:3000
EOF

    echo -e "${GREEN}Created .env.prod with generated secrets${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Update API_URL in .env.prod with your actual domain${NC}"
else
    echo -e "${YELLOW}.env.prod already exists - skipping${NC}"
fi

# Set proper permissions on secrets
echo ""
echo -e "${YELLOW}Setting secure permissions on secrets...${NC}"
chmod 600 secrets/*.txt 2>/dev/null || true
chmod 600 .env.prod 2>/dev/null || true
echo -e "${GREEN}Done${NC}"

# Create Grafana datasource config
echo ""
echo -e "${YELLOW}Creating monitoring configurations...${NC}"

cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

cat > monitoring/loki-config.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-05-15
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 168h

storage_config:
  boltdb:
    directory: /loki/index
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
EOF

echo -e "${GREEN}Done${NC}"

# Verify Docker is available
echo ""
echo -e "${YELLOW}Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}Docker found: ${DOCKER_VERSION}${NC}"
else
    echo -e "${RED}Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo -e "${GREEN}Docker Compose found: ${COMPOSE_VERSION}${NC}"
else
    echo -e "${YELLOW}docker-compose not found. Using 'docker compose' instead.${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}Production setup complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Review and update .env.prod with your settings"
echo "  2. Update API_URL with your actual domain"
echo "  3. Set up SSL certificates in ./nginx/ssl/"
echo "  4. Start services: docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "Monitoring dashboards:"
echo "  - Grafana: http://localhost:3030 (admin / see .env.prod)"
echo "  - Prometheus: http://localhost:9090"
echo ""
echo -e "${YELLOW}Remember to change default passwords before going live!${NC}"
