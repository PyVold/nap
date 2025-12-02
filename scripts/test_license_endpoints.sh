#!/bin/bash

# test_license_endpoints.sh
# Script to test all license-related endpoints

set -e

echo "========================================="
echo "License Endpoint Test Suite"
echo "========================================="
echo ""

API_BASE_URL="${API_BASE_URL:-http://localhost:3000}"
ADMIN_SERVICE_URL="${ADMIN_SERVICE_URL:-http://localhost:3005}"

echo "🔧 Configuration:"
echo "   API Gateway: $API_BASE_URL"
echo "   Admin Service: $ADMIN_SERVICE_URL"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local url=$2
    local expected_code=$3
    local description=$4
    local data=$5
    
    echo -n "Testing: $description... "
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        test_passed=$((test_passed + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_code, got $http_code)"
        echo "   Response: $body"
        test_failed=$((test_failed + 1))
        return 1
    fi
}

echo "========================================="
echo "1. Health Checks"
echo "========================================="
echo ""

test_endpoint "GET" "$ADMIN_SERVICE_URL/health" "200" "Admin service health check"
test_endpoint "GET" "$API_BASE_URL/health" "200" "API gateway health check"

echo ""
echo "========================================="
echo "2. License Status (via API Gateway)"
echo "========================================="
echo ""

# License status should return 404 if no license is active
test_endpoint "GET" "$API_BASE_URL/api/license/status" "404" "License status (no active license)"

echo ""
echo "========================================="
echo "3. License Activation (via API Gateway)"
echo "========================================="
echo ""

# Test with invalid license key (should return 400, not 404)
test_endpoint "POST" "$API_BASE_URL/api/license/activate" "400" "Activate invalid license" \
    '{"license_key": "invalid-key"}'

echo ""
echo "========================================="
echo "4. License Tiers (via API Gateway)"
echo "========================================="
echo ""

test_endpoint "GET" "$API_BASE_URL/api/license/tiers" "200" "Get license tiers"

echo ""
echo "========================================="
echo "5. Direct Admin Service Tests"
echo "========================================="
echo ""

test_endpoint "POST" "$ADMIN_SERVICE_URL/license/activate" "400" "Direct: Activate invalid license" \
    '{"license_key": "invalid-key"}'

test_endpoint "GET" "$ADMIN_SERVICE_URL/license/tiers" "200" "Direct: Get license tiers"

echo ""
echo "========================================="
echo "Test Results"
echo "========================================="
echo ""
echo -e "${GREEN}Passed: $test_passed${NC}"
echo -e "${RED}Failed: $test_failed${NC}"
echo ""

if [ $test_failed -gt 0 ]; then
    echo "❌ Some tests failed. Check the output above for details."
    echo ""
    echo "Common issues:"
    echo "1. Services not running: docker compose ps"
    echo "2. Services not rebuilt: ./rebuild_services.sh"
    echo "3. Check logs: docker compose logs admin-service"
    exit 1
else
    echo "✅ All tests passed!"
    echo ""
    echo "The license endpoints are working correctly."
    echo "You can now:"
    echo "1. Access the license page: http://localhost:8080/license"
    echo "2. Activate a license through the UI"
    echo "3. View license status and usage"
fi

echo ""
