# Frontend Features Guide

## Overview
This guide documents all frontend features available in the Network Audit Platform, including the newly implemented advanced enterprise features.

## Core Features (12 Total)

### 1. Dashboard
- **Path**: `/`
- **Component**: `Dashboard.js`
- **Features**: Overview of compliance status, recent audits, device health metrics

### 2. Device Management
- **Path**: `/devices`
- **Component**: `DeviceManagement.js`
- **Features**: Add, edit, delete network devices; manage credentials; test connectivity

### 3. Device Groups
- **Path**: `/device-groups`
- **Component**: `DeviceGroups.js`
- **Features**: Create and manage logical device groupings; bulk operations

### 4. Discovery Groups
- **Path**: `/discovery-groups`
- **Component**: `DiscoveryGroups.js`
- **Features**: Configure network device auto-discovery; scheduled discovery tasks

### 5. Device Import
- **Path**: `/device-import`
- **Component**: `DeviceImport.js`
- **Features**: Bulk import devices via CSV; template download; import validation

### 6. Audit Results
- **Path**: `/audits`
- **Component**: `AuditResults.js`
- **Features**: View compliance audit results; filter by device, rule, status; export reports

### 7. Audit Schedules
- **Path**: `/audit-schedules`
- **Component**: `AuditSchedules.js`
- **Features**: Schedule recurring audits; cron-based scheduling; manage audit jobs

### 8. Rule Management
- **Path**: `/rules`
- **Component**: `RuleManagement.js`
- **Features**: Create custom compliance rules; YANG/XPath/CLI rule types; rule testing

### 9. Rule Templates
- **Path**: `/rule-templates`
- **Component**: `RuleTemplates.js`
- **Features**: Pre-built rule library; import/export templates; customize rules

### 10. Config Backups
- **Path**: `/config-backups`
- **Component**: `ConfigBackups.js`
- **Features**: Automated configuration backups; version history; restore capabilities

### 11. Drift Detection
- **Path**: `/drift-detection`
- **Component**: `DriftDetection.js`
- **Features**: Detect unauthorized configuration changes; drift alerts; baseline management

### 12. Notifications
- **Path**: `/notifications`
- **Component**: `Notifications.js`
- **Features**: Email notifications; webhook integrations; notification rules

### 13. Device Health
- **Path**: `/health`
- **Component**: `DeviceHealth.js`
- **Features**: Real-time device health monitoring; CPU, memory, interface stats

---

## Advanced Features (5 Total - New!)

### 1. Integration Hub 🆕
- **Path**: `/integrations`
- **Component**: `Integrations.js`
- **Icon**: Hub
- **Features**:
  - **NetBox Integration**: Sync devices with NetBox IPAM/DCIM
  - **Git Integration**: Store configs in Git repositories
  - **Ansible Integration**: Trigger Ansible playbooks
  - **ServiceNow Integration**: Create tickets for compliance failures
  - **Prometheus Integration**: Export metrics to Prometheus
  - Auto-sync capabilities with configurable intervals
  - Test connection functionality
  - Integration logs and status tracking

#### Integration Types Supported:
1. **NetBox** - IPAM/DCIM synchronization
   - URL configuration
   - API token authentication
   - Device sync

2. **Git** - Configuration version control
   - Repository URL
   - Branch selection
   - Access token authentication

3. **Ansible Tower/AWX** - Automation platform
   - Tower/AWX URL
   - Username/password authentication
   - Playbook execution

4. **ServiceNow** - ITSM platform
   - Instance URL
   - User credentials
   - Automated ticket creation

5. **Prometheus** - Metrics monitoring
   - Pushgateway URL
   - Job name configuration
   - Metrics export at `/integrations/prometheus/metrics`

### 2. Licensing Management 🆕
- **Path**: `/licensing`
- **Component**: `Licensing.js`
- **Icon**: MonetizationOn
- **Features**:
  - Track software licenses across all devices
  - License types: Perpetual, Subscription, Term-Based, Evaluation
  - Expiration tracking with alerts (30-day, 90-day warnings)
  - Capacity usage monitoring with visual indicators
  - Cost tracking and reporting
  - Software inventory automatically discovered from devices
  - License alerts with acknowledgment workflow

#### License Management Tabs:
1. **Licenses**: Full license inventory with expiration dates, capacity usage, costs
2. **Alerts**: Active license alerts (expiring, over-capacity, expired)
3. **Software Inventory**: Discovered software on all devices

#### Statistics Dashboard:
- Total licenses count
- Active licenses
- Licenses expiring soon
- Total licensing cost

### 3. Network Topology 🆕
- **Path**: `/topology`
- **Component**: `Topology.js`
- **Icon**: DeviceHub
- **Features**:
  - Visual network topology graph with interactive canvas
  - LLDP/CDP-based automatic discovery
  - Node types: Routers, Switches, Firewalls, Servers
  - Color-coded by device type
  - Discovery session management with progress tracking
  - Configurable discovery depth (1-10 hops)
  - Real-time topology updates
  - Node list view with detailed information

#### Topology Views:
1. **Topology Graph**: Interactive visual network map
   - Canvas-based rendering
   - Color-coded nodes (Router: Blue, Switch: Green, Firewall: Red, Server: Orange)
   - Link visualization
   - Legend for device types

2. **Node List**: Tabular view of discovered devices
   - Hostname, IP address
   - Device type
   - Discovery method (LLDP, CDP, ARP, manual)
   - Last seen timestamp
   - Active status

#### Discovery Features:
- Seed device selection
- Maximum hop depth configuration (1, 2, 3, 5, 10 hops)
- Background discovery with progress tracking
- Automatic graph updates on completion

### 4. Configuration Templates 🆕
- **Path**: `/config-templates`
- **Component**: `ConfigTemplates.js`
- **Icon**: Description
- **Features**:
  - Template library with categorization
  - Variable substitution ({{variable_name}} syntax)
  - Multi-vendor support (Cisco, Juniper, Arista, Palo Alto)
  - Template deployment to devices
  - Built-in and custom templates
  - Template preview functionality
  - Copy/modify templates
  - Deployment tracking

#### Template Categories:
- **Security**: Firewall rules, ACLs, security policies
- **QoS**: Quality of Service configurations
- **Routing**: BGP, OSPF, static routes
- **Interfaces**: Interface configs, VLANs
- **System**: System-level settings, logging, NTP
- **Monitoring**: SNMP, NetFlow, syslog
- **VPN**: VPN configurations
- **ACL**: Access control lists

#### Template Views:
1. **Templates List**: All templates with filtering by category
2. **Browse by Category**: Card-based browsing grouped by category

#### Template Deployment:
- Select target device
- Fill in template variables
- Preview before deployment
- Deployment status tracking

### 5. Analytics & Forecasting 🆕
- **Path**: `/analytics`
- **Component**: `Analytics.js`
- **Icon**: Timeline
- **Features**:
  - Compliance trend analysis with historical data
  - ML-based compliance forecasting
  - Statistical anomaly detection
  - Time-series analysis (7, 14, 30, 90 days)
  - Configurable forecast periods
  - Anomaly acknowledgment workflow
  - Dashboard summary statistics

#### Analytics Tabs:
1. **Trends**: Historical compliance trends
   - Overall compliance percentage
   - Compliance change over time
   - Device counts (total, compliant, failed)
   - Create snapshots for trend tracking

2. **Forecasts**: Predictive compliance analysis
   - Predicted compliance scores
   - Confidence scores
   - Per-device or global forecasts
   - Configurable forecast periods (7, 14, 30, 90 days)

3. **Anomalies**: Unusual pattern detection
   - Anomaly type classification
   - Severity levels (Critical, High, Medium, Low)
   - Z-score statistical measure
   - Device-specific anomalies
   - Acknowledgment workflow

#### Summary Statistics:
- Average compliance (7-day rolling)
- Recent anomalies count
- Devices at risk
- Total trend data points

---

## Navigation Structure

### Main Navigation Menu
The application features a sidebar navigation with the following sections:

**Core Features** (above divider):
- Dashboard
- Devices
- Device Groups
- Discovery Groups
- Device Import
- Audit Results
- Audit Schedules
- Rule Management
- Rule Templates
- Config Backups
- Drift Detection
- Notifications
- Device Health

**Advanced Features** (below divider):
- Integration Hub 🆕
- Licensing 🆕
- Topology 🆕
- Config Templates 🆕
- Analytics 🆕

### Theme Support
- **Light Mode**: Default clean interface
- **Dark Mode**: Toggle available in top-right corner
- Persistent theme selection across sessions

---

## API Integration

All frontend components use the centralized API client located in `frontend/src/api/api.js`:

### API Endpoints by Feature:

**Integrations API**:
- `GET /integrations/` - List all integrations
- `POST /integrations/` - Create integration
- `PUT /integrations/{id}` - Update integration
- `DELETE /integrations/{id}` - Delete integration
- `POST /integrations/{id}/test` - Test connection
- `POST /integrations/{id}/sync` - Trigger sync
- `GET /integrations/{id}/logs` - Get integration logs
- `GET /integrations/prometheus/metrics` - Export Prometheus metrics

**Licensing API**:
- `GET /licensing/` - List licenses
- `POST /licensing/` - Create license
- `PUT /licensing/{id}` - Update license
- `DELETE /licensing/{id}` - Delete license
- `GET /licensing/alerts/` - Get license alerts
- `POST /licensing/alerts/{id}/acknowledge` - Acknowledge alert
- `GET /licensing/software/` - Get software inventory
- `GET /licensing/stats/summary` - Get statistics

**Topology API**:
- `GET /topology/graph` - Get topology graph data
- `GET /topology/nodes` - List topology nodes
- `POST /topology/discover` - Start discovery session
- `GET /topology/discovery/{session_id}` - Get discovery status

**Config Templates API**:
- `GET /config-templates/` - List templates
- `POST /config-templates/` - Create template
- `PUT /config-templates/{id}` - Update template
- `DELETE /config-templates/{id}` - Delete template
- `POST /config-templates/deploy` - Deploy template
- `GET /config-templates/categories/list` - List categories

**Analytics API**:
- `GET /analytics/trends` - Get compliance trends
- `POST /analytics/trends/snapshot` - Create snapshot
- `GET /analytics/forecast` - Get forecasts
- `POST /analytics/forecast/generate` - Generate forecast
- `GET /analytics/anomalies` - Get anomalies
- `POST /analytics/anomalies/detect` - Detect anomalies
- `POST /analytics/anomalies/{id}/acknowledge` - Acknowledge anomaly
- `GET /analytics/dashboard/summary` - Get dashboard summary

---

## Component Architecture

### Design Patterns
All frontend components follow consistent patterns:

1. **Material-UI (MUI)**: All components use MUI v5 for consistent design
2. **State Management**: React hooks (useState, useEffect) for local state
3. **API Calls**: Centralized API client with axios interceptors
4. **Loading States**: CircularProgress indicators during data fetching
5. **Error Handling**: Alert components for user feedback
6. **Responsive Design**: Mobile-friendly with drawer navigation
7. **Tabs**: Multi-view components use MUI Tabs
8. **Dialogs**: Modal dialogs for create/edit operations
9. **Tables**: MUI Table components for data display
10. **Cards**: Statistics displayed in MUI Card components

### Common UI Elements

**Statistics Cards**:
- Grid layout (xs=12, sm=6, md=3)
- Icon + metric display
- Color-coded by status

**Data Tables**:
- TableContainer with pagination support
- Sortable columns
- Action buttons (Edit, Delete, etc.)
- Empty state messages

**Forms**:
- Dialog-based forms
- Validation feedback
- Material-UI form controls
- Grid layout for multi-column forms

**Alerts & Notifications**:
- Success/Error alerts at page top
- Dismissible alerts
- Severity-based color coding

---

## Testing Guide

### Testing Each Feature

**Integration Hub**:
1. Navigate to `/integrations`
2. Click "Add Integration"
3. Select integration type (NetBox, Git, etc.)
4. Fill in configuration details
5. Test connection
6. Enable auto-sync if desired
7. View integration logs

**Licensing**:
1. Navigate to `/licensing`
2. View statistics dashboard
3. Click "Add License"
4. Fill in license details (name, type, expiration, cost)
5. Track capacity usage
6. View alerts tab for expiring licenses
7. Check software inventory tab

**Topology**:
1. Navigate to `/topology`
2. View current topology graph (if available)
3. Click "Start Discovery"
4. Select seed device IDs
5. Choose maximum discovery depth
6. Monitor discovery progress
7. View updated topology graph
8. Switch to "Node List" tab for details

**Config Templates**:
1. Navigate to `/config-templates`
2. Browse templates by category
3. Click "Create Template"
4. Define template with variables ({{var_name}})
5. Preview template
6. Deploy to device
7. Fill in variable values
8. Track deployment

**Analytics**:
1. Navigate to `/analytics`
2. View summary statistics
3. Create trend snapshots
4. Generate forecasts
5. Run anomaly detection
6. Acknowledge anomalies
7. Adjust time range filter

---

## Deployment Notes

### Environment Requirements
- Node.js 14+ for frontend build
- React 18.x
- Material-UI v5
- Axios for API calls

### Build & Deploy
```bash
cd frontend
npm install
npm run build
# Serve build directory with your preferred web server
```

### Configuration
API base URL is configured in `frontend/src/api/api.js`:
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

Set environment variable `REACT_APP_API_URL` for production deployments.

---

## Future Enhancements

### Planned Features
1. **Integration Hub**: Add more integration types (Slack, Teams, Jira)
2. **Licensing**: Auto-discovery improvements, cost optimization suggestions
3. **Topology**: Interactive graph with zoom/pan, export to PNG/SVG
4. **Config Templates**: Template versioning, approval workflows
5. **Analytics**: Advanced ML models, predictive maintenance, capacity planning

### Known Limitations
- Topology graph currently uses basic canvas rendering (consider D3.js or Cytoscape.js)
- Analytics forecasting requires sufficient historical data for accuracy
- Integration sync is manual or scheduled (no real-time sync)
- Template variable validation is basic (no type checking)

---

## Support & Documentation

### Additional Resources
- **API Documentation**: `/docs` endpoint on backend server
- **User Guide**: See main README.md
- **Configuration Guide**: See CONFIGURATION.md
- **Feature Status**: See FEATURE_STATUS_REVIEW.md

### Getting Help
For issues or questions:
1. Check FEATURE_STATUS_REVIEW.md for known limitations
2. Review API documentation at backend `/docs`
3. Check browser console for frontend errors
4. Review backend logs for API errors

---

**Last Updated**: 2025-11-22
**Frontend Version**: 2.0.0
**Total Features**: 17 (12 Core + 5 Advanced)
