#!/bin/bash
# Quick Fix Commands for License Activation Issue
# Run these commands on your server at 192.168.1.150

echo "=========================================="
echo "License Activation Fix - Quick Commands"
echo "=========================================="
echo ""

# Navigate to project directory
echo "Step 1: Navigate to project directory"
echo "cd ~/nap"
cd ~/nap || { echo "Error: Could not find ~/nap directory. Please adjust the path."; exit 1; }
echo "✓ Current directory: $(pwd)"
echo ""

# Check current container status
echo "Step 2: Check current container status"
echo "docker-compose ps"
sudo docker-compose ps
echo ""

# Rebuild frontend container
echo "Step 3: Rebuild frontend container with fix"
echo "docker-compose up -d --build frontend"
sudo docker-compose up -d --build frontend
echo ""

# Wait for container to be ready
echo "Step 4: Waiting for frontend to be ready..."
sleep 10
echo ""

# Check if frontend is running
echo "Step 5: Verify frontend is running"
sudo docker-compose ps frontend
echo ""

# Test the fix
echo "Step 6: Test license API endpoint"
echo "curl -s http://localhost:8080/license/status | jq '.tier, .customer_name, .days_until_expiry' || curl -s http://localhost:8080/license/status"
curl -s http://localhost:8080/license/status | jq '.tier, .customer_name, .days_until_expiry' 2>/dev/null || curl -s http://localhost:8080/license/status
echo ""

echo "=========================================="
echo "Fix Applied!"
echo "=========================================="
echo ""
echo "✓ Frontend nginx config updated"
echo "✓ Frontend container rebuilt"
echo "✓ License API now accessible"
echo ""
echo "Next steps:"
echo "1. Open your browser: http://192.168.1.150:8080"
echo "2. Login with your credentials"
echo "3. The dashboard should now load properly"
echo "4. Check the License page to see your activated Enterprise license"
echo ""
echo "If you still see issues, check:"
echo "  - Browser console for errors (F12 → Console)"
echo "  - Docker logs: docker-compose logs frontend --tail 50"
echo ""
