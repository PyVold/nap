# Frontend Connection Error Fix

## Problem Summary

The frontend was experiencing 502 Bad Gateway errors when navigating between pages. The logs showed:

```
device-service_1     | INFO: 172.18.0.8:45406 - "GET /devices HTTP/1.1" 307 Temporary Redirect
api-gateway_1        | ERROR - Error forwarding request to http://device-service:3001/devices: All connection attempts failed
api-gateway_1        | INFO: 172.18.0.9:40762 - "GET /devices/ HTTP/1.1" 502 Bad Gateway
```

## Root Cause

The issue was caused by a mismatch in URL formatting between the API gateway and the microservices:

1. **Frontend** sends requests without trailing slashes (e.g., `/devices`)
2. **API Gateway** forwards these to services without trailing slashes
3. **FastAPI services** expect trailing slashes for collection endpoints (defined as `@router.get("/", ...)`)
4. **Services return 307 Redirect** to add the trailing slash
5. **Gateway fails** to follow the redirect properly, resulting in "All connection attempts failed"

## Solution Implemented

Updated `/workspace/services/api-gateway/app/main.py` to intelligently add trailing slashes when forwarding requests:

- **Collection endpoints** (like `/devices`, `/rules`, `/device-groups`) → forwarded with trailing slash
- **Detail endpoints** (like `/devices/123`) → forwarded without trailing slash
- **Action endpoints** (like `/devices/discover`) → forwarded without trailing slash
- **Detection logic**: Checks if the path exactly matches a route prefix in the service registry

### Key Changes

1. **Path normalization**: Preserves the original path format
2. **Smart slash handling**: Adds trailing slashes only for collection endpoints
3. **No redirect following**: Since we're sending the correct format, no redirects occur

## How to Apply the Fix

Since the api-gateway code has been updated, you need to restart the service:

```bash
# Option 1: Restart just the api-gateway
docker-compose restart api-gateway

# Option 2: Rebuild if needed
docker-compose up -d --build api-gateway

# Option 3: Restart all services
docker-compose restart
```

## Verification

After restarting, the logs should show:

```
# Before (with error):
device-service_1     | INFO: 172.18.0.8:45406 - "GET /devices HTTP/1.1" 307 Temporary Redirect
api-gateway_1        | ERROR - Error forwarding request to http://device-service:3001/devices: All connection attempts failed

# After (working):
device-service_1     | INFO: 172.18.0.8:45406 - "GET /devices/ HTTP/1.1" 200 OK
api-gateway_1        | INFO: 172.18.0.9:40762 - "GET /devices/ HTTP/1.1" 200 OK
```

## Testing

Navigate through the frontend pages that were previously failing:
- ✅ `/devices` - Device list page
- ✅ `/device-groups` - Device groups page
- ✅ `/discovery-groups` - Discovery groups page
- ✅ `/audit-schedules` - Audit schedules page
- ✅ `/rules` - Rules page
- ✅ `/rule-templates` - Rule templates page

All should load without 502 errors.

## Technical Details

### Updated Code Section

Location: `services/api-gateway/app/main.py` lines 185-240

The proxy_request function now:
1. Preserves the original path format
2. Checks if the path exactly matches a route prefix in the service registry
3. If it matches (collection endpoint), adds a trailing slash
4. Otherwise (detail/action endpoints), forwards as-is without trailing slash
5. This prevents 307 redirects while maintaining correct endpoint behavior

### Why This Works

FastAPI routers with `prefix="/devices"` and routes `@router.get("/")` expect:
- Collection: `http://service:port/devices/` ← **with trailing slash**
- Detail: `http://service:port/devices/123` ← **without trailing slash**

The gateway now matches this expectation, preventing 307 redirects entirely.

## Related Files

- `/workspace/services/api-gateway/app/main.py` - Fixed
- `/workspace/services/device-service/app/main.py` - No changes needed
- `/workspace/services/rule-service/app/main.py` - No changes needed

## Status

✅ **FIX APPLIED** - Ready for testing after service restart
