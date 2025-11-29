# License Enforcement API Documentation

This document describes all API endpoints and features related to license enforcement and management.

## Table of Contents

- [Overview](#overview)
- [License Management Endpoints](#license-management-endpoints)
- [License Enforcement Middleware](#license-enforcement-middleware)
- [Admin License Control](#admin-license-control)
- [Module Access Management](#module-access-management)
- [Quota Enforcement](#quota-enforcement)
- [Frontend Integration](#frontend-integration)

---

## Overview

The license enforcement system provides comprehensive control over:

1. **Tier-based module availability** - Different license tiers unlock different features
2. **Admin-controlled module permissions** - Admins can grant/revoke module access per user group
3. **User creation limits** - Enforced at the license tier level
4. **Device limits with queue management** - Discovered devices are queued if quota exceeded
5. **Storage control** - Config backup storage is monitored and enforced
6. **License upgrade/renewal handling** - Seamless transitions when upgrading

---

## License Management Endpoints

### GET `/license/status`

Get current license status and usage information.

**Response:**
```json
{
  "valid": true,
  "tier": "professional",
  "tier_display": "Professional",
  "expires_at": "2026-01-01T00:00:00",
  "days_until_expiry": 365,
  "is_active": true,
  "quotas": {
    "devices": {
      "current": 25,
      "max": 100,
      "percentage": 25.0,
      "within_quota": true
    },
    "users": {
      "current": 5,
      "max": 10,
      "percentage": 50.0,
      "within_quota": true
    },
    "storage_gb": {
      "current": 12,
      "max": 50,
      "percentage": 24.0,
      "within_quota": true
    }
  },
  "enabled_modules": [
    "devices",
    "manual_audits",
    "scheduled_audits",
    "basic_rules",
    "rule_templates",
    "api_access",
    "config_backups",
    "drift_detection",
    "webhooks",
    "device_groups",
    "discovery"
  ],
  "module_details": [
    {
      "key": "devices",
      "name": "Device Management",
      "enabled": true
    }
  ],
  "customer_name": "ACME Corp",
  "activated_at": "2025-01-01T00:00:00",
  "last_validated": "2025-11-29T12:00:00"
}
```

### POST `/license/activate`

Activate a new license key.

**Request:**
```json
{
  "license_key": "encrypted_license_key_here"
}
```

**Response:**
```json
{
  "success": true,
  "message": "License activated successfully",
  "license_status": { /* Same as GET /license/status */ }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid license key
- `402 Payment Required` - License expired

### POST `/license/deactivate`

Deactivate the current license.

**Response:**
```json
{
  "success": true,
  "message": "Deactivated 1 license(s)"
}
```

### GET `/license/tiers`

Get all available license tiers with their features.

**Response:**
```json
{
  "tiers": [
    {
      "key": "starter",
      "name": "Starter",
      "max_devices": 10,
      "max_users": 2,
      "max_storage_gb": 5,
      "modules": [
        {
          "key": "devices",
          "name": "Device Management"
        },
        {
          "key": "manual_audits",
          "name": "Manual Audits"
        }
      ],
      "module_count": 4
    },
    {
      "key": "professional",
      "name": "Professional",
      "max_devices": 100,
      "max_users": 10,
      "max_storage_gb": 50,
      "modules": [ /* ... */ ],
      "module_count": 11
    },
    {
      "key": "enterprise",
      "name": "Enterprise",
      "max_devices": 999999,
      "max_users": 999999,
      "max_storage_gb": 999999,
      "modules": [ /* all modules */ ],
      "module_count": 20
    }
  ]
}
```

### GET `/license/check-module/{module_name}`

Check if current license has access to a specific module.

**Parameters:**
- `module_name` - Module key (e.g., "scheduled_audits")

**Response:**
```json
{
  "has_access": true,
  "module": "scheduled_audits",
  "module_display": "Scheduled Audits",
  "current_tier": "professional"
}
```

**Response (No Access):**
```json
{
  "has_access": false,
  "module": "ai_features",
  "module_display": "AI-Powered Features",
  "current_tier": "professional",
  "required_tier": "enterprise",
  "required_tier_display": "Enterprise",
  "message": "Module not available in professional tier"
}
```

### POST `/license/upgrade`

Handle license upgrade (called after activating a higher-tier license).

**Response:**
```json
{
  "success": true,
  "current_tier": "enterprise",
  "changes": [
    "Added modules: ai_features, topology, sso",
    "Max Devices: 100 → Unlimited",
    "Max Users: 10 → Unlimited",
    "Max Storage Gb: 50 → Unlimited"
  ],
  "message": "License successfully upgraded from professional to enterprise"
}
```

### POST `/license/renew`

Handle license renewal (refreshes validation timestamps).

**Response:**
```json
{
  "success": true,
  "message": "License renewed successfully"
}
```

---

## License Enforcement Middleware

### Module Access Enforcement

Endpoints can require specific modules using the `require_license_module` dependency:

```python
from shared.license_middleware import require_license_module

@router.get("/schedules")
async def get_schedules(
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("scheduled_audits"))
):
    """Get audit schedules (requires 'scheduled_audits' module)"""
    # ...
```

**Error Response (Module Not Available):**
```json
{
  "detail": {
    "error": "Module not available in license",
    "module": "scheduled_audits",
    "current_tier": "starter",
    "message": "Module 'scheduled_audits' is not available in starter tier",
    "action": "upgrade_license"
  }
}
```

**HTTP Status:** `403 Forbidden`

### Quota Enforcement

Endpoints can enforce quotas using the `enforce_quota` dependency:

```python
from shared.license_middleware import enforce_quota

@router.post("/devices")
async def create_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
    _quota: None = Depends(enforce_quota("devices", 1))
):
    """Create device (enforces device quota)"""
    # ...
```

**Error Response (Quota Exceeded):**
```json
{
  "detail": {
    "error": "Quota exceeded",
    "quota_type": "devices",
    "current": 100,
    "max": 100,
    "requested": 1,
    "message": "Cannot add 1 more devices. Current: 100/100",
    "action": "upgrade_license"
  }
}
```

**HTTP Status:** `403 Forbidden`

---

## Admin License Control

### GET `/admin/license/quotas`

Get current license quota status (admin only).

**Response:**
```json
{
  "devices": {
    "current": 25,
    "max": 100,
    "available_slots": 75,
    "within_quota": true
  },
  "users": {
    "current": 5,
    "max": 10,
    "within_quota": true
  },
  "storage": {
    "current_gb": 12,
    "max_gb": 50,
    "used_percentage": 24.0,
    "within_quota": true
  }
}
```

### GET `/admin/license/available-modules`

Get all modules available in the current license tier (admin only).

**Response:**
```json
[
  {
    "key": "devices",
    "name": "Device Management",
    "available": true
  },
  {
    "key": "scheduled_audits",
    "name": "Scheduled Audits",
    "available": true
  },
  {
    "key": "ai_features",
    "name": "AI-Powered Features",
    "available": false
  }
]
```

---

## Module Access Management

Admins can control which modules are accessible to specific user groups.

### GET `/admin/groups/{group_id}/module-access`

Get module access permissions for a user group.

**Response:**
```json
{
  "group_id": 1,
  "module_access": {
    "devices": true,
    "manual_audits": true,
    "scheduled_audits": false,
    "config_backups": true,
    "drift_detection": false
  }
}
```

### PUT `/admin/groups/{group_id}/module-access`

Set module access permissions for a user group.

**Request:**
```json
{
  "module_permissions": {
    "devices": true,
    "manual_audits": true,
    "scheduled_audits": true,
    "config_backups": true,
    "drift_detection": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Module access updated successfully",
  "group_id": 1,
  "module_permissions": { /* same as request */ }
}
```

**Error (Module Not in License):**
```json
{
  "detail": "Module 'ai_features' is not available in professional tier. Please upgrade license first."
}
```

**HTTP Status:** `400 Bad Request`

---

## Quota Enforcement

### User Creation

When creating users via `/user-management/users`, the system:

1. Checks current user count vs. license max
2. Rejects creation if quota exceeded
3. Updates license usage after successful creation

**Error Response:**
```json
{
  "detail": "Cannot create user: License limit reached (10/10). Please upgrade your license to add more users."
}
```

**HTTP Status:** `400 Bad Request`

### Device Creation

When creating devices via `/devices/`, the system:

1. Checks current device count vs. license max
2. Rejects creation if quota exceeded
3. Updates license usage after successful creation

**Error Response:**
```json
{
  "detail": {
    "error": "Quota exceeded",
    "quota_type": "devices",
    "current": 100,
    "max": 100,
    "message": "Cannot add 1 more devices. Current: 100/100",
    "action": "upgrade_license"
  }
}
```

**HTTP Status:** `403 Forbidden`

### Device Discovery with Queue Management

When discovering devices via `/devices/discover`, the system:

1. Discovers all devices in subnet
2. Checks available device slots
3. Accepts devices up to quota limit (FIFO)
4. Rejects excess devices with warning

**Response (Partial Success):**
```json
{
  "status": "partial",
  "discovered": 150,
  "added": 75,
  "rejected": 75,
  "message": "Device limit reached. Added 75 devices, rejected 75 devices. Upgrade license for more capacity.",
  "total_devices": 100
}
```

**Response (All Accepted):**
```json
{
  "status": "success",
  "discovered": 50,
  "added": 50,
  "rejected": 0,
  "message": "All 50 devices within quota",
  "total_devices": 75
}
```

### Storage Enforcement

When creating config backups, the system:

1. Calculates total storage usage
2. Checks if new backup would exceed quota
3. Attempts automatic cleanup of old backups if needed
4. Rejects backup creation if still over quota

**Error Response:**
```json
{
  "detail": "Cannot create backup: Storage quota exceeded. Current: 52 GB, Max: 50 GB. Backup size: 3 GB. Please upgrade your license for more storage."
}
```

**HTTP Status:** `400 Bad Request`

---

## Frontend Integration

### LicenseContext Hook

The frontend provides a `useLicense()` hook for accessing license information:

```javascript
import { useLicense } from '../contexts/LicenseContext';

function MyComponent() {
  const {
    license,
    loading,
    hasModule,
    isWithinQuota,
    getUsagePercentage,
    isLicenseValid,
    tier
  } = useLicense();

  // Check if module is available
  if (!hasModule('scheduled_audits')) {
    return <UpgradePrompt module="Scheduled Audits" />;
  }

  // Check quota status
  const deviceUsage = getUsagePercentage('devices');
  if (deviceUsage > 90) {
    // Show warning
  }

  // ...
}
```

### LicenseGuard Component

Wrap routes with `LicenseGuard` to enforce license requirements:

```javascript
<Route path="/schedules" element={
  <LicenseGuard module="scheduled_audits">
    <AuditSchedules />
  </LicenseGuard>
} />
```

### LicenseQuotaManager Component

Admin component for managing license quotas and module permissions:

```javascript
import LicenseQuotaManager from './components/LicenseQuotaManager';

// In admin routes
<Route path="/license-quotas" element={
  <LicenseGuard>
    <LicenseQuotaManager />
  </LicenseGuard>
} />
```

Features:
- Visual quota displays (devices, users, storage)
- Module access control per user group
- Real-time quota status
- Warning indicators

---

## License Tiers Comparison

| Feature | Starter | Professional | Enterprise |
|---------|---------|--------------|------------|
| Max Devices | 10 | 100 | Unlimited |
| Max Users | 2 | 10 | Unlimited |
| Max Storage | 5 GB | 50 GB | Unlimited |
| Devices | ✓ | ✓ | ✓ |
| Manual Audits | ✓ | ✓ | ✓ |
| Basic Rules | ✓ | ✓ | ✓ |
| Health Checks | ✓ | ✓ | ✓ |
| Scheduled Audits | ✗ | ✓ | ✓ |
| Rule Templates | ✗ | ✓ | ✓ |
| Config Backups | ✗ | ✓ | ✓ |
| Drift Detection | ✗ | ✓ | ✓ |
| Device Groups | ✗ | ✓ | ✓ |
| Discovery | ✗ | ✓ | ✓ |
| Webhooks | ✗ | ✓ | ✓ |
| API Access | ✗ | ✓ | ✓ |
| Workflow Automation | ✗ | ✗ | ✓ |
| Network Topology | ✗ | ✗ | ✓ |
| AI Features | ✗ | ✗ | ✓ |
| Advanced Integrations | ✗ | ✗ | ✓ |
| SSO & SAML | ✗ | ✗ | ✓ |

---

## Error Handling

### Common Error Codes

- `402 Payment Required` - No active license or license expired
- `403 Forbidden` - Module not available in license tier or quota exceeded
- `400 Bad Request` - Invalid license key or operation not allowed

### Error Response Format

All license-related errors follow this format:

```json
{
  "detail": {
    "error": "Error type",
    "message": "Human-readable message",
    "action": "Suggested action (activate_license, upgrade_license, contact_admin)",
    // Additional context-specific fields
  }
}
```

---

## Best Practices

1. **Always check license status** before performing quota-limited operations
2. **Use middleware** for automatic enforcement instead of manual checks
3. **Handle quota exceeded gracefully** with user-friendly messages
4. **Monitor storage usage** and implement cleanup strategies
5. **Log all license-related actions** for audit purposes
6. **Test license enforcement** in development before deployment
7. **Provide upgrade paths** when users hit limits

---

## Support

For license-related issues:

1. Check `/license/status` endpoint for detailed information
2. Review `/license/validation-logs` for activation history
3. Contact support with license key and error details
4. Provide quota status from `/admin/license/quotas`

---

## Changelog

### Version 1.0.0 (2025-11-29)

- Initial implementation of comprehensive license enforcement
- Tier-based module availability
- Admin-controlled module permissions
- User and device quota enforcement
- Storage control for config backups
- License upgrade/renewal handling
- Frontend integration with LicenseContext
- Admin dashboard for quota management
