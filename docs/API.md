# Network Audit Platform - API Reference

## Overview

The Network Audit Platform provides a RESTful API for managing network devices, audit rules, configuration backups, and compliance reporting.

**Base URL**: `https://your-domain.com/api`

**Authentication**: All endpoints (except `/health`, `/login`) require Bearer token authentication.

---

## Authentication

### Login
```http
POST /login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Using the Token
```http
GET /api/devices
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Devices API

### List All Devices
```http
GET /api/devices
Authorization: Bearer <token>
```

**Response**:
```json
[
  {
    "id": 1,
    "hostname": "router-01",
    "vendor": "nokia",
    "ip": "192.168.1.1",
    "port": 830,
    "username": "admin",
    "status": "active",
    "compliance": 95,
    "last_audit": "2024-01-15T10:30:00Z",
    "metadata": {
      "bgp": {"router_id": "1.1.1.1"},
      "igp": {"router_id": "49.0001.0001.0001.00"}
    }
  }
]
```

### Get Device by ID
```http
GET /api/devices/{device_id}
Authorization: Bearer <token>
```

### Create Device
```http
POST /api/devices
Authorization: Bearer <token>
Content-Type: application/json

{
  "hostname": "router-02",
  "vendor": "nokia",
  "ip": "192.168.1.2",
  "port": 830,
  "username": "admin",
  "password": "device-password"
}
```

**Required Role**: `admin` or `operator`

### Update Device
```http
PUT /api/devices/{device_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "hostname": "router-02-updated",
  "status": "maintenance"
}
```

**Required Role**: `admin` or `operator`

### Delete Device
```http
DELETE /api/devices/{device_id}
Authorization: Bearer <token>
```

**Required Role**: `admin` or `operator`

### Discover Devices
```http
POST /api/devices/discover
Authorization: Bearer <token>
Content-Type: application/json

{
  "subnet": "192.168.1.0/24",
  "username": "admin",
  "password": "discovery-password",
  "port": 830
}
```

**Response**:
```json
{
  "status": "success",
  "discovered": 5,
  "added": 3,
  "total_devices": 10
}
```

### Get Metadata Overlaps
```http
GET /api/devices/metadata/overlaps
Authorization: Bearer <token>
```

Returns devices with duplicate router IDs, ISIS addresses, etc.

---

## Audit Rules API

### List Rules
```http
GET /api/rules
Authorization: Bearer <token>
```

### Create Rule
```http
POST /api/rules
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "check-ntp-servers",
  "description": "Verify NTP server configuration",
  "vendor": "nokia",
  "severity": "medium",
  "category": "configuration",
  "xpath": "/configure/system/time/ntp",
  "expected_value": "enabled",
  "operator": "equals"
}
```

### Run Audit
```http
POST /api/audit/run
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_ids": [1, 2, 3],
  "rule_ids": [1, 2]
}
```

**Response**:
```json
{
  "audit_id": "abc123",
  "status": "running",
  "started_at": "2024-01-15T10:30:00Z"
}
```

### Get Audit Results
```http
GET /api/audit/results/{audit_id}
Authorization: Bearer <token>
```

---

## Configuration Backups API

### List Backups
```http
GET /api/backups
Authorization: Bearer <token>
```

### Create Backup
```http
POST /api/backups
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_ids": [1, 2, 3],
  "description": "Pre-maintenance backup"
}
```

### Download Backup
```http
GET /api/backups/{backup_id}/download
Authorization: Bearer <token>
```

### Compare Backups
```http
GET /api/backups/compare?backup1_id=1&backup2_id=2
Authorization: Bearer <token>
```

---

## Health Check API

### Application Health
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Readiness Check
```http
GET /ready
```

### Liveness Check
```http
GET /live
```

### Metrics (Prometheus)
```http
GET /metrics
```

---

## Users API

### List Users
```http
GET /api/users
Authorization: Bearer <token>
```

**Required Role**: `admin`

### Create User
```http
POST /api/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecurePass123!",
  "role": "operator"
}
```

**Required Role**: `admin`

### Update User
```http
PUT /api/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "admin",
  "is_active": true
}
```

**Required Role**: `admin`

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid input: hostname is required"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions. Required roles: admin"
}
```

### 404 Not Found
```json
{
  "detail": "Device with ID 999 not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Retry after 60 seconds."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

- **Default limit**: 100 requests per minute per IP
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Window`: Time window in seconds
  - `Retry-After`: Seconds until rate limit resets (on 429)

---

## Webhooks

Configure webhooks to receive real-time notifications:

```http
POST /api/webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "events": ["audit.completed", "device.offline", "compliance.failed"],
  "secret": "your-webhook-secret"
}
```

### Event Types
- `audit.completed` - Audit run finished
- `audit.failed` - Audit run failed
- `device.online` - Device became reachable
- `device.offline` - Device became unreachable
- `compliance.failed` - Device below compliance threshold
- `backup.completed` - Backup finished
- `backup.failed` - Backup failed

---

## SDKs & Examples

### Python
```python
import requests

class NAPClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.token = self._login(username, password)

    def _login(self, username, password):
        response = requests.post(
            f"{self.base_url}/login",
            json={"username": username, "password": password}
        )
        return response.json()["access_token"]

    def get_devices(self):
        response = requests.get(
            f"{self.base_url}/api/devices",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()

# Usage
client = NAPClient("https://nap.example.com", "admin", "password")
devices = client.get_devices()
```

### curl
```bash
# Login
TOKEN=$(curl -s -X POST https://nap.example.com/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r .access_token)

# Get devices
curl -H "Authorization: Bearer $TOKEN" https://nap.example.com/api/devices
```
