"""
Hardware Inventory Service
Collects hardware inventory from Nokia SROS and Cisco IOS-XR devices
"""
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import xml.etree.ElementTree as ET

from db_models import DeviceDB, HardwareInventoryDB
from models.enums import VendorType
from models.device import Device
from connectors.nokia_sros_connector import NokiaSROSConnector
from connectors.netconf_connector import NetconfConnector
from utils.logger import setup_logger

logger = setup_logger(__name__)


class HardwareInventoryService:
    """Service for collecting and managing hardware inventory"""

    @staticmethod
    async def scan_device(db: Session, device_id: int) -> Dict[str, Any]:
        """Scan a device and collect hardware inventory"""
        try:
            device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
            if not device:
                return {"success": False, "error": "Device not found"}

            logger.info(f"Starting hardware inventory scan for {device.hostname}")

            # Delete existing inventory for this device
            db.query(HardwareInventoryDB).filter(
                HardwareInventoryDB.device_id == device_id
            ).delete()
            db.commit()

            # Collect inventory based on vendor
            if device.vendor == VendorType.NOKIA_SROS:
                components = await HardwareInventoryService._collect_nokia_inventory(device)
            elif device.vendor == VendorType.CISCO_IOS_XR:
                components = await HardwareInventoryService._collect_cisco_inventory(device)
            else:
                return {"success": False, "error": f"Vendor {device.vendor} not supported"}

            # Store in database
            for comp in components:
                hardware = HardwareInventoryDB(
                    device_id=device_id,
                    **comp
                )
                db.add(hardware)

            db.commit()

            logger.info(f"Hardware inventory scan completed for {device.hostname}: {len(components)} components")
            return {
                "success": True,
                "device_id": device_id,
                "device_name": device.hostname,
                "components_found": len(components),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.exception(f"Failed to scan device {device_id}: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def _extract_pysros_value(obj, default=''):
        """Extract actual value from pySROS Leaf object"""
        if obj is None:
            return default
        # pySROS Leaf objects have a .data attribute with the actual value
        if hasattr(obj, 'data'):
            return str(obj.data) if obj.data is not None else default
        # If it's already a simple type, return it
        return str(obj) if obj else default

    @staticmethod
    async def _collect_nokia_inventory(device: DeviceDB) -> List[Dict[str, Any]]:
        """Collect inventory from Nokia SROS device using pySROS NETCONF with debug logging"""
        connector = None
        components = []

        try:
            # Convert DB device to Device model
            device_model = Device(
                id=device.id,
                hostname=device.hostname,
                vendor=VendorType(device.vendor),
                ip=device.ip,
                port=device.port,
                username=device.username,
                password=device.password
            )

            connector = NokiaSROSConnector(device_model)
            connected = await connector.connect()

            if not connected:
                logger.error(f"Failed to connect to Nokia device {device.hostname}")
                return []

            # Get chassis state
            loop = asyncio.get_event_loop()
            chassis_state = await loop.run_in_executor(
                None,
                lambda: connector.connection.running.get('/nokia-state:state/chassis')
            )

            # DEBUG: Log the actual structure
            logger.info(f"DEBUG - Raw chassis_state type: {type(chassis_state)}")
            logger.info(f"DEBUG - Raw chassis_state keys: {chassis_state.keys() if isinstance(chassis_state, dict) else 'Not a dict'}")
            logger.info(f"DEBUG - Raw chassis_state content: {str(chassis_state)[:1000]}")

            # Process chassis - extract first value from dict (key is tuple like ('router', 1))
            if chassis_state and isinstance(chassis_state, dict):
                # Get first value regardless of key (key is tuple like ('router', 1))
                chassis_container = next(iter(chassis_state.values())) if chassis_state else None

                if chassis_container:
                    # Extract data from pySROS Container object using helper
                    chassis_class = HardwareInventoryService._extract_pysros_value(
                        chassis_container.get('chassis-class'), 'Unknown'
                    )
                    hardware_data = chassis_container.get('hardware-data', {})

                    part_num = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('part-number'), ''
                    ) if hardware_data else ''
                    serial_num = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('serial-number'), ''
                    ) if hardware_data else ''
                    clei = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('common-language-equipment-identifier'), ''
                    ) if hardware_data else ''
                    mfg_date = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('manufacturing-date'), ''
                    ) if hardware_data else ''
                    oper_state = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('oper-state'), 'up'
                    ) if hardware_data else 'up'

                    components.append({
                        'component_type': 'chassis',
                        'component_name': f"Chassis {chassis_class}",
                        'slot_number': None,
                        'part_number': part_num or None,
                        'serial_number': serial_num or None,
                        'hardware_revision': None,
                        'model_name': chassis_class,
                        'description': f"Nokia {chassis_class} Chassis",
                        'clei_code': clei or None,
                        'manufacturing_date': mfg_date or None,
                        'is_fru': True,
                        'operational_state': oper_state,
                    })
                    logger.info(f"Parsed chassis: {chassis_class}, SN: {serial_num}, PN: {part_num}")

                    # Parse power supplies
                    power_supplies_count = HardwareInventoryService._extract_pysros_value(
                        chassis_container.get('power-supplies'), '0'
                    )
                    try:
                        ps_count = int(power_supplies_count)
                        logger.info(f"Found {ps_count} power supplies")
                        for ps_num in range(1, ps_count + 1):
                            components.append({
                                'component_type': 'power',
                                'component_name': f"Power Supply {ps_num}",
                                'slot_number': str(ps_num),
                                'part_number': None,
                                'serial_number': None,
                                'hardware_revision': None,
                                'model_name': 'Power Supply',
                                'description': f"Power Supply unit {ps_num}",
                                'operational_state': 'up',
                                'admin_state': None,
                                'is_fru': True,
                            })
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse power supplies count: {power_supplies_count}")

                    # Parse fan trays
                    fan_trays_count = HardwareInventoryService._extract_pysros_value(
                        chassis_container.get('fan-trays'), '0'
                    )
                    try:
                        fan_count = int(fan_trays_count)
                        logger.info(f"Found {fan_count} fan trays")
                        for fan_num in range(1, fan_count + 1):
                            components.append({
                                'component_type': 'fan',
                                'component_name': f"Fan Tray {fan_num}",
                                'slot_number': str(fan_num),
                                'part_number': None,
                                'serial_number': None,
                                'hardware_revision': None,
                                'model_name': 'Fan Tray',
                                'description': f"Fan tray unit {fan_num}",
                                'operational_state': 'up',
                                'admin_state': None,
                                'is_fru': True,
                            })
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse fan trays count: {fan_trays_count}")

            # Get card state
            card_state = await loop.run_in_executor(
                None,
                lambda: connector.connection.running.get('/nokia-state:state/card')
            )

            # DEBUG: Log card structure
            logger.info(f"DEBUG - Raw card_state type: {type(card_state)}")
            logger.info(f"DEBUG - Raw card_state keys: {card_state.keys() if isinstance(card_state, dict) else 'Not a dict'}")
            logger.info(f"DEBUG - Raw card_state content: {str(card_state)[:1000]}")

            if card_state and isinstance(card_state, dict):
                # card_state is a dict where keys are slot numbers (integers)
                logger.info(f"Processing {len(card_state)} cards")

                for slot_num, card_container in card_state.items():
                    # Extract data from pySROS Container object using helper
                    equipped_type = HardwareInventoryService._extract_pysros_value(
                        card_container.get('equipped-type'), 'Unknown'
                    )
                    hardware_data = card_container.get('hardware-data', {})

                    part_num = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('part-number'), ''
                    ) if hardware_data else ''
                    serial_num = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('serial-number'), ''
                    ) if hardware_data else ''
                    oper_state = HardwareInventoryService._extract_pysros_value(
                        hardware_data.get('oper-state'), 'unknown'
                    ) if hardware_data else 'unknown'

                    components.append({
                        'component_type': 'card',
                        'component_name': f"{equipped_type} Slot {slot_num}",
                        'slot_number': str(slot_num),
                        'part_number': part_num or None,
                        'serial_number': serial_num or None,
                        'hardware_revision': None,
                        'firmware_version': None,
                        'model_name': equipped_type,
                        'description': f"{equipped_type} in slot {slot_num}",
                        'operational_state': oper_state,
                        'admin_state': None,
                        'is_fru': True,
                    })
                    logger.info(f"Parsed card: {equipped_type} in slot {slot_num}, SN: {serial_num}, PN: {part_num}")

            logger.info(f"Collected {len(components)} components from Nokia device {device.hostname}")
            return components

        except Exception as e:
            logger.exception(f"Error collecting Nokia inventory: {e}")
            return []
        finally:
            if connector:
                try:
                    await connector.disconnect()
                except:
                    pass

    @staticmethod
    async def _collect_cisco_inventory(device: DeviceDB) -> List[Dict[str, Any]]:
        """Collect inventory from Cisco IOS-XR device using NETCONF"""
        connector = None
        components = []

        try:
            # Convert DB device to Device model
            device_model = Device(
                id=device.id,
                hostname=device.hostname,
                vendor=VendorType(device.vendor),
                ip=device.ip,
                port=device.port,
                username=device.username,
                password=device.password
            )

            connector = NetconfConnector(device_model)
            connected = await connector.connect()

            if not connected:
                logger.error(f"Failed to connect to Cisco device {device.hostname}")
                return []

            # Build NETCONF filter for inventory
            filter_xml = '''
            <inventory xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper">
                <racks>
                    <rack>
                        <entity>
                            <attributes/>
                        </entity>
                    </rack>
                </racks>
            </inventory>
            '''

            # Get inventory
            result = connector.netconf_manager.get(('subtree', filter_xml))

            # Parse XML
            root = ET.fromstring(result.data_xml)

            # Define namespace
            ns = {'inv': 'http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper'}

            # Process racks
            for rack in root.findall('.//inv:rack', ns):
                rack_num = rack.find('inv:rack-name', ns)
                rack_num_text = rack_num.text if rack_num is not None else '0'

                # Process entities (components)
                for entity in rack.findall('.//inv:entity', ns):
                    attrs = entity.find('inv:attributes', ns)
                    if attrs is None:
                        continue

                    name = attrs.find('inv:name', ns)
                    desc = attrs.find('inv:description', ns)
                    pid = attrs.find('inv:model-name', ns)  # or basic-info/model-name
                    vid = attrs.find('inv:hardware-revision', ns)
                    sn = attrs.find('inv:serial-number', ns)
                    is_fru = attrs.find('inv:is-field-replaceable-unit', ns)

                    name_text = name.text if name is not None else 'Unknown'
                    desc_text = desc.text if desc is not None else ''
                    pid_text = pid.text if pid is not None else None
                    vid_text = vid.text if vid is not None else None
                    sn_text = sn.text if sn is not None else None
                    is_fru_val = is_fru.text == 'true' if is_fru is not None else False

                    # Determine component type based on name
                    comp_type = 'card'
                    if 'chassis' in name_text.lower() or 'rack' in name_text.lower():
                        comp_type = 'chassis'
                    elif 'power' in name_text.lower() or 'pem' in name_text.lower() or 'pm' in name_text.lower():
                        comp_type = 'power'
                    elif 'fan' in name_text.lower() or 'ft' in name_text.lower():
                        comp_type = 'fan'
                    elif 'rp' in name_text.lower() or 'route' in name_text.lower():
                        comp_type = 'rp'

                    components.append({
                        'component_type': comp_type,
                        'component_name': name_text,
                        'slot_number': name_text,  # Cisco uses name as location
                        'part_number': pid_text,
                        'serial_number': sn_text,
                        'hardware_revision': vid_text,
                        'model_name': pid_text,
                        'description': desc_text,
                        'is_fru': is_fru_val,
                    })

            logger.info(f"Collected {len(components)} components from Cisco device {device.hostname}")
            return components

        except Exception as e:
            logger.exception(f"Error collecting Cisco inventory: {e}")
            return []
        finally:
            if connector:
                try:
                    await connector.disconnect()
                except:
                    pass

    @staticmethod
    def get_device_inventory(db: Session, device_id: int) -> List[HardwareInventoryDB]:
        """Get all hardware inventory for a device"""
        return db.query(HardwareInventoryDB).filter(
            HardwareInventoryDB.device_id == device_id
        ).all()

    @staticmethod
    def get_chassis_summary(db: Session) -> List[Dict[str, Any]]:
        """Get summary of all chassis grouped by vendor and model"""
        from sqlalchemy import func

        results = db.query(
            DeviceDB.vendor,
            HardwareInventoryDB.model_name,
            func.count(HardwareInventoryDB.id).label('count')
        ).join(
            HardwareInventoryDB,
            HardwareInventoryDB.device_id == DeviceDB.id
        ).filter(
            HardwareInventoryDB.component_type == 'chassis'
        ).group_by(
            DeviceDB.vendor,
            HardwareInventoryDB.model_name
        ).all()

        return [
            {
                'vendor': r.vendor.value if hasattr(r.vendor, 'value') else str(r.vendor),
                'chassis_model': r.model_name,
                'count': r.count
            }
            for r in results
        ]
