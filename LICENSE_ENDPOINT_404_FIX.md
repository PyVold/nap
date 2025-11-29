# License Endpoint 404 Fix

## Problem

The frontend is receiving a 404 error when trying to activate a license:
```
api-gateway_1 | INFO: 192.168.1.150:47958 - "POST /api/license/activate HTTP/1.1" 404 Not Found
```

## Root Cause

The license router exists and is properly configured in the admin-service, but the running Docker containers were built before the license functionality was added. The containers need to be rebuilt to include the updated code.

## Architecture Verification

### API Gateway Routing ✓
- Location: `/workspace/services/api-gateway/app/main.py`
- The gateway correctly routes `/api/license/*` requests to admin-service
- Route mapping: `POST /api/license/activate` → `http://admin-service:3005/license/activate`

### Admin Service License Router ✓
- Location: `/workspace/services/admin-service/app/routes/license.py`
- Router prefix: `/license`
- Endpoints:
  - `POST /license/activate` - Activate a license key
  - `GET /license/status` - Get license status and usage
  - `POST /license/deactivate` - Deactivate current license
  - `GET /license/tiers` - Get available license tiers
  - `GET /license/check-module/{module_name}` - Check module access
  - `GET /license/validation-logs` - Get validation logs

### Router Registration ✓
- Location: `/workspace/services/admin-service/app/main.py:180`
- Code: `app.include_router(license.router, tags=["License"])`
- The license router is properly imported and registered

### Database Models ✓
- Location: `/workspace/services/admin-service/app/db_models.py`
- Models defined:
  - `LicenseDB` (line 497) - License information
  - `LicenseValidationLogDB` (line 532) - Validation logs

### Dependencies ✓
- Location: `/workspace/services/admin-service/requirements.txt`
- All required packages are present
- Shared modules: `shared/license_manager.py` exists and is complete

## Solution

Rebuild and restart the admin-service container to include the license functionality:

```bash
# Option 1: Rebuild just the admin-service
docker compose build admin-service
docker compose up -d admin-service

# Option 2: Rebuild all services (recommended for consistency)
docker compose build
docker compose up -d

# Option 3: Force rebuild without cache
docker compose build --no-cache admin-service
docker compose up -d admin-service
```

## Verification

After rebuilding, test the license endpoint:

```bash
# Check if the endpoint is accessible
curl -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "your-license-key-here"}'

# Expected responses:
# - 400 Bad Request (if license key is invalid) - This is good, means endpoint works!
# - 200 OK (if license key is valid) - Success!
# - 404 Not Found - Still broken, need to investigate further
```

## Additional Checks

1. **Verify services are running:**
   ```bash
   docker compose ps
   ```

2. **Check admin-service logs:**
   ```bash
   docker compose logs -f admin-service
   ```

3. **Verify admin-service health:**
   ```bash
   curl http://localhost:3005/health
   ```

4. **Test license endpoint directly on admin-service:**
   ```bash
   docker compose exec admin-service curl -X POST http://localhost:3005/license/activate \
     -H "Content-Type: application/json" \
     -d '{"license_key": "test"}'
   ```

## Expected Behavior After Fix

1. **API Gateway** receives `POST /api/license/activate`
2. **API Gateway** strips `/api/` prefix → `/license/activate`
3. **API Gateway** matches `/license` route to admin-service
4. **API Gateway** forwards to `http://admin-service:3005/license/activate`
5. **Admin Service** receives request and routes to license router
6. **License Router** handles the request and validates the license
7. Returns appropriate response (200, 400, etc.)

## Files Involved

- `/workspace/services/api-gateway/app/main.py` - API Gateway routing
- `/workspace/services/admin-service/app/main.py` - Admin service with router registration
- `/workspace/services/admin-service/app/routes/license.py` - License endpoints
- `/workspace/services/admin-service/app/db_models.py` - License database models
- `/workspace/services/admin-service/Dockerfile` - Admin service container definition
- `/workspace/docker-compose.yml` - Service orchestration
- `/workspace/shared/license_manager.py` - License validation logic

## Alternative: Manual Service Restart

If rebuilding doesn't work, try restarting the services:

```bash
docker compose restart admin-service
docker compose restart api-gateway
```

## Next Steps

After fixing the 404 error, users should be able to:
1. Access the license management page at http://localhost:8080/license
2. Activate licenses via the UI
3. View license status and usage quotas
4. Manage license tiers and modules
