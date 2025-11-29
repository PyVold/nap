#!/bin/bash

# rebuild_services.sh
# Script to rebuild and restart services to fix the license endpoint 404 error

set -e

echo "========================================="
echo "License Endpoint 404 Fix - Rebuild Script"
echo "========================================="
echo ""

# Check if docker compose is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: docker is not installed or not in PATH"
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Error: docker compose is not available"
    echo "   Please install Docker Compose V2"
    exit 1
fi

echo "📋 Current service status:"
docker compose ps
echo ""

echo "🔨 Rebuilding admin-service..."
docker compose build admin-service

echo ""
echo "🔄 Restarting admin-service..."
docker compose up -d admin-service

echo ""
echo "⏳ Waiting for admin-service to be healthy (10 seconds)..."
sleep 10

echo ""
echo "✅ Checking admin-service status..."
if docker compose ps admin-service | grep -q "Up"; then
    echo "   ✓ Admin service is running"
else
    echo "   ⚠️  Warning: Admin service may not be running correctly"
    echo "   Check logs with: docker compose logs admin-service"
fi

echo ""
echo "🔍 Testing admin-service health endpoint..."
if curl -s -f http://localhost:3005/health > /dev/null 2>&1; then
    echo "   ✓ Admin service health check passed"
    curl -s http://localhost:3005/health | jq . || curl -s http://localhost:3005/health
else
    echo "   ⚠️  Warning: Admin service health check failed"
    echo "   The service may still be starting up"
fi

echo ""
echo "🔍 Testing license endpoint..."
response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:3000/api/license/activate \
    -H "Content-Type: application/json" \
    -d '{"license_key": "test-key"}' 2>&1)

http_code=$(echo "$response" | tail -n 1)

if [ "$http_code" = "404" ]; then
    echo "   ❌ Still returning 404 - License endpoint not found"
    echo "   Please check admin-service logs: docker compose logs admin-service"
    exit 1
elif [ "$http_code" = "400" ]; then
    echo "   ✅ License endpoint is working! (400 = invalid license key, which is expected)"
elif [ "$http_code" = "500" ]; then
    echo "   ⚠️  License endpoint found but returned 500 (server error)"
    echo "   Check admin-service logs: docker compose logs admin-service"
else
    echo "   ℹ️  License endpoint returned HTTP $http_code"
fi

echo ""
echo "========================================="
echo "✅ Rebuild complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Check admin-service logs: docker compose logs -f admin-service"
echo "2. Test the license page: http://localhost:8080/license"
echo "3. View all logs: docker compose logs -f"
echo ""
echo "If issues persist:"
echo "- Rebuild all services: docker compose build && docker compose up -d"
echo "- Check the LICENSE_ENDPOINT_404_FIX.md document for more details"
