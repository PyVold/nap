#!/bin/bash
# Export all base images as tar files for offline deployment

set -e

cd "$(dirname "$0")"

OUTPUT_DIR="./exported-images"
mkdir -p "$OUTPUT_DIR"

echo "============================================"
echo "Exporting NAP Base Images"
echo "============================================"
echo ""

# Export Python base image
echo "Exporting nap-python-base:latest..."
docker save nap-python-base:latest | gzip > "$OUTPUT_DIR/nap-python-base.tar.gz"
echo "Done"

# Export Frontend base image
echo "Exporting nap-frontend-base:latest..."
docker save nap-frontend-base:latest | gzip > "$OUTPUT_DIR/nap-frontend-base.tar.gz"
echo "Done"

# Export nginx
echo "Exporting nginx:alpine..."
docker save nginx:alpine | gzip > "$OUTPUT_DIR/nginx-alpine.tar.gz"
echo "Done"

# Export PostgreSQL
echo "Exporting postgres:15..."
docker save postgres:15 | gzip > "$OUTPUT_DIR/postgres-15.tar.gz"
echo "Done"

# Export Prometheus
echo "Exporting prom/prometheus:latest..."
docker save prom/prometheus:latest | gzip > "$OUTPUT_DIR/prometheus.tar.gz"
echo "Done"

# Export Grafana
echo "Exporting grafana/grafana:latest..."
docker save grafana/grafana:latest | gzip > "$OUTPUT_DIR/grafana.tar.gz"
echo "Done"

# Export Redis
echo "Exporting redis:7-alpine..."
docker save redis:7-alpine | gzip > "$OUTPUT_DIR/redis-7-alpine.tar.gz"
echo "Done"

echo ""
echo "============================================"
echo "Export Complete!"
echo "============================================"
echo ""
echo "Exported files:"
ls -lh "$OUTPUT_DIR"
echo ""
echo "Copy the '$OUTPUT_DIR' directory to your offline system"
echo "Then run ./load-base-images.sh to load them"
