# Audit Rule Filter Field Fix Summary

## Issue
When adding a filter to an audit rule in the frontend, the filter was not being saved to the database. The filter field was collected in the frontend but was silently dropped by the backend, so it was not used during audit execution.

## Root Cause
The `filter` field was missing from the `RuleCheck` Pydantic model in the rule-service, even though:
1. The frontend was collecting and sending it
2. The database (JSON column) could store it
3. The Nokia SROS connector was ready to use it
4. The root models already had it defined

## Files Modified

### 1. `/workspace/services/rule-service/app/models/rule.py`
**Change**: Added `filter` field to `RuleCheck` model
```python
class RuleCheck(BaseModel):
    name: Optional[str] = "Check"
    filter_xml: Optional[str] = None
    xpath: Optional[str] = None
    filter: Optional[dict] = None  # Nokia SROS filter dict - ADDED
    comparison: Optional[ComparisonType] = None
    reference_value: Optional[str] = None
    reference_config: Optional[str] = None
    error_message: Optional[str] = "Check failed"
    success_message: Optional[str] = "Check passed"
```

### 2. `/workspace/services/rule-service/app/engine/rule_executor.py`
**Change**: Updated to pass the filter parameter to the Nokia SROS connector
```python
elif device.vendor == VendorType.NOKIA_SROS and check.xpath:
    # Nokia SROS uses XPath and returns configuration (not operational state)
    # If filter is provided, use it to narrow down the query
    if check.filter:
        config_data = await connector.get_config(xpath=check.xpath, filter=check.filter)
    else:
        config_data = await connector.get_config(xpath=check.xpath)
```

### 3. `/workspace/services/rule-service/app/connectors/nokia_sros_connector.py`
**Change**: Added `filter` parameter to `get_config()` method signature and implementation
```python
async def get_config(self, source: str = 'running', filter_data: Optional[str] = None, 
                     xpath: Optional[str] = None, filter: Optional[dict] = None) -> str:
    # ...
    if filter and len(filter) > 0:
        logger.debug(f"Getting config from {self.device.hostname} using pysros path: {path} with filter: {filter}")
        result = await loop.run_in_executor(
            None,
            lambda: self.connection.running.get(path, filter=filter)
        )
    else:
        logger.debug(f"Getting config from {self.device.hostname} using pysros path: {path}")
        result = await loop.run_in_executor(
            None,
            lambda: self.connection.running.get(path)
        )
```

## What Was Already Working
- `/workspace/models/rule.py` - Root model already had the filter field
- `/workspace/engine/rule_executor.py` - Root executor already used the filter
- `/workspace/connectors/nokia_sros_connector.py` - Root connector already supported filter
- Frontend (`/workspace/frontend/src/components/RuleManagement.jsx`) - Already collecting filter input

## How the Filter Works

### Frontend (RuleManagement.jsx)
1. User enters filter in JSON format (e.g., `{"service-name": "\"", "admin-state": {}}`)
2. On "Add Check", the JSON is parsed and added to the check object
3. When saving the rule, the entire rule including checks with filters is sent to the backend

### Backend Flow
1. **API Layer** (`rules.py`): Receives the rule with checks
2. **Service Layer** (`rule_service.py`): Validates and stores the rule in database (JSON column)
3. **Audit Execution** (`rule_executor.py`): 
   - Retrieves rule from database
   - For Nokia SROS devices with filter defined:
     - Passes `xpath` and `filter` to connector
4. **Connector** (`nokia_sros_connector.py`):
   - Uses pysros `connection.running.get(path, filter=filter)`
   - Filter narrows down the configuration query

### Example Filter Usage
For Nokia SROS services, a filter like:
```json
{
  "service-name": "\"",
  "admin-state": {},
  "interface": {
    "interface-name": {}
  }
}
```

This tells pysros to only return service instances with their service-name, admin-state, and interface details, significantly reducing the amount of data retrieved and improving audit performance.

## Testing Recommendations

1. **Create a new rule** with a Nokia SROS check that includes a filter
2. **Save the rule** and verify it's stored in the database with the filter intact
3. **Run an audit** with this rule on a Nokia SROS device
4. **Check logs** to confirm the filter is being passed to the connector
5. **Verify results** show only the filtered configuration data

## Impact
- **Positive**: Filters will now be saved and used during audits
- **Performance**: Nokia SROS audits with filters will be much faster (less data retrieved)
- **Backward Compatible**: Existing rules without filters continue to work
- **No Database Migration**: Filter field was always storable in JSON column

## Status
✅ **FIXED** - All necessary changes have been applied to the rule-service microservice.

The filter field will now be:
1. ✅ Collected in the frontend
2. ✅ Accepted by the backend API
3. ✅ Stored in the database
4. ✅ Used during audit execution
5. ✅ Passed to the Nokia SROS connector
