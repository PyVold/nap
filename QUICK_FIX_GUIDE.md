# Quick Fix Guide - License Endpoint 404

## The Problem
```
api-gateway_1 | INFO: 192.168.1.150:47958 - "POST /api/license/activate HTTP/1.1" 404 Not Found
```

## The Solution (3 Simple Steps)

### Step 1: Rebuild the Admin Service
```bash
cd /workspace
docker compose build admin-service
```

### Step 2: Restart the Admin Service
```bash
docker compose up -d admin-service
```

### Step 3: Verify It's Working
```bash
# Should return 400 (invalid license), NOT 404 (not found)
curl -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "test"}'
```

## Automated Fix

Run the automated fix script:
```bash
./rebuild_services.sh
```

Or run the full test suite:
```bash
./test_license_endpoints.sh
```

## Why This Happened

The license functionality was added to the codebase, but the Docker containers were built before these changes. The containers need to be rebuilt to include the new license endpoints.

## If It Still Doesn't Work

1. **Check if services are running:**
   ```bash
   docker compose ps
   ```

2. **View admin-service logs:**
   ```bash
   docker compose logs -f admin-service
   ```

3. **Rebuild all services:**
   ```bash
   docker compose build
   docker compose up -d
   ```

4. **Force rebuild without cache:**
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

## Verification Checklist

- [ ] Admin service is running (`docker compose ps admin-service`)
- [ ] Health check passes (`curl http://localhost:3005/health`)
- [ ] License endpoint returns 400 (not 404) for invalid keys
- [ ] License tiers endpoint works (`curl http://localhost:3000/api/license/tiers`)
- [ ] Frontend can access license page (http://localhost:8080/license)

## Next Steps After Fix

1. Access the license management page: http://localhost:8080/license
2. Activate a valid license key
3. View license status, quotas, and enabled modules
4. Manage license tiers and features

## Need More Help?

See detailed documentation:
- `LICENSE_ENDPOINT_404_FIX.md` - Comprehensive troubleshooting guide
- `LICENSE_SYSTEM_README.md` - License system overview
- `LICENSE_QUICKSTART.md` - How to generate and activate licenses
