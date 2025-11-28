# Remediation 502 Error Fix

## Problem
Getting a 502 Bad Gateway error when pressing "Apply Fix" button in the Audit Results page:
```
api-gateway_1  | 2025-11-28 13:32:01 - __main__ - ERROR - Error forwarding request to http://admin-service:3005/remediation/push:
api-gateway_1  | INFO:  172.18.0.10:35758 - "POST /remediation/push HTTP/1.1" 502 Bad Gateway
```

## Root Cause Analysis

The API Gateway is correctly routing the request to `admin-service:3005/remediation/push`, but the admin-service is either:
1. Not running
2. Running but the endpoint is not responding
3. Has a runtime error in the remediation endpoint

## Solution Steps

### Step 1: Check Service Status

```bash
# Check if admin-service is running
docker-compose ps admin-service

# Check admin-service logs for errors
docker-compose logs admin-service --tail=100

# Check for startup errors
docker-compose logs admin-service | grep -i error
```

### Step 2: Verify Service Health

```bash
# Test admin-service health endpoint directly
curl http://localhost:3000/admin/health

# Or if you have direct access to admin-service:
docker-compose exec admin-service curl http://localhost:3005/health
```

### Step 3: Test Remediation Endpoint Directly

```bash
# Test the remediation endpoint (requires auth token)
curl -X POST http://localhost:3000/remediation/push \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "device_ids": [1],
    "dry_run": true,
    "re_audit": false
  }'
```

### Step 4: Common Issues and Fixes

#### Issue 1: Admin Service Not Running

**Fix**: Restart the admin-service
```bash
docker-compose restart admin-service
docker-compose logs -f admin-service
```

#### Issue 2: Database Connection Error

**Symptoms**: Admin-service logs show database connection errors

**Fix**: Restart database and admin-service
```bash
docker-compose restart database
sleep 10
docker-compose restart admin-service
```

#### Issue 3: Import/Dependency Error

**Symptoms**: Admin-service logs show Python import errors

**Fix**: Rebuild the admin-service container
```bash
docker-compose stop admin-service
docker-compose build admin-service
docker-compose up -d admin-service
docker-compose logs -f admin-service
```

#### Issue 4: Missing Environment Variables

**Symptoms**: Admin-service starts but endpoints fail

**Fix**: Check environment variables in docker-compose.yml
```yaml
admin-service:
  environment:
    - DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
    - JWT_SECRET=${JWT_SECRET:-GENERATE_SECURE_KEY_BEFORE_PRODUCTION}
    - ENCRYPTION_KEY=${ENCRYPTION_KEY:-GENERATE_SECURE_KEY_BEFORE_PRODUCTION}
    - RULE_SERVICE_URL=http://rule-service:3002
    - DEVICE_SERVICE_URL=http://device-service:3001
```

### Step 5: Verify API Gateway Routing

The API Gateway configuration should include remediation in admin-service routes:

```python
# In /workspace/services/api-gateway/app/main.py
"admin-service": {
    "url": "http://admin-service:3005",
    "name": "Administration",
    "enabled": True,
    "routes": ["/admin", "/user-management", "/integrations", "/notifications", "/remediation"],
    "ui_routes": ["admin", "users", "integrations"]
},
```

✅ This is already correctly configured (line 65 in api-gateway/app/main.py)

### Step 6: Verify Remediation Route Registration

The remediation router should be included in admin-service main.py:

```python
# In /workspace/services/admin-service/app/main.py
from routes import (
    admin, user_management, integrations, notifications, remediation,
    workflows
)

# ...

app.include_router(remediation.router, tags=["Remediation"])
```

✅ This is already correctly configured (lines 14-16 and 179 in admin-service/app/main.py)

## Quick Fix Script

Create a script to restart and verify all services:

```bash
#!/bin/bash
# remediation_fix.sh

echo "=== Fixing Remediation 502 Error ==="

echo "Step 1: Restarting admin-service..."
docker-compose restart admin-service

echo "Step 2: Waiting for service to start..."
sleep 5

echo "Step 3: Checking admin-service health..."
curl -s http://localhost:3000/admin/health || echo "Admin service health check failed"

echo "Step 4: Checking admin-service logs..."
docker-compose logs --tail=20 admin-service

echo "Step 5: Testing API gateway connection..."
curl -s http://localhost:3000/health

echo ""
echo "=== Fix Complete ==="
echo "If the issue persists, run: docker-compose logs -f admin-service"
```

## Verification Steps

After applying the fix, verify the remediation endpoint works:

### 1. Log in to get authentication token
```bash
curl -X POST http://localhost:3000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin"
  }' | jq -r '.access_token'
```

### 2. Test remediation endpoint with dry run
```bash
# Replace TOKEN with the token from step 1
TOKEN="your_token_here"

curl -X POST http://localhost:3000/remediation/push \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "device_ids": [1],
    "dry_run": true,
    "re_audit": false
  }' | jq
```

Expected response:
```json
{
  "success": true,
  "dry_run": true,
  "total_devices": 1,
  "successful": 1,
  "failed": 0,
  "results": [...]
}
```

### 3. Test from Frontend

1. Log in to the web interface (http://localhost:8080)
2. Navigate to "Audit Results" page
3. Select one or more devices with failed audits
4. Click "Validate Fix" (dry run) - should succeed
5. If validation succeeds, click "Apply Fix" to actually apply

## Monitoring and Debugging

### Watch Logs in Real-Time
```bash
# Terminal 1: Watch API gateway logs
docker-compose logs -f api-gateway

# Terminal 2: Watch admin-service logs
docker-compose logs -f admin-service

# Terminal 3: Watch rule-service logs (for re-audit)
docker-compose logs -f rule-service
```

### Common Log Messages

**Success**:
```
admin-service_1  | INFO:  Applying remediation for rule X on device Y
admin-service_1  | INFO:  Successfully applied remediation for rule X
admin-service_1  | INFO:  Triggering re-audit for device Y after remediation
```

**Errors**:
```
admin-service_1  | ERROR: Failed to connect to device X
admin-service_1  | ERROR: Invalid JSON in reference_config
admin-service_1  | ERROR: Remediation error: ...
```

## Alternative: Rebuild All Services

If the above steps don't work, rebuild all services:

```bash
# Stop all services
docker-compose down

# Remove volumes (optional - will reset database)
# docker-compose down -v

# Rebuild all services
docker-compose build

# Start all services
docker-compose up -d

# Watch logs
docker-compose logs -f
```

## Root Cause Prevention

To prevent this issue in the future:

1. **Add Health Checks** to docker-compose.yml:
```yaml
admin-service:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3005/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

2. **Add Dependency Management**:
```yaml
admin-service:
  depends_on:
    database:
      condition: service_healthy
    rule-service:
      condition: service_started
```

3. **Add Retry Logic** in API Gateway for failed requests

4. **Monitor Service Status** with a dashboard

## Related Files

- **API Gateway**: `/workspace/services/api-gateway/app/main.py`
- **Admin Service**: `/workspace/services/admin-service/app/main.py`
- **Remediation Route**: `/workspace/services/admin-service/app/routes/remediation.py`
- **Remediation Service**: `/workspace/services/admin-service/app/services/remediation_service.py`
- **Docker Compose**: `/workspace/docker-compose.yml`

## Summary

The 502 error occurs when the admin-service is not responding to the remediation request. The most common causes are:

1. ✅ Service not running → Restart with `docker-compose restart admin-service`
2. ✅ Database connection issue → Restart database and service
3. ✅ Import/dependency error → Rebuild container
4. ✅ Missing environment variables → Check docker-compose.yml

After applying the fix, verify that:
- Admin service is running: `docker-compose ps admin-service`
- Health check passes: `curl http://localhost:3000/admin/health`
- Remediation endpoint responds: Test with curl command above
- Frontend "Apply Fix" button works

## Next Steps

Once the service is running:
1. Test with "Validate Fix" first (dry run = true)
2. Review validation results
3. Apply actual remediation with "Apply Fix" button
4. Monitor auto-refresh to see updated audit results
