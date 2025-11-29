#!/bin/bash
# Quick License Activation Script
# This will activate your license directly in the PostgreSQL database

echo "=================================="
echo "License Activation Script"
echo "=================================="

# Your license key
LICENSE_KEY="gAAAAABpKnlkEKob2-VPArRRKwAQbhcFsrLkWY_rmwfQQKUc9yPzdJvy45JOEWZby3v1-xLSQtmxsuq7A6VkiZXOzS0k7-nBwABi42gaO29R_Qcddj-E2pUrtpYbvrDRcJ92DRu8W79Ro01-uNHAF7wNmTTX2SgPzLV7QWSX6vSRIIctYqZ-HgSED66m_Ui7sJvtCcbT-RypT9kCqwXbu1H1K_C0pOGW_WWHpd3meIeHA7y4EtjH08AiT1ZHMMW-jU-KdYCVAYIb-79Sa_A8MBeriRz4NhxOHTFo-aMZ0kKygO5DzGr0CfhVnArNDeIy8cjbN2HEYLv5wuacKk0Xf-e7_yuFG6_ieiRlFq7umaElCWguZp0gqNtmgNRcqR_J30bHU0F0cB7pPZogli2P-wlIb6Q3z3MndDWeEJbi2JNSpfVjhDUTmxr_BMV6hfA_yGWredexJbVlQfejAI1Zrbi02c0csxHdQeHmGu9ziqWTEfqsSB1MpLxefwOZEHyp1hzInPPxUJWtek-aYtmuRoWQuoVo4VJBrgVUrBmZr8ZReOw-JpOHxGcdbj6sV2wbV-ntsdr6qB-lWigepzm-uMWyZW4D0Njb4499gdb28eeWIRO5kTlXEZE="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "   Make sure you're in the NAP directory"
    exit 1
fi

# Load environment variables
source .env

# Check if keys are set
if [ -z "$LICENSE_ENCRYPTION_KEY" ] || [ -z "$LICENSE_SECRET_SALT" ]; then
    echo "❌ Error: LICENSE_ENCRYPTION_KEY or LICENSE_SECRET_SALT not set in .env"
    exit 1
fi

echo "✓ Environment loaded"
echo "✓ License keys found"
echo ""

# Method 1: Try via API (if services are running)
echo "Attempting activation via API..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d "{\"license_key\": \"$LICENSE_KEY\"}" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ License activated successfully via API!"
    echo ""
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    exit 0
elif [ "$HTTP_CODE" = "000" ] || [ -z "$HTTP_CODE" ]; then
    echo "⚠ API not responding, trying direct database activation..."
else
    echo "⚠ API returned error (HTTP $HTTP_CODE), trying direct database activation..."
fi

# Method 2: Direct database activation
echo ""
echo "Activating license directly in database..."

# Install required packages if not present
pip3 show sqlalchemy >/dev/null 2>&1 || {
    echo "Installing sqlalchemy..."
    pip3 install sqlalchemy psycopg2-binary >/dev/null 2>&1
}

# Run Python activation script
python3 activate_license_direct.py "$LICENSE_KEY"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Your license is now active."
    echo ""
    echo "Next steps:"
    echo "  1. Restart your services: docker-compose restart"
    echo "  2. Access your platform"
    echo "  3. You should no longer see the 'expired or invalid' message"
else
    echo ""
    echo "❌ Activation failed. Please check the error messages above."
    exit 1
fi
