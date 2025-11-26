# Hardware Inventory Dashboard - Research Guide

## Overview
This document provides comprehensive research on Nokia 7750 SR and Cisco IOS-XR (NCS/ASR9K) router hardware architectures for building a hardware inventory dashboard.

---

## 1. Nokia 7750 SR Architecture

### 1.1 Chassis Models and Types

**Supported Chassis:**
- **7750 SR-1**: Smallest Service Router with integrated IOM (no card slots)
- **7750 SR-7**: Mid-size chassis with 7 card slots
- **7750 SR-12**: Full-size chassis with 12 card slots
- **7750 SR-12e**: Enhanced 12-slot chassis
- **7750 SR-s**: Compact service router series

### 1.2 Card Slot Architecture

#### Card Types:
1. **CPM (Control Processing Module)**: System control processor
2. **IOM (Input/Output Module)**: Line cards with MDA slots
   - IOM3-XP, IOM3-XP-B, IOM3-XP-C
   - IOM4-e, IOM4-e-B
   - IOM5-e
3. **IMM (Integrated Media Module)**: Fixed integrated media cards
4. **MDA (Media Dependent Adapter)**: Port adapters that plug into IOMs
   - MDA (standard)
   - MDA-XP (extended port)
   - MDA-e (enhanced)
   - MDA-e-XP (enhanced extended port)
5. **SFM (Switch Fabric Module)**: Interconnect fabric
6. **Power Supplies**: Redundant AC/DC power modules
7. **Fan Trays**: Cooling modules

#### Slot Configuration:
- IOMs have 2 slots for pluggable MDAs
- MDA and MDA-XP modules go into IOM3-XP-C
- MDA-e modules go into IOM4-e and IOM4-e-B
- MDA-e-XP modules go into IOM5-e

### 1.3 NETCONF/YANG Access

#### YANG Models:
Nokia SROS uses proprietary YANG models available at: https://github.com/nokia/7x50_YangModels

**Key Namespaces:**
- Configuration: `urn:nokia.com:sros:ns:yang:sr:conf`
- State data: `urn:nokia.com:sros:ns:yang:sr:state`

**Relevant YANG Modules:**
- `nokia-state-chassis.yang` - Chassis state information
- `nokia-state-cpm.yang` - CPM state information
- `nokia-types-chassis.yang` - Chassis type definitions
- `nokia-conf-card.yang` - Card configuration
- `nokia-state-card.yang` - Card state information

#### pySROS YANG Paths for Hardware Inventory:

```python
# Chassis state
'/nokia-state:state/chassis'
'/nokia-state:state/chassis[chassis-class="router"][chassis-number="1"]'

# Card/IOM state
'/nokia-state:state/card'
'/nokia-state:state/card[slot-number="1"]'

# Get chassis including power supplies and fans
chassis_state = connection.running.get('/nokia-state:state/chassis')
# Access: chassis_state['power-supply'], chassis_state['fan']

# Card with MDA information
card_state = connection.running.get('/nokia-state:state/card')
# Access: card_state[card_id]['mda'][mda_id]
```

#### Key Data Fields:
- **serial-number**: Hardware serial number
- **part-number**: Part number (e.g., "3HE04410ABAC01")
- **clei-code**: Common Language Equipment Identifier
- **equipped-type**: Card/module type
- **oper-state**: Operational status (up, down, diagnosing, etc.)
- **admin-state**: Administrative status
- **mfg-date**: Manufacturing date
- **hw-index**: Hardware index
- **slot-number**: Physical slot location

### 1.4 CLI Commands for Hardware Inventory

```bash
# Show chassis information
show chassis

# Show all cards with detail
show card
show card detail

# Show specific card
show card 1

# Show card state
show state card

# Hardware data output includes:
# - Part number
# - CLEI code
# - Serial number
# - Manufacture date
# - Manufacturing string
```

**Example Output Fields:**
```
Hardware Data
    Part number         : 3HE04410ABAC01
    CLEI code          : IPMK310JRA
    Serial number      : NS1026C0341
    Manufacture date   : 11082010
```

### 1.5 NETCONF XPath Filter Example

```xml
<filter type="xpath"
        xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
        xmlns:state="urn:nokia.com:sros:ns:yang:sr:state"
        select="/state:state/state:chassis" />
```

---

## 2. Cisco IOS-XR (NCS/ASR9K) Architecture

### 2.1 Chassis Models

**ASR 9000 Series:**
- ASR 9001
- ASR 9006 (6-slot)
- ASR 9010 (10-slot)
- ASR 9912 (12-slot)
- ASR 9922 (22-slot)

**NCS Series:**
- NCS 540 (fixed configuration)
- NCS 5500 (modular)
- NCS 5700 (high-density)

### 2.2 Line Card and RP Architecture

#### Component Types:
1. **RP (Route Processor)**: Control plane processor
2. **Line Cards (LC)**: Forwarding cards with ports
3. **Fabric Cards**: Switch fabric modules
4. **Fan Trays**: Cooling modules
5. **Power Modules**: AC/DC power supplies
6. **SPA (Shared Port Adapter)**: Interface modules (on some platforms)

#### Modular Structure:
- Rack → Slot → Card → Module → Port

### 2.3 NETCONF/YANG Access

#### YANG Models:
Cisco IOS-XR YANG models available at: https://github.com/YangModels/yang

**Key Modules:**
- `Cisco-IOS-XR-invmgr-oper.yang` - Inventory manager operational data
- `Cisco-IOS-XR-plat-chas-invmgr-oper.yang` - Platform chassis inventory (older)
- `Cisco-IOS-XR-plat-chas-invmgr-ng-oper.yang` - Platform chassis inventory (newer)
- `Cisco-IOS-XR-sdr-invmgr-oper.yang` - SDR inventory
- `Cisco-IOS-XR-asr9k-sc-invmgr-admin-oper.yang` - ASR9K admin inventory

**Module Naming Convention:**
- Prefix: `Cisco-IOS-XR`
- Platform substring (optional): `asr9k`, `ncs5500`, etc.
- Technology substring: `invmgr`, `platform`, etc.
- Suffix: `-cfg` (config), `-oper` (operational), `-act` (actions)

#### YANG Structure:

```
inventory (container)
├── entities (list) - Flat list of all inventory items
└── racks (list)
    └── slots (list)
        ├── cards (list)
        │   ├── port-slots (list)
        │   │   └── ports (list)
        │   └── sub-slots (list)
        │       └── modules (list)
        ├── powershelf (list)
        └── fantray (list)
```

#### NETCONF Filter Example:

```xml
<platform xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-plat-chas-invmgr-oper">
  <racks>
    <rack>
      <slots>
        <slot>
          <cards>
            <card>
              <attributes/>
            </card>
          </cards>
        </slot>
      </slots>
    </rack>
  </racks>
</platform>
```

#### Key Data Fields:
- **name**: Component name/identifier
- **description**: Component description
- **serial-number**: Hardware serial number (SN)
- **pid**: Product ID (part number)
- **vid**: Version ID (hardware revision)
- **model-name**: Model name
- **hardware-revision**: Hardware revision
- **firmware-revision**: Firmware version
- **software-revision**: Software version
- **basic-info**: Basic inventory attributes (from inv-basic-bag)
- **asset-info**: Asset tracking attributes (from inv-asset-bag)
- **state**: Operational state
- **is-field-replaceable-unit**: FRU indicator

### 2.4 CLI Commands for Hardware Inventory

```bash
# Show platform summary
show platform

# Show inventory (all components)
show inventory
admin show inventory all

# Show inventory for specific location
show inventory location 0/RP0/CPU0

# Show inventory with UDI (Unique Device Identifier)
show inventory chassis

# Show inventory rack view
admin show inventory rack

# Show detailed inventory (raw format - includes all entities)
show inventory raw
```

**Example Command Outputs:**

```
# show inventory
NAME: "Rack 0", DESCR: "ASR 9006 4 Line Card Slot Chassis"
PID: ASR-9006-AC, VID: V01, SN: FOX1234ABCD

NAME: "0/RSP0/CPU0", DESCR: "ASR9K Route Switch Processor"
PID: A9K-RSP440-TR, VID: V02, SN: FOX5678EFGH

NAME: "0/0/CPU0", DESCR: "ASR 9000 10-port 10GE Modular Port Adapter"
PID: A9K-MOD80-SE, VID: V01, SN: FOX9012IJKL
```

### 2.5 NETCONF Query Example

```xml
<rpc message-id="101" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <get>
    <filter type="subtree">
      <inventory xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper">
        <racks>
          <rack>
            <entity>
              <attributes/>
            </entity>
          </rack>
        </racks>
      </inventory>
    </filter>
  </get>
</rpc>
```

---

## 3. Best Practices for Inventory Collection

### 3.1 Recommended NETCONF Paths

#### Nokia 7750 SR:
```python
# Use pySROS for Nokia (preferred over NETCONF)
chassis_inventory = connection.running.get('/nokia-state:state/chassis')
card_inventory = connection.running.get('/nokia-state:state/card')

# Or via NETCONF with XPath filter
xpath = '/state:state/state:chassis'
```

#### Cisco IOS-XR:
```xml
<!-- Use subtree filter for Cisco -->
<inventory xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper">
  <racks/>
</inventory>
```

### 3.2 Critical Data Fields for Inventory Tracking

#### Minimum Required Fields:
1. **Location/Slot**: Physical location identifier
2. **Type/Description**: Component type and description
3. **Part Number (PID)**: Manufacturer part number
4. **Serial Number (SN)**: Unique serial identifier
5. **Hardware Revision (VID)**: Version/revision
6. **Operational Status**: Current operational state
7. **Administrative Status**: Admin state (if applicable)

#### Recommended Additional Fields:
8. **Model Name**: Human-readable model designation
9. **CLEI Code**: For Nokia equipment
10. **Manufacturing Date**: Date of manufacture
11. **Firmware Version**: Current firmware
12. **Software Version**: Current software
13. **Is FRU**: Field Replaceable Unit indicator
14. **Parent/Container**: Hierarchical relationship

### 3.3 Distinguishing Card/Module Types

#### Nokia 7750 SR:
- **equipped-type**: Indicates card type (e.g., "iom3-xp-b", "cpm5", "mda-e-xp")
- **slot-number**: Physical slot location
- **card-type**: IOM, IMM, CPM, SFM, etc.
- **mda**: Nested container for MDA information within IOMs

#### Cisco IOS-XR:
- **name**: Location-based naming (e.g., "0/RP0/CPU0", "0/0/CPU0")
- **pid**: Product ID identifies specific card model
- **description**: Human-readable component description
- Use hierarchical structure: rack → slot → card → module

### 3.4 Handling Hierarchical Relationships

```python
# Example data structure for inventory dashboard

{
  "device_id": 1,
  "vendor": "nokia_sros",
  "chassis": {
    "model": "7750 SR-12",
    "serial_number": "NS1234567890",
    "part_number": "3HE12345AAAA01",
    "cards": [
      {
        "slot": "1",
        "type": "iom3-xp-b",
        "part_number": "3HE04410ABAC01",
        "serial_number": "NS1026C0341",
        "oper_state": "up",
        "admin_state": "in-service",
        "mdas": [
          {
            "slot": "1",
            "type": "m10-1gb-sfp-b",
            "part_number": "3HE03568AAAA01",
            "serial_number": "NS1027D4456",
            "oper_state": "up"
          }
        ]
      }
    ],
    "power_supplies": [
      {
        "id": "1",
        "type": "AC",
        "status": "up",
        "serial_number": "PS1234567890"
      }
    ],
    "fans": [
      {
        "id": "1",
        "status": "operational",
        "speed": "normal"
      }
    ]
  }
}
```

### 3.5 Polling Strategy

**Recommended Approach:**
1. **Initial Discovery**: Full inventory collection on device registration
2. **Periodic Updates**: Re-scan every 24 hours to detect hardware changes
3. **Event-Driven**: Subscribe to NETCONF notifications for real-time updates (if supported)
4. **On-Demand**: Allow manual refresh via dashboard

**Error Handling:**
- Implement retry logic with exponential backoff
- Cache last known good state
- Flag devices with stale inventory data
- Log all collection failures with timestamps

### 3.6 Performance Considerations

**Nokia 7750 SR:**
- pySROS is more efficient than NETCONF for Nokia devices
- Request specific paths rather than full state tree
- Batch multiple related queries when possible

**Cisco IOS-XR:**
- Use subtree filters to limit data returned
- Avoid requesting full `/inventory` tree on large chassis
- Request specific racks or slots when possible
- Consider using `show inventory` CLI via SSH as fallback

---

## 4. Implementation Recommendations

### 4.1 Database Schema

```sql
-- Hardware Inventory Tables

CREATE TABLE hardware_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    component_type VARCHAR(50) NOT NULL,  -- chassis, card, module, power, fan
    slot_location VARCHAR(50),            -- Physical location
    parent_id INTEGER,                     -- For hierarchical relationships

    -- Hardware identification
    part_number VARCHAR(100),
    serial_number VARCHAR(100),
    model_name VARCHAR(100),
    description TEXT,
    hardware_revision VARCHAR(50),
    clei_code VARCHAR(50),

    -- Status
    operational_state VARCHAR(50),
    administrative_state VARCHAR(50),

    -- Metadata
    manufacturing_date DATE,
    firmware_version VARCHAR(100),
    is_fru BOOLEAN DEFAULT FALSE,

    -- Tracking
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (device_id) REFERENCES devices(id),
    FOREIGN KEY (parent_id) REFERENCES hardware_inventory(id)
);

CREATE INDEX idx_hw_device ON hardware_inventory(device_id);
CREATE INDEX idx_hw_type ON hardware_inventory(component_type);
CREATE INDEX idx_hw_serial ON hardware_inventory(serial_number);
```

### 4.2 API Endpoints

```python
# Suggested REST API endpoints

GET    /api/hardware/inventory              # Get all hardware inventory
GET    /api/hardware/inventory?vendor=nokia # Filter by vendor
GET    /api/hardware/inventory?chassis=7750-SR-12  # Filter by chassis
GET    /api/hardware/inventory/{device_id}  # Get inventory for specific device
GET    /api/hardware/chassis/{device_id}    # Get chassis details
GET    /api/hardware/cards/{device_id}      # Get all cards
GET    /api/hardware/power/{device_id}      # Get power supplies
GET    /api/hardware/fans/{device_id}       # Get fan status
POST   /api/hardware/scan/{device_id}       # Trigger inventory scan
```

### 4.3 Dashboard Features

**Filtering Options:**
- By vendor (Nokia, Cisco)
- By chassis model
- By component type (cards, power, fans)
- By operational status
- By location/slot

**Display Views:**
- **Summary View**: Count of components by type and status
- **Chassis View**: Visual representation of slots and cards
- **List View**: Tabular data with sorting and filtering
- **Detail View**: Complete information for selected component

**Key Metrics:**
- Total chassis count by model
- Card installation percentage (occupied vs. available slots)
- Power supply redundancy status
- Fan health status
- Components with warnings/failures

### 4.4 Vendor-Specific Considerations

#### Nokia 7750 SR:
- Use pySROS library when available (more reliable than NETCONF)
- Handle nested MDA structures within IOMs
- Parse CLEI codes for regulatory compliance
- Different chassis models have different slot counts

#### Cisco IOS-XR:
- Admin mode may be required for some inventory commands
- Handle location-based naming scheme (rack/slot/module)
- PID/VID/SN format is standard across platforms
- Some platforms support SPA (Shared Port Adapter) sub-modules

---

## 5. Code Examples

### 5.1 Nokia 7750 SR Inventory Collection (pySROS)

```python
from pysros.management import connect
import json

async def collect_nokia_inventory(device_ip, username, password, port=830):
    """Collect hardware inventory from Nokia 7750 SR device"""

    inventory = {
        "chassis": {},
        "cards": [],
        "power_supplies": [],
        "fans": []
    }

    # Connect to device
    connection = connect(
        host=device_ip,
        username=username,
        password=password,
        port=port,
        hostkey_verify=False
    )

    try:
        # Get chassis state
        chassis_state = connection.running.get(
            '/nokia-state:state/chassis[chassis-class="router"][chassis-number="1"]'
        )

        if chassis_state:
            inventory["chassis"] = {
                "model": str(chassis_state.get('chassis-class', '')),
                "serial_number": str(chassis_state.get('serial-number', '')),
                "part_number": str(chassis_state.get('part-number', '')),
                "oper_state": str(chassis_state.get('oper-state', ''))
            }

            # Extract power supplies
            if 'power-supply' in chassis_state:
                for ps_id, ps_data in chassis_state['power-supply'].items():
                    inventory["power_supplies"].append({
                        "id": ps_id,
                        "type": str(ps_data.get('type', '')),
                        "status": str(ps_data.get('status', '')),
                        "serial_number": str(ps_data.get('serial-number', ''))
                    })

            # Extract fans
            if 'fan' in chassis_state:
                for fan_id, fan_data in chassis_state['fan'].items():
                    inventory["fans"].append({
                        "id": fan_id,
                        "status": str(fan_data.get('oper-state', '')),
                        "speed": str(fan_data.get('speed', ''))
                    })

        # Get card state
        card_state = connection.running.get('/nokia-state:state/card')

        if card_state:
            for slot_id, card_data in card_state.items():
                card_info = {
                    "slot": slot_id,
                    "type": str(card_data.get('equipped-type', '')),
                    "part_number": str(card_data.get('part-number', '')),
                    "serial_number": str(card_data.get('serial-number', '')),
                    "oper_state": str(card_data.get('oper-state', '')),
                    "admin_state": str(card_data.get('admin-state', '')),
                    "mdas": []
                }

                # Extract MDAs if present
                if 'mda' in card_data:
                    for mda_id, mda_data in card_data['mda'].items():
                        card_info["mdas"].append({
                            "slot": mda_id,
                            "type": str(mda_data.get('equipped-type', '')),
                            "part_number": str(mda_data.get('part-number', '')),
                            "serial_number": str(mda_data.get('serial-number', '')),
                            "oper_state": str(mda_data.get('oper-state', ''))
                        })

                inventory["cards"].append(card_info)

    finally:
        connection.disconnect()

    return inventory
```

### 5.2 Cisco IOS-XR Inventory Collection (NETCONF)

```python
from ncclient import manager
from lxml import etree
import json

async def collect_cisco_inventory(device_ip, username, password, port=830):
    """Collect hardware inventory from Cisco IOS-XR device"""

    inventory = {
        "chassis": {},
        "cards": [],
        "power_supplies": [],
        "fans": []
    }

    # NETCONF filter for inventory
    filter_xml = """
    <inventory xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper">
      <racks>
        <rack>
          <entity>
            <attributes/>
          </entity>
          <powershelf>
            <attributes/>
          </powershelf>
          <fantray>
            <attributes/>
          </fantray>
        </rack>
      </racks>
    </inventory>
    """

    # Connect via NETCONF
    with manager.connect(
        host=device_ip,
        port=port,
        username=username,
        password=password,
        hostkey_verify=False,
        device_params={'name': 'iosxr'}
    ) as m:

        # Get inventory data
        result = m.get(filter=('subtree', filter_xml))
        root = etree.fromstring(result.data_xml.encode())

        # Define namespace
        ns = {'inv': 'http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper'}

        # Parse racks
        for rack in root.findall('.//inv:rack', ns):
            rack_name = rack.find('inv:name', ns).text if rack.find('inv:name', ns) is not None else ""

            # Parse entities (cards/modules)
            for entity in rack.findall('.//inv:entity', ns):
                attrs = entity.find('inv:attributes', ns)
                if attrs is not None:
                    name = attrs.find('inv:name', ns)
                    desc = attrs.find('inv:description', ns)
                    pid = attrs.find('inv:pid', ns)
                    vid = attrs.find('inv:vid', ns)
                    sn = attrs.find('inv:serial-number', ns)

                    component = {
                        "location": name.text if name is not None else "",
                        "description": desc.text if desc is not None else "",
                        "pid": pid.text if pid is not None else "",
                        "vid": vid.text if vid is not None else "",
                        "serial_number": sn.text if sn is not None else ""
                    }

                    # Determine component type based on description
                    desc_lower = component["description"].lower()
                    if "chassis" in desc_lower:
                        inventory["chassis"] = component
                    elif any(x in desc_lower for x in ["card", "processor", "module", "adapter"]):
                        inventory["cards"].append(component)

            # Parse power supplies
            for ps in rack.findall('.//inv:powershelf', ns):
                attrs = ps.find('inv:attributes', ns)
                if attrs is not None:
                    inventory["power_supplies"].append({
                        "location": attrs.find('inv:name', ns).text if attrs.find('inv:name', ns) is not None else "",
                        "description": attrs.find('inv:description', ns).text if attrs.find('inv:description', ns) is not None else "",
                        "serial_number": attrs.find('inv:serial-number', ns).text if attrs.find('inv:serial-number', ns) is not None else ""
                    })

            # Parse fan trays
            for fan in rack.findall('.//inv:fantray', ns):
                attrs = fan.find('inv:attributes', ns)
                if attrs is not None:
                    inventory["fans"].append({
                        "location": attrs.find('inv:name', ns).text if attrs.find('inv:name', ns) is not None else "",
                        "description": attrs.find('inv:description', ns).text if attrs.find('inv:description', ns) is not None else ""
                    })

    return inventory
```

---

## 6. References and Documentation

### Nokia 7750 SR:
- [Nokia 7x50 YANG Models Repository](https://github.com/nokia/7x50_YangModels)
- [Nokia SR OS NETCONF Documentation](https://documentation.nokia.com/html/0_add-h-f/93-0071-HTML/7750_SR_OS_System_Management_Guide/NETCONF-Intro.html)
- [Nokia SR OS Interface Configuration Guide](https://documentation.nokia.com/html/0_add-h-f/93-0072-HTML/7750_SR_OS_Interfaces_Guide/Interface-CLI-Show-CLI.html)
- [pySROS Documentation](https://network.developer.nokia.com/static/sr/learn/pysros/latest/introduction.html)
- [Nokia YANG Navigation Guide](https://network.developer.nokia.com/sr/learn/yang/sr-os-yang-navigation-101/)

### Cisco IOS-XR:
- [Cisco YANG Models Repository](https://github.com/YangModels/yang)
- [Cisco IOS-XR YANG Data Model Overview](https://xrdocs.io/programmability/tutorials/2016-09-15-xr-data-model-overview/)
- [Cisco ASR 9000 System Setup Command Reference](https://www.cisco.com/c/en/us/td/docs/iosxr/asr9000/system-setup/cumulative/command/reference/b-system-setup-cr-asr9000/m-show-commands.html)
- [Cisco IOS-XR Hardware Commands](https://freenetworktutorials.com/useful-cisco-ios-xr-hardware-related-commands/)
- [Find YANG Models in Cisco IOS XR](https://www.cisco.com/c/en/us/support/docs/ios-nx-os-software/ios-xr-software/213339-find-yang-models-in-cisco-ios-xr-softwar.html)

### General:
- [NETCONF RFC 6241](https://datatracker.ietf.org/doc/html/rfc6241)
- [YANG RFC 7950](https://datatracker.ietf.org/doc/html/rfc7950)

---

## 7. Next Steps for Implementation

1. **Create Database Schema**: Implement the hardware_inventory table
2. **Develop Inventory Service**: Create service layer for collecting and storing inventory
3. **Build API Endpoints**: Expose hardware inventory via REST API
4. **Design Frontend Dashboard**: Create React components for visualization
5. **Implement Filtering**: Add vendor and chassis model filtering
6. **Add Scheduling**: Set up periodic inventory collection
7. **Create Alerts**: Notify on hardware failures or changes
8. **Test with Real Devices**: Validate against actual Nokia and Cisco equipment

---

**Document Version**: 1.0
**Last Updated**: 2025-11-25
**Author**: Network Audit Platform Development Team
