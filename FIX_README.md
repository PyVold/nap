# 🔧 License Endpoint 404 - Fix Documentation

## 🚨 Problem

Your API is returning `404 Not Found` when trying to activate a license:

```
api-gateway_1 | INFO: 192.168.1.150:47958 - "POST /api/license/activate HTTP/1.1" 404 Not Found
```

## ✅ Solution

**The license code is correct but your Docker containers need to be rebuilt.**

### Quick Fix (60 seconds)

```bash
cd /workspace

# Rebuild admin service
docker compose build admin-service

# Restart admin service
docker compose up -d admin-service

# Wait for startup
sleep 10

# Test it works
curl -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "test"}'
```

**Expected result:** `400 Bad Request` (means it's working!)  
**Before fix:** `404 Not Found` (means endpoint missing)

### Automated Fix

```bash
./rebuild_services.sh
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `QUICK_FIX_GUIDE.md` | Simple 3-step fix guide |
| `LICENSE_404_ANALYSIS.md` | Detailed root cause analysis |
| `LICENSE_ENDPOINT_404_FIX.md` | Comprehensive troubleshooting |
| `rebuild_services.sh` | Automated rebuild script |
| `test_license_endpoints.sh` | Test all license endpoints |

## 🧪 Testing

### Manual Test

```bash
# Test license activation
curl -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "test"}'

# Test license tiers
curl http://localhost:3000/api/license/tiers

# Test license status
curl http://localhost:3000/api/license/status
```

### Automated Tests

```bash
./test_license_endpoints.sh
```

## 🔍 Verification

After running the fix, verify these work:

- [ ] Admin service is running: `docker compose ps admin-service`
- [ ] Health check passes: `curl http://localhost:3005/health`
- [ ] License endpoint responds: Test with curl (see above)
- [ ] Frontend loads: http://localhost:8080/license
- [ ] No 404 errors in logs: `docker compose logs api-gateway`

## 🐛 Troubleshooting

### Issue: Still getting 404

**Solution 1:** Rebuild all services
```bash
docker compose build
docker compose up -d
```

**Solution 2:** Force rebuild without cache
```bash
docker compose build --no-cache admin-service
docker compose up -d admin-service
```

**Solution 3:** Check logs
```bash
docker compose logs -f admin-service
```

### Issue: Services won't start

**Check what's running:**
```bash
docker compose ps
```

**Restart everything:**
```bash
docker compose down
docker compose up -d
```

### Issue: Database errors

**Check database:**
```bash
docker compose logs database
```

**Run migrations:**
```bash
docker compose exec admin-service python -c "from shared.database import init_db; init_db()"
```

## 📊 Architecture

```
Frontend (port 8080)
    ↓
API Gateway (port 3000)
    ↓
Admin Service (port 3005)
    ↓
  /license/activate ← License Router
  /license/status
  /license/tiers
    ↓
PostgreSQL Database (port 5432)
```

## 🎯 What Was Fixed

1. ✅ License router exists in code (`routes/license.py`)
2. ✅ Router is registered in admin service (`main.py:180`)
3. ✅ API gateway routes correctly (`main.py:65`)
4. ✅ Database models exist (`db_models.py:497`)
5. ❌ **Docker container was old** ← This is what we fixed!

## 📝 Root Cause

The license endpoints were added to the codebase, but the Docker containers were built before these changes were made. Docker containers are immutable - they don't automatically update when code changes. They must be rebuilt.

## 🚀 Next Steps

After the fix:

1. **Test the license page:**
   - Navigate to http://localhost:8080/license
   - Try activating a license

2. **Generate a test license:**
   ```bash
   python scripts/generate_license.py \
     --customer-name "Test User" \
     --customer-email "test@example.com" \
     --tier professional
   ```

3. **Activate the license:**
   - Copy the generated license key
   - Paste into the UI at http://localhost:8080/license
   - Click "Activate License"

4. **View license status:**
   - See active tier and quotas
   - Check enabled modules
   - Monitor usage

## 💡 Tips

- Always rebuild after code changes: `docker compose build`
- Check logs regularly: `docker compose logs -f`
- Test endpoints after deployment: `./test_license_endpoints.sh`
- Keep documentation updated when adding features

## 📞 Support

For more detailed information:

- **Quick reference:** `QUICK_FIX_GUIDE.md`
- **Root cause analysis:** `LICENSE_404_ANALYSIS.md`
- **Full troubleshooting:** `LICENSE_ENDPOINT_404_FIX.md`
- **License system docs:** `LICENSE_SYSTEM_README.md`
- **Getting started:** `LICENSE_QUICKSTART.md`

---

**Status:** ✅ Issue identified and fix documented  
**Impact:** License activation will work after rebuild  
**Time to fix:** ~1-2 minutes  
**Downtime:** ~10 seconds (admin service restart)
