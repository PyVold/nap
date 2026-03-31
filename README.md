# Network Audit Platform (NAP)

A comprehensive enterprise network audit and compliance platform for Cisco IOS-XR and Nokia SR OS routers. Automate configuration audits, ensure compliance, monitor device health, and manage network configuration with a modern web interface.

![Platform](https://img.shields.io/badge/Platform-Linux-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![React](https://img.shields.io/badge/React-18.2-61dafb)
![License](https://img.shields.io/badge/License-Commercial-red)
![Version](https://img.shields.io/badge/Version-2.0.0-orange)

## Features

### Device Management
- **Multi-Vendor Support**: Cisco IOS-XR (NETCONF) and Nokia SR OS (pysros/NETCONF)
- **Device Discovery**: Automatic network scanning and device detection
- **Discovery Groups**: Organize devices into logical groups for batch operations
- **Metadata Collection**: Automatic collection of BGP, IGP, MPLS, and system information
- **Health Monitoring**: Real-time connectivity checks (Ping, NETCONF, SSH)
- **Hardware Inventory**: Track chassis, line cards, optics, and firmware versions

### Compliance & Auditing
- **Rule-Based Auditing**: Create custom audit rules with XPath queries and XML filters
- **Multi-Check Rules**: Define multiple validation checks per rule
- **Rule Templates**: Pre-built compliance templates for common standards
- **Severity Levels**: Critical, High, Medium, Low classifications
- **Category Organization**: Group rules by routing, security, interfaces, etc.
- **Scheduled Audits**: Automated compliance checking on configurable schedules
- **Compliance Scoring**: Real-time compliance percentage tracking per device and fleet-wide

### Configuration Management
- **Configuration Backup**: Automated backup of device configurations with scheduling
- **Drift Detection**: Detect unauthorized configuration changes between backups
- **Configuration Comparison**: Side-by-side diff viewing with highlighted changes
- **Remediation Workflows**: Guided remediation for compliance violations

### AI-Powered Features (v2.0)
- **Natural Language Rule Builder**: Describe audit rules in plain English, AI generates XPath/XML
- **AI Chat Assistant**: Context-aware chat for network troubleshooting and analysis
- **Intelligent Reports**: AI-generated compliance summaries and executive reports
- **Anomaly Detection**: ML-based detection of unusual configuration patterns
- **Compliance Prediction**: Predict compliance drift before it happens
- **Impact Analysis**: Assess the blast radius of configuration changes
- **Automated Remediation**: AI-suggested fixes for compliance violations
- **MCP Integration Hub**: Connect NAP as a data source for AI operations tools

### Analytics & Reporting
- **Dashboard**: Real-time compliance scores, device health, and fleet statistics
- **Trend Analysis**: Historical compliance and health trends with charts
- **Export Reports**: Generate compliance reports for auditors (PDF/CSV)
- **Visualizations**: Charts and graphs powered by Recharts

### Administration
- **User Management**: Role-based access control (Admin, Operator, Viewer)
- **Group-Based Permissions**: Fine-grained permission assignment via user groups
- **License Management**: Commercial licensing with feature and device quota controls
- **Module Access Control**: Enable/disable platform modules per user group
- **Audit Logging**: Complete audit trail of all actions
- **Integration Hub**: Webhook, syslog, and third-party integrations

## Architecture

NAP uses a microservices architecture with 8 backend services behind an API gateway:

```
                    ┌──────────────────────────┐
                    │   Frontend (React/Nginx)  │
                    │        Port: 80           │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   API Gateway (FastAPI)   │
                    │       Port: 3000          │
                    └────────────┬─────────────┘
                                 │
       ┌──────────┬──────────┬───┴───┬──────────┬──────────┐
       ▼          ▼          ▼       ▼          ▼          ▼
  ┌─────────┐┌─────────┐┌───────┐┌───────┐┌─────────┐┌────────┐
  │ Device  ││  Rule   ││ Admin ││Backup ││Inventory││  AI    │
  │ Service ││ Service ││Service││Service││ Service ││Service │
  │ :3001   ││ :3002   ││ :3003 ││ :3004 ││ :3005   ││ :3006  │
  └────┬────┘└────┬────┘└───┬───┘└───┬───┘└────┬────┘└────┬───┘
       └──────────┴─────────┴────┬───┴─────────┴──────────┘
                                 ▼
                    ┌────────────────────────┐
                    │  PostgreSQL Database   │
                    │      Port: 5432        │
                    └────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Network access to devices via NETCONF (port 830)
- Valid license key

### Installation

1. **Clone and configure:**
```bash
git clone <repository-url>
cd nap
cp .env.example .env
cp .env.prod.example .env.prod
# Edit .env with your configuration - set all SECRET/KEY values
```

2. **Start the platform:**
```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

3. **Access the web interface:**
- URL: http://localhost:80
- Default login: admin / admin (**change immediately after first login**)

4. **Activate your license:**
- Navigate to Administration > License Management
- Enter your license key

## Configuration

All configuration is managed through environment variables. Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `JWT_SECRET` | Secret key for JWT token signing | Yes |
| `ENCRYPTION_KEY` | Key for encrypting device credentials at rest | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `LICENSE_ENCRYPTION_KEY` | License system encryption key | Yes |
| `LICENSE_SECRET_SALT` | License validation salt | Yes |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins | Yes |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No |

**Important:** Never commit `.env` or `.env.prod` files to version control.

## Supported Platforms

| Vendor | Platform | Protocol | Features |
|--------|----------|----------|----------|
| Cisco | IOS-XR | NETCONF | Full audit, backup, remediation, health monitoring |
| Nokia | SR OS 23.x+ | pysros/NETCONF | Full audit, backup, remediation, health monitoring |

## System Requirements

### Minimum
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB SSD
- Network: 100 Mbps

### Recommended (Production)
- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 200+ GB SSD
- Network: 1 Gbps

## Deployment Options

| Option | File | Use Case |
|--------|------|----------|
| Development | `docker-compose.yml` | Local development and testing |
| Production | `docker-compose.prod.yml` | Production with monitoring stack |
| Air-Gapped | `docker-compose.online.yml` | Offline/disconnected environments |

## Documentation

- **[Developer Guide](DEVELOPER.md)** — Architecture, project structure, API reference
- **[API Documentation](docs/API.md)** — REST API endpoints and examples
- **[Deployment Guide](docs/DEPLOYMENT.md)** — Production deployment instructions
- **[AI Features Roadmap](docs/FEATURE_BRAINSTORM_AI_MCP.md)** — AI and MCP integration plans

## Security

This platform manages network device credentials and configurations. Follow these security practices:

- **Always use HTTPS** in production (configure a reverse proxy with TLS)
- **Change default credentials** immediately after installation
- **Set strong encryption keys** — never use default values
- **Restrict network access** to the platform management interface
- **Regular database backups** — use the built-in backup scheduler
- **Review audit logs** regularly for unauthorized access attempts
- **Keep the platform updated** to receive security patches

## License

Commercial software. All rights reserved.

Contact your account manager for licensing inquiries.

---

**Copyright 2025 PyVold. All Rights Reserved.**
