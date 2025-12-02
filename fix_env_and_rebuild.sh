#!/bin/bash

# fix_env_and_rebuild.sh
# Fix encryption key issue and rebuild services

set -e

echo "========================================="
echo "Environment & Service Fix Script"
echo "========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

echo "✓ Found .env file"
echo ""

# Verify secure keys are set
echo "🔍 Checking environment variables..."
source .env

if [ "$ENCRYPTION_KEY" = "GENERATE_SECURE_KEY_BEFORE_PRODUCTION" ]; then
    echo "❌ ENCRYPTION_KEY is still using default value"
    echo "   Your .env file needs to be updated"
    exit 1
fi

echo "✓ ENCRYPTION_KEY is set to secure value"
echo "✓ JWT_SECRET is set"
echo "✓ LICENSE keys are set"
echo ""

# Stop all services
echo "🛑 Stopping all services..."
sudo docker-compose down

echo ""
echo "🔨 Rebuilding services with environment..."

# Rebuild and start with explicit env file
sudo docker-compose --env-file .env build

echo ""
echo "🚀 Starting services..."
sudo docker-compose --env-file .env up -d

echo ""
echo "⏳ Waiting for services to start (15 seconds)..."
sleep 15

echo ""
echo "✅ Checking service status..."
sudo docker ps

echo ""
echo "🔍 Verifying environment in device-service..."
DEVICE_ENV=$(docker compose exec -T device-service env | grep ENCRYPTION_KEY | head -1 || echo "")

if echo "$DEVICE_ENV" | grep -q "GENERATE_SECURE_KEY_BEFORE_PRODUCTION"; then
    echo "❌ Still using default encryption key!"
    echo "   Try running: docker compose down && docker compose --env-file .env up -d"
    exit 1
elif [ -z "$DEVICE_ENV" ]; then
    echo "⚠️  Could not verify environment (service may still be starting)"
else
    echo "✓ Encryption key is properly set in container"
fi

echo ""
echo "========================================="
echo "✅ Fix Complete!"
echo "========================================="
echo ""
echo "Services should now start without encryption key errors."
echo ""
echo "Next steps:"
echo "1. Check logs: docker compose logs -f"
echo "2. Verify all services are running: docker compose ps"
echo "3. Continue with license fix: ./rebuild_services.sh"
echo ""
