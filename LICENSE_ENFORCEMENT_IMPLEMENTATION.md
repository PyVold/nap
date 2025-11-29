# License Enforcement System - Complete Implementation

## Overview

This document describes the comprehensive license enforcement system implemented across the entire application stack (database, backend, API gateway, and frontend).

## License Tiers

### Starter Tier
- **Max Devices**: 10
- **Max Users**: 2
- **Max Storage**: 5 GB
- **Modules**:
  - Device Management
  - Manual Audits
  - Basic Audit Rules
  - Health Monitoring

### Professional Tier
- **Max Devices**: 100
- **Max Users**: 10
- **Max Storage**: 50 GB
- **Modules**:
  - All Starter modules, plus:
  - Device Groups
  - Device Import
  - Device Discovery
  - Scheduled Audits
  - Rule Templates
  - Configuration Backups
  - Drift Detection
  - Webhook Notifications
  - Hardware Inventory
  - API Access

### Enterprise Tier
- **Max Devices**: Unlimited (999,999)
- **Max Users**: Unlimited (999,999)
- **Max Storage**: Unlimited (999,999 GB)
- **Modules**: ALL modules
  - All Professional modules, plus:
  - Workflow Automation
  - Advanced Integrations
  - Analytics & Reporting
  - Remediation Tasks
  - SSO & SAML Authentication
  - Network Topology Maps
  - AI-Powered Features

## Enforcement Layers

### 1. Database Layer (`db_models.py`)

**LicenseDB Model** stores:
- Customer information
- License key (encrypted)
- License tier
- Activation status
- Validity period
- Quotas (max_devices, max_users, max_storage_gb)
- Enabled modules (JSON array)
- Current usage tracking

**Related Tables**:
- `UserDB` - User accounts
- `DeviceDB` - Network devices
- `ConfigBackupDB` - Configuration backups (for storage calculation)
- `GroupModuleAccessDB` - Per-group module access permissions

### 2. Backend License Management (`shared/license_manager.py`)

**LicenseManager Class**:
- `validate_license(license_key)` - Validates and decrypts license keys
- `has_module(license_data, module_name)` - Checks if module is in license
- `check_quota(license_data, quota_type, current_value)` - Validates quota limits
- `get_tier_info(tier)` - Returns tier configuration
- `get_tier_modules(tier)` - Returns available modules for tier

**Features**:
- Fernet encryption for license keys
- SHA256 signature verification to prevent tampering
- Expiration date checking
- Module mapping between backend names and frontend names

### 3. Backend License Middleware (`shared/license_middleware.py`)

**LicenseEnforcer Class**:
- `get_active_license_data(db)` - Retrieves and validates active license
- `check_module_access(db, module_name, user_id)` - Checks license + user permissions
- `check_quota(db, quota_type, requested_amount)` - Validates quota before action
- `update_license_usage(db)` - Updates current usage statistics

**FastAPI Dependencies**:
- `require_license_module(module_name)` - Dependency for module-level enforcement
- `enforce_quota(quota_type, amount)` - Dependency for quota enforcement

**Enforces**:
- ✅ Module access based on license tier
- ✅ User-specific module permissions (group-based)
- ✅ Device quota limits
- ✅ User quota limits
- ✅ Storage quota limits

### 4. License Enforcement Service (`services/license_enforcement_service.py`)

**LicenseEnforcementService Class**:

**Module Management**:
- `set_group_module_access(db, group_id, module_permissions)` - Admin sets group access
- `get_available_modules_for_license(db)` - Returns all licensed modules
- `get_group_module_access(db, group_id)` - Gets group's module permissions

**Device Enforcement**:
- `check_can_add_devices(db, count)` - Checks device quota
- `enforce_device_limit_on_discovery(db, discovered_devices)` - FIFO queue for discovery

**User Enforcement**:
- `check_can_create_user(db)` - Checks user quota
- `enforce_user_creation_limit(db)` - Raises exception if limit reached

**Storage Enforcement**:
- `check_storage_quota(db, additional_gb)` - Checks storage quota
- `enforce_storage_limit(db, backup_size_bytes)` - Validates before backup
- `cleanup_old_backups_if_needed(db)` - Auto-cleanup when quota exceeded

**Upgrade/Renewal**:
- `handle_license_upgrade(db, old_tier, new_tier)` - Manages tier transitions
- `handle_license_renewal(db)` - Updates validation timestamp

### 5. API Gateway License Enforcement (`services/api-gateway/app/license_middleware.py`)

**LicenseGatewayMiddleware Class**:
- `get_required_module_for_path(path)` - Maps API paths to required modules
- `check_license_for_request(path)` - Validates license before proxying request

**Module to Route Mapping**:
```python
"devices": ["/devices", "/device-groups", "/device-import", "/health"]
"manual_audits": ["/audit"]
"scheduled_audits": ["/audit-schedules"]
"basic_rules": ["/rules"]
"rule_templates": ["/rule-templates"]
"config_backups": ["/config-backups"]
"drift_detection": ["/drift-detection"]
"webhooks": ["/notifications"]
"hardware_inventory": ["/hardware-inventory", "/hardware"]
"integrations": ["/integrations"]
"workflow_automation": ["/workflows"]
"analytics": ["/analytics"]
"remediation": ["/remediation"]
```

**Public Paths** (no license required):
- `/`, `/health`, `/api/services`
- `/login`, `/me`, `/license`
- `/admin`, `/user-management` (authenticated only)

**Enforcement**:
- ✅ Blocks API calls to modules not in license
- ✅ Returns 402 for missing license
- ✅ Returns 403 for module not in tier
- ✅ Integrated into `proxy_request()` handler

### 6. Backend API Routes

**License-Enforced Routes**:

**Devices** (`api/routes/devices.py`):
- `GET /devices` - requires "devices" module
- `POST /devices` - requires "devices" module + device quota check
- `POST /devices/discover` - requires "discovery" module + device quota

**Audits** (`api/routes/audits.py`):
- `POST /audit` - requires "manual_audits" module

**Audit Schedules** (`api/routes/audit_schedules.py`):
- `GET /audit-schedules` - requires "scheduled_audits" module
- `POST /audit-schedules` - requires "scheduled_audits" module

**Users** (`api/routes/user_management.py`):
- `POST /users` - enforces user quota limit
- `DELETE /users` - updates license usage

**Config Backups** (`services/backup-service/app/routes/config_backups.py`):
- `POST /config-backups` - enforces storage quota, auto-cleanup if exceeded

### 7. User Group Service (`services/user_group_service.py`)

**`get_user_modules(db, user_id)` Method**:

**Enforcement Logic**:
1. Get active license from database
2. If no license → return empty set (no access)
3. Get tier and available modules from license
4. If user is superuser → return ALL licensed modules
5. For regular users:
   - Get user's group memberships
   - Get group-assigned modules
   - Return **INTERSECTION** of license modules AND group modules

**Key Points**:
- ✅ Superusers see all licensed modules (not more)
- ✅ Regular users see only modules in BOTH license AND their groups
- ✅ Module name mapping from backend to frontend
- ✅ Used by AuthContext to populate `userModules`

### 8. Frontend License Context (`frontend/src/contexts/LicenseContext.jsx`)

**LicenseProvider**:
- Fetches license status from `/license/status`
- Provides license data to all components
- Handles license validation errors gracefully

**Exported Functions**:
- `hasModule(module)` - Check if module is in license
- `isWithinQuota(quotaType)` - Check quota status
- `getUsagePercentage(quotaType)` - Get quota usage percentage
- `isExpiringSoon()` - Check if expiring within 30 days
- `getDaysUntilExpiry()` - Days until expiration
- `getTierDisplayName()` - Human-readable tier name
- `getEnabledModules()` - List of all enabled modules

**Computed Values**:
- `isLicenseActive` - License is active
- `isLicenseValid` - License is valid and not expired
- `hasLicense` - License exists
- `tier` - Current license tier

### 9. Frontend License Guard (`frontend/src/components/LicenseGuard.jsx`)

**LicenseGuard Component**:
- Wraps protected routes
- Shows loading spinner while checking license
- Redirects to `/license` if no license or invalid
- Allows access if license is valid

**Usage**:
```jsx
<Route path="/devices" element={<LicenseGuard><DeviceManagement /></LicenseGuard>} />
```

**LicenseWarningBanner Component**:
- Displays on `/license` page
- Shows "No License Activated" if no license
- Shows "License Expired/Invalid" with details

### 10. Frontend Menu Filtering (`frontend/src/App.js`)

**Menu Item Structure**:
```javascript
{ 
  text: 'Devices', 
  icon: <DevicesIcon />, 
  path: '/devices', 
  module: 'devices' 
}
```

**Menu Filtering Logic**:
1. Always show items without `module` property (Dashboard, License)
2. Show `adminOnly` items only to admins
3. For module-specific items:
   - Check if `module` is in `userModules` (from AuthContext)
   - `userModules` already contains license-restricted modules
   - Only show if user has access

**Key Points**:
- ✅ Menu dynamically adjusts based on license
- ✅ Applies to ALL users including admins
- ✅ Admin-only items (User Management, Admin Panel) are separate
- ✅ License and Dashboard always visible

### 11. Frontend Auth Context (`frontend/src/contexts/AuthContext.js`)

**User Module Fetching**:
- Calls `/user-management/users/{user_id}/modules`
- Backend returns modules filtered by license AND group permissions
- Stored in `userModules` state
- Used by menu filtering logic

**Key Points**:
- ✅ Modules pre-filtered by backend (includes license enforcement)
- ✅ Frontend doesn't need to check license separately
- ✅ Refetched after login

## Quota Enforcement

### Device Quota

**Enforcement Points**:
1. **Manual Device Creation** (`POST /devices`)
   - Check before creating device
   - Reject if quota exceeded

2. **Device Discovery** (`POST /devices/discover`)
   - Enforce FIFO queue
   - Accept first N devices within quota
   - Reject remaining devices
   - Return `{accepted: [], rejected: [], message: ""}`

3. **Device Import**
   - Same logic as discovery

**Usage Update**:
- After device creation → `update_license_usage(db)`
- After device deletion → `update_license_usage(db)`
- Periodic background task updates `current_devices` in LicenseDB

### User Quota

**Enforcement Points**:
1. **User Creation** (`POST /users`)
   - Check before creating user
   - Raise exception if quota exceeded
   - Returns 400 with error message

**Usage Update**:
- After user creation → `update_license_usage(db)`
- After user deletion → `update_license_usage(db)`
- Periodic background task updates `current_users` in LicenseDB

### Storage Quota

**Enforcement Points**:
1. **Config Backup Creation** (`POST /config-backups`)
   - Check after backup created (post-action)
   - If exceeded:
     - Attempt auto-cleanup of old backups
     - Keep at least 1 backup per device
     - Delete oldest backups first
     - Log warning if still exceeded

**Calculation**:
- Sum of all `ConfigBackupDB.size_bytes`
- Converted to GB (rounded up)
- Updated periodically in `LicenseDB.current_storage_gb`

**Usage Update**:
- Calculated on-demand by `_calculate_storage_usage(db)`
- Stored in LicenseDB for quick reference

## Module Access Control

### Module Name Mapping

**Backend Module Names** → **Frontend Module Names**:
```
devices → devices
device_groups → device_groups
device_import → device_import
discovery → discovery_groups
manual_audits → audit
scheduled_audits → audit_schedules
basic_rules → rules
rule_templates → rule_templates
config_backups → config_backups
drift_detection → drift_detection
webhooks → notifications
health_checks → health
hardware_inventory → hardware_inventory
workflow_automation → workflows
integrations → integrations
analytics → analytics
remediation → remediation
```

### Access Determination Flow

```
User requests access to module "devices"
    ↓
1. API Gateway checks if "/devices" requires "devices" module
    ↓
2. LicenseGatewayMiddleware validates active license has "devices"
    ↓
3. Request proxied to device-service
    ↓
4. Device service route checks require_license_module("devices")
    ↓
5. LicenseEnforcer checks license tier includes "devices"
    ↓
6. If user_id provided, checks user's group has "devices"
    ↓
7. Request allowed if all checks pass
```

### Group-Based Module Access

**Admin Workflow**:
1. Admin creates user groups
2. Admin assigns modules to groups (via `set_group_module_access`)
3. Admin adds users to groups
4. Users inherit module access from all their groups

**Constraints**:
- Admin can only assign modules that are in the license tier
- Attempting to assign unlicensed module raises exception
- Superusers bypass group checks (see all licensed modules)

## Error Handling

### HTTP Status Codes

**402 Payment Required** - No active license
```json
{
  "error": "No active license",
  "message": "Please activate a valid license to use this feature",
  "action": "activate_license"
}
```

**403 Forbidden** - Module not in license tier
```json
{
  "error": "Module not available",
  "module": "scheduled_audits",
  "current_tier": "starter",
  "message": "The module 'Scheduled Audits' is not available in your starter tier",
  "action": "upgrade_license"
}
```

**403 Forbidden** - Quota exceeded
```json
{
  "error": "Quota exceeded",
  "quota_type": "devices",
  "current": 10,
  "max": 10,
  "message": "Cannot add 1 more devices. Current: 10/10",
  "action": "upgrade_license"
}
```

**403 Forbidden** - User permission denied
```json
{
  "error": "Access denied",
  "module": "scheduled_audits",
  "message": "User does not have access to module 'scheduled_audits'",
  "action": "contact_admin"
}
```

## Testing

### Manual Test Cases

**1. License Tier Enforcement**:
- [ ] Create Starter license
- [ ] Verify only Starter modules appear in menu
- [ ] Attempt to access Professional module (should be blocked)
- [ ] Upgrade to Professional license
- [ ] Verify Professional modules now appear

**2. Device Quota Enforcement**:
- [ ] Create Starter license (10 devices max)
- [ ] Add 10 devices successfully
- [ ] Attempt to add 11th device (should fail)
- [ ] Discover 20 devices (should accept first 10, reject 10)

**3. User Quota Enforcement**:
- [ ] Create Starter license (2 users max)
- [ ] Add 2 users successfully
- [ ] Attempt to add 3rd user (should fail with quota error)

**4. Storage Quota Enforcement**:
- [ ] Create backups until quota reached
- [ ] Verify auto-cleanup triggers
- [ ] Verify warning logged if cleanup insufficient

**5. Group Module Access**:
- [ ] Create Professional license
- [ ] Create user group with only "devices" module
- [ ] Add user to group
- [ ] Verify user only sees "devices" in menu
- [ ] Add "scheduled_audits" to group
- [ ] Verify user now sees both modules

**6. Superuser Access**:
- [ ] Create Professional license
- [ ] Create superuser
- [ ] Verify superuser sees ALL Professional modules
- [ ] Upgrade to Enterprise
- [ ] Verify superuser now sees ALL Enterprise modules

**7. API Gateway Enforcement**:
- [ ] Create Starter license
- [ ] Attempt API call to `/audit-schedules` (should return 403)
- [ ] Attempt API call to `/devices` (should succeed)
- [ ] Upgrade to Professional
- [ ] Attempt API call to `/audit-schedules` (should now succeed)

**8. Frontend Menu Filtering**:
- [ ] Login with Starter license
- [ ] Verify menu shows only Starter modules
- [ ] Verify clicking on hidden module redirects to license page
- [ ] Login with Professional license
- [ ] Verify menu shows Professional modules

## Security Considerations

### License Key Security
- ✅ License keys encrypted with Fernet (symmetric encryption)
- ✅ SHA256 signature prevents tampering
- ✅ Encryption key stored in environment variable
- ✅ License validation on every request
- ✅ Expired licenses automatically deactivated

### Access Control
- ✅ Three-layer enforcement (API Gateway → Backend Route → Service)
- ✅ License checked before proxying requests
- ✅ Module access validated on every API call
- ✅ User permissions checked for user-specific routes
- ✅ Superuser status verified from database

### Quota Bypass Prevention
- ✅ Quota checked before resource creation
- ✅ Usage tracked in database
- ✅ Periodic usage updates
- ✅ FIFO queue for discovery prevents overflow
- ✅ Storage auto-cleanup prevents disk exhaustion

## Monitoring & Logging

### License Validation Logs
```
[INFO] License renewed for customer@example.com
[WARNING] Active license is invalid: License expired on 2025-01-01
[WARNING] License check failed for path /audit-schedules: No active license
```

### Quota Enforcement Logs
```
[WARNING] Device quota limit reached. Accepting 5 of 15 discovered devices.
[WARNING] Storage quota exceeded after backup creation. Current: 52 GB / Max: 50 GB
[INFO] Cleaned up 10 old backups, freed 2.5 GB
```

### Module Access Logs
```
[DEBUG] User 123 modules: group={'devices', 'audit'}, license={'devices', 'audit', 'rules'}, allowed={'devices', 'audit'}
[DEBUG] Superuser 456 has access to all licensed modules: {'devices', 'audit', 'rules', 'scheduled_audits'}
```

## Configuration Files

### Environment Variables Required
```bash
LICENSE_ENCRYPTION_KEY=<fernet-key>
LICENSE_SECRET_SALT=<random-salt>
DATABASE_URL=postgresql://...
```

### Database Migration
```bash
python migrations/add_license_system.py
```

## API Endpoints

### License Management
- `GET /license/status` - Get current license status
- `POST /license/activate` - Activate new license key
- `GET /license/quotas` - Get quota usage statistics

### User Module Access
- `GET /user-management/users/{user_id}/modules` - Get user's accessible modules
- `GET /user-management/users/{user_id}/permissions` - Get user's permissions

### Module Management (Admin)
- `POST /admin/groups/{group_id}/modules` - Set group module access

## Deployment Checklist

- [ ] Generate and set `LICENSE_ENCRYPTION_KEY` in production
- [ ] Set unique `LICENSE_SECRET_SALT` in production
- [ ] Run database migrations to create license tables
- [ ] Create initial admin user
- [ ] Activate production license key
- [ ] Verify API Gateway license middleware is active
- [ ] Test all quota limits
- [ ] Test module access restrictions
- [ ] Configure periodic usage update task
- [ ] Set up license expiration monitoring
- [ ] Configure alerts for quota thresholds

## Summary

The license enforcement system provides **comprehensive, multi-layered protection** across:

✅ **Database** - Stores license data, quotas, and usage  
✅ **Backend API** - Enforces module access and quotas  
✅ **API Gateway** - Blocks unauthorized requests before routing  
✅ **Frontend** - Hides unavailable modules from menu  
✅ **User Groups** - Fine-grained module access control  

**All users**, including admins and superusers, are subject to license restrictions. No user can access modules not included in the active license tier.

**Quotas** are enforced at creation time (devices, users) and checked periodically (storage), with automatic cleanup mechanisms for storage.

**Module access** is determined by the intersection of license tier modules AND user group permissions, ensuring both organizational and licensing constraints are respected.
