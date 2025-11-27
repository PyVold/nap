# pySROS Serialization Fix for Config Push

## Problem
When applying remediation fixes from the audit results page, the Nokia SROS connector was failing with the error:
```
MO contents not a dict '{...}'
```

The issue was that pySROS expects configuration values to be Python dictionaries, but the connector was receiving JSON strings and failing to deserialize them properly before passing them to pySROS.

## Root Cause
In the `edit_config()` method of `nokia_sros_connector.py`, the JSON deserialization logic had several issues:

1. **Incomplete type checking**: Didn't check if `config_data` was already a dict
2. **Silent failure**: When JSON parsing failed, it silently fell back to using the string value
3. **AttributeError risk**: Calling `.strip()` on a dict would raise an uncaught `AttributeError`
4. **Poor error messages**: No clear indication of what went wrong

## Solution
Updated the JSON deserialization logic in both:
- `/workspace/connectors/nokia_sros_connector.py`
- `/workspace/services/admin-service/app/connectors/nokia_sros_connector.py`

### New Logic Flow
```python
# Check if config_data is already a dict
if isinstance(config_data, dict):
    # Use it directly
    config_value = config_data
    
elif isinstance(config_data, str):
    # Try to deserialize if it's a JSON string
    if config_data.strip().startswith('{') or config_data.strip().startswith('['):
        config_value = json.loads(config_data)
    else:
        # Not JSON format - raise clear error
        raise ValueError("Config must be a dict or JSON string for xpath mode")
        
else:
    # Unexpected type - raise clear error
    raise ValueError(f"Config must be dict or JSON string, got: {type(config_data)}")
```

### Key Improvements
1. ✅ Handles both dict and string inputs properly
2. ✅ Raises clear errors instead of silently failing
3. ✅ Properly deserializes JSON strings to dicts for pySROS
4. ✅ Prevents AttributeError on dict inputs
5. ✅ Better logging for debugging

## Testing
Created and ran verification tests to ensure:
- ✅ Dict inputs are used directly
- ✅ JSON string inputs are deserialized correctly
- ✅ Malformed JSON raises appropriate errors
- ✅ Non-JSON strings raise appropriate errors

All tests passed successfully.

## Next Steps
To apply this fix, you need to rebuild/restart the admin-service container:

```bash
# Option 1: Restart the admin-service container
docker-compose restart admin-service

# Option 2: Rebuild if using volumes
docker-compose up -d --build admin-service

# Option 3: Full restart (if needed)
docker-compose down
docker-compose up -d
```

After restarting the service, try applying the audit fix again from the audit results page.

## Expected Behavior After Fix
When you click "Apply Fix" on an audit discrepancy:

1. The remediation service will retrieve the `reference_config` from the audit finding
2. This config (either JSON string or dict) will be passed to the Nokia connector
3. The connector will properly deserialize it into a Python dict
4. pySROS will receive the dict and apply the configuration successfully
5. The configuration will be committed to the device

You should see logs like:
```
admin-service_1 | Config is already a dict, using directly
OR
admin-service_1 | Deserialized JSON config to: {...}
admin-service_1 | Setting /configure/system/management-interface = {...}
admin-service_1 | Committing configuration on sros1
admin-service_1 | Configuration applied successfully to sros1
```

## Files Modified
- `/workspace/connectors/nokia_sros_connector.py` (lines 231-258)
- `/workspace/services/admin-service/app/connectors/nokia_sros_connector.py` (lines 231-258)
