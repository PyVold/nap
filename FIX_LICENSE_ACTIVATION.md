# Fix Applied: License Activation Issue

## What Was Wrong

The API Gateway wasn't properly routing requests with the `/api` prefix to the license service.

**Error**: `"No service found for path: /api/license/activate"`

## What I Fixed

Updated `/services/api-gateway/app/main.py` to strip the `/api/` prefix from incoming requests before routing them to the appropriate service.

## How to Apply the Fix

Run these commands on your server (`npm@npm-pro:~/nap$`):

### Step 1: Rebuild the API Gateway Container

```bash
cd ~/nap

# Rebuild only the API gateway (faster than rebuilding everything)
sudo docker-compose build api-gateway
```

### Step 2: Restart the Services

```bash
# Restart all services to pick up the changes
sudo docker-compose restart

# OR restart just the API gateway
sudo docker-compose restart api-gateway
```

### Step 3: Wait for Services to Start

```bash
# Check that all services are running
sudo docker-compose ps

# Wait until all services show "Up" status
```

### Step 4: Activate Your License

Now try activating your license again:

```bash
curl -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "gAAAAABpKnlkEKob2-VPArRRKwAQbhcFsrLkWY_rmwfQQKUc9yPzdJvy45JOEWZby3v1-xLSQtmxsuq7A6VkiZXOzS0k7-nBwABi42gaO29R_Qcddj-E2pUrtpYbvrDRcJ92DRu8W79Ro01-uNHAF7wNmTTX2SgPzLV7QWSX6vSRIIctYqZ-HgSED66m_Ui7sJvtCcbT-RypT9kCqwXbu1H1K_C0pOGW_WWHpd3meIeHA7y4EtjH08AiT1ZHMMW-jU-KdYCVAYIb-79Sa_A8MBeriRz4NhxOHTFo-aMZ0kKygO5DzGr0CfhVnArNDeIy8cjbN2HEYLv5wuacKk0Xf-e7_yuFG6_ieiRlFq7umaElCWguZp0gqNtmgNRcqR_J30bHU0F0cB7pPZogli2P-wlIb6Q3z3MndDWeEJbi2JNSpfVjhDUTmxr_BMV6hfA_yGWredexJbVlQfejAI1Zrbi02c0csxHdQeHmGu9ziqWTEfqsSB1MpLxefwOZEHyp1hzInPPxUJWtek-aYtmuRoWQuoVo4VJBrgVUrBmZr8ZReOw-JpOHxGcdbj6sV2wbV-ntsdr6qB-lWigepzm-uMWyZW4D0Njb4499gdb28eeWIRO5kTlXEZE="}'
```

**Expected Response**:
```json
{
  "success": true,
  "message": "License activated successfully",
  "license_status": {
    "valid": true,
    "tier": "enterprise",
    "tier_display": "Enterprise",
    "expires_at": "2026-02-27T...",
    "days_until_expiry": 90,
    "is_active": true,
    "quotas": {
      "devices": {
        "current": 0,
        "max": 50,
        "percentage": 0.0,
        "within_quota": true
      },
      "users": {
        "current": 3,
        "max": 10,
        "percentage": 30.0,
        "within_quota": true
      }
    },
    "customer_name": "BICS",
    ...
  }
}
```

### Step 5: Verify in Web UI

1. Open your browser and go to your NAP platform
2. Refresh the page (Ctrl+F5 or Cmd+Shift+R)
3. The "expired or invalid license" error should be **GONE**
4. You should now have full access to all features

### Step 6: Check License Status

```bash
curl http://localhost:3000/api/license/status
```

This should show your active BICS Enterprise license.

## Alternative: Activate via Web UI

After rebuilding and restarting:

1. Go to your NAP platform in browser
2. Navigate to `/license` page
3. Paste your license key:
   ```
   gAAAAABpKnlkEKob2-VPArRRKwAQbhcFsrLkWY_rmwfQQKUc9yPzdJvy45JOEWZby3v1-xLSQtmxsuq7A6VkiZXOzS0k7-nBwABi42gaO29R_Qcddj-E2pUrtpYbvrDRcJ92DRu8W79Ro01-uNHAF7wNmTTX2SgPzLV7QWSX6vSRIIctYqZ-HgSED66m_Ui7sJvtCcbT-RypT9kCqwXbu1H1K_C0pOGW_WWHpd3meIeHA7y4EtjH08AiT1ZHMMW-jU-KdYCVAYIb-79Sa_A8MBeriRz4NhxOHTFo-aMZ0kKygO5DzGr0CfhVnArNDeIy8cjbN2HEYLv5wuacKk0Xf-e7_yuFG6_ieiRlFq7umaElCWguZp0gqNtmgNRcqR_J30bHU0F0cB7pPZogli2P-wlIb6Q3z3MndDWeEJbi2JNSpfVjhDUTmxr_BMV6hfA_yGWredexJbVlQfejAI1Zrbi02c0csxHdQeHmGu9ziqWTEfqsSB1MpLxefwOZEHyp1hzInPPxUJWtek-aYtmuRoWQuoVo4VJBrgVUrBmZr8ZReOw-JpOHxGcdbj6sV2wbV-ntsdr6qB-lWigepzm-uMWyZW4D0Njb4499gdb28eeWIRO5kTlXEZE=
   ```
4. Click "Activate"
5. Success! ✅

## Troubleshooting

### If rebuild fails
```bash
# Clean rebuild
sudo docker-compose down
sudo docker-compose build --no-cache api-gateway
sudo docker-compose up -d
```

### If services don't start
```bash
# Check logs
sudo docker-compose logs api-gateway
sudo docker-compose logs admin-service

# Check if database is ready
sudo docker-compose logs database | tail -20
```

### If activation still fails
Check that your `.env` file has the correct license keys:
```bash
cat .env | grep LICENSE
```

Should show:
```
LICENSE_ENCRYPTION_KEY="ZCh8vvIIZ0bNUsQb6uMbAzBRdM_wx7SeMzFN7BU-asY="
LICENSE_SECRET_SALT="89804dd358f60767a542891529e1d20eaf2f33900a30f73fd007024c2270a2ea"
```

## Summary

✅ **Fixed**: API Gateway now properly handles `/api/license/*` routes
✅ **Your License**: Ready to activate (BICS Enterprise, 90 days, 50 devices, 10 users)
✅ **Next Step**: Rebuild API gateway and activate via API or Web UI

After following these steps, your license will be active and you won't see the "expired or invalid" error anymore! 🎉
