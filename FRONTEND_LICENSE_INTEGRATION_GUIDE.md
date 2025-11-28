# Frontend License Integration Guide

**Created**: November 28, 2025
**Purpose**: How to integrate the license management UI into your existing React app

---

## Files Created

✅ `/workspace/frontend/src/components/LicenseManagement.jsx` - Main license management page
✅ `/workspace/frontend/src/contexts/LicenseContext.jsx` - License state management
✅ `/workspace/frontend/src/components/UpgradePrompt.jsx` - Upgrade prompt component
✅ `/workspace/frontend/src/components/AuditSchedulesWrapper.jsx` - Example wrapper

---

## Step 1: Wrap App with License Provider

Update your `frontend/src/App.js`:

```jsx
// frontend/src/App.js

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';

// Import License Provider
import { LicenseProvider } from './contexts/LicenseContext';

// Import components
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Devices from './components/Devices';
import Rules from './components/Rules';
import Audits from './components/Audits';
import LicenseManagement from './components/LicenseManagement';
import AuditSchedulesWrapper from './components/AuditSchedulesWrapper';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <LicenseProvider>  {/* ← Add this wrapper */}
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/rules" element={<Rules />} />
              <Route path="/audits" element={<Audits />} />
              
              {/* License management route */}
              <Route path="/license" element={<LicenseManagement />} />
              
              {/* Protected route example */}
              <Route path="/audit-schedules" element={<AuditSchedulesWrapper />} />
            </Routes>
          </Layout>
        </Router>
      </LicenseProvider>  {/* ← Close wrapper */}
    </ThemeProvider>
  );
}

export default App;
```

---

## Step 2: Add License Menu Item to Navigation

Update your navigation component (e.g., `Sidebar.jsx` or `Layout.jsx`):

```jsx
// frontend/src/components/Sidebar.jsx

import React from 'react';
import { List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import DevicesIcon from '@mui/icons-material/Router';
import RuleIcon from '@mui/icons-material/Rule';
import AssessmentIcon from '@mui/icons-material/Assessment';
import KeyIcon from '@mui/icons-material/Key'; // ← Add this

// Import license context
import { useLicense } from '../contexts/LicenseContext';

export default function Sidebar() {
  const navigate = useNavigate();
  const { isExpiringSoon, getDaysUntilExpiry } = useLicense();

  const menuItems = [
    { label: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    { label: 'Devices', icon: <DevicesIcon />, path: '/devices' },
    { label: 'Rules', icon: <RuleIcon />, path: '/rules' },
    { label: 'Audits', icon: <AssessmentIcon />, path: '/audits' },
    { 
      label: 'License', 
      icon: <KeyIcon />, 
      path: '/license',
      badge: isExpiringSoon() ? `${getDaysUntilExpiry()}d` : null,
      badgeColor: 'warning'
    },
  ];

  return (
    <List>
      {menuItems.map((item) => (
        <ListItem
          button
          key={item.path}
          onClick={() => navigate(item.path)}
        >
          <ListItemIcon>{item.icon}</ListItemIcon>
          <ListItemText 
            primary={item.label}
            secondary={item.badge}
          />
        </ListItem>
      ))}
    </List>
  );
}
```

---

## Step 3: Protect Features with License Checks

### Method 1: Using the Hook Directly

```jsx
// frontend/src/components/SomeFeature.jsx

import React from 'react';
import { useLicense } from '../contexts/LicenseContext';
import UpgradePrompt from './UpgradePrompt';

export default function SomeFeature() {
  const { hasModule } = useLicense();

  // Check if user has access
  if (!hasModule('feature_name')) {
    return (
      <UpgradePrompt
        module="feature_name"
        featureName="Feature Display Name"
        description="What this feature does..."
        requiredTier="professional"
      />
    );
  }

  // Normal feature code
  return (
    <div>
      Your feature content here
    </div>
  );
}
```

### Method 2: Using the HOC (Higher-Order Component)

```jsx
// frontend/src/components/AdvancedFeature.jsx

import React from 'react';
import { withLicenseCheck } from './UpgradePrompt';

function AdvancedFeature() {
  return (
    <div>
      Your feature content here
    </div>
  );
}

// Wrap with license check
export default withLicenseCheck(
  AdvancedFeature,
  'advanced_feature',
  'Advanced Feature',
  'This feature provides advanced capabilities...'
);
```

### Method 3: Conditionally Show UI Elements

```jsx
// frontend/src/components/Dashboard.jsx

import React from 'react';
import { Button } from '@mui/material';
import { useLicense } from '../contexts/LicenseContext';

export default function Dashboard() {
  const { hasModule, isWithinQuota } = useLicense();

  return (
    <div>
      <h1>Dashboard</h1>
      
      {/* Show button only if user has the module */}
      {hasModule('scheduled_audits') && (
        <Button onClick={handleScheduleAudit}>
          Schedule Audit
        </Button>
      )}
      
      {/* Show warning if approaching quota */}
      {!isWithinQuota('devices') && (
        <Alert severity="warning">
          You've reached your device limit. Please upgrade to add more devices.
        </Alert>
      )}
    </div>
  );
}
```

---

## Step 4: Show License Info in Header/Navbar

```jsx
// frontend/src/components/Header.jsx

import React from 'react';
import { AppBar, Toolbar, Typography, Chip, Box } from '@mui/material';
import { useLicense } from '../contexts/LicenseContext';

export default function Header() {
  const { 
    getTierDisplayName, 
    isExpiringSoon, 
    getDaysUntilExpiry,
    hasLicense 
  } = useLicense();

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Network Audit Platform
        </Typography>
        
        {hasLicense && (
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={getTierDisplayName()}
              color="secondary"
              size="small"
            />
            
            {isExpiringSoon() && (
              <Chip
                label={`Expires in ${getDaysUntilExpiry()} days`}
                color="warning"
                size="small"
              />
            )}
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
}
```

---

## Step 5: Add License Check Before API Calls

Handle quota errors gracefully:

```jsx
// frontend/src/components/Devices.jsx

import React, { useState } from 'react';
import { useLicense } from '../contexts/LicenseContext';
import api from '../api/api';

export default function Devices() {
  const { isWithinQuota, refetch } = useLicense();
  const [error, setError] = useState(null);

  const handleAddDevice = async (deviceData) => {
    // Check quota before attempting
    if (!isWithinQuota('devices')) {
      setError('Device quota exceeded. Please upgrade your license.');
      return;
    }

    try {
      await api.post('/devices/', deviceData);
      // Success
      refetch(); // Refresh license status to update usage
    } catch (err) {
      // Handle API errors
      if (err.response?.status === 403) {
        const detail = err.response.data.detail;
        if (detail.error === 'Device quota exceeded') {
          setError(`Quota exceeded: ${detail.current}/${detail.max} devices. Please upgrade.`);
        }
      } else {
        setError('Failed to add device');
      }
    }
  };

  return (
    <div>
      {error && <Alert severity="error">{error}</Alert>}
      {/* Rest of component */}
    </div>
  );
}
```

---

## Module Names Reference

Use these module names when checking license:

| Module Key | Display Name | Tier |
|-----------|--------------|------|
| `devices` | Device Management | Starter+ |
| `manual_audits` | Manual Audits | Starter+ |
| `basic_rules` | Basic Audit Rules | Starter+ |
| `health_checks` | Health Monitoring | Starter+ |
| `scheduled_audits` | Scheduled Audits | Professional+ |
| `api_access` | API Access | Professional+ |
| `config_backups` | Config Backups | Professional+ |
| `drift_detection` | Drift Detection | Professional+ |
| `webhooks` | Webhook Notifications | Professional+ |
| `rule_templates` | Rule Templates | Professional+ |
| `device_groups` | Device Groups | Professional+ |
| `discovery` | Device Discovery | Professional+ |
| `workflow_automation` | Workflow Automation | Enterprise+ |
| `topology` | Network Topology | Enterprise+ |
| `ai_features` | AI-Powered Features | Enterprise+ |
| `integrations` | Advanced Integrations | Enterprise+ |
| `sso` | SSO & SAML | Enterprise+ |

---

## Example: Protecting Existing Components

### Before (No License Check)

```jsx
// frontend/src/components/AuditSchedules.jsx

export default function AuditSchedules() {
  return (
    <div>
      {/* Audit schedule UI */}
    </div>
  );
}
```

### After (With License Check)

```jsx
// frontend/src/components/AuditSchedules.jsx

import { useLicense } from '../contexts/LicenseContext';
import UpgradePrompt from './UpgradePrompt';

export default function AuditSchedules() {
  const { hasModule } = useLicense();

  if (!hasModule('scheduled_audits')) {
    return (
      <UpgradePrompt
        module="scheduled_audits"
        featureName="Scheduled Audits"
        description="Automate your compliance checks with cron-based scheduling."
        requiredTier="professional"
      />
    );
  }

  return (
    <div>
      {/* Audit schedule UI */}
    </div>
  );
}
```

---

## Common Patterns

### Pattern 1: Conditional Button

```jsx
{hasModule('api_access') ? (
  <Button onClick={handleExport}>Export via API</Button>
) : (
  <Tooltip title="API access requires Professional plan">
    <span>
      <Button disabled>Export via API (Upgrade Required)</Button>
    </span>
  </Tooltip>
)}
```

### Pattern 2: Feature Teaser

```jsx
<Card>
  <CardContent>
    <Typography variant="h6">Workflow Automation</Typography>
    {hasModule('workflow_automation') ? (
      <Button onClick={handleOpenWorkflows}>Open Workflows</Button>
    ) : (
      <>
        <Typography color="text.secondary">
          Automate your network operations with visual workflows.
        </Typography>
        <Button variant="outlined" href="mailto:sales@yourcompany.com">
          Upgrade to Access
        </Button>
      </>
    )}
  </CardContent>
</Card>
```

### Pattern 3: Quota Warning

```jsx
const { getUsagePercentage } = useLicense();
const deviceUsage = getUsagePercentage('devices');

{deviceUsage > 80 && (
  <Alert severity="warning">
    You're using {deviceUsage.toFixed(0)}% of your device quota.
    <Button size="small" href="mailto:sales@yourcompany.com">
      Upgrade Plan
    </Button>
  </Alert>
)}
```

---

## Testing License System

### Test Scenarios

1. **No License Activated**
   - Should show "No License" page on `/license`
   - Should show upgrade prompts for all premium features

2. **Starter License**
   - Can access: devices, manual_audits, basic_rules
   - Cannot access: scheduled_audits, api_access, etc.
   - Shows upgrade prompts for premium features

3. **Professional License**
   - Can access most features
   - Cannot access: workflow_automation, ai_features, sso
   - Shows device/user quota warnings when approaching limits

4. **Enterprise License**
   - Can access all features
   - Shows unlimited on device/user counts
   - No upgrade prompts

5. **Expired License**
   - Shows "License Expired" warning on all pages
   - May block access to all features (depending on your policy)

---

## API Integration

Make sure your API client handles license errors:

```jsx
// frontend/src/api/api.js

import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:3000'
});

// Add response interceptor to handle license errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 402 Payment Required (license error)
    if (error.response?.status === 402) {
      const detail = error.response.data.detail;
      
      // Show notification or redirect to license page
      window.dispatchEvent(new CustomEvent('license-error', { 
        detail: { message: detail } 
      }));
    }
    
    // Handle 403 Forbidden (quota/feature error)
    if (error.response?.status === 403) {
      const detail = error.response.data.detail;
      
      if (detail.error === 'Device quota exceeded') {
        window.dispatchEvent(new CustomEvent('quota-exceeded', {
          detail: { type: 'devices', ...detail }
        }));
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
```

---

## Styling Tips

### Make Upgrade Prompts Stand Out

```jsx
// Use consistent colors for upgrade CTAs
const upgradeTheme = {
  primary: '#1976d2',
  warning: '#ff9800',
  success: '#4caf50'
};

// Add animations
<Button
  variant="contained"
  sx={{
    animation: 'pulse 2s infinite',
    '@keyframes pulse': {
      '0%, 100%': { transform: 'scale(1)' },
      '50%': { transform: 'scale(1.05)' }
    }
  }}
>
  Upgrade Now
</Button>
```

---

## Deployment Checklist

- [ ] LicenseProvider added to App.js
- [ ] License route added (`/license`)
- [ ] Navigation menu item added
- [ ] All premium features wrapped with license checks
- [ ] API error handling for license/quota errors
- [ ] Environment variables set (if using config from backend)
- [ ] Tested all license tiers (Starter, Professional, Enterprise)
- [ ] Tested quota warnings and errors
- [ ] Tested license expiration scenarios
- [ ] Tested license activation flow

---

## Summary

**What You Get**:
1. ✅ Beautiful license management page with module visualization
2. ✅ License context for easy access throughout app
3. ✅ Upgrade prompt component for locked features
4. ✅ Helper functions for checking modules, quotas, expiration
5. ✅ Example implementations for common patterns

**Time to Integrate**: 2-3 hours

**Files to Update**:
- `App.js` - Add LicenseProvider and route
- `Sidebar.jsx` - Add license menu item
- Existing feature components - Add license checks

**Ready to integrate? Follow the steps above!**
