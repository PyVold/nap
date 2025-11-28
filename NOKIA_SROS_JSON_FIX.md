# Nokia SROS JSON Configuration Error Fix

## Problem

The remediation service was failing when trying to apply configuration changes to Nokia SROS devices with the following error:

```
Failed to parse config as JSON: Expecting ',' delimiter: line 11 column 4 (char 176)
Invalid JSON config for xpath mode: Expecting ',' delimiter: line 11 column 4 (char 176)
```

This occurred when:
1. An audit identified a configuration discrepancy
2. User attempted to apply remediation 
3. The Nokia SROS connector received malformed JSON in the `reference_config` field

## Root Causes

1. **Malformed JSON in Reference Configs**: Some audit rules had `reference_config` values with invalid JSON syntax (e.g., trailing commas)
2. **Insufficient Error Handling**: The Nokia connector didn't provide detailed error information when JSON parsing failed
3. **No Pre-validation**: The remediation service didn't validate JSON before sending to the connector
4. **Limited Type Support**: The connector only handled JSON objects/arrays, not simple string/number/boolean values

## Solutions Implemented

### 1. Enhanced Nokia SROS Connector JSON Parsing

**Files Updated:**
- `/workspace/services/admin-service/app/connectors/nokia_sros_connector.py`
- `/workspace/services/backup-service/app/connectors/nokia_sros_connector.py`

**Improvements:**
- Added detailed logging of config type, length, and content
- Enhanced error messages showing exact line where JSON parsing fails
- Support for simple string/number/boolean values (not just JSON objects)
- Automatic type inference for simple values
- Better handling of dict objects passed directly (not just strings)

```python
# Now supports:
config = {"admin-state": "enable"}  # Dict
config = '{"admin-state": "enable"}'  # JSON string
config = "enable"  # Simple string
config = "true"  # Boolean (converted)
config = "100"  # Integer (converted)
```

### 2. Added JSON Validation Utility

**File Created:**
- `/workspace/utils/validators.py` - Added `validate_and_fix_json()` function

**Features:**
- Validates JSON syntax
- Auto-fixes common issues:
  - Trailing commas before closing braces/brackets
  - Multi-line trailing comma issues
- Returns parsed data or error details
- Can be used throughout the application

### 3. Pre-validation in Remediation Service

**File Updated:**
- `/workspace/services/admin-service/app/services/remediation_service.py`

**Improvements:**
- Pre-validates JSON configs before sending to connector
- Uses shared `validate_and_fix_json()` utility
- Attempts to auto-fix common JSON errors
- Provides detailed error logging with first 500 chars of problematic config

### 4. Improved JSON Serialization from pySROS

**File Updated:**
- `/workspace/services/admin-service/app/connectors/nokia_sros_connector.py`

**Improvements:**
- Better error handling when converting pySROS objects to JSON
- Validates serialization before returning
- Falls back to non-indented JSON if indented version fails

### 5. Rule Validation Script

**File Created:**
- `/workspace/scripts/validate_rule_configs.py`

**Purpose:**
- Scans all audit rules in database for malformed JSON in `reference_config`
- Can optionally auto-fix and update the rules
- Provides detailed report of issues found

**Usage:**
```bash
# Check for issues (read-only)
python scripts/validate_rule_configs.py

# Fix issues automatically
python scripts/validate_rule_configs.py --fix
```

## Testing the Fix

### 1. Test with Existing Rules

```bash
# Validate existing rule configs
cd /workspace
python scripts/validate_rule_configs.py

# Fix any issues found
python scripts/validate_rule_configs.py --fix
```

### 2. Test Remediation Flow

1. Run an audit that will generate findings
2. Attempt to apply remediation
3. Check logs for improved error messages:
   - Should show config type and content
   - Should show exact line number of JSON errors
   - Should indicate if auto-fix was attempted

### 3. Monitor Logs

The following log messages indicate the fix is working:

```
✅ Success indicators:
- "Validated JSON config: {...}"
- "Config is a simple string value, will use directly"
- "Converted to boolean/integer: ..."

⚠️  Auto-fix indicators:
- "Fixed JSON by removing trailing commas"

❌ Error indicators (with detailed info):
- "Failed to parse config as JSON: ..."
- "Config content (first 500 chars): ..."
- "Error near line X: ..."
```

## Prevention Measures

### For Future Rule Creation

1. **Validate JSON Before Saving**: When creating rules via API/UI, validate the `reference_config` field
2. **Use JSON Editor**: Consider adding a JSON editor in the UI with syntax highlighting
3. **Template Validation**: Validate rule templates before they're used

### For Developers

1. Use the `validate_and_fix_json()` utility when working with JSON configs
2. Always test rules with `dry_run=True` before applying
3. Check the validation script output regularly

## Files Modified

### Core Fixes
1. `/workspace/services/admin-service/app/connectors/nokia_sros_connector.py`
2. `/workspace/services/backup-service/app/connectors/nokia_sros_connector.py`
3. `/workspace/services/admin-service/app/services/remediation_service.py`
4. `/workspace/utils/validators.py`

### Utilities
5. `/workspace/scripts/validate_rule_configs.py` (new)

### Documentation
6. `/workspace/NOKIA_SROS_JSON_FIX.md` (this file)

## Related Issues

This fix addresses issues with:
- Rule execution failing due to malformed reference configs
- Lack of visibility into JSON parsing errors
- No way to diagnose or fix existing malformed configs
- Limited support for simple value types in remediation

## Next Steps

1. **Run the validation script** to identify and fix existing issues
2. **Test remediation** with the improved error handling
3. **Monitor logs** for any remaining JSON-related errors
4. **Consider UI improvements** for rule config editing
5. **Add validation** to rule creation/update endpoints

## Technical Details

### JSON Parsing Flow

```
Rule Finding (reference_config)
    ↓
Remediation Service
    ↓ (validates & auto-fixes)
validate_and_fix_json()
    ↓ (if valid or fixed)
Nokia SROS Connector
    ↓ (parses & applies)
pySROS candidate.set()
    ↓
Device Configuration
```

### Error Handling Hierarchy

1. **Prevention**: Validate when rules are created
2. **Detection**: Pre-validate in remediation service
3. **Auto-fix**: Attempt to fix common issues
4. **Reporting**: Detailed error logs with context
5. **Recovery**: Discard candidate config on failure

### Supported Config Formats

| Format | Example | Supported |
|--------|---------|-----------|
| JSON Object | `{"key": "value"}` | ✅ |
| JSON Array | `["item1", "item2"]` | ✅ |
| Simple String | `"enable"` | ✅ |
| Boolean | `"true"` or `"false"` | ✅ (auto-converted) |
| Integer | `"100"` | ✅ (auto-converted) |
| Dict Object | `{"key": "value"}` (as dict) | ✅ |

## Rollback Plan

If issues persist:

1. The changes are backward-compatible
2. Old behavior can be restored by removing auto-fix logic
3. Validation can be disabled by setting `auto_fix=False`
4. Original error messages are still logged

## Support

For issues related to this fix:
1. Check logs for detailed error messages
2. Run validation script: `python scripts/validate_rule_configs.py`
3. Review specific rule's `reference_config` field
4. Test with `dry_run=True` first
