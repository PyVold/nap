# Changelog

All notable changes to the Network Audit Platform (NAP) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-03-17

### Added
- **AI-Powered Rule Builder**: Create audit rules using natural language descriptions
- **AI Chat Assistant**: Context-aware network troubleshooting and analysis chat
- **AI Reports**: Intelligent compliance summaries and executive report generation
- **Anomaly Detection**: ML-based detection of unusual configuration patterns
- **Compliance Prediction**: Predictive analytics for compliance drift
- **Impact Analysis**: Blast-radius assessment for configuration changes
- **Automated Remediation**: AI-suggested fixes for compliance violations
- **Multi-Agent Operations**: Coordinate multiple AI agents for complex network tasks
- **Configuration Optimizer**: AI-driven configuration optimization suggestions
- **MCP Integration Hub**: Model Context Protocol support for AI tool integration

### Security
- Restricted CORS to configured origins (previously allowed all origins)
- Removed hardcoded fallback encryption keys — keys are now required via environment
- Replaced unsafe `eval()` with secure expression evaluator in rule engine
- Removed committed secrets from version control
- Updated `.gitignore` to prevent accidental secret commits

### Changed
- Upgraded architecture to support AI service microservice
- Enhanced Docker Compose with AI service integration
- Improved frontend with new AI feature components

## [1.5.0] - 2026-03-04

### Added
- Search bars and permission-based access controls in frontend
- Scheduled backup integration with backup-service API
- Grafana datasource provisioning for monitoring

### Fixed
- Nokia SSH connection handling improvements
- Config hash made optional in backup responses
- Backup scheduler timestamp column and compressed field fixes
- Authentication flow improvements

## [1.4.0] - 2025-12-17

### Security
- Comprehensive pre-production security review and hardening
- Input validation improvements across all API endpoints

## [1.3.0] - 2025-12-01

### Added
- Hardware inventory tracking (chassis, line cards, optics)
- Device import via CSV/Excel
- Workflow automation engine with DAG execution
- Integration hub (webhooks, syslog)
- Admin dashboard with system health monitoring
- User group management with fine-grained permissions
- Module-level access control
- License enforcement with device and user quotas

### Changed
- Migrated to microservices architecture (8 services)
- Added API gateway for centralized routing and auth

## [1.2.0] - 2025-11-15

### Added
- Configuration backup scheduling
- Drift detection between backup snapshots
- Rule templates library
- Compliance trend analytics

## [1.1.0] - 2025-10-01

### Added
- Nokia SR OS support via pysros/NETCONF
- Device discovery and auto-detection
- Discovery groups for batch operations
- Device health monitoring (Ping, NETCONF, SSH)
- Scheduled audit execution

## [1.0.0] - 2025-09-01

### Added
- Initial release
- Cisco IOS-XR device management via NETCONF
- Rule-based configuration auditing with XPath queries
- Multi-check rules with severity levels
- Real-time compliance scoring
- Dashboard with compliance statistics
- Role-based access control (Admin, Operator, Viewer)
- Commercial license system
- Docker Compose deployment
- PostgreSQL database backend
- React web interface with Material UI
