# Network Audit Platform - Frontend

Modern React frontend for the Network Audit Platform with Material-UI.

## Features

- **Dashboard**: Overview of audit status, compliance scores, and system health
- **Rule Management**: Create, edit, and delete audit rules with support for XPath (Nokia) and XML filters (Cisco)
- **Device Health**: Monitor device health with ping and NETCONF connectivity checks
- **Audit Results**: View detailed audit results with compliance visualization

## Setup

### Install Dependencies

```bash
cd frontend
npm install
```

### Environment Configuration

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=http://localhost:3000
```

### Development Server

```bash
npm start
```

The frontend will start on `http://localhost:3001` and proxy API requests to the backend at `http://localhost:3000`.

### Build for Production

```bash
npm run build
```

The production build will be created in the `build/` directory.

## Technology Stack

- **React 18.2**: Modern React with hooks
- **Material-UI 5**: Beautiful, responsive UI components
- **React Router 6**: Client-side routing
- **Recharts**: Data visualization
- **Axios**: HTTP client for API calls

## Components

### Dashboard
Shows overall system health, compliance scores, and audit statistics with beautiful gradient cards and charts.

### Rule Management
Full CRUD interface for audit rules:
- Add/edit/delete rules
- Configure XPath for Nokia devices
- Configure XML filters for Cisco devices
- Set severity levels and categories
- Enable/disable rules with toggle

### Device Health
Monitor network device health:
- Real-time ping status
- NETCONF connectivity checks
- Health history for each device
- Overall health summary

### Audit Results
View and analyze audit results:
- Run audits on selected devices
- Filter by specific rules
- View compliance scores
- Drill down into individual findings

## API Integration

All API calls are centralized in `src/api/api.js`:
- Device API
- Rules API
- Audit API
- Health API
- System API

## Styling

The app features:
- Modern gradient backgrounds
- Responsive design for mobile/tablet/desktop
- Dark mode toggle
- Smooth animations and transitions
- Professional color scheme
