#!/bin/bash
# Load base images on offline system
# Run this on the offline/air-gapped system

set -e

echo "============================================"
echo "Loading NAP Base Images (Offline System)"
echo "============================================"
echo ""

# Check if we're in the right directory
if [ ! -d "docker/base-images-export" ]; then
    echo "❌ Error: docker/base-images-export directory not found"
    echo "Please ensure you copied the exported tar files to docker/base-images-export/"
    exit 1
fi

cd docker/base-images-export

echo "📦 Loading nap-python-base.tar..."
docker load -i nap-python-base.tar
echo "✅ Loaded nap-python-base:latest"

echo "📦 Loading nap-frontend-base.tar..."
docker load -i nap-frontend-base.tar
echo "✅ Loaded nap-frontend-base:latest"

echo "📦 Loading nginx-alpine.tar..."
docker load -i nginx-alpine.tar
echo "✅ Loaded nginx:alpine"

echo "📦 Loading postgres-15.tar..."
docker load -i postgres-15.tar
echo "✅ Loaded postgres:15"

echo ""
echo "============================================"
echo "All Base Images Loaded Successfully!"
echo "============================================"
echo ""
docker images | grep -E "nap-python-base|nap-frontend-base|nginx.*alpine|postgres"
echo ""
echo "Next steps:"
echo "1. Build application images: docker compose -f docker-compose.offline.yml build"
echo "2. Start services: docker compose -f docker-compose.offline.yml up -d"
