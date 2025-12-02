# Device Metadata Collection

## Overview

The Network Audit Platform now automatically collects protocol and system metadata from network devices during the discovery process. This metadata includes:

### Nokia SR OS Devices
- **BGP Information**
  - AS number
  - Router ID
  - Neighbor count
  - Established sessions count

- **IGP Information (ISIS or OSPF)**
  - Protocol type (ISIS/OSPF)
  - Router ID / System ID
  - ISIS level (if ISIS)
  - Adjacency/neighbor count

- **LDP Information**
  - Enabled status
  - Router ID
  - Session count

- **System Information**
  - System interface IP address

- **MPLS/Segment Routing**
  - MPLS enabled status
  - Segment Routing status

### Cisco IOS-XR Devices
- **BGP Information**
  - AS number
  - Router ID
  - Neighbor count

- **IGP Information (OSPF or ISIS)**
  - Protocol type
  - Router ID / System ID

- **LDP Information**
  - Enabled status
  - Neighbor count

- **System Information**
  - Loopback0 IP address

## Architecture

### Components

1. **Device Metadata Collector** (`services/device_metadata_collector.py`)
   - Vendor-specific metadata collection logic
   - Runs show commands via device connectors
   - Parses output using regex patterns

2. **Enhanced Connectors**
   - `NokiaSROSConnector`: Added `run_command()` method using pysros CLI
   - `NetconfConnector`: Added `run_command()` method using SSH for Cisco devices

3. **Integration Points**
   - Manual discovery endpoint (`/discover`)
   - Discovery group triggers
   - Scheduled discovery jobs

4. **Database Storage**
   - Metadata stored in `devices.metadata` column (JSONB in PostgreSQL)
   - Automatically created by SQLAlchemy on service startup

## Migration

### Automatic (Recommended)
The `metadata` column will be automatically added to the `devices` table when services restart, as it's defined in the DeviceDB model.

### Manual (If Needed)
If you need to run the migration manually:

```bash
# Option 1: From host
./run_metadata_migration.sh

# Option 2: Inside container
docker-compose exec admin-service python /app/migrations/add_device_metadata.py
```

## Testing

### 1. Restart Services
Restart the services to apply code changes and create the metadata column:

```bash
docker-compose restart
```

Or rebuild if you've made significant changes:

```bash
docker-compose down
docker-compose up -d --build
```

### 2. Run Discovery
Trigger a device discovery to collect metadata:

**Via API:**
```bash
curl -X POST http://localhost:8001/api/devices/discover \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subnet": "192.168.1.0/24",
    "username": "admin",
    "password": "password",
    "port": 830
  }'
```

**Via UI:**
- Navigate to Devices page
- Click "Discover Devices"
- Enter subnet and credentials

### 3. Verify Metadata Collection
Check the logs to see metadata collection:

```bash
# Device service logs (discovery + metadata collection)
docker-compose logs -f device-service | grep -i metadata

# Example successful output:
# device-service_1 | Collecting metadata for device: router1 (nokia_sros)
# device-service_1 | Collected BGP metadata: AS65000, 2 sessions
# device-service_1 | Collected ISIS metadata: L2, 3 adjacencies
# device-service_1 | Metadata collected and stored for router1
```

### 4. Query Metadata from Database
Check if metadata was stored:

```bash
docker-compose exec database psql -U nap_user -d nap_db -c \
  "SELECT hostname, metadata FROM devices WHERE metadata IS NOT NULL;"
```

Expected output format:
```json
{
  "bgp": {
    "as_number": 65000,
    "router_id": "10.0.0.1",
    "neighbor_count": 2,
    "established_sessions": 2
  },
  "igp": {
    "type": "ISIS",
    "router_id": "1000.0000.0001",
    "isis_level": "L2",
    "adjacency_count": 3
  },
  "ldp": {
    "enabled": true,
    "router_id": "10.0.0.1",
    "session_count": 3
  },
  "mpls": {
    "enabled": true,
    "segment_routing": true
  },
  "system": {
    "ip_address": "10.0.0.1"
  }
}
```

### 5. Test Error Handling
The metadata collector is designed to gracefully handle errors:

- If a protocol is not configured (e.g., no BGP), that section will be empty
- If a command fails, it logs a warning but continues
- Discovery succeeds even if metadata collection fails

### 6. Check Discovery Group Integration
If you use discovery groups with scheduled runs:

```bash
# Check scheduler logs
docker-compose logs -f device-service | grep -i "scheduled discovery"

# Should show metadata collection for each discovered device
```

## Troubleshooting

### Metadata Column Not Created
If the metadata column doesn't exist:

1. Check that db_models.py was updated:
   ```bash
   grep -n "metadata = Column" services/device-service/app/db_models.py
   ```

2. Run the migration script:
   ```bash
   ./run_metadata_migration.sh
   ```

3. Restart services:
   ```bash
   docker-compose restart device-service
   ```

### No Metadata Collected
If devices are discovered but metadata is empty:

1. **Check connector logs:**
   ```bash
   docker-compose logs device-service | grep -E "(run_command|metadata)"
   ```

2. **Verify CLI access:**
   - Nokia: Ensure user has access to `show` commands
   - Cisco: Ensure port 22 (SSH) is accessible and user can run show commands

3. **Test connector manually:**
   You can create a test script to verify connectivity and command execution

### Partial Metadata
If only some metadata is collected:

- This is normal - not all protocols may be configured on every device
- Check device configuration (e.g., device may not have BGP configured)
- Review logs for specific protocol collection warnings

## Next Steps

### UI Display
The next phase will add metadata display to the device details page:

- Show BGP AS and router ID
- Display IGP type and details
- Show LDP and MPLS status
- Display system IP addresses

### API Endpoints
Future enhancements:
- GET `/api/devices/{id}/metadata` - Retrieve device metadata
- POST `/api/devices/{id}/metadata/refresh` - Manually refresh metadata
- GET `/api/devices/metadata/summary` - Aggregate metadata across devices

## Code Locations

- **Metadata Collector:** `shared/device_metadata_collector.py`
- **Nokia Connector:** `connectors/nokia_sros_connector.py` (run_command method)
- **Cisco Connector:** `connectors/netconf_connector.py` (run_command method)
- **Device Service:** `services/device-service/app/services/device_service.py`
  - `collect_device_metadata()` - Collect metadata for one device
  - `collect_metadata_for_discovered_devices()` - Batch collection
- **Discovery Routes:**
  - `services/device-service/app/routes/devices.py`
  - `services/device-service/app/routes/discovery_groups.py`
  - `services/device-service/app/scheduler.py`
- **Database Model:** `db_models.py` - DeviceDB.metadata field
- **Migration:** `migrations/add_device_metadata.py`
