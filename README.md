# Network Audit Platform (NAP)

A comprehensive enterprise network audit and compliance platform for Cisco IOS-XR and Nokia SR OS routers. Automate configuration audits, ensure compliance, monitor device health, and manage network configuration with a modern web interface.

![Platform](https://img.shields.io/badge/Platform-Linux-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![React](https://img.shields.io/badge/React-18.2-61dafb)
![License](https://img.shields.io/badge/License-Commercial-red)

## Features

### Device Management
- **Multi-Vendor Support**: Cisco IOS-XR (NETCONF) and Nokia SR OS (pysros/NETCONF)
- **Device Discovery**: Automatic network scanning and device detection
- **Discovery Groups**: Organize devices into logical groups for batch operations
- **Metadata Collection**: Automatic collection of BGP, IGP, MPLS, and system information
- **Health Monitoring**: Real-time connectivity checks (Ping, NETCONF, SSH)

### Compliance & Auditing
- **Rule-Based Auditing**: Create custom audit rules with XPath queries and XML filters
- **Multi-Check Rules**: Define multiple validation checks per rule
- **Severity Levels**: Critical, High, Medium, Low classifications
- **Category Organization**: Group rules by routing, security, interfaces, etc.
- **Scheduled Audits**: Automated compliance checking on schedule
- **Compliance Scoring**: Real-time compliance percentage tracking

### Configuration Management
- **Configuration Backup**: Automated backup of device configurations
- **Drift Detection**: Detect unauthorized configuration changes
- **Configuration Comparison**: Side-by-side diff viewing
- **Remediation Workflows**: Guided remediation for compliance violations

### Analytics & Reporting
- **Dashboard**: Real-time compliance scores and statistics
- **Trend Analysis**: Historical compliance and health trends
- **Export Reports**: Generate compliance reports for auditors
- **Visualizations**: Charts and graphs for quick insights

### Administration
- **User Management**: Role-based access control (Admin, Operator, Viewer)
- **License Management**: Commercial licensing with feature controls
- **Audit Logging**: Complete audit trail of all actions
- **Dark/Light Mode**: User preference for interface theme

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Network access to devices via NETCONF (port 830)
- Valid license key (contact sales for trial)

### Installation

1. **Clone and configure:**
```bash
git clone https://github.com/your-org/nap.git
cd nap
cp .env.example .env
# Edit .env with your configuration
```

2. **Start the platform:**
```bash
docker-compose up -d
```

3. **Access the web interface:**
- URL: http://localhost:80
- Default login: admin / admin (change immediately)

4. **Activate your license:**
- Navigate to Administration > License
- Upload your license file or enter the license key

## Usage Guide

### Adding Devices

1. Navigate to **Devices** in the sidebar
2. Click **Add Device** or use **Discovery**
3. For manual addition:
   - Enter hostname, IP address, and credentials
   - Select vendor type (Cisco XR or Nokia SROS)
   - Test connection before saving

### Creating Audit Rules

1. Navigate to **Rules** in the sidebar
2. Click **Create Rule**
3. Configure:
   - Name and description
   - Severity level (Critical/High/Medium/Low)
   - Target vendors
   - Add checks with XPath/XML filters

**Example: Check BGP is configured on Nokia**
```yaml
Name: BGP Configuration Check
Vendor: Nokia SROS
XPath: /configure/router[router-name="Base"]/bgp
Comparison: exists
```

### Running Audits

1. Navigate to **Audits** in the sidebar
2. Click **Run Audit**
3. Select:
   - Devices to audit (or all)
   - Rules to apply (or all enabled)
4. View results in real-time

### Health Monitoring

1. Navigate to **Health** in the sidebar
2. View device health status at a glance
3. Click on a device for detailed history
4. Configure health check intervals in Settings

## Supported Platforms

| Vendor | Model | Protocol | Features |
|--------|-------|----------|----------|
| Cisco | IOS-XR | NETCONF | Full audit, backup, remediation |
| Nokia | SR OS 23.x+ | pysros/NETCONF | Full audit, backup, remediation |

## System Requirements

### Minimum Requirements
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB SSD
- Network: 100 Mbps

### Recommended (Production)
- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 200+ GB SSD
- Network: 1 Gbps

## Support

- **Documentation**: See DEVELOPER.md for technical details
- **Issues**: Contact support@your-company.com
- **Sales**: Contact sales@your-company.com for licensing

## Security Notice

This platform manages network device credentials. Ensure:
- Use HTTPS in production (configure reverse proxy)
- Change default passwords immediately
- Restrict network access to the platform
- Regular backup of the database
- Follow your organization's security policies

---

**Copyright 2024 Your Company. All Rights Reserved.**
