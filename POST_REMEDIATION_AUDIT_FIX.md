# Post-Remediation Audit Fix

## Problem Summary

After applying remediation to a device, the automatic re-audit was failing with a 404 error:

```
rule-service_1       | INFO:     172.18.0.7:35750 - "POST /audits HTTP/1.1" 404 Not Found
admin-service_1      | WARNING - Re-audit request returned status 404: {"detail":"Not Found"}
```

The remediation was applied successfully, but the subsequent audit to verify the fix was not being triggered.

## Root Cause

**URL Path Mismatch**: The admin-service was calling the wrong endpoint on the rule-service:

- **Admin-service was calling**: `POST /audits`
- **Rule-service expects**: `POST /audit/` (singular, with trailing slash)

This mismatch occurred in the remediation service when trying to trigger a re-audit after successfully applying configuration changes.

## Files Changed

### 1. `/workspace/services/admin-service/app/services/remediation_service.py`

**Line 245**: Changed the API endpoint from `/audits` to `/audit/`

```python
# Before (INCORRECT):
response = await client.post(
    f"{rule_service_url}/audits",
    json=audit_request
)

# After (CORRECT):
response = await client.post(
    f"{rule_service_url}/audit/",
    json=audit_request
)
```

### 2. `/workspace/RE_AUDIT_FIX.md`

**Line 86**: Updated documentation to reflect correct endpoint

```markdown
# Before:
↓ (POST /audits with device_ids)

# After:
↓ (POST /audit/ with device_ids)
```

## Expected Behavior After Fix

### Successful Flow

1. User triggers remediation via `POST /remediation/push`
2. Admin-service applies configuration to device
3. Device accepts and commits configuration
4. Admin-service triggers re-audit via `POST /audit/` (FIXED)
5. Rule-service accepts request with `202 Accepted`
6. Rule-service runs audit in background
7. Audit results are stored and device compliance is updated

### Log Output (Expected)

```
admin-service_1      | INFO - Configuration applied successfully to sros1
admin-service_1      | INFO - Triggering re-audit for device sros1 after remediation
admin-service_1      | INFO - Re-auditing with 1 rules from last audit
rule-service_1       | INFO:     172.18.0.7:xxxxx - "POST /audit/ HTTP/1.1" 202 Accepted
admin-service_1      | INFO - Re-audit triggered for sros1: Audit started in background
admin-service_1      | INFO - Audit will run with 1 device(s) and 1 rule(s)
```

## Verification Steps

### 1. Restart Admin Service

The fix requires restarting the admin-service to pick up the code changes:

```bash
docker-compose restart admin-service
```

### 2. Trigger Remediation

Apply remediation to a device with failed audit checks:

```bash
curl -X POST http://localhost:3000/remediation/push \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "device_ids": [1],
    "dry_run": false,
    "re_audit": true
  }'
```

### 3. Check Logs

Monitor the logs for successful re-audit trigger:

```bash
docker-compose logs -f admin-service | grep -i audit
docker-compose logs -f rule-service | grep -i audit
```

### 4. Verify Audit Results

Check that new audit results are created:

```bash
# Get latest audit results
curl http://localhost:3000/audit/results

# Get audit results for specific device
curl http://localhost:3000/audit/results/1
```

## Technical Details

### Rule-Service Endpoint Configuration

The rule-service (`services/rule-service/app/main.py`) registers the audits router with prefix `/audit`:

```python
app.include_router(audits.router, prefix="/audit", tags=["Audits"])
```

The audits router (`services/rule-service/app/routes/audits.py`) defines the POST endpoint at `/`:

```python
@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def run_audit(audit_request: AuditRequest, ...):
    """Execute audit on specified devices with specified rules"""
```

This creates the full endpoint path: `/audit/`

### API Gateway Configuration

The API Gateway (`services/api-gateway/app/main.py`) correctly routes `/audit` to the rule-service:

```python
"rule-service": {
    "url": "http://rule-service:3002",
    "routes": ["/rules", "/rule-templates", "/audit", "/audit-schedules"],
}
```

The gateway automatically handles trailing slashes for collection endpoints.

## Related Files

- `/workspace/services/admin-service/app/services/remediation_service.py` - Main fix location
- `/workspace/services/rule-service/app/main.py` - Endpoint registration
- `/workspace/services/rule-service/app/routes/audits.py` - Audit endpoint implementation
- `/workspace/services/api-gateway/app/main.py` - Route configuration
- `/workspace/RE_AUDIT_FIX.md` - Documentation update

## Impact

- **Scope**: Post-remediation automatic re-audit functionality
- **Severity**: Medium - remediation still works, but compliance verification is skipped
- **Services Affected**: admin-service (requires restart)
- **Backward Compatibility**: No breaking changes to other services

## Testing Checklist

- [x] Fix applied to admin-service remediation code
- [x] Documentation updated
- [ ] Admin-service restarted
- [ ] Manual remediation test with re-audit
- [ ] Verify 202 Accepted response from rule-service
- [ ] Verify audit results are created
- [ ] Verify device compliance is updated
- [ ] Check logs for successful flow

## Additional Notes

### Why Trailing Slash Matters

FastAPI's router matching is strict about trailing slashes:
- Route defined as `@router.post("/")` with prefix `/audit` → matches `/audit/`
- Request to `/audits` or `/audit` (no slash) → 404 or 307 redirect
- Request to `/audit/` → matches correctly

### Alternative Solutions Considered

1. **Change rule-service endpoint to `/audits`**: Rejected - would require changes to multiple files and tests
2. **Remove trailing slash from admin-service call**: Rejected - API Gateway expects trailing slash for collection endpoints
3. **Use prefix `/audits` in rule-service**: Rejected - inconsistent with other services using singular form

The chosen solution (updating admin-service to use correct endpoint) is minimal and aligns with existing conventions.
