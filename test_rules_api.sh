#!/bin/bash
#
# Test script to verify the Rules API is working
#

echo "================================"
echo "Rules API Test Script"
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

# Test 2: Rule Service health
echo "Test 2: Checking Rule Service health..."
response=$(curl -s http://localhost:3002/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Rule Service is healthy${NC}"
    echo "   Response: $response"
else
    echo -e "${RED}✗ Rule Service is not accessible${NC}"
fi
echo ""

# Test 3: Get all rules via API Gateway
echo "Test 3: Fetching rules via API Gateway..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:3000/rules/)
http_code=$(echo "$response" | grep HTTP_CODE | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Successfully fetched rules${NC}"
    echo "   HTTP Status: $http_code"
    echo "   Response Body: $body"
    echo "   Body Length: ${#body} bytes"
else
    echo -e "${RED}✗ Failed to fetch rules${NC}"
    echo "   HTTP Status: $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 4: Get rules directly from Rule Service
echo "Test 4: Fetching rules directly from Rule Service..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:3002/rules/ 2>/dev/null)
if [ $? -eq 0 ]; then
    http_code=$(echo "$response" | grep HTTP_CODE | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✓ Successfully fetched rules from Rule Service${NC}"
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

# Test 5: Frontend accessibility
echo "Test 5: Checking Frontend accessibility..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/)
if [ "$response" -eq 200 ]; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
    echo -e "${RED}✗ Frontend returned $response${NC}"
fi
echo ""

# Test 6: Frontend rules proxy
echo "Test 6: Testing frontend proxy for /rules/..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:8080/rules/)
http_code=$(echo "$response" | grep HTTP_CODE | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Frontend proxy is working${NC}"
    echo "   HTTP Status: $http_code"
    echo "   Response Body: $body"
    echo "   Body Length: ${#body} bytes"
else
    echo -e "${YELLOW}! Frontend proxy returned $http_code${NC}"
    echo "   This might be expected if nginx routes /rules/ to the React app"
    echo "   Response: $body"
fi
echo ""

echo "================================"
echo "Test Summary"
echo "================================"
echo ""
echo -e "${YELLOW}Note:${NC} If all tests pass but the frontend page doesn't load,"
echo "check the browser console for JavaScript errors."
echo ""
echo "To check container logs:"
echo "  docker logs rule-service"
echo "  docker logs api-gateway"
echo "  docker logs frontend"
echo ""
