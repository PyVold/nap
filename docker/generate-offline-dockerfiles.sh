#!/bin/bash
# Generate Dockerfile.offline for all Python services
# These use the pre-built base image

set -e

SERVICES=(
    "device-service"
    "rule-service"
    "backup-service"
    "inventory-service"
    "analytics-service"
    "api-gateway"
)

for SERVICE in "${SERVICES[@]}"; do
    echo "Creating Dockerfile.offline for $SERVICE..."

    cat > "services/$SERVICE/Dockerfile.offline" <<'EOF'
# Offline-ready Dockerfile
# Uses pre-built base image with all dependencies installed
# No network access required during build

FROM nap-python-base:latest

WORKDIR /app

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/SERVICE_NAME/app /app

# Expose port (will be overridden by docker-compose)
EXPOSE 3000

# Run the service
CMD ["python", "main.py"]
EOF

    # Replace SERVICE_NAME placeholder
    sed -i "s/SERVICE_NAME/$SERVICE/g" "services/$SERVICE/Dockerfile.offline"

    echo "✅ Created services/$SERVICE/Dockerfile.offline"
done

echo ""
echo "All offline Dockerfiles created successfully!"
