# Frontend Testing Guide

## Overview
All Phase 1 & 2 features are now fully integrated into the React frontend with Material-UI components.

## Quick Start

### 1. Install Frontend Dependencies
```bash
cd frontend
npm install
```

### 2. Configure API URL
Edit `frontend/.env`:
```bash
REACT_APP_API_URL=http://localhost:3000
```

### 3. Start Backend API
```bash
# In root directory
python3 main.py
```

The API will start on http://localhost:3000

### 4. Start Frontend (in a new terminal)
```bash
cd frontend
npm start
```

The frontend will start on http://localhost:3001 (or next available port)

## New Features in Frontend

### 1. **Device Import** (`/device-import`)
**What you can do:**
- Download CSV template for bulk import
- Upload CSV file with multiple devices
- Export existing devices to CSV
- See import results with error reporting

**Testing:**
```bash
1. Click "Device Import" in sidebar
2. Click "Download CSV Template"
3. Fill in the template with test data
4. Click "Upload CSV File" and select the file
5. Review import results
6. Click "Export All Devices" to download current devices
```

### 2. **Rule Templates** (`/rule-templates`)
**What you can do:**
- Browse pre-built compliance rules (CIS, PCI-DSS, NIST, Best Practices)
- Initialize built-in templates
- Apply individual templates to create audit rules
- Apply entire compliance frameworks at once
- Filter by vendor and framework

**Testing:**
```bash
1. Click "Rule Templates" in sidebar
2. Click "Initialize Built-in Templates"
3. Browse templates grouped by framework (CIS, PCI-DSS, NIST)
4. Filter by vendor (Cisco XR, Nokia SROS)
5. Click "Apply" on individual template to create rule
6. Or click "Apply Compliance Framework" to apply all templates from a framework
```

### 3. **Config Backups** (`/config-backups`)
**What you can do:**
- View all configuration backups
- Filter backups by device
- View full configuration content
- Compare two backups (diff view)
- Create manual backups

**Testing:**
```bash
1. Click "Config Backups" in sidebar
2. Run an audit first to create automatic backups
3. Filter by device to see device-specific backups
4. Click eye icon to view full configuration
5. Select a device and click "Create Manual Backup"
```

### 4. **Drift Detection** (`/drift-detection`)
**What you can do:**
- View drift detection statistics
- Scan all devices for configuration drift
- Check individual device drift
- Set baseline configurations
- View drift details with diff highlighting

**Testing:**
```bash
1. Click "Drift Detection" in sidebar
2. Set baseline for a device using "Set Baseline" button
3. Make a configuration change on the device (manual or via audit)
4. Click "Scan All Devices" to detect drift
5. View drift details including lines changed and severity
6. Click "View Details" to see full diff
```

### 5. **Notifications** (`/notifications`)
**What you can do:**
- Configure notification webhooks (Slack, Teams, Discord, Generic)
- Set up event triggers with thresholds
- Test webhooks
- View notification statistics
- Enable/disable webhooks

**Testing:**
```bash
1. Click "Notifications" in sidebar
2. Click "Add Webhook"
3. Fill in webhook details:
   - Name: "Test Slack Webhook"
   - Webhook URL: (your Slack webhook URL)
   - Type: Slack
   - Enable "Audit Failure" with threshold 80%
4. Click Save
5. Click test icon to send test notification
6. View statistics cards showing success rate
```

## Navigation Structure

The sidebar now includes **13 menu items**:

1. **Dashboard** - Overview and statistics
2. **Devices** - Manage individual devices
3. **Device Groups** - Organize devices into groups
4. **Discovery Groups** - Subnet-based discovery configurations
5. **Device Import** ← NEW - Bulk import/export via CSV
6. **Audit Results** - View audit execution results
7. **Audit Schedules** - Configure scheduled audits
8. **Rule Management** - Create and manage audit rules
9. **Rule Templates** ← NEW - Browse and apply compliance templates
10. **Config Backups** ← NEW - View and manage configuration backups
11. **Drift Detection** ← NEW - Detect configuration drift
12. **Notifications** ← NEW - Configure webhook notifications
13. **Device Health** - Monitor device connectivity

## Feature Testing Workflows

### Workflow 1: Complete Compliance Setup
```
1. Go to "Rule Templates"
2. Click "Initialize Built-in Templates"
3. Click "Apply Compliance Framework"
4. Select "CIS" framework and "CISCO_XR" vendor
5. Click "Apply Framework"
6. Go to "Rule Management" to see all created rules
7. Run an audit on a device
8. View results in "Audit Results"
```

### Workflow 2: Automated Monitoring with Notifications
```
1. Go to "Notifications"
2. Add a Slack webhook with:
   - Audit Failure threshold: 80%
   - Config Change enabled
3. Go to "Devices" and run an audit
4. If compliance < 80%, receive Slack notification
5. Make a config change on device
6. Run another audit
7. Receive config change notification
```

### Workflow 3: Configuration Drift Monitoring
```
1. Go to "Drift Detection"
2. Click "Set Baseline" for a device
3. Make a manual configuration change on the device
4. Run an audit (creates new backup)
5. Click "Scan All Devices"
6. View detected drift with severity and line counts
7. Click "View Details" to see exact configuration changes
```

### Workflow 4: Bulk Device Onboarding
```
1. Go to "Device Import"
2. Click "Download CSV Template"
3. Fill template with device information:
   hostname,ip,vendor,port,username,password
   router1,192.168.1.1,CISCO_XR,830,admin,pass123
4. Click "Upload CSV File"
5. Review import results (created/updated/errors)
6. Go to "Devices" to see newly added devices
```

## API Endpoints Used by Frontend

### Device Import
- GET `/device-import/template` - Download CSV template
- POST `/device-import/upload` - Upload CSV file
- GET `/device-import/export` - Export devices

### Rule Templates
- POST `/rule-templates/initialize` - Initialize built-in templates
- GET `/rule-templates/` - List all templates
- GET `/rule-templates/frameworks` - Get frameworks
- GET `/rule-templates/categories` - Get categories
- POST `/rule-templates/apply` - Apply single template
- POST `/rule-templates/apply-framework` - Apply framework

### Config Backups
- GET `/config-backups/` - List all backups
- GET `/config-backups/{id}` - Get backup details
- POST `/config-backups/` - Create manual backup
- GET `/config-backups/device/{id}/history` - Get device backups
- GET `/config-backups/compare/{id1}/{id2}` - Compare backups

### Drift Detection
- GET `/drift-detection/summary` - Get statistics
- GET `/drift-detection/scan` - Scan all devices
- GET `/drift-detection/device/{id}` - Check device drift
- POST `/drift-detection/device/{id}/baseline` - Set baseline

### Notifications
- POST `/notifications/webhooks` - Create webhook
- GET `/notifications/webhooks` - List webhooks
- PATCH `/notifications/webhooks/{id}` - Update webhook
- DELETE `/notifications/webhooks/{id}` - Delete webhook
- POST `/notifications/webhooks/{id}/test` - Test webhook
- GET `/notifications/stats` - Get statistics

## Troubleshooting

### Frontend won't start
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
npm start
```

### API connection errors
- Verify backend is running: `curl http://localhost:3000/`
- Check `.env` file has correct `REACT_APP_API_URL`
- Check browser console for CORS errors

### Components not loading
- Check browser console for errors
- Verify all npm dependencies are installed
- Clear browser cache

## Dark Mode
Click the sun/moon icon in the top right to toggle dark mode. All components support dark mode with automatic color adjustments.

## Mobile Support
All components are mobile-responsive with collapsible sidebar navigation. Tap the menu icon to open/close the sidebar on mobile devices.

## Browser Compatibility
- Chrome/Edge (Recommended)
- Firefox
- Safari

## Next Steps
1. Build the frontend for production:
   ```bash
   cd frontend
   npm run build
   ```

2. The build output will be in `frontend/build/`

3. The FastAPI backend will automatically serve the frontend from `/app` when the build exists

4. Access the full application at: `http://localhost:3000/app`
