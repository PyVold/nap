# Fix License Issues - Step by Step Guide

## Issue Summary
You're experiencing:
1. ❌ Menu showing wrong modules for license tier
2. ❌ License activation not switching tiers
3. ❌ Quota enforcement not working

## Root Cause
**The backend code was updated but the containers haven't been restarted with the new code.**

---

## ✅ SOLUTION: Restart with Updated Code

### Step 1: Rebuild and Restart Backend

```bash
cd /home/user/nap

# Stop all containers
docker-compose down

# Rebuild with new code
docker-compose build

# Start containers
docker-compose up -d

# Check logs to ensure it started
docker-compose logs -f --tail=50
```

### Step 2: Fix Database State (if needed)

If license switching still doesn't work, you may have multiple active licenses in the database:

```bash
# Access the database
docker-compose exec database psql -U nap_user -d nap_db

# Check for multiple active licenses
SELECT id, license_tier, customer_name, is_active, activated_at
FROM licenses
WHERE is_active = true;

# If multiple licenses shown, deactivate all
UPDATE licenses SET is_active = false;

# Activate only the one you want (replace LICENSE_KEY with your actual key)
UPDATE licenses
SET is_active = true
WHERE license_key = 'YOUR_LICENSE_KEY_HERE';

# Verify
SELECT id, license_tier, is_active FROM licenses;

# Exit
\q
```

### Step 3: Clear Frontend Cache

In your browser:
- Press **Ctrl+Shift+R** (Windows/Linux) or **Cmd+Shift+R** (Mac)
- Or use Incognito/Private mode

### Step 4: Test Each Issue

#### Test 1: Menu Filtering
1. Login with Starter license
2. Menu should show ONLY:
   - ✅ Dashboard
   - ✅ Devices
   - ✅ Device Import
   - ✅ Audit Results
   - ✅ Rule Management
   - ✅ Device Health
   - ✅ Hardware Inventory
   - ✅ License

3. Menu should NOT show:
   - ❌ Device Groups
   - ❌ Discovery Groups
   - ❌ Audit Schedules
   - ❌ Config Backups
   - ❌ Drift Detection

#### Test 2: License Switching
1. Note current tier in `/license` page
2. Activate a different tier license
3. Page should refresh and show new tier immediately
4. Menu should update to show/hide features

#### Test 3: Quota Enforcement

**Device Quota:**
```bash
# Try to add 11th device with Starter license (max 10)
# Should get error: "Device quota exceeded"
```

**User Quota:**
```bash
# Try to create 3rd user with Starter license (max 2)
# Should get error: "Cannot create user: License limit reached (2/2)"
```

**Storage:**
- Create some config backups
- Check `/license` page - storage should show non-zero

---

## 🔍 Advanced Debugging

### Check if backend is running updated code:

```bash
# Check backend logs
docker-compose logs backend | grep -i "license"

# Or exec into container and check file
docker-compose exec backend cat /app/services/user_group_service.py | grep -A10 "def get_user_modules"
# Should show: "Returns BACKEND LICENSE MODULE NAMES"
```

### Check user's module access:

```bash
docker-compose exec backend python3 -c "
import sys
sys.path.insert(0, '/app')
from database import SessionLocal
from services.user_group_service import user_group_service

db = SessionLocal()
user_modules = user_group_service.get_user_modules(db, 1)  # User ID 1
print('User modules:', sorted(user_modules))
db.close()
"
```

### Manual SQL Fixes:

```sql
-- Connect to database
docker-compose exec database psql -U nap_user -d nap_db

-- Check active licenses
SELECT id, license_tier, is_active, activated_at FROM licenses;

-- Deactivate all except newest
UPDATE licenses SET is_active = false;
UPDATE licenses SET is_active = true
WHERE activated_at = (SELECT MAX(activated_at) FROM licenses);

-- Check device count vs quota
SELECT
  (SELECT COUNT(*) FROM devices) as current_devices,
  (SELECT max_devices FROM licenses WHERE is_active = true) as max_devices;

-- Check user count vs quota
SELECT
  (SELECT COUNT(*) FROM users) as current_users,
  (SELECT max_users FROM licenses WHERE is_active = true) as max_users;

-- Check storage usage
SELECT
  SUM(size_bytes) / (1024*1024*1024) as storage_gb,
  (SELECT max_storage_gb FROM licenses WHERE is_active = true) as max_storage_gb
FROM config_backups;
```

---

## 📝 Expected Behavior After Fix

### Starter License
- **Menu:** 8 items (Dashboard, Devices, Import, Audits, Rules, Health, Hardware, License)
- **Max Devices:** 10
- **Max Users:** 2
- **Modules:** devices, manual_audits, basic_rules, health_checks

### Professional License
- **Menu:** 15 items (all Starter + Groups, Discovery, Schedules, Templates, Backups, Drift, Notifications)
- **Max Devices:** 100
- **Max Users:** 10
- **Modules:** All Starter + scheduled_audits, rule_templates, config_backups, drift_detection, webhooks, device_groups, discovery

### Enterprise License
- **Menu:** 18 items (all Professional + Integrations, Workflows, Analytics)
- **Max Devices:** Unlimited (999999)
- **Max Users:** Unlimited (999999)
- **Modules:** All features

---

## ⚠️ Common Issues

1. **"Nothing changed after restart"**
   - Make sure you ran `docker-compose build` not just `docker-compose restart`
   - Clear browser cache (hard refresh)

2. **"Still seeing multiple tiers"**
   - Check database for multiple active licenses (see SQL above)
   - Run the UPDATE to deactivate all, then activate one

3. **"Menu shows everything even on Starter"**
   - Check user is not a superuser (they get all licensed modules)
   - Check user's groups have correct module access
   - Verify backend restarted with new code

4. **"Quota not enforced"**
   - Backend must be restarted
   - Check endpoint has `Depends(enforce_quota("devices", 1))`
   - Device import now checks quota before importing

---

## Need More Help?

Run this to get full diagnostic:

```bash
docker-compose exec backend python3 /app/debug_license.py
```

This will show:
- Active licenses
- Database state
- User module access
- What needs to be fixed
