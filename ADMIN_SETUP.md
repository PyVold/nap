# Admin Panel Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Admin User and Modules

```bash
python scripts/init_admin.py
```

This will create:
- Default admin user (username: `admin`, password: `admin`)
- System modules configuration

**⚠️ IMPORTANT: Change the default admin password immediately!**

### 3. Start the Application

```bash
python main.py
```

## API Endpoints

### Authentication

#### Login
```bash
POST /admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin"
}

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "username": "admin",
  "role": "admin"
}
```

#### Get Current User
```bash
GET /admin/me
Authorization: Bearer <token>
```

### User Management

#### List Users
```bash
GET /admin/users
Authorization: Bearer <token>
```

#### Create User
```bash
POST /admin/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "operator1",
  "email": "operator@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "role": "operator"
}
```

Roles:
- `admin`: Full access
- `operator`: Can manage devices and run audits
- `viewer`: Read-only access

#### Update User
```bash
PUT /admin/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "viewer",
  "is_active": false
}
```

#### Delete User
```bash
DELETE /admin/users/{user_id}
Authorization: Bearer <token>
```

### Module Management

#### List Modules
```bash
GET /admin/modules
Authorization: Bearer <token>
```

#### Get Module
```bash
GET /admin/modules/{module_id}
Authorization: Bearer <token>
```

#### Update Module (Enable/Disable)
```bash
PUT /admin/modules/{module_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "enabled": false,
  "settings": {
    "custom_setting": "value"
  }
}
```

Available Modules:
- `devices`: Device Management
- `audit`: Audit & Compliance
- `config_backups`: Configuration Backups
- `drift_detection`: Drift Detection
- `health_monitoring`: Health Monitoring
- `notifications`: Notifications & Webhooks
- `rule_templates`: Rule Templates
- `integrations`: External Integrations (disabled by default)
- `topology`: Network Topology (disabled by default)
- `licensing`: License Management (disabled by default)
- `analytics`: Analytics & Forecasting (disabled by default)

### Audit Logs

#### List Audit Logs
```bash
GET /admin/audit-logs?limit=100&skip=0
Authorization: Bearer <token>
```

### Statistics

#### Get Admin Stats
```bash
GET /admin/stats
Authorization: Bearer <token>
```

## Using with cURL

### Login Example
```bash
# Login and save token
TOKEN=$(curl -X POST "http://localhost:3000/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token')

# Use token for authenticated requests
curl "http://localhost:3000/admin/users" \
  -H "Authorization: Bearer $TOKEN"
```

### Create User Example
```bash
curl -X POST "http://localhost:3000/admin/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "viewer1",
    "email": "viewer@example.com",
    "password": "password123",
    "role": "viewer"
  }'
```

### Disable Module Example
```bash
curl -X PUT "http://localhost:3000/admin/modules/8" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## Security Best Practices

1. **Change Default Password**: Immediately change the default admin password
2. **Use Strong Passwords**: Enforce strong password policies
3. **JWT Secret**: Change the SECRET_KEY in `utils/auth.py` to a secure random value
4. **HTTPS**: Always use HTTPS in production
5. **Regular Audits**: Review audit logs regularly
6. **Principle of Least Privilege**: Assign users the minimum role needed

## Frontend Integration

The admin panel APIs are designed to work with any frontend framework. Example using JavaScript:

```javascript
// Login
const login = async (username, password) => {
  const response = await fetch('http://localhost:3000/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  return data;
};

// List users
const getUsers = async () => {
  const token = localStorage.getItem('token');
  const response = await fetch('http://localhost:3000/admin/users', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// Toggle module
const toggleModule = async (moduleId, enabled) => {
  const token = localStorage.getItem('token');
  await fetch(`http://localhost:3000/admin/modules/${moduleId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ enabled })
  });
};
```

## Troubleshooting

### "Admin user already exists"
The admin user has already been created. Use the existing credentials or reset the database.

### "Could not validate credentials"
- Check that the token is valid and not expired
- Tokens expire after 24 hours by default
- Login again to get a new token

### "Admin privileges required"
The current user doesn't have the `admin` role. Only admin users can access admin endpoints.

## API Documentation

Full interactive API documentation is available at:
- Swagger UI: http://localhost:3000/docs
- ReDoc: http://localhost:3000/redoc
