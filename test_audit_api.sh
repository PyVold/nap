#!/bin/bash
#
# Test script to verify the Audit Results API endpoints are working
#

echo "================================"
echo "Audit Results API Test Script"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: API Gateway health
echo "Test 1: Checking API Gateway health..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/health)
if [ "$response" -eq 200 ]; then
    echo -e "${GREEN}✓ API Gateway is healthy${NC}"
else
    echo -e "${RED}✗ API Gateway returned $response${NC}"
fi
echo ""

# Test 2: Rule Service health (handles /audit endpoints)
echo "Test 2: Checking Rule Service health..."
response=$(curl -s http://localhost:3002/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Rule Service is healthy${NC}"
    echo "   Response: $response"
else
    echo -e "${RED}✗ Rule Service is not accessible${NC}"
fi
echo ""

# Test 3: Device Service health
echo "Test 3: Checking Device Service health..."
response=$(curl -s http://localhost:3001/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Device Service is healthy${NC}"
    echo "   Response: $response"
else
    echo -e "${RED}✗ Device Service is not accessible${NC}"
fi
echo ""

# Test 4: Get audit results via API Gateway
echo "Test 4: Fetching audit results via API Gateway..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:3000/audit/results)
http_code=$(echo "$response" | grep HTTP_CODE | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Successfully fetched audit results${NC}"
    echo "   HTTP Status: $http_code"
    echo "   Response Body: $body"
    echo "   Body Length: ${#body} bytes"
    
    # Count results if it's a JSON array
    if command -v jq &> /dev/null; then
        count=$(echo "$body" | jq '. | length' 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "   Number of results: $count"
        fi
    fi
else
    echo -e "${RED}✗ Failed to fetch audit results${NC}"
    echo "   HTTP Status: $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 5: Get devices via API Gateway
echo "Test 5: Fetching devices via API Gateway..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:3000/devices/)
http_code=$(echo "$response" | grep HTTP_CODE | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Successfully fetched devices${NC}"
    echo "   HTTP Status: $http_code"
    echo "   Body Length: ${#body} bytes"
    
    # Count devices if it's a JSON array
    if command -v jq &> /dev/null; then
        count=$(echo "$body" | jq '. | length' 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "   Number of devices: $count"
        fi
    fi
else
    echo -e "${RED}✗ Failed to fetch devices${NC}"
    echo "   HTTP Status: $http_code"
fi
echo ""

# Test 6: Get rules via API Gateway
echo "Test 6: Fetching rules via API Gateway..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:3000/rules/)
http_code=$(echo "$response" | grep HTTP_CODE | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Successfully fetched rules${NC}"
    echo "   HTTP Status: $http_code"
    echo "   Body Length: ${#body} bytes"
    
    # Count rules if it's a JSON array
    if command -v jq &> /dev/null; then
        count=$(echo "$body" | jq '. | length' 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "   Number of rules: $count"
        fi
    fi
else
    echo -e "${RED}✗ Failed to fetch rules${NC}"
    echo "   HTTP Status: $http_code"
fi
echo ""

# Test 7: Test audit results directly from Rule Service
echo "Test 7: Fetching audit results directly from Rule Service..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:3002/audit/results 2>/dev/null)
if [ $? -eq 0 ]; then
    http_code=$(echo "$response" | grep HTTP_CODE | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✓ Successfully fetched audit results from Rule Service${NC}"
        echo "   HTTP Status: $http_code"
        echo "   Response Body: $body"
    else
        echo -e "${RED}✗ Rule Service returned $http_code${NC}"
        echo "   Response: $body"
    fi
else
    echo -e "${RED}✗ Cannot connect to Rule Service${NC}"
fi
echo ""

# Test 8: Frontend accessibility
echo "Test 8: Checking Frontend accessibility..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/)
if [ "$response" -eq 200 ]; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
    echo -e "${RED}✗ Frontend returned $response${NC}"
fi
echo ""

# Test 9: Frontend proxy for /audit/results
echo "Test 9: Testing frontend proxy for /audit/results..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/audit/results)
if [ "$response" -eq 200 ]; then
    echo -e "${GREEN}✓ Frontend proxy for /audit/results is working${NC}"
elif [ "$response" -eq 404 ]; then
    echo -e "${YELLOW}! Frontend returned 404${NC}"
    echo "   This might be expected - nginx routes /audit/results to API gateway"
else
    echo -e "${RED}✗ Frontend proxy returned $response${NC}"
fi
echo ""

echo "================================"
echo "Test Summary"
echo "================================"
echo ""
echo "All three endpoints required by the Audit Results page:"
echo "  1. GET /audit/results"
echo "  2. GET /devices/"
echo "  3. GET /rules/"
echo ""
echo -e "${YELLOW}Note:${NC} If all tests pass but the frontend page doesn't load,"
echo "check the browser console for JavaScript errors."
echo ""
echo "To check container logs:"
echo "  docker logs rule-service --tail 50"
echo "  docker logs device-service --tail 50"
echo "  docker logs api-gateway --tail 50"
echo "  docker logs frontend --tail 50"
echo ""
echo "To test with authentication (if required):"
echo "  curl -H 'Authorization: Bearer YOUR_TOKEN' http://localhost:3000/audit/results"
echo ""
