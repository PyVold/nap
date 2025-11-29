# 🚀 START HERE - License 404 Fix

## The Problem in 10 Seconds

Your license activation endpoint returns **404 Not Found** because the Docker containers were built before the license code was added.

## The Fix in 30 Seconds

```bash
docker compose build admin-service && docker compose up -d admin-service
```

That's it! Wait 10 seconds, then test:

```bash
curl -X POST http://localhost:3000/api/license/activate -H "Content-Type: application/json" -d '{"license_key":"test"}'
```

If you see `400 Bad Request` instead of `404 Not Found`, **it's fixed!** ✅

---

## Choose Your Path

### 🎯 Just Fix It (Recommended)

Run the automated fix script:

```bash
./rebuild_services.sh
```

### 🧪 Fix and Test

Run rebuild + automated tests:

```bash
./rebuild_services.sh && ./test_license_endpoints.sh
```

### 📚 I Want to Understand

Read these in order:

1. **`QUICK_FIX_GUIDE.md`** - Simple 3-step guide (2 min read)
2. **`LICENSE_404_ANALYSIS.md`** - What went wrong and why (5 min read)
3. **`LICENSE_ENDPOINT_404_FIX.md`** - Detailed troubleshooting (10 min read)

### 🐛 It's Still Broken

1. Check if services are running:
   ```bash
   docker compose ps
   ```

2. View logs:
   ```bash
   docker compose logs -f admin-service
   ```

3. Try full rebuild:
   ```bash
   docker compose build && docker compose up -d
   ```

4. See `LICENSE_ENDPOINT_404_FIX.md` for advanced troubleshooting

---

## What's Included

### 📄 Documentation Files

| File | Description | Read Time |
|------|-------------|-----------|
| `QUICK_FIX_GUIDE.md` | 3-step quick fix | 2 min |
| `FIX_README.md` | Complete fix documentation | 5 min |
| `LICENSE_404_ANALYSIS.md` | Root cause analysis | 5 min |
| `LICENSE_ENDPOINT_404_FIX.md` | Detailed troubleshooting | 10 min |

### 🔧 Scripts

| Script | Purpose |
|--------|---------|
| `rebuild_services.sh` | Automated rebuild and test |
| `test_license_endpoints.sh` | Test all license endpoints |

### 📊 Technical Details

- **Issue:** License endpoints return 404
- **Cause:** Containers built before license code was added
- **Fix:** Rebuild admin-service container
- **Downtime:** ~10 seconds
- **Risk:** Low (only restarts one service)

---

## Quick Commands Reference

### Rebuild Services

```bash
# Rebuild just admin-service
docker compose build admin-service
docker compose up -d admin-service

# Rebuild all services
docker compose build
docker compose up -d
```

### Test Endpoints

```bash
# Test license activation (should return 400, not 404)
curl -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key":"test"}'

# Test license tiers (should return 200)
curl http://localhost:3000/api/license/tiers

# Test health (should return 200)
curl http://localhost:3005/health
```

### View Logs

```bash
# View admin-service logs
docker compose logs -f admin-service

# View all service logs
docker compose logs -f

# View last 50 lines
docker compose logs --tail=50 admin-service
```

### Service Management

```bash
# Check service status
docker compose ps

# Restart a service
docker compose restart admin-service

# Stop services
docker compose down

# Start services
docker compose up -d
```

---

## Success Checklist

After running the fix, verify:

- [ ] Admin service is running: `docker compose ps admin-service`
- [ ] Health check passes: `curl http://localhost:3005/health`
- [ ] License activate returns 400 (not 404): Test with curl above
- [ ] License tiers loads: `curl http://localhost:3000/api/license/tiers`
- [ ] Frontend works: http://localhost:8080/license
- [ ] No errors in logs: `docker compose logs --tail=20 admin-service`

---

## Next Steps After Fix

1. **Access license page:** http://localhost:8080/license

2. **Generate a license:**
   ```bash
   python scripts/generate_license.py \
     --customer-name "Test User" \
     --customer-email "test@example.com" \
     --tier professional
   ```

3. **Activate license:** Copy the key and paste in the UI

4. **Verify it works:** Check license status and quotas

---

## Why This Happened

Docker containers are **immutable** - they don't update when code changes. The license endpoints were added to your codebase, but the running containers were built from older code that didn't have them yet.

Think of it like this:
- ✅ New code has license endpoints
- ❌ Old container doesn't have them
- 🔄 Rebuild container = Get new code

---

## Need More Help?

| If you see... | Read this... |
|---------------|--------------|
| 404 errors | `QUICK_FIX_GUIDE.md` |
| 500 errors | `LICENSE_ENDPOINT_404_FIX.md` |
| Database errors | `DOCKER_LICENSE_SETUP.md` |
| Import errors | `LICENSE_404_ANALYSIS.md` |
| Any other issues | `LICENSE_ENDPOINT_404_FIX.md` |

---

## TL;DR

**Problem:** License endpoint returns 404  
**Cause:** Old container, new code  
**Fix:** `docker compose build admin-service && docker compose up -d admin-service`  
**Time:** 1 minute  
**Result:** License activation works ✅

---

**Ready?** Run this now:

```bash
./rebuild_services.sh
```

Then open: http://localhost:8080/license
