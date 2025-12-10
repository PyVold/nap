#!/bin/bash
# Build base images with all dependencies pre-installed
# Run this script on a system with internet access
# Then export the images for offline deployment

set -e

echo "============================================"
echo "Building NAP Base Images for Offline Deploy"
echo "============================================"
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Build Python base image with ALL dependencies
echo "[1/7] Building Python base image..."
docker build \
  -f docker/base-images/Dockerfile.python-base \
  -t nap-python-base:latest \
  --progress=plain \
  .

echo "Python base image built successfully"
echo ""

# Build Frontend base image with node_modules
echo "[2/7] Building Frontend base image..."
docker build \
  -f docker/base-images/Dockerfile.frontend-base \
  -t nap-frontend-base:latest \
  --progress=plain \
  .

echo "Frontend base image built successfully"
echo ""

# Pull nginx:alpine for frontend production stage
echo "[3/7] Pulling nginx:alpine..."
docker pull nginx:alpine

echo "nginx:alpine pulled successfully"
echo ""

# Pull PostgreSQL for database
echo "[4/7] Pulling postgres:15..."
docker pull postgres:15

echo "postgres:15 pulled successfully"
echo ""

# Pull Prometheus for monitoring
echo "[5/7] Pulling prom/prometheus:latest..."
docker pull prom/prometheus:latest

echo "prom/prometheus:latest pulled successfully"
echo ""

# Pull Grafana for dashboards
echo "[6/7] Pulling grafana/grafana:latest..."
docker pull grafana/grafana:latest

echo "grafana/grafana:latest pulled successfully"
echo ""

# Pull Redis for caching (optional)
echo "[7/7] Pulling redis:7-alpine..."
docker pull redis:7-alpine

echo "redis:7-alpine pulled successfully"
echo ""

echo "============================================"
echo "All base images ready!"
echo "============================================"
echo ""
echo "Base Images Summary:"
echo "--------------------------------------------"
docker images | grep -E "nap-python-base|nap-frontend-base|nginx.*alpine|postgres|prometheus|grafana|redis"
echo ""
echo "Next steps:"
echo "1. Run ./docker/export-base-images.sh to export images as tar files"
echo "2. Copy tar files to offline system"
echo "3. Run ./docker/load-base-images.sh on offline system"
