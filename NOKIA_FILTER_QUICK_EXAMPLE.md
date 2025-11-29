# Nokia SROS Filter - Quick Example

## What's New?

You can now add a **filter** to Nokia SROS audit rules to retrieve only specific configuration elements.

## Quick Example

### Scenario: Audit VPRN Services

**Without Filter (Old Way)**:
- Retrieves entire VPRN configuration
- Lots of unnecessary data
- Slower query

**With Filter (New Way)**:
- Retrieves only what you need
- Faster and more efficient
- Less data to parse

### How to Use

1. **Go to Rule Management** → Add New Rule

2. **Fill in Rule Details**:
   - Name: `Check VPRN Admin State`
   - Vendor: `Nokia SROS`
   - Add Check

3. **In the Check Form**:
   - **Check Name**: `VPRN Service Check`
   - **XPath**: `/nokia-conf:configure/service/vprn`
   - **Filter** (NEW!):
     ```json
     {
       "service-name": "\"",
       "admin-state": {},
       "interface": {
         "interface-name": {}
       }
     }
     ```
   - **Reference Config**: Your expected configuration

4. **Save** → Run Audit

### What the Filter Does

The filter tells pySROS: "Give me only these elements":
- `service-name` - The name of each VPRN
- `admin-state` - The admin state
- `interface.interface-name` - Names of interfaces in each VPRN

**Instead of getting**:
```json
{
  "service": {
    "vprn": {
      "service-name": "VPRN-100",
      "admin-state": "enable",
      "service-id": 100,
      "customer": "1",
      "autonomous-system": 65000,
      "interface": {
        "interface-name": "to-PE2",
        "ipv4": {...},
        "ipv6": {...},
        ... lots more ...
      },
      ... lots more ...
    }
  }
}
```

**You get**:
```json
{
  "service": {
    "vprn": {
      "service-name": "VPRN-100",
      "admin-state": "enable",
      "interface": {
        "interface-name": "to-PE2"
      }
    }
  }
}
```

## Filter Syntax Cheat Sheet

| What You Want | Filter Syntax | Example |
|---------------|---------------|---------|
| Get a leaf value | `"leaf": "\""` | `"service-name": "\""` |
| Get a leaf (any value) | `"leaf": {}` | `"admin-state": {}` |
| Get nested elements | `"container": {"leaf": {}}` | `"interface": {"interface-name": {}}` |

## Common Filters

### 1. Service Names Only
```json
{
  "service-name": "\""
}
```

### 2. Admin States
```json
{
  "admin-state": {}
}
```

### 3. Interface Names in a Service
```json
{
  "interface": {
    "interface-name": "\""
  }
}
```

### 4. Multiple Fields
```json
{
  "service-name": "\"",
  "admin-state": {},
  "description": "\""
}
```

## When to Use Filter

✅ **Use Filter When**:
- You only need specific configuration fields
- Configuration tree is large
- You want faster audits
- You're checking specific compliance points

❌ **Don't Use Filter When**:
- You need full configuration
- Configuration is already small
- You're not sure what you need
- You're doing drift detection (need full config)

## Tips

1. **Leave Empty for Full Config**: If you don't enter anything in the filter field, it works like before (gets full config)

2. **Test Your Filter**: Start with a simple filter and add more fields as needed

3. **JSON Validation**: The UI checks your JSON is valid before saving

4. **Check Logs**: Backend logs show whether filter is being used

## Need Help?

See full documentation: `NOKIA_SROS_FILTER_FEATURE.md`

---

**Quick Reference**: Just add JSON in the "Filter" field when creating Nokia SROS rules!
