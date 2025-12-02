#!/bin/bash
# Export base images as tar files for offline deployment
# Run this after building base images

set -e

echo "============================================"
echo "Exporting Base Images for Offline Transfer"
echo "============================================"
echo ""

# Create export directory
mkdir -p docker/base-images-export
cd docker/base-images-export

echo "📦 Exporting nap-python-base:latest..."
docker save nap-python-base:latest -o nap-python-base.tar
echo "✅ Exported nap-python-base.tar ($(du -h nap-python-base.tar | cut -f1))"

echo "📦 Exporting nap-frontend-base:latest..."
docker save nap-frontend-base:latest -o nap-frontend-base.tar
echo "✅ Exported nap-frontend-base.tar ($(du -h nap-frontend-base.tar | cut -f1))"

echo "📦 Exporting nginx:alpine..."
docker save nginx:alpine -o nginx-alpine.tar
echo "✅ Exported nginx-alpine.tar ($(du -h nginx-alpine.tar | cut -f1))"

# Also export postgres if needed
echo "📦 Exporting postgres:15..."
docker pull postgres:15
docker save postgres:15 -o postgres-15.tar
echo "✅ Exported postgres-15.tar ($(du -h postgres-15.tar | cut -f1))"

echo ""
echo "============================================"
echo "Export Complete!"
echo "============================================"
echo "Total size:"
du -sh .
echo ""
echo "Files exported to: docker/base-images-export/"
ls -lh *.tar
echo ""
echo "Next steps:"
echo "1. Copy these tar files to your offline system"
echo "2. Run ./docker/load-base-images.sh on the offline system"
echo ""
echo "You can compress for transfer:"
echo "  tar czf nap-base-images.tar.gz *.tar"
