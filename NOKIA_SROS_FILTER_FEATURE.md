# Nokia SROS Filter Feature - Documentation

## Overview

Added support for pySROS filter parameter in audit rules to narrow down configuration queries. This allows you to retrieve specific configuration elements instead of the entire configuration tree, making audits more efficient.

## What This Feature Does

When creating audit rules for Nokia SROS devices, you can now specify a **filter** dictionary that gets passed to the pySROS `get()` function. This filter tells the device to return only the configuration elements you're interested in, with the structure you specify.

### Example Use Case

Instead of retrieving all VPRN services and then parsing through them, you can filter to get only:
- Service names
- Admin states  
- Specific interfaces

## How It Works

### Backend Flow

1. **Rule Model** (`models/rule.py`)
   - Added `filter: Optional[dict] = None` field to `RuleCheck` class
   - Filter is stored as a JSON dictionary

2. **Rule Executor** (`engine/rule_executor.py`)
   - Checks if `check.filter` is provided and not empty
   - Passes filter to Nokia connector's `get_config()` method

3. **Nokia Connector** (`connectors/nokia_sros_connector.py`)
   - Updated `get_config()` method to accept `filter` parameter
   - Only uses filter if it's provided and not empty (`if filter and len(filter) > 0`)
   - Calls `connection.running.get(path, filter=filter)` when filter is present

### Frontend Implementation

**Location**: `/workspace/frontend/src/components/RuleManagement.jsx`

**Features**:
- New input field: "Filter (Nokia - JSON format)"
- Accepts JSON dictionary format
- Validates JSON before saving
- Converts between JSON string (UI) and dict (API)

## Usage Guide

### Creating a Rule with Filter

1. **Navigate to Rules Management**
   - Go to "Rule Management" in the sidebar

2. **Create/Edit a Rule**
   - Click "Add New Rule" or edit existing rule
   - Select Nokia SROS as vendor

3. **Add a Check with Filter**
   - Enter check name
   - Enter XPath (e.g., `/nokia-conf:configure/service/vprn`)
   - Enter Filter in JSON format

### Filter Format Examples

#### Example 1: Filter VPRN Services
Get only service names, admin states, and interface names:

```json
{
  "service-name": "\"",
  "admin-state": {},
  "interface": {
    "interface-name": {}
  }
}
```

**Explanation**:
- `"service-name": "\""` - Get the service-name leaf (value with empty string as placeholder)
- `"admin-state": {}` - Get admin-state leaf (empty dict means get this leaf)
- `"interface": {"interface-name": {}}` - Get interface container with interface-name leaf

#### Example 2: Filter BGP Configuration
Get only BGP groups and their admin states:

```json
{
  "group": {
    "group-name": "\"",
    "admin-state": {}
  }
}
```

#### Example 3: Filter Specific Service by ID
Get configuration for a specific service ID:

```json
{
  "service-id": "100"
}
```

### Filter Syntax Rules

1. **Leaf with value placeholder**: Use `"\"` (empty string in JSON)
   ```json
   "leaf-name": "\""
   ```

2. **Leaf without specific value**: Use empty dict `{}`
   ```json
   "leaf-name": {}
   ```

3. **Container with nested elements**: Nested dict structure
   ```json
   "container": {
     "nested-leaf": {}
   }
   ```

4. **List items**: Specify the list key
   ```json
   "list-name": {
     "key-value": {
       "nested-element": {}
     }
   }
   ```

### Frontend JSON Input

When entering the filter in the UI:

1. **Use proper JSON format**
   - Double quotes for keys and string values
   - Escape quotes in values: `"\"`
   - Valid: `{"name": "\""}`
   - Invalid: `{name: ''}` or `{'name': ''}`

2. **Validation**
   - Frontend validates JSON before saving
   - Shows error message if JSON is invalid
   - Example error: "Invalid JSON format for filter. Please check your syntax."

3. **Empty Filter**
   - Leave field empty to not use filtering
   - Backend will call `get()` without filter parameter
   - Retrieves entire configuration tree

## Technical Details

### Backend Changes

#### 1. Model Definition (`models/rule.py`)
```python
class RuleCheck(BaseModel):
    name: Optional[str] = "Check"
    filter_xml: Optional[str] = None  # For Cisco XR
    xpath: Optional[str] = None
    filter: Optional[dict] = None  # NEW: For Nokia SROS
    comparison: Optional[ComparisonType] = None
    reference_value: Optional[str] = None
    reference_config: Optional[str] = None
    # ...
```

#### 2. Rule Executor (`engine/rule_executor.py`)
```python
elif device.vendor == VendorType.NOKIA_SROS and check.xpath:
    # Nokia SROS uses XPath
    # If filter is provided, use it to narrow down the query
    if check.filter:
        config_data = await connector.get_config(xpath=check.xpath, filter=check.filter)
    else:
        config_data = await connector.get_config(xpath=check.xpath)
```

#### 3. Nokia Connector (`connectors/nokia_sros_connector.py`)
```python
async def get_config(
    self, 
    source: str = 'running', 
    filter_data: Optional[str] = None, 
    xpath: Optional[str] = None, 
    filter: Optional[dict] = None  # NEW parameter
) -> str:
    # ...
    # Use filter if provided and not empty
    if filter and len(filter) > 0:
        logger.debug(f"Getting config with filter: {filter}")
        result = await loop.run_in_executor(
            None,
            lambda: self.connection.running.get(path, filter=filter)
        )
    else:
        logger.debug(f"Getting config without filter")
        result = await loop.run_in_executor(
            None,
            lambda: self.connection.running.get(path)
        )
```

### Frontend Changes

#### 1. Form State
```javascript
const [checkForm, setCheckForm] = useState({
  name: '',
  filter_xml: '',    // Cisco
  xpath: '',         // Nokia path
  filter: '',        // NEW: Nokia filter (JSON string)
  reference_value: '',
  reference_config: '',
});
```

#### 2. JSON Parsing on Save
```javascript
const handleAddCheck = () => {
  // Parse filter JSON if it's provided
  let parsedFilter = null;
  if (checkForm.filter && checkForm.filter.trim()) {
    try {
      parsedFilter = JSON.parse(checkForm.filter);
    } catch (e) {
      setError('Invalid JSON format for filter. Please check your syntax.');
      return;
    }
  }

  const checkData = {
    // ...
    filter: parsedFilter,  // Stored as object, not string
    // ...
  };
};
```

#### 3. JSON Formatting on Edit
```javascript
const handleEditCheck = (index) => {
  const check = formData.checks[index];
  setCheckForm({
    // ...
    filter: typeof check.filter === 'object' 
      ? JSON.stringify(check.filter, null, 2)  // Pretty-print for editing
      : (check.filter || ''),
    // ...
  });
};
```

## Testing

### Test Case 1: Filter with XPath

**Rule Setup**:
- Vendor: Nokia SROS
- XPath: `/nokia-conf:configure/service/vprn`
- Filter:
  ```json
  {
    "service-name": "\"",
    "admin-state": {}
  }
  ```
- Reference Config: Expected service configuration

**Expected Result**:
- Audit retrieves only service names and admin states
- Faster than retrieving full VPRN configuration
- Comparison works against reference config

### Test Case 2: No Filter (Full Config)

**Rule Setup**:
- Vendor: Nokia SROS
- XPath: `/nokia-conf:configure/service/vprn`
- Filter: (empty)
- Reference Config: Expected configuration

**Expected Result**:
- Audit retrieves full VPRN configuration
- Behaves like before this feature
- No filter parameter passed to pySROS

### Test Case 3: Invalid JSON

**Rule Setup**:
- Try to save a check with invalid JSON in filter field
- Example: `{name: 'value'}` (missing quotes)

**Expected Result**:
- Frontend shows error: "Invalid JSON format for filter. Please check your syntax."
- Check is not saved
- User can correct the JSON

## Database Schema

No database migration required! The `checks` column in `audit_rules` table is already JSON, so it automatically supports the new `filter` field:

```python
checks = Column(JSON, nullable=False)  # List of RuleCheck dictionaries
```

Example stored check:
```json
{
  "name": "VPRN Service Check",
  "xpath": "/nokia-conf:configure/service/vprn",
  "filter": {
    "service-name": "\"",
    "admin-state": {}
  },
  "reference_config": "...",
  "comparison": "exact"
}
```

## Benefits

1. **Performance**: 
   - Retrieve only needed config elements
   - Faster queries, especially for large configurations
   - Less data to transfer from device

2. **Precision**:
   - Focus audit on specific configuration aspects
   - Avoid parsing unnecessary data
   - More targeted compliance checks

3. **Flexibility**:
   - Optional feature - can still use full config
   - Works alongside existing XPath queries
   - Compatible with all comparison types

4. **Backward Compatible**:
   - Existing rules without filters work unchanged
   - Empty filter = no filter applied
   - Database schema unchanged

## Troubleshooting

### Issue: Filter not working
**Check**:
1. Verify filter is valid JSON
2. Check filter syntax matches pySROS expectations
3. Verify XPath is correct
4. Check device logs for pySROS errors

### Issue: JSON validation error
**Solution**:
- Use double quotes for all keys and values
- Escape special characters properly
- Test JSON in online validator first
- Example: Use `"\""` not `''` or `""`

### Issue: Empty results
**Possible causes**:
1. Filter too restrictive - no matching elements
2. XPath doesn't exist in device config
3. Wrong filter syntax for the config structure

### Issue: Error parsing config
**Check**:
- Ensure filter returns valid structure
- Verify reference config matches filtered structure
- Check comparison type is appropriate for filtered data

## Examples by Use Case

### Use Case: Audit VPRN Interface Configuration

```json
{
  "service-name": "\"",
  "interface": {
    "interface-name": "\"",
    "admin-state": {},
    "ipv4": {
      "primary": {
        "address": "\"",
        "prefix-length": {}
      }
    }
  }
}
```

### Use Case: Audit BGP Neighbor Status

```json
{
  "group": {
    "group-name": "\"",
    "neighbor": {
      "ip-address": "\"",
      "admin-state": {}
    }
  }
}
```

### Use Case: Audit System NTP Configuration

```json
{
  "server": {
    "ip-address": "\"",
    "prefer": {}
  }
}
```

## Related Documentation

- pySROS documentation: https://network.developer.nokia.com/static/sr/learn/pysros/latest/
- Nokia YANG models: https://github.com/nokia/7x50_YangModels
- Rule Management: `/workspace/frontend/src/components/RuleManagement.jsx`
- Audit Engine: `/workspace/engine/audit_engine.py`

---

**Feature Added**: 2025-11-29  
**Status**: Complete and Tested ✅
