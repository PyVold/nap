# Nokia SROS JSON Config Error - Quick Fix Guide

## ✅ What Was Fixed

The remediation service was failing with JSON parsing errors when trying to apply configuration to Nokia SROS devices. This has been fixed with:

1. **Enhanced error handling** - Better logging and error messages
2. **Auto-fix for common JSON issues** - Automatically fixes trailing commas
3. **Support for simple values** - Not just JSON objects/arrays
4. **Pre-validation** - Validates config before sending to device

## 🚀 Quick Start

### 1. Rebuild and Restart Services

```bash
cd /workspace
docker-compose down
docker-compose build admin-service backup-service
docker-compose up -d
```

### 2. Validate Existing Rules (Optional but Recommended)

```bash
# Check for issues in existing rules
python scripts/validate_rule_configs.py

# If issues found, auto-fix them
python scripts/validate_rule_configs.py --fix
```

### 3. Test Remediation

1. Run an audit on a Nokia SROS device
2. If failures found, try applying remediation
3. Check logs for improved error messages

## 📋 What to Look For in Logs

### ✅ Success Messages

```
INFO: Validated JSON config: {"admin-state": "enable"}
INFO: Configuration applied successfully to sros1
```

### ⚠️ Auto-Fix Messages

```
WARNING: Fixed JSON by removing trailing commas
INFO: Validated JSON config: {...}
```

### ❌ Error Messages (Now with Details!)

```
ERROR: Failed to parse config as JSON: Expecting ',' delimiter: line 11 column 4
ERROR: Config content (first 500 chars): {"key": "value"...
ERROR: Error near line 11: "another_key": "value"
```

## 🔧 Files Changed

| Service | File | Purpose |
|---------|------|---------|
| All Services | `connectors/nokia_sros_connector.py` | Enhanced JSON handling |
| Admin Service | `services/remediation_service.py` | Pre-validation |
| Shared | `utils/validators.py` | JSON validation utility |
| Scripts | `validate_rule_configs.py` | Rule validator |

## 📚 Documentation

- **Detailed Guide**: [NOKIA_SROS_JSON_FIX.md](./NOKIA_SROS_JSON_FIX.md)
- **Full Summary**: [FIX_SUMMARY.md](./FIX_SUMMARY.md)
- **This Quick Guide**: [QUICK_FIX_GUIDE.md](./QUICK_FIX_GUIDE.md)

## 🧪 Test Results

All functionality tested and verified:

```
✅ Valid JSON parsing
✅ Trailing comma auto-fix
✅ Simple value handling
✅ Boolean/integer conversion
✅ Detailed error messages
✅ Backward compatibility
```

See `test_json_fix_standalone.py` for test details.

## ❓ Troubleshooting

### Remediation Still Failing?

1. **Check the specific error in logs**:
   ```bash
   docker-compose logs admin-service | grep -A 5 "Failed to parse"
   ```

2. **Validate the problematic rule**:
   ```bash
   python scripts/validate_rule_configs.py
   ```

3. **Check the reference_config field** in the database for the failing rule

### Rule Validation Script Issues?

Make sure you're in the workspace directory:
```bash
cd /workspace
python scripts/validate_rule_configs.py
```

### Still Getting JSON Errors?

The error message now shows:
- Exact line number of the error
- First 500 characters of the config
- The problematic line

Use this info to manually fix the rule's `reference_config` in the database or UI.

## 💡 Tips for Creating Rules

### ✅ Good JSON Configs

```json
{"admin-state": "enable"}
```

```json
{
  "admin-state": "enable",
  "description": "Main interface"
}
```

### ❌ Bad JSON Configs (Will Auto-Fix)

```json
{"admin-state": "enable",}  // Trailing comma - will be fixed
```

```json
{
  "admin-state": "enable",
  "description": "Main interface",  // Trailing comma - will be fixed
}
```

### ✅ Simple Values (Now Supported!)

```
enable
```

```
true
```

```
100
```

## 🎯 Key Improvements

1. **Better Errors**: Now shows exactly where JSON is invalid
2. **Auto-Fix**: Automatically fixes trailing commas
3. **More Types**: Supports strings, booleans, integers (not just JSON)
4. **Validation**: Pre-validates before sending to device
5. **Logging**: Detailed logging of all transformations

## 📞 Support

If issues persist:

1. Review logs: `docker-compose logs admin-service`
2. Run validation: `python scripts/validate_rule_configs.py`
3. Check documentation: `NOKIA_SROS_JSON_FIX.md`
4. Verify rule configs in database

## ✨ Summary

**Before:**
- Unclear JSON errors
- No auto-fix
- Only JSON objects supported
- Hard to diagnose issues

**After:**
- Clear error messages with line numbers
- Auto-fixes trailing commas
- Supports JSON, strings, booleans, integers
- Easy to diagnose and fix issues

---

**Status:** ✅ Ready for deployment
**Risk:** Low (backward compatible)
**Testing:** ✅ All tests pass
