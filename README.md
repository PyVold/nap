# Network Audit Platform

A comprehensive network audit platform for Cisco XR and Nokia SROS routers with automated compliance checking, health monitoring, and a modern React-based web interface.

![Platform](https://img.shields.io/badge/Platform-Linux-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![React](https://img.shields.io/badge/React-18.2-61dafb)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688)

## 🌟 Features

### Backend Capabilities
- **Multi-Vendor Support**: Cisco XR and Nokia SROS devices
- **NETCONF Protocol**: Automated device configuration retrieval
- **Dynamic Rule Engine**: Flexible audit rules with XPath (Nokia) and XML filters (Cisco)
- **Device Discovery**: Integration with astrest for automatic device discovery
- **Health Monitoring**: Ping and NETCONF connectivity checks
- **Database Persistence**: SQLite database for audit history and device inventory
- **RESTful API**: Complete microservices architecture

### Frontend Features
- **Modern React UI**: Beautiful, responsive interface with Material-UI
- **Real-Time Dashboard**: Compliance scores, audit statistics, and visualizations
- **Rule Management**: Full CRUD operations for audit rules
- **Device Health Monitoring**: Live health status with historical data
- **Audit Results Viewer**: Detailed findings with drill-down capabilities
- **Dark Mode**: Toggle between light and dark themes
- **Auto-Refresh**: Real-time data updates

## 📋 Prerequisites

### Backend Requirements
- Python 3.9 or higher
- pip package manager
- Access to network devices via NETCONF (port 830)

### Frontend Requirements
- Node.js 16 or higher
- npm or yarn package manager

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/PyVold/network-audit.git
cd network-audit/network-audit-platform-main
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# The database will be created automatically on first run
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install
```

## 🔧 Configuration

### Backend Configuration

Edit `config.py` to customize settings:

```python
# API Settings
api_host = "0.0.0.0"
api_port = 3000

# Database (optional - defaults to SQLite)
database_url = "sqlite:///./network_audit.db"

# Logging
log_level = "INFO"
```

### Frontend Configuration

Create `frontend/.env` file:

```env
# API URL (change if backend runs on different host/port)
REACT_APP_API_URL=http://localhost:3000
```

## ▶️ Running the Application

### Start the Backend

```bash
# From the project root directory
cd network-audit-platform-main
python main.py
```

The backend API will start on `http://localhost:3000`

**Expected Output:**
```
INFO:     Starting Network Audit Platform v1.0
INFO:     Database initialized
INFO:     Uvicorn running on http://0.0.0.0:3000
```

### Start the Frontend (Development)

```bash
# In a new terminal, navigate to frontend directory
cd network-audit-platform-main/frontend

# Start development server
npm start
```

The frontend will start on `http://localhost:3001` and automatically open in your browser.

### Build Frontend for Production

```bash
cd frontend
npm run build
```

The production build will be created in `frontend/build/` and automatically served by the backend at `http://localhost:3000/app`

## 📚 API Documentation

### Interactive API Docs

Once the backend is running, visit:
- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc

### Main Endpoints

#### Devices
- `GET /devices/` - List all devices
- `POST /devices/` - Add a new device
- `PUT /devices/{id}` - Update device
- `DELETE /devices/{id}` - Delete device
- `POST /devices/discover` - Discover devices via astrest

#### Audit Rules
- `GET /rules/` - List all rules
- `POST /rules/` - Create new rule
- `PUT /rules/{id}` - Update rule
- `DELETE /rules/{id}` - Delete rule
- `PUT /rules/{id}/toggle` - Enable/disable rule

#### Audits
- `POST /audit/` - Run audit on devices
- `GET /audit/results` - Get all audit results
- `GET /audit/compliance` - Get compliance summary

#### Health Monitoring
- `POST /health/check/{device_id}` - Check device health
- `POST /health/check-all` - Check all devices
- `GET /health/summary` - Get health summary
- `GET /health/history/{device_id}` - Get health history

## 📁 Project Structure

```
network-audit-platform-main/
├── api/                    # API routes
│   └── routes/
│       ├── audits.py      # Audit endpoints
│       ├── devices.py     # Device endpoints
│       ├── health.py      # Health monitoring endpoints
│       └── rules.py       # Rule management endpoints
├── connectors/            # Device connectors
│   ├── base_connector.py
│   └── netconf_connector.py
├── engine/                # Audit engine
│   ├── audit_engine.py
│   ├── comparators.py
│   └── rule_executor.py
├── models/                # Pydantic models
│   ├── audit.py
│   ├── device.py
│   ├── rule.py
│   └── enums.py
├── services/              # Business logic
│   ├── audit_service.py
│   ├── device_service.py
│   ├── health_service.py
│   └── rule_service.py
├── utils/                 # Utilities
│   ├── exceptions.py
│   ├── logger.py
│   └── validators.py
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── api/          # API client
│   │   ├── App.js        # Main app
│   │   └── index.js      # Entry point
│   └── public/
├── database.py            # Database configuration
├── db_models.py          # SQLAlchemy models
├── config.py             # Configuration
├── main.py               # Application entry point
└── requirements.txt      # Python dependencies
```

## 🎯 Usage Examples

### Adding a Device

```bash
curl -X POST http://localhost:3000/devices/ \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "router1",
    "vendor": "cisco_xr",
    "ip": "192.168.1.1",
    "port": 830,
    "username": "admin",
    "password": "admin"
  }'
```

### Creating an Audit Rule

```bash
curl -X POST http://localhost:3000/rules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Check OSPF Configuration",
    "description": "Verify OSPF is configured",
    "severity": "high",
    "category": "routing",
    "enabled": true,
    "vendors": ["cisco_xr"],
    "checks": [{
      "name": "OSPF Check",
      "filter_xml": "<ospf></ospf>",
      "comparison": "exists",
      "reference_value": "",
      "reference_config": "",
      "error_message": "OSPF not configured",
      "success_message": "OSPF is configured"
    }]
  }'
```

### Running an Audit

```bash
curl -X POST http://localhost:3000/audit/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": null,
    "rule_ids": null
  }'
```

## 🗄️ Database Schema

The platform uses SQLite with the following tables:

- **devices**: Network device inventory
- **audit_rules**: Audit rule definitions
- **audit_results**: Historical audit results
- **health_checks**: Device health check history

All tables include proper foreign keys, indexes, and CASCADE delete for data integrity.

## 🔒 Security Considerations

⚠️ **Important**: This platform is designed for internal network use. Before deploying:

1. Change default credentials in device configurations
2. Enable authentication (currently disabled by default)
3. Use HTTPS in production
4. Restrict CORS origins in `main.py`
5. Store credentials securely (consider using environment variables or vault)
6. Use SSH tunneling or VPN for NETCONF connections

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 3000 is already in use
lsof -i :3000

# Check Python version
python --version  # Should be 3.9+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend won't start
```bash
# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 16+
```

### NETCONF connection fails
- Verify device IP and port (default: 830)
- Check firewall rules allow NETCONF traffic
- Verify SSH subsystem is enabled on devices
- Check credentials are correct

### Database errors after updates
```bash
# Delete existing database (will lose data!)
rm network_audit.db

# Restart backend - database will be recreated
python main.py
```

## 📊 Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **Pydantic**: Data validation
- **ncclient**: NETCONF client library
- **uvicorn**: ASGI server

### Frontend
- **React**: UI framework
- **Material-UI**: Component library
- **Recharts**: Data visualization
- **Axios**: HTTP client
- **React Router**: Navigation

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 👥 Support

For issues and questions:
- Create an issue in the repository
- Contact the development team

## 🗺️ Roadmap

- [ ] Support for additional vendors (Juniper, Arista)
- [ ] Advanced reporting and analytics
- [ ] Email notifications for audit failures
- [ ] Multi-user authentication and RBAC
- [ ] Scheduled audits
- [ ] Configuration backup and version control
- [ ] Compliance templates (PCI-DSS, NIST, etc.)

---

**Made with ❤️ for Network Engineers**
