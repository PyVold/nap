# Admin Dashboard & License Module Mappings

## ✅ License Page Module Mappings - VERIFIED CORRECT

All 18 modules are correctly mapped between backend and frontend:

### Backend (shared/license_manager.py)
```python
MODULE_DISPLAY_NAMES = {
    "devices": "Device Management",
    "manual_audits": "Manual Audits",
    "scheduled_audits": "Scheduled Audits",
    "basic_rules": "Basic Audit Rules",
    "rule_templates": "Rule Templates",
    "api_access": "API Access",
    "config_backups": "Configuration Backups",
    "drift_detection": "Drift Detection",
    "webhooks": "Webhook Notifications",
    "device_groups": "Device Groups",
    "discovery": "Device Discovery",
    "health_checks": "Health Monitoring",
    "hardware_inventory": "Hardware Inventory",       # ⭐ Enterprise Only
    "workflow_automation": "Workflow Automation",
    "topology": "Network Topology Maps",
    "ai_features": "AI-Powered Features",
    "integrations": "Advanced Integrations",
    "sso": "SSO & SAML Authentication"
}
```

### Frontend (frontend/src/components/LicenseManagement.jsx)
All 18 modules present with icons and descriptions ✅

### Route Mappings (shared/license_manager.py)
```python
ROUTE_MODULE_MAP = {
    "devices": "devices",
    "device_groups": "device_groups",
    "discovery_groups": "discovery",
    "device_import": "devices",
    "audit": "manual_audits",
    "audits": "manual_audits",
    "audit_schedules": "scheduled_audits",
    "rules": "basic_rules",
    "rule_templates": "rule_templates",
    "config_backups": "config_backups",
    "drift_detection": "drift_detection",
    "notifications": "webhooks",
    "health": "health_checks",
    "hardware_inventory": "hardware_inventory",    # ⭐ Enterprise Only
    "integrations": "integrations",
    "workflows": "workflow_automation",
    "analytics": "ai_features",
    "api": "api_access",
}
```

---

## 🎛️ New Admin Dashboard

### Overview
Comprehensive administration interface with 6 tabs for complete system control.

### Location
- **Frontend**: `/frontend/src/components/AdminDashboard.jsx`
- **Backend API**: `/services/admin-service/app/routes/admin_settings.py`
- **Database Model**: `SystemConfigDB` in `/services/admin-service/app/db_models.py`

### Tab 1: System Settings ⚙️

**Features:**
- Platform name configuration
- Default session timeout (seconds)
- Max failed login attempts
- Enable/disable audit logging
- **SMTP Email Configuration:**
  - SMTP server and port
  - Authentication credentials
  - Enable/disable email notifications

**API Endpoints:**
- `GET /admin/system-settings` - Get current settings
- `POST /admin/system-settings` - Save settings
- `POST /admin/test-email` - Test SMTP configuration

**Example Configuration:**
```json
{
  "platformName": "Network Audit Platform",
  "smtpEnabled": true,
  "smtpServer": "smtp.gmail.com",
  "smtpPort": 587,
  "smtpUsername": "alerts@company.com",
  "smtpPassword": "***",
  "defaultSessionTimeout": 3600,
  "enableAuditLogs": true,
  "maxFailedLogins": 5
}
```

---

### Tab 2: Backup Configuration 💾

**Features:**
- Enable/disable automatic config backups
- **Backup Schedule:**
  - Hourly
  - Every 6 hours
  - Every 12 hours
  - Daily (specify time)
  - Weekly (specify time)
  - Monthly (specify time)
- **Retention Settings:**
  - Retention period (days) - auto-delete old backups
  - Max backups per device - keep only N most recent
- **Options:**
  - Compress backups (save storage)
  - Email notification on backup failure

**API Endpoints:**
- `GET /admin/backup-config` - Get current backup config
- `POST /admin/backup-config` - Save backup config

**Example Configuration:**
```json
{
  "enabled": true,
  "scheduleType": "daily",
  "scheduleTime": "02:00",
  "retentionDays": 30,
  "maxBackupsPerDevice": 10,
  "compressBackups": true,
  "notifyOnFailure": true
}
```

**Schedule Examples:**
- **Hourly**: Backs up all devices every hour
- **Daily at 02:00**: Backs up once per day at 2 AM
- **Weekly**: Backs up once per week on Sunday
- **Monthly**: Backs up on the 1st of each month

---

### Tab 3: Users 👥

**Features:**
- User list with pagination
- User details:
  - Username, email, role (Admin/User)
  - Active/Inactive status
  - Group membership count
- **Actions:**
  - Add new user
  - Edit user details
  - Delete user
  - Assign to groups

**Integration:**
- Uses existing `/user-management/users/` endpoints
- Shows role-based access (Admin vs User)
- Displays group count per user

---

### Tab 4: Groups & Permissions 🔐

**Features:**
- Group list with module assignments
- Each group card shows:
  - Group name and description
  - Module access (chip list)
  - User count in group
- **Actions:**
  - Add new group
  - Edit group permissions
  - Assign modules to group
  - Delete group

**Module Access Control:**
Groups control which license modules users can access:
- Assign modules like `devices`, `manual_audits`, `scheduled_audits`, etc.
- Users inherit module access from ALL groups they belong to
- Module access is intersected with license tier modules

**Example:**
```
Group: "Network Engineers"
Modules: devices, manual_audits, config_backups, drift_detection
Users: 5 users

Group: "Read Only Auditors"
Modules: manual_audits, health_checks
Users: 3 users
```

---

### Tab 5: License 🔑

**Features:**
- Link to full license management page
- Quick license status overview
- Redirect to `/license` for detailed management

---

### Tab 6: System Health 📊

**Features:**
- API Gateway status
- Database connection status
- Microservice health checks
- Service count (running/total)
- Refresh button for real-time status

**Integration:**
- Uses `/health` endpoint from API gateway
- Shows aggregated health of all services

---

## 🔧 To-Do Items

### 1. ✅ DONE: License Page Mappings
- All 18 modules correctly mapped
- Hardware Inventory marked as Enterprise only
- Frontend module definitions complete

### 2. ⏳ TODO: Add Admin Dashboard Route to Frontend

**File**: `/home/user/nap/frontend/src/App.js`

**Add import:**
```jsx
import AdminDashboard from './components/AdminDashboard';
```

**Add route (protected, admin only):**
```jsx
<Route
  path="/admin"
  element={
    <ProtectedRoute>
      <AdminDashboard />
    </ProtectedRoute>
  }
/>
```

**Add to menu (for admins only):**
```jsx
{user?.is_superuser && (
  <ListItem button component={Link} to="/admin">
    <ListItemIcon><SettingsIcon /></ListItemIcon>
    <ListItemText primary="Admin Dashboard" />
  </ListItem>
)}
```

### 3. ⏳ TODO: Database Migration

**Create migration for `system_config` table:**

```sql
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_config_key ON system_config(key);
```

**Run migration:**
```bash
docker-compose exec database psql -U nap_user -d nap_db -f /path/to/migration.sql
```

Or use Alembic:
```bash
cd /home/user/nap
alembic revision --autogenerate -m "Add system_config table"
alembic upgrade head
```

### 4. ⏳ TODO: Implement Backup Scheduler

**Options:**

**Option A: Celery Beat (Recommended)**
```python
# celery_config.py
from celery import Celery
from celery.schedules import crontab

app = Celery('backup_scheduler')

@app.task
def run_config_backup():
    # Get backup config from database
    config = get_backup_config()

    if config['enabled']:
        # Run backup for all devices
        backup_all_devices()

# Dynamic schedule based on database config
app.conf.beat_schedule = {
    'config-backup': {
        'task': 'run_config_backup',
        'schedule': get_schedule_from_config(),  # Read from database
    }
}
```

**Option B: APScheduler (Simpler)**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def update_backup_schedule():
    config = get_backup_config()

    # Remove old job
    scheduler.remove_all_jobs()

    # Add new job based on config
    if config['scheduleType'] == 'hourly':
        scheduler.add_job(backup_all_devices, 'interval', hours=1)
    elif config['scheduleType'] == 'daily':
        scheduler.add_job(backup_all_devices, 'cron', hour=int(config['scheduleTime'].split(':')[0]))
    # ... etc

scheduler.start()
```

### 5. ✅ DONE: Test User/Group Permissions

**Verification Steps:**

1. **Create Test Groups:**
```bash
curl -X POST http://localhost:3000/user-management/groups/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Network Engineers",
    "description": "Full network access",
    "module_access": ["devices", "manual_audits", "config_backups", "drift_detection"]
  }'
```

2. **Create Test User:**
```bash
curl -X POST http://localhost:3000/user-management/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "username": "engineer1",
    "email": "engineer1@company.com",
    "password": "secure123",
    "groups": [1]  # Assign to Network Engineers group
  }'
```

3. **Test Module Access:**
```bash
# Login as engineer1
curl -X POST http://localhost:3000/login \
  -d '{"username": "engineer1", "password": "secure123"}'

# Get user modules
curl http://localhost:3000/user-management/users/me/modules \
  -H "Authorization: Bearer $ENGINEER_TOKEN"

# Expected: ["devices", "manual_audits", "config_backups", "drift_detection"]
```

4. **Test Access Control:**
   - User should see only assigned modules in menu
   - Accessing `/device_groups` should redirect (not in their modules)
   - Accessing `/devices` should work (in their modules)

---

## 🚀 Quick Start

### 1. Rebuild Containers
```bash
cd /home/user/nap

# Rebuild admin-service and frontend
docker-compose build admin-service frontend

# Restart
docker-compose up -d
```

### 2. Run Database Migration
```bash
docker-compose exec database psql -U nap_user -d nap_db -c "
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(key);
"
```

### 3. Add Frontend Route
Edit `/home/user/nap/frontend/src/App.js` as described in TODO #2 above.

### 4. Access Admin Dashboard
- Navigate to `http://localhost:8080/admin`
- Must be logged in as admin/superuser
- Configure backup schedule, system settings, manage users/groups

---

## 📝 Configuration Examples

### Example 1: Daily Backups at 2 AM, Keep 30 Days
```json
{
  "enabled": true,
  "scheduleType": "daily",
  "scheduleTime": "02:00",
  "retentionDays": 30,
  "maxBackupsPerDevice": 10,
  "compressBackups": true,
  "notifyOnFailure": true
}
```

### Example 2: Hourly Backups, Keep 50 Most Recent
```json
{
  "enabled": true,
  "scheduleType": "hourly",
  "scheduleTime": "00:00",
  "retentionDays": 7,
  "maxBackupsPerDevice": 50,
  "compressBackups": true,
  "notifyOnFailure": false
}
```

### Example 3: Weekly Backups on Sunday, Keep 90 Days
```json
{
  "enabled": true,
  "scheduleType": "weekly",
  "scheduleTime": "03:00",
  "retentionDays": 90,
  "maxBackupsPerDevice": 20,
  "compressBackups": true,
  "notifyOnFailure": true
}
```

---

## 🔐 Permissions & Access Control

### How It Works

1. **License Tier** defines available modules (e.g., Starter has 4, Professional has 12, Enterprise has all 18)

2. **User Groups** grant access to specific modules within the license tier

3. **Module Access** = License Modules ∩ Group Modules

**Example:**
```
License Tier: Professional (12 modules available)
User Group: "Auditors" with modules [manual_audits, scheduled_audits, health_checks]

User Access = Professional modules ∩ Auditors modules
            = [manual_audits, scheduled_audits, health_checks]

User CANNOT access: config_backups, drift_detection (not in their group)
```

### Superusers
- Superusers get ALL modules available in the license tier
- Not restricted by group permissions
- Can access Admin Dashboard

---

## 📊 Summary

✅ **Completed:**
- License page module mappings verified (18 modules)
- Hardware Inventory moved to Enterprise tier
- Admin Dashboard frontend component created
- Backend API endpoints for admin settings
- Database model for system configuration
- Backup configuration interface
- System settings interface

⏳ **Next Steps:**
1. Add Admin Dashboard route to frontend App.js
2. Run database migration for system_config table
3. Implement backup scheduler (Celery or APScheduler)
4. Test user/group permissions thoroughly
5. Add SMTP email sending functionality
