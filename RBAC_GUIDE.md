# Role-Based Access Control (RBAC) Guide

## Overview

The Network Audit Platform implements Role-Based Access Control (RBAC) to restrict access to modification endpoints based on user roles.

## User Roles

### Admin
- **Full access** to all features
- Can manage users, modules, system settings
- Can create, modify, and delete everything
- Access to admin panel

### Operator
- **Modify access** to operational features
- Can manage devices, rules, groups, schedules
- Can run audits and push remediation
- **Cannot** manage users or system modules
- **Cannot** access admin panel

### Viewer
- **Read-only access** to all features
- Can view devices, rules, audit results, dashboards
- **Cannot** modify, create, or delete anything
- Good for monitoring and reporting

## Implementation

### Backend (API Endpoints)

#### Step 1: Import Dependencies

```python
from api.deps import get_db, require_admin_or_operator, require_admin, require_any_authenticated
```

#### Step 2: Add Role Check to Endpoint

```python
# Before (no protection)
@router.post("/")
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create a new item"""
    return service.create_item(db, item)

# After (protected for admin/operator)
@router.post("/")
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)  # <- Add this
):
    """Create a new item (requires admin or operator role)"""
    return service.create_item(db, item)
```

### Available Role Dependencies

```python
# Require admin role only
current_user: dict = Depends(require_admin)

# Require admin OR operator role
current_user: dict = Depends(require_admin_or_operator)

# Require any authenticated user (all roles)
current_user: dict = Depends(require_any_authenticated)

# Custom role check
current_user: dict = Depends(require_role("admin", "custom_role"))
```

### Current User Object

The `current_user` dict contains:
```python
{
    "username": "admin",
    "role": "admin",
    "user_id": 1
}
```

## Endpoints That Should Be Protected

### Critical (Admin Only)
- User management (`/admin/users/*`)
- Module management (`/admin/modules/*`)
- System settings

### Operational (Admin/Operator)
✅ **Already Protected:**
- Rules CRUD (`/rules/*`)
- Devices CRUD (`/devices/*`)
- Remediation (`/remediation/*`)

⚠️ **Need Protection** (apply same pattern):
- Device Groups (`/device-groups/*`)
- Discovery Groups (`/discovery-groups/*`)
- Audit Schedules (`/audit-schedules/*`)
- Config Templates (`/config-templates/*`)
- Rule Templates (`/rule-templates/apply`)
- Config Backups (delete/restore)
- Drift Detection (set baseline)
- Notifications (webhooks CRUD)
- Device Import (upload)
- Integrations CRUD
- Licensing CRUD
- Topology discovery
- Analytics (snapshot creation)

### Read-Only (All Roles)
- GET endpoints for viewing data
- Dashboard statistics
- Health checks
- Audit result viewing

## Frontend Integration

### Get Current User Role

```javascript
import { useAuth } from '../contexts/AuthContext';

function MyComponent() {
  const { user } = useAuth();

  // user.role is "admin", "operator", or "viewer"
  const canModify = user?.role === 'admin' || user?.role === 'operator';
  const isAdmin = user?.role === 'admin';

  return (
    <>
      {canModify && (
        <Button onClick={handleCreate}>Create</Button>
      )}
      {isAdmin && (
        <Button onClick={handleAdminAction}>Admin Panel</Button>
      )}
    </>
  );
}
```

### Hide UI Elements Based on Role

```javascript
// Hide delete button for viewers
{user?.role !== 'viewer' && (
  <IconButton onClick={handleDelete}>
    <DeleteIcon />
  </IconButton>
)}

// Show admin-only features
{user?.role === 'admin' && (
  <MenuItem onClick={() => navigate('/admin')}>
    Admin Panel
  </MenuItem>
)}
```

### Handle 403 Errors

```javascript
try {
  await api.post('/devices/', deviceData);
} catch (error) {
  if (error.response?.status === 403) {
    setError('Insufficient permissions. Contact your administrator.');
  }
}
```

## Adding RBAC to a New Endpoint

### Example: Protect Device Group Creation

1. **Update imports:**
```python
from api.deps import get_db, require_admin_or_operator
```

2. **Add role dependency:**
```python
@router.post("/device-groups/", response_model=DeviceGroup)
async def create_device_group(
    group: DeviceGroupCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)  # Add this
):
    """Create device group (requires admin/operator role)"""
    return service.create_group(db, group)
```

3. **Update docstring** to indicate role requirement

4. **Test:**
```bash
# As admin/operator - should work
curl -X POST "http://localhost:3000/device-groups/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Group"}'

# As viewer - should fail with 403
curl -X POST "http://localhost:3000/device-groups/" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Group"}'
```

## Testing RBAC

### Create Test Users

```bash
# Login as admin
curl -X POST "http://localhost:3000/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Save token
export ADMIN_TOKEN="eyJ..."

# Create operator user
curl -X POST "http://localhost:3000/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "email": "operator@example.com",
    "password": "password",
    "role": "operator"
  }'

# Create viewer user
curl -X POST "http://localhost:3000/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "viewer1",
    "email": "viewer@example.com",
    "password": "password",
    "role": "viewer"
  }'
```

### Test Permissions

```bash
# Login as viewer
curl -X POST "http://localhost:3000/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"viewer1","password":"password"}'

export VIEWER_TOKEN="eyJ..."

# Try to create a rule (should fail with 403)
curl -X POST "http://localhost:3000/rules/" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Rule",
    "description": "Test",
    "vendor": "cisco",
    "enabled": true,
    "checks": []
  }'

# Expected response:
# {
#   "detail": "Insufficient permissions. Required roles: admin, operator"
# }
```

## Security Best Practices

1. **Always protect modification endpoints** - Any POST, PUT, PATCH, DELETE should require authentication
2. **Use appropriate role levels** - Admin-only for sensitive operations, Admin/Operator for operational tasks
3. **Don't trust frontend** - Always validate permissions on the backend
4. **Log access attempts** - Track who does what for audit trails
5. **Change default passwords** - The default admin password should be changed immediately
6. **Use HTTPS in production** - Protect JWT tokens in transit
7. **Set token expiration** - Currently 24 hours, adjust based on security requirements

## Troubleshooting

### "Not authenticated" Error
- User hasn't logged in
- JWT token missing or invalid
- Frontend: Check `localStorage.getItem('auth_token')`

### "Insufficient permissions" Error (403)
- User logged in but doesn't have required role
- Check user role matches endpoint requirements
- Viewers cannot modify anything

### Token Expired
- Current expiration: 24 hours (1440 minutes)
- User must login again
- To change: Update `ACCESS_TOKEN_EXPIRE_MINUTES` in `utils/auth.py`

## Migration Guide

To add RBAC to your existing codebase:

1. **Update all modification endpoints** following the pattern above
2. **Test each protected endpoint** with different roles
3. **Update frontend** to show/hide UI elements based on role
4. **Handle 403 errors** gracefully in the frontend
5. **Document** which endpoints require which roles

## Next Steps

1. Apply RBAC to remaining modification endpoints
2. Add audit logging for all protected operations
3. Implement frontend role-based UI hiding
4. Add module visibility control (hide disabled modules)
5. Consider adding custom roles beyond admin/operator/viewer
