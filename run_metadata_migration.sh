#!/bin/bash

# Script to run the device metadata migration
# This adds the metadata JSONB column to the devices table

echo "Running device metadata migration..."

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container"
    python /app/migrations/add_device_metadata.py
else
    echo "Running on host - will execute inside admin-service container"
    docker-compose exec admin-service python /app/migrations/add_device_metadata.py
fi

echo "Migration complete!"
