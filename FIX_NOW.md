# Immediate Fix Steps - License Issues

## Problem Summary
1. ❌ Menu showing wrong modules (seeing device inventory in Starter)
2. ❌ License switching not working (can't activate new license)
3. ❌ Quota enforcement not working (exceeding limits, storage shows 0)

## Root Cause
The containers are running OLD CODE. The fixes were applied to the source files but the Docker containers haven't been rebuilt with the new code.

---

## ✅ STEP-BY-STEP FIX (Run these commands exactly)

### Step 1: Stop All Containers
```bash
cd /home/user/nap
docker-compose down
```

### Step 2: Rebuild ONLY the Services We Changed
```bash
# Rebuild admin-service (this is the critical one)
docker-compose build admin-service

# Rebuild device-service (for device quota enforcement)
docker-compose build device-service

# Rebuild frontend (for module mappings)
docker-compose build frontend
```

### Step 3: Start Everything
```bash
docker-compose up -d
```

### Step 4: Watch the Logs (to see if it starts correctly)
```bash
docker-compose logs -f admin-service | head -50
```
Press Ctrl+C after you see "Uvicorn running"

### Step 5: Fix Multiple Active Licenses (if any)
```bash
# Check how many active licenses exist
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT id, license_tier, is_active, activated_at FROM licenses ORDER BY activated_at DESC;"

# If you see multiple is_active=true, fix it:
docker-compose exec database psql -U nap_user -d nap_db -c \
  "UPDATE licenses SET is_active = false;
   UPDATE licenses SET is_active = true
   WHERE activated_at = (SELECT MAX(activated_at) FROM licenses);"

# Verify fix
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT id, license_tier, is_active FROM licenses;"
```

### Step 6: Run Full Diagnostic
```bash
# Make diagnostic executable
chmod +x /home/user/nap/COMPREHENSIVE_DIAGNOSTIC.sh

# Run it
./COMPREHENSIVE_DIAGNOSTIC.sh
```

Or run the detailed Python diagnostic inside the container:
```bash
docker-compose exec admin-service python3 /app/diagnose_detailed.py
```

### Step 7: Test Each Issue

#### Test 1: Check Module Mappings Endpoint
```bash
curl http://localhost:3000/license/module-mappings | python3 -m json.tool
```
**Expected**: Should show JSON with "mappings", "modules", "tiers"
**If it fails**: admin-service wasn't rebuilt properly

#### Test 2: Check User Modules
```bash
# Get first user ID
USER_ID=$(docker-compose exec -T database psql -U nap_user -d nap_db -t -c \
  "SELECT id FROM users ORDER BY id LIMIT 1;" | tr -d ' ')

# Test endpoint
curl http://localhost:3000/user-management/users/$USER_ID/modules
```
**Expected**: Should return backend module names like `["devices", "manual_audits", "basic_rules", "health_checks"]`
**Wrong**: If it returns frontend names like `["audit", "rules", "health"]`

#### Test 3: Test License Switching
1. Go to http://localhost:8080/license
2. Note current tier
3. Activate a different tier license key
4. **Expected**: Page should refresh and show new tier
5. Menu should update immediately

#### Test 4: Test Quota Enforcement

**User Quota:**
```bash
# Check current users vs limit
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT
    (SELECT COUNT(*) FROM users) as current_users,
    (SELECT max_users FROM licenses WHERE is_active = true) as max_users;"

# If at limit, try creating a new user through UI
# Should get error: "Cannot create user: License limit reached"
```

**Device Quota:**
```bash
# Check current devices vs limit
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT
    (SELECT COUNT(*) FROM devices) as current_devices,
    (SELECT max_devices FROM licenses WHERE is_active = true) as max_devices;"

# If at limit, try importing devices through CSV
# Should get error: "Device quota exceeded"
```

**Storage:**
```bash
# Check storage calculation
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT
    COALESCE(SUM(size_bytes) / (1024*1024*1024.0), 0)::numeric(10,2) as storage_gb
  FROM config_backups;"
```

---

## ⚠️ If Issues Persist After Rebuild

### Issue 1: Module Mappings Endpoint 404

**Check:**
```bash
docker-compose logs admin-service | grep "module-mappings"
```

**Fix:**
```bash
# Verify the file exists in container
docker-compose exec admin-service cat /app/routes/license.py | grep "module-mappings"

# Should show: @router.get("/module-mappings")
# If not found, container has old code - force rebuild:
docker-compose build --no-cache admin-service
docker-compose up -d admin-service
```

### Issue 2: get_user_modules Returns Wrong Names

**Check:**
```bash
docker-compose exec admin-service cat /app/services/user_group_service.py | grep "Returns BACKEND"
```

**Should show**: "Returns BACKEND LICENSE MODULE NAMES"
**If not**: Container has old code, rebuild as above

### Issue 3: Storage Always Shows Zero

This happens if:
1. No config backups have been created yet
2. The `config_backups` table doesn't exist
3. The `size_bytes` column is missing

**Check:**
```bash
# See if table exists
docker-compose exec database psql -U nap_user -d nap_db -c "\d config_backups"

# Check if any backups exist
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT id, device_id, size_bytes, created_at FROM config_backups LIMIT 5;"
```

**Note**: Storage only includes config backups, NOT database size.
If you want to include database size, we need to modify the calculation.

### Issue 4: Quotas Not Enforced

**Check device import endpoint:**
```bash
docker-compose exec device-service cat /app/routes/device_import.py | grep "quota"
```

**Check user creation endpoint:**
```bash
docker-compose exec admin-service cat /app/routes/user_management.py | grep "quota"
```

If these don't show quota checks, those services also need to be rebuilt.

---

## 🔍 Quick Verification Checklist

After running all fixes, verify:

- [ ] Only 1 active license in database
- [ ] `/license/module-mappings` endpoint returns JSON
- [ ] `/user-management/users/1/modules` returns backend names like "manual_audits"
- [ ] License page shows correct tier and quotas
- [ ] Menu shows ONLY modules for your tier:
  - **Starter**: Dashboard, Devices, Import, Audits, Rules, Health, Hardware, License (8 items)
  - **Professional**: Starter + Groups, Discovery, Schedules, Templates, Backups, Drift, Notifications (15 items)
  - **Enterprise**: Professional + Integrations, Workflows, Analytics (18 items)
- [ ] Creating user beyond limit shows error
- [ ] Importing devices beyond limit shows error
- [ ] Storage calculation shows non-zero if backups exist

---

## 📞 Still Not Working?

Run this and send me the full output:

```bash
cd /home/user/nap
./COMPREHENSIVE_DIAGNOSTIC.sh > diagnostic_output.txt 2>&1
cat diagnostic_output.txt
```

Also check:
```bash
# Container image creation times
docker-compose images

# Should show recent "Created" times for admin-service, device-service, frontend
# If "Created" is days/weeks ago, rebuild didn't work
```

---

## 🚀 Expected Behavior After Fix

### Starter License Should Show:
**Menu Items:**
- ✅ Dashboard
- ✅ Devices
- ✅ Device Import
- ✅ Audit Results
- ✅ Rule Management
- ✅ Device Health
- ✅ Hardware Inventory
- ✅ License

**Should NOT show:**
- ❌ Device Groups
- ❌ Discovery Groups
- ❌ Audit Schedules
- ❌ Config Backups
- ❌ Drift Detection
- ❌ Rule Templates
- ❌ Notifications

### License Switching:
1. Activate Professional license
2. **Immediate effect:**
   - License page shows "Professional" tier
   - Menu adds: Device Groups, Discovery, Schedules, Templates, Backups, Drift, Notifications
   - Max devices increases to 100
   - Max users increases to 10

### Quota Enforcement:
- Starter (10 devices): Importing 11th device shows error
- Starter (2 users): Creating 3rd user shows error
- Storage: Shows sum of all config backup sizes in GB
