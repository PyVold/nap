#!/bin/bash
# Load base images from tar files for offline deployment

set -e

cd "$(dirname "$0")"

INPUT_DIR="./exported-images"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Directory '$INPUT_DIR' not found!"
    echo "Make sure you've copied the exported images to this location."
    exit 1
fi

echo "============================================"
echo "Loading NAP Base Images"
echo "============================================"
echo ""

# Load Python base image
if [ -f "$INPUT_DIR/nap-python-base.tar.gz" ]; then
    echo "Loading nap-python-base:latest..."
    gunzip -c "$INPUT_DIR/nap-python-base.tar.gz" | docker load
    echo "Done"
fi

# Load Frontend base image
if [ -f "$INPUT_DIR/nap-frontend-base.tar.gz" ]; then
    echo "Loading nap-frontend-base:latest..."
    gunzip -c "$INPUT_DIR/nap-frontend-base.tar.gz" | docker load
    echo "Done"
fi

# Load nginx
if [ -f "$INPUT_DIR/nginx-alpine.tar.gz" ]; then
    echo "Loading nginx:alpine..."
    gunzip -c "$INPUT_DIR/nginx-alpine.tar.gz" | docker load
    echo "Done"
fi

# Load PostgreSQL
if [ -f "$INPUT_DIR/postgres-15.tar.gz" ]; then
    echo "Loading postgres:15..."
    gunzip -c "$INPUT_DIR/postgres-15.tar.gz" | docker load
    echo "Done"
fi

# Load Prometheus
if [ -f "$INPUT_DIR/prometheus.tar.gz" ]; then
    echo "Loading prom/prometheus:latest..."
    gunzip -c "$INPUT_DIR/prometheus.tar.gz" | docker load
    echo "Done"
fi

# Load Grafana
if [ -f "$INPUT_DIR/grafana.tar.gz" ]; then
    echo "Loading grafana/grafana:latest..."
    gunzip -c "$INPUT_DIR/grafana.tar.gz" | docker load
    echo "Done"
fi

# Load Redis
if [ -f "$INPUT_DIR/redis-7-alpine.tar.gz" ]; then
    echo "Loading redis:7-alpine..."
    gunzip -c "$INPUT_DIR/redis-7-alpine.tar.gz" | docker load
    echo "Done"
fi

echo ""
echo "============================================"
echo "Load Complete!"
echo "============================================"
echo ""
echo "Loaded images:"
docker images | grep -E "nap-python-base|nap-frontend-base|nginx.*alpine|postgres|prometheus|grafana|redis"
echo ""
echo "You can now run: docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d"
