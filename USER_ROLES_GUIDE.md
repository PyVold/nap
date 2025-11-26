# User Roles & Permissions Guide

## Overview
The Network Audit Platform supports role-based access control (RBAC) with three default user roles:
- **Admin** - Full system access
- **Operator** - Can perform operations but cannot manage users
- **Viewer** - Read-only access

---

## Default Test Users

The system automatically creates 3 default users on first startup:

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| `admin` | `admin` | admin | Full access to all features |
| `operator` | `operator` | operator | Can manage devices, run audits, configure backups |
| `viewer` | `viewer` | viewer | Read-only access to view data |

⚠️ **IMPORTANT:** Change these default passwords immediately in production!

---

## User Roles & Permissions Matrix

### Admin Role
**Full system access - can do everything**

| Feature | View | Create | Update | Delete |
|---------|------|--------|--------|--------|
| Devices | ✅ | ✅ | ✅ | ✅ |
| Device Groups | ✅ | ✅ | ✅ | ✅ |
| Discovery | ✅ | ✅ | ✅ | ✅ |
| Rules | ✅ | ✅ | ✅ | ✅ |
| Audits | ✅ | ✅ | ✅ | ✅ |
| Config Backups | ✅ | ✅ | ✅ | ✅ |
| Hardware Inventory | ✅ | ✅ | ✅ | ✅ |
| Users | ✅ | ✅ | ✅ | ✅ |
| Integrations | ✅ | ✅ | ✅ | ✅ |
| System Settings | ✅ | ✅ | ✅ | ✅ |

### Operator Role
**Can perform network operations but cannot manage users**

| Feature | View | Create | Update | Delete |
|---------|------|--------|--------|--------|
| Devices | ✅ | ✅ | ✅ | ✅ |
| Device Groups | ✅ | ✅ | ✅ | ✅ |
| Discovery | ✅ | ✅ | ✅ | ✅ |
| Rules | ✅ | ✅ | ✅ | ❌ |
| Audits | ✅ | ✅ | ✅ | ❌ |
| Config Backups | ✅ | ✅ | ✅ | ❌ |
| Hardware Inventory | ✅ | ✅ | ✅ | ❌ |
| Users | ❌ | ❌ | ❌ | ❌ |
| Integrations | ✅ | ❌ | ❌ | ❌ |
| System Settings | ✅ | ❌ | ❌ | ❌ |

### Viewer Role
**Read-only access - can view but not modify**

| Feature | View | Create | Update | Delete |
|---------|------|--------|--------|--------|
| Devices | ✅ | ❌ | ❌ | ❌ |
| Device Groups | ✅ | ❌ | ❌ | ❌ |
| Discovery | ✅ | ❌ | ❌ | ❌ |
| Rules | ✅ | ❌ | ❌ | ❌ |
| Audits | ✅ | ❌ | ❌ | ❌ |
| Config Backups | ✅ | ❌ | ❌ | ❌ |
| Hardware Inventory | ✅ | ❌ | ❌ | ❌ |
| Users | ❌ | ❌ | ❌ | ❌ |
| Integrations | ❌ | ❌ | ❌ | ❌ |
| System Settings | ❌ | ❌ | ❌ | ❌ |

---

## Login Endpoint

**URL:** `http://localhost:8080/login` (Frontend) → Routes to → `http://localhost:3000/admin/login` (API Gateway) → `http://localhost:3005/admin/login` (Admin Service)

**Method:** POST

**Request Body:**
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "username": "admin",
  "role": "admin"
}
```

The JWT token contains:
- `sub`: username
- `role`: user role (admin/operator/viewer)
- `user_id`: user ID in database

---

## Frontend Integration

### Login Flow
1. User visits `http://localhost:8080/login`
2. Frontend sends POST to `/admin/login` with credentials
3. Backend validates credentials and returns JWT token
4. Frontend stores token (localStorage or sessionStorage)
5. Frontend includes token in all subsequent requests: `Authorization: Bearer <token>`
6. Frontend reads role from token and adapts UI

### Role-Based UI Adaptation

The frontend should check the user's role and show/hide features accordingly:

```javascript
// Example: Get user role from JWT token
const getUserRole = () => {
  const token = localStorage.getItem('access_token');
  if (!token) return null;

  const payload = JSON.parse(atob(token.split('.')[1]));
  return payload.role;
};

// Example: Check permissions
const canEditDevices = () => {
  const role = getUserRole();
  return role === 'admin' || role === 'operator';
};

const canManageUsers = () => {
  const role = getUserRole();
  return role === 'admin';
};
```

### Dynamic Navigation Example

```javascript
// Navigation items with role requirements
const navItems = [
  { path: '/devices', label: 'Devices', minRole: 'viewer' },
  { path: '/rules', label: 'Rules', minRole: 'viewer' },
  { path: '/audits', label: 'Audits', minRole: 'viewer' },
  { path: '/backups', label: 'Backups', minRole: 'viewer' },
  { path: '/inventory', label: 'Inventory', minRole: 'viewer' },
  { path: '/users', label: 'User Management', minRole: 'admin' },
  { path: '/integrations', label: 'Integrations', minRole: 'admin' },
];

// Filter nav items based on user role
const getVisibleNavItems = (userRole) => {
  const roleHierarchy = { viewer: 1, operator: 2, admin: 3 };
  return navItems.filter(item =>
    roleHierarchy[userRole] >= roleHierarchy[item.minRole]
  );
};
```

### Button Visibility Example

```javascript
// In your React components
const DeviceListPage = () => {
  const userRole = getUserRole();
  const canEdit = ['admin', 'operator'].includes(userRole);

  return (
    <div>
      <DeviceList />
      {canEdit && <Button onClick={handleAddDevice}>Add Device</Button>}
      {canEdit && <Button onClick={handleEditDevice}>Edit</Button>}
      {canEdit && <Button onClick={handleDeleteDevice}>Delete</Button>}
    </div>
  );
};
```

---

## Testing Different Roles

### Test as Admin
```bash
curl -X POST http://localhost:3000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### Test as Operator
```bash
curl -X POST http://localhost:3000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"operator","password":"operator"}'
```

### Test as Viewer
```bash
curl -X POST http://localhost:3000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"viewer","password":"viewer"}'
```

### Verify Role in Token
```bash
# Get token from login response
TOKEN="<your-token-here>"

# Decode JWT (base64 decode the middle part)
echo $TOKEN | cut -d. -f2 | base64 -d | jq

# Output shows:
# {
#   "sub": "admin",
#   "role": "admin",
#   "user_id": 1,
#   "exp": 1234567890
# }
```

---

## Creating Additional Users

Admins can create additional users via the User Management API:

**Endpoint:** `POST /user-management/users`

**Headers:**
```
Authorization: Bearer <admin-token>
Content-Type: application/json
```

**Body:**
```json
{
  "username": "john.doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "password": "securepassword123",
  "role": "operator",
  "is_active": true
}
```

---

## Security Considerations

### JWT Token Security
- Tokens expire after 7 days (configurable in `shared/auth.py`)
- Tokens are signed with HS256 algorithm
- JWT_SECRET should be changed from default in production
- Tokens should be stored securely (httpOnly cookies preferred)

### Password Security
- Passwords are hashed with bcrypt
- Minimum password length should be enforced (add validation)
- Default passwords MUST be changed in production

### API Endpoint Protection
- All endpoints use `@Depends(get_current_user)` for authentication
- Role-specific endpoints use `@Depends(require_admin)` or `@Depends(require_role("admin", "operator"))`
- Unauthorized requests return 401 Unauthorized
- Insufficient permissions return 403 Forbidden

---

## Frontend Implementation Checklist

- [ ] Login page at `/login` route
- [ ] Login form with username and password fields
- [ ] Store JWT token on successful login
- [ ] Include token in all API requests
- [ ] Decode token to get user role
- [ ] Show/hide navigation items based on role
- [ ] Show/hide action buttons based on role
- [ ] Disable forms/inputs for viewers (read-only mode)
- [ ] Display user info in header (username, role)
- [ ] Logout functionality (clear token)
- [ ] Redirect to login if token is expired
- [ ] Handle 401/403 errors gracefully

---

## API Endpoints Summary

### Authentication
- `POST /admin/login` - Login (all users)
- `GET /admin/me` - Get current user info

### User Management (Admin only)
- `GET /user-management/users` - List all users
- `POST /user-management/users` - Create new user
- `GET /user-management/users/{id}` - Get user details
- `PUT /user-management/users/{id}` - Update user
- `DELETE /user-management/users/{id}` - Delete user

### Protected Endpoints
All other endpoints require authentication via JWT token in `Authorization: Bearer <token>` header.

---

## Migration from Monolith

The RBAC system was already present in the monolith and has been preserved in the microservices architecture:

- User database model unchanged
- Authentication logic moved to `shared/deps.py`
- Login endpoint in admin-service
- Token generation/validation in `shared/auth.py`
- Role checking works across all services

---

## Next Steps

1. **Frontend:** Implement login page and role-based UI
2. **Backend:** Add more granular permissions if needed
3. **Security:** Change JWT_SECRET and default passwords
4. **Monitoring:** Log authentication attempts
5. **Enhancement:** Add 2FA, password reset, session management
