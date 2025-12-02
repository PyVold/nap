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
echo "📦 Building Python base image..."
docker build \
  -f docker/base-images/Dockerfile.python-base \
  -t nap-python-base:latest \
  --progress=plain \
  .

echo "✅ Python base image built successfully"
echo ""

# Build Frontend base image with node_modules
echo "📦 Building Frontend base image..."
docker build \
  -f docker/base-images/Dockerfile.frontend-base \
  -t nap-frontend-base:latest \
  --progress=plain \
  .

echo "✅ Frontend base image built successfully"
echo ""

# Also pull nginx:alpine for frontend production stage
echo "📦 Pulling nginx:alpine..."
docker pull nginx:alpine

echo "✅ All base images ready"
echo ""
echo "============================================"
echo "Base Images Summary:"
echo "============================================"
docker images | grep -E "nap-python-base|nap-frontend-base|nginx.*alpine"
echo ""
echo "Next steps:"
echo "1. Run ./docker/export-base-images.sh to export images as tar files"
echo "2. Copy tar files to offline system"
echo "3. Run ./docker/load-base-images.sh on offline system"
