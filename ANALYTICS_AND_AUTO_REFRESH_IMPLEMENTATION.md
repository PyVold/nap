# Analytics Service & Auto-Refresh Implementation

## Overview
This document describes the implementation of:
1. **Analytics Service** - A separate microservice for compliance intelligence
2. **Auto-Refresh Functionality** - Automatic polling in the frontend after audit/remediation operations

## Changes Summary

### 1. Analytics Service (New Microservice)

#### Created New Service Container
- **Location**: `/workspace/services/analytics-service/`
- **Port**: 3006
- **Purpose**: Compliance trends, forecasting, and anomaly detection

#### Directory Structure
```
services/analytics-service/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application
│   ├── db_models.py                 # Analytics database models
│   ├── models/
│   │   ├── __init__.py
│   │   └── enums.py                 # SeverityLevel enum
│   ├── routes/
│   │   ├── __init__.py
│   │   └── analytics.py             # Analytics API endpoints
│   └── services/
│       ├── __init__.py
│       └── analytics_service.py     # Business logic
├── Dockerfile
└── requirements.txt
```

#### Database Models
**ComplianceTrendDB**
- Tracks compliance metrics over time
- Captures snapshot data: overall compliance, device counts, check results
- Supports both device-specific and overall trends

**ComplianceForecastDB**
- Generates compliance predictions using linear regression
- Includes confidence scores and model metadata
- Forecasts future compliance trends

**ComplianceAnomalyDB**
- Detects anomalies using statistical analysis (Z-score method)
- Tracks compliance drops and failure spikes
- Supports acknowledgment workflow

#### API Endpoints

**Trends**
- `GET /analytics/trends?days=7&device_id={id}` - Get compliance trends
- `POST /analytics/trends/snapshot` - Create a new snapshot

**Forecasts**
- `GET /analytics/forecast?device_id={id}` - Get existing forecasts
- `POST /analytics/forecast/generate` - Generate new forecasts

**Anomalies**
- `GET /analytics/anomalies?acknowledged=false` - Get detected anomalies
- `POST /analytics/anomalies/detect` - Run anomaly detection
- `POST /analytics/anomalies/{id}/acknowledge` - Acknowledge an anomaly

**Dashboard**
- `GET /analytics/dashboard/summary` - Get summary statistics

#### Service Communication
The analytics service communicates with other services via HTTP:
- **Rule Service (port 3002)**: Fetches audit results
- **Device Service (port 3001)**: Can fetch device information
- Uses `httpx` async HTTP client for inter-service communication

### 2. Frontend Auto-Refresh Implementation

#### AuditResults Component Updates
**File**: `/workspace/frontend/src/components/AuditResults.jsx`

#### New Features

**Polling Mechanism**
```javascript
// Automatically polls for results every 5 seconds
// Stops after 60 seconds (12 attempts) or manually
const startPolling = (maxAttempts = 12) => {
  // Polls every 5 seconds for up to 60 seconds
  // Shows "Auto-refreshing..." indicator
}
```

**Triggered On**:
1. **Run Audit** - When starting a new audit
2. **Re-Audit Selected** - When re-auditing selected devices
3. **Apply Fix** - When applying remediation (automatically re-audits after fix)

**User Experience**:
- Visual indicator: "Auto-refreshing..." chip in header
- Automatic updates without manual refresh
- Polling stops after 60 seconds or can be manually stopped
- Clear success messages indicating automatic updates

### 3. API Gateway Updates

**File**: `/workspace/services/api-gateway/app/main.py`

Updated service registry:
```python
"analytics-service": {
    "url": "http://analytics-service:3006",
    "name": "Analytics",
    "enabled": True,
    "routes": ["/analytics"],
    "ui_routes": ["analytics"]
}
```

### 4. Docker Compose Updates

**File**: `/workspace/docker-compose.yml`

Added new analytics-service container:
```yaml
analytics-service:
  build:
    context: .
    dockerfile: services/analytics-service/Dockerfile
  ports:
    - "3006:3006"
  environment:
    - DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
    - RULE_SERVICE_URL=http://rule-service:3002
    - DEVICE_SERVICE_URL=http://device-service:3001
```

### 5. Database Migration

**File**: `/workspace/migrations/add_analytics_tables.py`

Creates three new tables:
- `compliance_trends`
- `compliance_forecasts`
- `compliance_anomalies`

Run migration on next database initialization or manually using Alembic.

### 6. Admin Service Cleanup

Removed analytics routes from admin-service:
- Removed `analytics` import from main.py
- Removed analytics router registration
- Removed analytics models from db_models.py (now in analytics-service)

## How to Use

### Starting the Services

```bash
# Build and start all services
docker-compose up -d --build

# View logs for analytics service
docker-compose logs -f analytics-service
```

### Accessing Analytics

#### Via Frontend
1. Navigate to **Analytics** menu item
2. View compliance trends, forecasts, and anomalies
3. Create snapshots, generate forecasts, detect anomalies

#### Via API
```bash
# Get trends (last 7 days)
curl http://localhost:3000/analytics/trends?days=7

# Create snapshot
curl -X POST http://localhost:3000/analytics/trends/snapshot \
  -H "Content-Type: application/json" \
  -d '{"device_id": null}'

# Generate forecast
curl -X POST http://localhost:3000/analytics/forecast/generate \
  -H "Content-Type: application/json" \
  -d '{"device_id": null, "days_ahead": 7}'

# Detect anomalies
curl -X POST http://localhost:3000/analytics/anomalies/detect \
  -H "Content-Type: application/json" \
  -d '{"device_id": null}'

# Get dashboard summary
curl http://localhost:3000/analytics/dashboard/summary
```

### Testing Auto-Refresh

1. Go to **Audit Results** page
2. Select one or more devices (using checkboxes)
3. Click **Re-Audit Selected** or **Apply Fix**
4. Watch for:
   - Success message indicating automatic updates
   - "Auto-refreshing..." indicator in header
   - Results updating automatically every 5 seconds
   - Indicator disappears after 60 seconds

## Analytics Features

### Compliance Trends
- Historical compliance tracking
- Device-specific or overall trends
- Tracks pass/fail/warning counts
- Severity-based failure breakdown

### Compliance Forecasting
- Linear regression predictions
- Confidence scores (R-squared)
- 7-90 day forecasts
- Device-specific or overall predictions

### Anomaly Detection
- Z-score statistical analysis
- Detects compliance drops (z < -2)
- Detects failure spikes (>2x average)
- Acknowledgment workflow

### Dashboard Summary
- Recent anomalies count (last 7 days)
- Average compliance (last 7 days)
- Devices at risk (compliance < 70%)
- Total trend snapshots

## Architecture Benefits

### Microservices Separation
✅ **Analytics is now a separate container**
- Independent scaling
- Isolated failures
- Dedicated resources
- Clear service boundaries

### Service Communication
- REST API communication between services
- Async HTTP clients (httpx)
- Service discovery via environment variables
- Fault-tolerant design

### Frontend UX
- Instant feedback on actions
- No manual refresh needed
- Visual polling indicator
- Automatic updates

## Next Steps

### Recommended Enhancements
1. **Advanced Analytics**
   - Machine learning models
   - Pattern recognition
   - Predictive alerting

2. **Real-time Updates**
   - WebSocket support
   - Server-sent events
   - Push notifications

3. **Performance**
   - Redis caching
   - Query optimization
   - Data aggregation

4. **Monitoring**
   - Service health metrics
   - Analytics performance tracking
   - Alert on anomalies

## Troubleshooting

### Analytics Service Not Starting
```bash
# Check logs
docker-compose logs analytics-service

# Verify database connection
docker-compose exec analytics-service python -c "from shared.database import engine; print(engine.connect())"
```

### Auto-Refresh Not Working
1. Check browser console for errors
2. Verify audit API is responding
3. Ensure polling isn't being blocked by browser
4. Check network tab for polling requests

### No Analytics Data
1. Create initial snapshots:
   ```bash
   curl -X POST http://localhost:3000/analytics/trends/snapshot
   ```
2. Run audits to generate data
3. Wait for data accumulation (forecasts need 2+ snapshots)

## Summary

✅ **Completed**:
1. ✅ Created analytics-service as separate microservice container
2. ✅ Implemented full analytics functionality (trends, forecasts, anomalies)
3. ✅ Added auto-refresh polling to frontend
4. ✅ Updated API gateway routing
5. ✅ Updated docker-compose configuration
6. ✅ Created database migration
7. ✅ Cleaned up admin service

The system now has:
- **Separated analytics microservice** running on port 3006
- **Auto-refreshing audit results** without manual page refresh
- **Working analytics dashboard** with real calculations
- **Complete API endpoints** for analytics operations
