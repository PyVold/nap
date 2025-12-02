# Complete Deployment Guide - Admin Dashboard & License System

## 🎯 What's Been Implemented

### ✅ 1. Admin Dashboard (6 Tabs)
- **System Settings**: Platform config, SMTP, security settings
- **Backup Configuration**: Automated backup scheduling
- **Users**: User management interface
- **Groups & Permissions**: Module-based access control
- **License**: Quick link to license page
- **System Health**: Service monitoring

### ✅ 2. Email Notification System
- SMTP configuration
- Multiple recipients support
- Notification templates:
  - Backup failures
  - Quota exceeded
  - License expiry warnings
  - Audit failures
- Test email functionality

### ✅ 3. Backup Scheduler
- APScheduler-based automated backups
- Schedule types: Hourly, Every 6/12h, Daily, Weekly, Monthly
- Retention management (days + max per device)
- Automatic cleanup of old backups
- Email alerts on failures

### ✅ 4. Frontend Integration
- Admin Dashboard route at `/admin`
- Admin-only menu item
- All components wired up

### ✅ 5. Database Migration
- `system_config` table for settings storage
- Default configurations pre-populated

---

## 🚀 Deployment Steps

### Step 1: Pull Latest Code

```bash
cd /home/user/nap
git pull origin claude/license-tier-modules-01Et6P4RTHAeNFgWxUu5iBYg
```

### Step 2: Add APScheduler Dependency

Add to `/home/user/nap/requirements.txt`:
```
APScheduler==3.10.4
```

Or if you have separate requirements per service, add to:
- `/home/user/nap/services/admin-service/requirements.txt`
- `/home/user/nap/services/backup-service/requirements.txt` (if exists)

### Step 3: Run Database Migration

```bash
cd /home/user/nap

# Make migration script executable
chmod +x run_migration.sh

# Run migration
./run_migration.sh migrations/001_add_system_config_table.sql
```

**Expected Output:**
```
✅ Migration completed successfully!
config_count: 3
```

**Manual Alternative:**
```bash
docker-compose exec database psql -U nap_user -d nap_db < migrations/001_add_system_config_table.sql
```

### Step 4: Initialize Backup Scheduler in Admin Service

Add to `/home/user/nap/services/admin-service/app/main.py` in the startup event:

```python
@app.on_event("startup")
async def startup_event():
    # ... existing code ...

    # Initialize backup scheduler
    try:
        import sys
        sys.path.insert(0, '/app')
        from shared.backup_scheduler import backup_scheduler
        from shared.database import SessionLocal

        db = SessionLocal()
        backup_scheduler.load_and_update_schedule(db)
        db.close()

        logger.info("✅ Backup scheduler initialized")
    except Exception as e:
        logger.error(f"❌ Error initializing backup scheduler: {e}")
```

And in the shutdown event:

```python
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        from shared.backup_scheduler import backup_scheduler
        backup_scheduler.shutdown()
        logger.info("Backup scheduler shutdown")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")
```

### Step 5: Rebuild Containers

```bash
cd /home/user/nap

# Stop all containers
docker-compose down

# Rebuild affected services
docker-compose build admin-service frontend

# Start everything
docker-compose up -d

# Check logs
docker-compose logs -f admin-service | grep -E "scheduler|Backup"
```

**Expected in logs:**
```
✅ Backup scheduler initialized
Scheduled daily backups at 02:00
```

### Step 6: Verify Deployment

#### 6.1 Check Database Migration

```bash
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT key, description FROM system_config;"
```

**Expected:**
```
       key           |          description
---------------------+-------------------------------
 backup_config       | Automatic backup configuration
 system_settings     | General system settings
 notification_settings| Email notification settings
```

#### 6.2 Access Admin Dashboard

1. Navigate to: `http://localhost:8080/admin`
2. **Login as admin** (must be superuser)
3. You should see 6 tabs

#### 6.3 Test Backup Configuration

1. Go to **Admin Dashboard → Backup Config** tab
2. Configure schedule (e.g., Daily at 02:00)
3. Click **Save Backup Configuration**
4. Check logs:

```bash
docker-compose logs admin-service | grep "Scheduled"
```

Should show: `Scheduled daily backups at 02:00`

#### 6.4 Test Email Notifications

1. Go to **Admin Dashboard → System Settings** tab
2. Enable SMTP
3. Configure:
   - **SMTP Server**: `smtp.gmail.com` (or your SMTP server)
   - **SMTP Port**: `587`
   - **Username**: Your email
   - **Password**: App password
4. Save settings
5. Click **Send Test Email**

**Expected:** Email arrives with subject `[NAP] Test Email - SMTP Configuration`

#### 6.5 Configure Notification Recipients

1. Create `/admin/notification-settings` tab in frontend (TODO)
2. Or manually via API:

```bash
curl -X POST http://localhost:3000/admin/notification-settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "emailEnabled": true,
    "emailRecipients": ["admin@company.com", "ops@company.com"],
    "notifyOnBackupFailure": true,
    "notifyOnLicenseExpiry": true,
    "notifyOnQuotaExceeded": true,
    "notifyOnAuditFailure": true
  }'
```

---

## 📧 Email Notification Configuration

### Gmail Setup (Example)

1. **Enable 2FA** on your Gmail account
2. **Create App Password**:
   - Google Account → Security → 2-Step Verification → App Passwords
   - Generate password for "Mail"
3. **Configure in Admin Dashboard**:
   - SMTP Server: `smtp.gmail.com`
   - SMTP Port: `587`
   - Username: `your-email@gmail.com`
   - Password: `<app-password>`

### Local SMTP Server (For Testing)

```bash
# Install and run local SMTP server
pip install aiosmtpd

# Run on port 1025
python -m aiosmtpd -n -l localhost:1025
```

Configure in Admin Dashboard:
- SMTP Server: `localhost`
- SMTP Port: `1025`
- Username: (leave blank)
- Password: (leave blank)

All emails will be printed to console.

---

## 🔧 API Endpoints Summary

### Admin Settings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/backup-config` | GET | Get backup configuration |
| `/admin/backup-config` | POST | Save backup configuration |
| `/admin/system-settings` | GET | Get system settings |
| `/admin/system-settings` | POST | Save system settings |
| `/admin/notification-settings` | GET | Get notification settings |
| `/admin/notification-settings` | POST | Save notification settings |
| `/admin/test-email` | POST | Send test email |

### Example: Update Backup Schedule

```bash
curl -X POST http://localhost:3000/admin/backup-config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "scheduleType": "daily",
    "scheduleTime": "03:00",
    "retentionDays": 30,
    "maxBackupsPerDevice": 15,
    "compressBackups": true,
    "notifyOnFailure": true
  }'
```

---

## 🧪 Testing

### Test 1: Verify License Page Module Display

```bash
# Login and get token
TOKEN=$(curl -X POST http://localhost:3000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token')

# Get license status
curl http://localhost:3000/license/status \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.enabled_modules'
```

**For Starter:** Should show 4 modules
**For Professional:** Should show 12 modules
**For Enterprise:** Should show all 18 modules

### Test 2: Hardware Inventory Access

```bash
# As Starter license user, try to access hardware inventory
curl http://localhost:3000/hardware-inventory \
  -H "Authorization: Bearer $TOKEN"
```

**Starter/Pro:** Should return 403 Forbidden
**Enterprise:** Should return 200 OK

### Test 3: User Group Permissions

```bash
# Create a test group with limited modules
curl -X POST http://localhost:3000/user-management/groups/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auditors",
    "description": "Audit-only access",
    "module_access": ["manual_audits", "health_checks"]
  }'

# Create a test user and assign to group
curl -X POST http://localhost:3000/user-management/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "auditor1",
    "email": "auditor@company.com",
    "password": "secure123",
    "groups": [1]
  }'

# Login as auditor1
AUDITOR_TOKEN=$(curl -X POST http://localhost:3000/login \
  -d '{"username":"auditor1","password":"secure123"}' \
  | jq -r '.access_token')

# Check their modules
curl http://localhost:3000/user-management/users/me/modules \
  -H "Authorization: Bearer $AUDITOR_TOKEN"
```

**Expected:** `["manual_audits", "health_checks"]` (only what their group allows)

### Test 4: Backup Scheduler Execution

```bash
# Trigger manual backup (if endpoint exists)
curl -X POST http://localhost:3000/admin/trigger-backup \
  -H "Authorization: Bearer $TOKEN"

# Check backup was created
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT device_id, backup_type, created_at FROM config_backups ORDER BY created_at DESC LIMIT 5;"
```

### Test 5: Email Notification Sending

```bash
# Manually trigger a notification
curl -X POST http://localhost:3000/admin/test-notification \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "backup_failure",
    "device": "router1.example.com",
    "error": "Connection timeout"
  }'
```

Check your email inbox for the notification.

---

## 🐛 Troubleshooting

### Issue: Admin Dashboard not accessible

**Symptoms:** 404 error on `/admin`

**Fix:**
```bash
# Verify frontend was rebuilt
docker-compose images frontend

# If old, rebuild
docker-compose build frontend
docker-compose up -d frontend

# Clear browser cache (Ctrl+Shift+R)
```

### Issue: Database migration failed

**Symptoms:** `relation "system_config" does not exist`

**Fix:**
```bash
# Check if table exists
docker-compose exec database psql -U nap_user -d nap_db -c "\d system_config"

# If not, run migration manually
docker-compose exec database psql -U nap_user -d nap_db < migrations/001_add_system_config_table.sql
```

### Issue: Backup scheduler not running

**Symptoms:** No scheduled backups being created

**Fix:**
```bash
# Check admin-service logs
docker-compose logs admin-service | grep scheduler

# Should show: "Backup scheduler initialized"
# If not, verify APScheduler is installed
docker-compose exec admin-service pip list | grep APScheduler

# If missing, install
docker-compose exec admin-service pip install APScheduler==3.10.4

# Restart
docker-compose restart admin-service
```

### Issue: Email not sending

**Symptoms:** "SMTP is not enabled" or "SMTP authentication failed"

**Fix:**
1. Verify SMTP settings in Admin Dashboard → System Settings
2. Check SMTP enabled checkbox is checked
3. For Gmail, ensure you're using an App Password, not your regular password
4. Test connectivity:

```bash
# Test SMTP connection
docker-compose exec admin-service python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.ehlo()
server.starttls()
server.login('your-email@gmail.com', 'app-password')
print('SUCCESS: SMTP connection works!')
server.quit()
"
```

### Issue: Hardware Inventory showing in Starter

**Symptoms:** Menu shows Hardware Inventory for Starter/Pro licenses

**Fix:**
```bash
# Verify module mapping
curl http://localhost:3000/license/module-mappings | jq '.mappings.hardware_inventory'

# Should return: "hardware_inventory" (not "devices")

# Clear frontend cache and hard refresh (Ctrl+Shift+R)
```

---

## 📊 Expected Behavior Summary

### License Tier Module Display

**Starter (4 modules):**
- ✅ Devices, Manual Audits, Basic Rules, Health Checks
- ❌ Everything else including Hardware Inventory

**Professional (12 modules):**
- ✅ All Starter + Scheduled Audits, Templates, Backups, Drift, Groups, Discovery, Webhooks
- ❌ Hardware Inventory, Integrations, Workflows, Analytics

**Enterprise (18 modules):**
- ✅ All modules including Hardware Inventory

### Admin Dashboard Access

- **Superusers**: ✅ Can access `/admin`
- **Regular users**: ❌ Redirected to dashboard

### Email Notifications

When enabled, sends emails for:
- ❌ Backup failures
- ⚠️ License expiring soon
- 🚫 Quota exceeded
- ❌ Audit failures

---

## 🎯 Next Steps

1. ✅ Run migration: `./run_migration.sh`
2. ✅ Rebuild containers: `docker-compose build && docker-compose up -d`
3. ✅ Configure SMTP in Admin Dashboard
4. ✅ Set backup schedule
5. ✅ Add notification recipients
6. ✅ Test email sending
7. ⏳ Monitor logs for scheduled backups
8. ⏳ Create test users/groups for permission testing

---

## 📝 Additional Configuration

### Add Notification Settings Tab to Frontend (TODO)

The backend endpoints exist, but frontend tab needs to be added to AdminDashboard.jsx:

```jsx
// Add to AdminDashboard.jsx
<Tab icon={<EmailIcon />} label="Notifications" />

// Add TabPanel with form for:
// - Email enabled checkbox
// - Email recipients (multi-input)
// - Checkboxes for each notification type
```

This allows configuring which emails receive notifications through the UI.

---

**Status:** Ready for deployment! 🚀

All code committed and pushed to: `claude/license-tier-modules-01Et6P4RTHAeNFgWxUu5iBYg`
