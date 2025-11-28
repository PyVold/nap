# Deployment Instructions - Nokia SROS Fixes

## What Was Fixed

### ✅ Issue 1: JSON Parsing Error (FIXED)
```
Failed to parse config as JSON: Expecting ',' delimiter: line 11 column 4
```

### ✅ Issue 2: Re-Audit Import Error (FIXED)
```
Failed to re-audit device sros1: No module named 'engine'
```

Both issues are now resolved and the remediation flow works end-to-end.

---

## 🚀 Quick Deployment

### Step 1: Rebuild Admin Service
```bash
cd /workspace

# Rebuild admin-service with both fixes
docker-compose build admin-service

# Restart the service
docker-compose up -d admin-service
```

### Step 2: Verify Deployment
```bash
# Check admin-service is running
docker-compose ps admin-service

# Check logs for startup messages
docker-compose logs --tail=50 admin-service
```

### Step 3: Test Remediation (Optional)
```bash
# Test on a device
# This will now:
# 1. Parse JSON correctly ✅
# 2. Apply config to device ✅
# 3. Trigger re-audit via API ✅

# Example (adjust device_ids for your environment):
curl -X POST http://localhost:3000/remediation/push \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "device_ids": [1],
    "dry_run": false,
    "re_audit": true
  }'
```

---

## 📊 Expected Behavior After Deployment

### Successful Remediation Logs

You should see logs like this:

```
✅ JSON Parsing Success:
admin-service | INFO: Validated JSON config: {"netconf": {"admin-state": "enable"}}
admin-service | INFO: Configuration applied successfully to sros1

✅ Re-Audit Triggered:
admin-service | INFO: Successfully applied remediation for rule Unknown
admin-service | INFO: Triggering re-audit for device sros1 after remediation
admin-service | INFO: Re-auditing with 5 rules from last audit
admin-service | INFO: Re-audit triggered for sros1: Audit started in background
admin-service | INFO: Audit will run with 1 device(s) and 5 rule(s)

✅ Audit Running in Background:
rule-service  | INFO: Audit started in background
```

---

## 🔍 Verification Checklist

After deployment, verify:

- [ ] Admin service is running: `docker-compose ps admin-service`
- [ ] No "module named 'engine'" errors in logs
- [ ] No JSON parsing errors when applying remediation
- [ ] Re-audit triggers successfully (check logs)
- [ ] Audit results update in database

---

## 🛠️ Files Changed

### This Deployment Affects

1. **Admin Service** ✅ (requires rebuild)
   - `services/admin-service/app/services/remediation_service.py`
   - `services/admin-service/app/connectors/nokia_sros_connector.py`
   - `services/admin-service/requirements.txt` (added httpx)

### Other Services Already Fixed (from previous deployment)

2. **Backup Service** ✅ (already includes JSON fix)
   - `services/backup-service/app/connectors/nokia_sros_connector.py`

3. **Device Service** ✅ (already includes JSON fix)
   - `services/device-service/app/connectors/nokia_sros_connector.py`

4. **Inventory Service** ✅ (already includes JSON fix)
   - `services/inventory-service/app/connectors/nokia_sros_connector.py`

5. **Rule Service** ✅ (already includes JSON fix)
   - `services/rule-service/app/connectors/nokia_sros_connector.py`

---

## 🔄 Full Rebuild (If Needed)

If you want to rebuild all services with fixes:

```bash
# Rebuild all affected services
docker-compose build admin-service backup-service device-service inventory-service rule-service

# Restart all services
docker-compose down
docker-compose up -d
```

---

## 📝 Validation Script (Optional)

Before deploying, you can validate existing rules:

```bash
# Check for malformed JSON in rules
python scripts/validate_rule_configs.py

# Auto-fix issues if found
python scripts/validate_rule_configs.py --fix
```

---

## 🚨 Rollback Plan

If issues occur after deployment:

### Quick Rollback
```bash
# Stop the service
docker-compose stop admin-service

# Revert to previous image
docker-compose up -d admin-service
```

### Full Rollback
```bash
# Checkout previous version
git checkout HEAD~1 services/admin-service/

# Rebuild
docker-compose build admin-service

# Restart
docker-compose up -d admin-service
```

**Note:** No database changes were made, so rollback is safe.

---

## 🔐 Environment Variables

The new re-audit functionality uses this environment variable:

```bash
RULE_SERVICE_URL=http://rule-service:3002  # Default value
```

If your rule-service is at a different URL, set this in docker-compose.yml:

```yaml
admin-service:
  environment:
    - RULE_SERVICE_URL=http://your-rule-service:port
```

---

## 📊 Monitoring After Deployment

### Key Log Messages to Watch

**✅ Success Indicators:**
```bash
# JSON parsing works
grep "Validated JSON config" logs

# Configuration applies
grep "Configuration applied successfully" logs

# Re-audit triggers
grep "Re-audit triggered" logs
```

**❌ Error Indicators:**
```bash
# JSON errors (should not appear)
grep "Failed to parse config as JSON" logs

# Import errors (should not appear)
grep "No module named 'engine'" logs

# Re-audit failures (remediation still succeeds)
grep "Failed to trigger re-audit" logs
```

---

## 🎯 Success Criteria

Deployment is successful when:

1. ✅ No JSON parsing errors in logs
2. ✅ No "module named 'engine'" errors in logs
3. ✅ Remediation applies configurations successfully
4. ✅ Re-audit triggers and runs in background
5. ✅ Audit results update in database

---

## 📞 Support

### Troubleshooting

| Issue | Command | Expected Result |
|-------|---------|-----------------|
| Check service status | `docker-compose ps admin-service` | State: Up |
| View recent logs | `docker-compose logs --tail=100 admin-service` | No errors |
| Test API | `curl http://localhost:3005/health` | {"status": "healthy"} |
| Check re-audit | `docker-compose logs admin-service \| grep "Re-audit"` | "triggered" messages |

### Documentation

- **JSON Fix Details:** [NOKIA_SROS_JSON_FIX.md](./NOKIA_SROS_JSON_FIX.md)
- **Re-Audit Fix Details:** [RE_AUDIT_FIX.md](./RE_AUDIT_FIX.md)
- **Quick Reference:** [QUICK_FIX_GUIDE.md](./QUICK_FIX_GUIDE.md)
- **Full Summary:** [COMPLETION_SUMMARY.md](./COMPLETION_SUMMARY.md)

---

## ✅ Summary

**What to Deploy:**
- Admin Service (rebuild required)

**Changes:**
- Fixed JSON parsing in Nokia SROS connector
- Fixed re-audit to use HTTP API instead of direct import
- Added httpx dependency

**Risk Level:** Low
- No database changes
- Backward compatible
- Easy rollback

**Deployment Time:** ~2-3 minutes
- Build: ~1-2 minutes
- Restart: ~30 seconds
- Verification: ~30 seconds

---

## 🎉 Post-Deployment

After successful deployment:

1. ✅ Monitor logs for 10-15 minutes
2. ✅ Test remediation on a test device
3. ✅ Verify audit results update
4. ✅ Document any issues
5. ✅ Update team

**Status:** Ready for Production ✅

---

**Last Updated:** 2025-11-28  
**Branch:** cursor/handle-sros-json-config-errors-claude-4.5-sonnet-thinking-f5a0  
**Deployment Status:** ✅ Ready
