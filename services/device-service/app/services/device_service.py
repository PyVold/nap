
# ============================================================================
# services/device_service.py
# ============================================================================

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.device import Device, DeviceCreate, DeviceUpdate
from models.enums import DeviceStatus, VendorType
from db_models import DeviceDB
from shared.logger import setup_logger
from shared.exceptions import DeviceNotFoundError
from shared.validators import validate_hostname, validate_ip
from shared.backoff import BackoffManager
from shared.device_metadata_collector import DeviceMetadataCollector
import json

logger = setup_logger(__name__)

class DeviceService:
    """Service for device management operations with database persistence"""

    def __init__(self):
        pass

    def get_all_devices(self, db: Session) -> List[Device]:
        """Get all devices"""
        db_devices = db.query(DeviceDB).all()
        return [self._to_pydantic(d) for d in db_devices]

    def get_device_by_id(self, db: Session, device_id: int) -> Optional[Device]:
        """Get device by ID"""
        db_device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
        return self._to_pydantic(db_device) if db_device else None

    def get_device_by_hostname(self, db: Session, hostname: str) -> Optional[Device]:
        """Get device by hostname"""
        db_device = db.query(DeviceDB).filter(DeviceDB.hostname == hostname).first()
        return self._to_pydantic(db_device) if db_device else None

    def create_device(self, db: Session, device_create: DeviceCreate) -> Device:
        """Create a new device"""
        # Validate inputs
        if not validate_hostname(device_create.hostname):
            raise ValueError(f"Invalid hostname: {device_create.hostname}")

        if device_create.ip and not validate_ip(device_create.ip):
            raise ValueError(f"Invalid IP address: {device_create.ip}")

        # Check for duplicate hostname
        if self.get_device_by_hostname(db, device_create.hostname):
            raise ValueError(f"Device with hostname {device_create.hostname} already exists")

        # Check for duplicate IP - if found, replace the old device
        if device_create.ip:
            existing_ip_device = db.query(DeviceDB).filter(DeviceDB.ip == device_create.ip).first()
            if existing_ip_device:
                logger.info(f"Replacing device {existing_ip_device.hostname} (ID: {existing_ip_device.id}) with same IP {device_create.ip}")
                # Delete the old device with the same IP
                db.delete(existing_ip_device)
                db.flush()  # Flush to release the IP constraint

        # Create device in database
        db_device = DeviceDB(
            hostname=device_create.hostname,
            vendor=device_create.vendor,
            ip=device_create.ip,
            port=device_create.port or 830,
            username=device_create.username,
            password=device_create.password,
            status=DeviceStatus.REGISTERED,
            compliance=0.0
        )

        db.add(db_device)
        db.commit()
        db.refresh(db_device)

        logger.info(f"Created device: {db_device.hostname} (ID: {db_device.id})")

        return self._to_pydantic(db_device)

    def update_device(self, db: Session, device_id: int, device_update: DeviceUpdate) -> Device:
        """Update an existing device"""
        db_device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
        if not db_device:
            raise DeviceNotFoundError(f"Device with ID {device_id} not found")

        # Update fields
        update_data = device_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_device, field, value)

        db_device.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_device)

        logger.info(f"Updated device: {db_device.hostname} (ID: {db_device.id})")
        return self._to_pydantic(db_device)

    def delete_device(self, db: Session, device_id: int) -> bool:
        """Delete a device"""
        db_device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
        if not db_device:
            raise DeviceNotFoundError(f"Device with ID {device_id} not found")

        db.delete(db_device)
        db.commit()

        logger.info(f"Deleted device ID: {device_id}")
        return True

    def merge_discovered_devices(self, db: Session, discovered: List[Device]) -> tuple[int, List[int]]:
        """
        Merge discovered devices with existing ones

        Returns:
            tuple: (added_count, device_ids_for_metadata_collection)
        """
        added_count = 0
        device_ids_for_metadata = set()  # Use set to prevent duplicate device IDs

        # Phase 1: Detect hostname/IP swaps and handle them with temporary names
        # This prevents incorrectly deleting devices when they swap identifiers
        swap_candidates = []

        for new_device in discovered:
            if not new_device.ip:
                continue

            existing_by_ip = db.query(DeviceDB).filter(DeviceDB.ip == new_device.ip).first()

            if existing_by_ip and existing_by_ip.hostname != new_device.hostname:
                # This device's hostname changed - check if it's part of a swap
                conflict_device = db.query(DeviceDB).filter(
                    DeviceDB.hostname == new_device.hostname,
                    DeviceDB.id != existing_by_ip.id
                ).first()

                if conflict_device:
                    # Check if this is a swap: does the conflict device want our old hostname?
                    reverse_discovery = next(
                        (d for d in discovered if d.ip == conflict_device.ip and d.hostname == existing_by_ip.hostname),
                        None
                    )

                    if reverse_discovery:
                        # This is a hostname SWAP between two devices
                        logger.info(f"Detected hostname swap: {existing_by_ip.hostname} <-> {conflict_device.hostname} between IPs {existing_by_ip.ip} and {conflict_device.ip}")
                        swap_candidates.append((existing_by_ip, conflict_device, new_device.hostname, existing_by_ip.hostname))

        # Handle swaps using temporary hostnames to avoid UNIQUE constraint violations
        temp_hostname_map = {}
        for device_a, device_b, hostname_a_wants, hostname_b_wants in swap_candidates:
            temp_name_a = f"__temp_swap_{device_a.id}_{datetime.utcnow().timestamp()}"
            temp_name_b = f"__temp_swap_{device_b.id}_{datetime.utcnow().timestamp()}"

            logger.info(f"Swapping hostnames: Device {device_a.id} ({device_a.hostname} -> {hostname_a_wants}), Device {device_b.id} ({device_b.hostname} -> {hostname_b_wants})")

            # Temporarily rename both to avoid conflicts
            device_a.hostname = temp_name_a
            device_b.hostname = temp_name_b
            db.flush()

            # Now assign final hostnames
            device_a.hostname = hostname_a_wants
            device_b.hostname = hostname_b_wants
            db.flush()

            # Track that these were already handled
            temp_hostname_map[device_a.ip] = device_a.id
            temp_hostname_map[device_b.ip] = device_b.id

        # Phase 2: Process all discovered devices normally
        for new_device in discovered:
            # Skip devices already handled in swap phase
            if new_device.ip in temp_hostname_map:
                device_id = temp_hostname_map[new_device.ip]
                existing = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
                if existing:
                    # Update other fields that might have changed
                    existing.vendor = new_device.vendor
                    existing.port = new_device.port or 830
                    existing.username = new_device.username
                    existing.password = new_device.password
                    existing.status = DeviceStatus.DISCOVERED
                    existing.updated_at = datetime.utcnow()
                    device_ids_for_metadata.add(existing.id)
                    logger.info(f"Updated device {existing.hostname} at {existing.ip} (ID: {existing.id}) - hostname swapped in Phase 1")
                continue

            # First check if a device with this IP already exists (primary match)
            existing_by_ip = None
            if new_device.ip:
                existing_by_ip = db.query(DeviceDB).filter(DeviceDB.ip == new_device.ip).first()

            # Also check by hostname
            existing_by_hostname = db.query(DeviceDB).filter(DeviceDB.hostname == new_device.hostname).first()

            if existing_by_ip:
                # Device with this IP exists - update it
                if existing_by_ip.hostname != new_device.hostname:
                    # Hostname changed - need to handle UNIQUE constraint
                    # Check if another device already has the new hostname
                    conflict_device = db.query(DeviceDB).filter(
                        DeviceDB.hostname == new_device.hostname,
                        DeviceDB.id != existing_by_ip.id
                    ).first()

                    if conflict_device:
                        # Device conflict that wasn't a swap - this means the conflicting device is no longer discovered
                        # Instead of deleting immediately, mark it for investigation
                        logger.warning(f"Hostname conflict detected: device at {new_device.ip} wants hostname '{new_device.hostname}', but device {conflict_device.id} at {conflict_device.ip} already has it")
                        logger.warning(f"Conflicting device {conflict_device.id} was not discovered in this scan - it may be offline or unreachable")
                        logger.info(f"Removing device '{conflict_device.hostname}' at {conflict_device.ip} (ID: {conflict_device.id}) - not discovered and hostname claimed by {new_device.ip}")
                        db.delete(conflict_device)
                        db.flush()  # Flush to release the hostname constraint

                    logger.info(f"Hostname changed for device at {new_device.ip}: {existing_by_ip.hostname} -> {new_device.hostname}")
                    existing_by_ip.hostname = new_device.hostname

                # Update other fields that might have changed
                existing_by_ip.vendor = new_device.vendor
                existing_by_ip.port = new_device.port or 830
                existing_by_ip.username = new_device.username
                existing_by_ip.password = new_device.password
                existing_by_ip.status = DeviceStatus.DISCOVERED
                existing_by_ip.updated_at = datetime.utcnow()
                db.flush()  # Flush so subsequent device queries see this update
                device_ids_for_metadata.add(existing_by_ip.id)
                logger.info(f"Updated existing device at {new_device.ip} (ID: {existing_by_ip.id})")
            elif existing_by_hostname:
                # Device with this hostname exists but different IP - update IP
                # Check if there's already a device at the new IP
                ip_conflict = db.query(DeviceDB).filter(
                    DeviceDB.ip == new_device.ip,
                    DeviceDB.id != existing_by_hostname.id
                ).first()

                if ip_conflict:
                    logger.warning(f"IP conflict: device '{new_device.hostname}' wants IP {new_device.ip}, but device {ip_conflict.id} ('{ip_conflict.hostname}') already has it")
                    logger.warning(f"Conflicting device {ip_conflict.id} was not discovered - removing it")
                    db.delete(ip_conflict)
                    db.flush()

                logger.info(f"IP changed for device {new_device.hostname}: {existing_by_hostname.ip} -> {new_device.ip}")
                existing_by_hostname.ip = new_device.ip
                existing_by_hostname.vendor = new_device.vendor
                existing_by_hostname.port = new_device.port or 830
                existing_by_hostname.username = new_device.username
                existing_by_hostname.password = new_device.password
                existing_by_hostname.status = DeviceStatus.DISCOVERED
                existing_by_hostname.updated_at = datetime.utcnow()
                db.flush()  # Flush so subsequent device queries see this update
                device_ids_for_metadata.add(existing_by_hostname.id)
            else:
                # Brand new device - add it
                db_device = DeviceDB(
                    hostname=new_device.hostname,
                    vendor=new_device.vendor,
                    ip=new_device.ip,
                    port=new_device.port or 830,
                    username=new_device.username,
                    password=new_device.password,
                    status=DeviceStatus.DISCOVERED,
                    compliance=0.0
                )
                db.add(db_device)
                db.flush()  # Flush to get the ID
                device_ids_for_metadata.add(db_device.id)
                added_count += 1
                logger.info(f"Added new device: {new_device.hostname} at {new_device.ip}")

        db.commit()
        logger.info(f"Merged {added_count} new devices, {len(device_ids_for_metadata)} devices for metadata collection")
        return added_count, list(device_ids_for_metadata)

    async def collect_device_metadata(self, db: Session, device_id: int) -> bool:
        """
        Collect protocol metadata for a device and store it in the database

        Args:
            db: Database session
            device_id: Device ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get device from database
            db_device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
            if not db_device:
                logger.error(f"Device {device_id} not found")
                return False

            logger.info(f"Collecting metadata for device: {db_device.hostname} ({db_device.vendor})")

            # Create a Device object for the connector
            device = Device(
                id=db_device.id,
                hostname=db_device.hostname,
                vendor=db_device.vendor,
                ip=db_device.ip,
                port=db_device.port,
                username=db_device.username,
                password=db_device.password,
                status=db_device.status,
                compliance=db_device.compliance
            )

            # Import and create appropriate connector
            from connectors import DeviceConnector

            connector = DeviceConnector(device)

            # Connect to device
            await connector.connect()

            # Collect metadata using the connector
            metadata = await DeviceMetadataCollector.collect_metadata(
                vendor=db_device.vendor,
                connection=connector.connector  # Pass the underlying connector
            )

            # Disconnect from device
            await connector.disconnect()

            if metadata:
                # Store metadata in database (using device_metadata attribute)
                db_device.device_metadata = metadata  # JSON column handles serialization
                db.commit()
                logger.info(f"Metadata collected and stored for {db_device.hostname}")
                return True
            else:
                logger.warning(f"No metadata collected for {db_device.hostname}")
                return False

        except Exception as e:
            logger.error(f"Failed to collect metadata for device {device_id}: {e}")
            return False

    async def collect_metadata_for_discovered_devices(self, db: Session, device_ids: List[int]):
        """
        Collect metadata for multiple devices (called after discovery)

        Args:
            db: Database session
            device_ids: List of device IDs to collect metadata for
        """
        logger.info(f"Starting metadata collection for {len(device_ids)} devices")

        for device_id in device_ids:
            try:
                await self.collect_device_metadata(db, device_id)
            except Exception as e:
                logger.error(f"Metadata collection failed for device {device_id}: {e}")
                # Continue with other devices even if one fails

        logger.info(f"Completed metadata collection for {len(device_ids)} devices")

    def get_devices_by_vendor(self, db: Session, vendor: str) -> List[Device]:
        """Get devices filtered by vendor"""
        db_devices = db.query(DeviceDB).filter(DeviceDB.vendor == vendor).all()
        return [self._to_pydantic(d) for d in db_devices]

    def get_devices_by_status(self, db: Session, status: DeviceStatus) -> List[Device]:
        """Get devices filtered by status"""
        db_devices = db.query(DeviceDB).filter(DeviceDB.status == status).all()
        return [self._to_pydantic(d) for d in db_devices]

    def detect_metadata_overlaps(self, db: Session) -> dict:
        """
        Detect overlapping metadata values across devices.

        Checks for duplicates in:
        - ISIS NET address
        - System address / Loopback0 address
        - BGP router-id

        Returns:
            dict: {
                'overlaps': {
                    field_path: {
                        value: [device_ids]
                    }
                },
                'device_alerts': {
                    device_id: [{'field': ..., 'value': ..., 'conflicts_with': [...]}]
                }
            }
        """
        db_devices = db.query(DeviceDB).filter(DeviceDB.__table__.c.metadata.isnot(None)).all()

        # Track values by field type
        field_values = {
            'isis_net': {},          # ISIS NET address
            'system_address': {},    # System/Loopback0 address
            'bgp_router_id': {},     # BGP router-id
        }

        # Extract values from each device's metadata
        for device in db_devices:
            # Access metadata via device_metadata attribute (renamed to avoid SQLAlchemy conflict)
            metadata = device.device_metadata
            if not metadata or not isinstance(metadata, dict):
                continue

            device_info = {'id': device.id, 'hostname': device.hostname}

            # Check IGP router-id (ISIS/OSPF system ID)
            # Note: ISIS NET address is not currently collected, so we use IGP router_id
            igp_router_id = None
            if 'igp' in metadata:
                igp = metadata.get('igp', {})
                igp_router_id = igp.get('router_id')
            if igp_router_id:
                if igp_router_id not in field_values['isis_net']:
                    field_values['isis_net'][igp_router_id] = []
                field_values['isis_net'][igp_router_id].append(device_info)

            # Check System address / Loopback0 address
            system_address = None
            if 'system' in metadata:
                system_data = metadata.get('system', {})
                system_address = (
                    system_data.get('system_address') or
                    system_data.get('loopback0_address') or
                    system_data.get('router_id')
                )
            if system_address:
                if system_address not in field_values['system_address']:
                    field_values['system_address'][system_address] = []
                field_values['system_address'][system_address].append(device_info)

            # Check BGP router-id
            bgp_router_id = None
            if 'bgp' in metadata:
                bgp_data = metadata.get('bgp', {})
                bgp_router_id = bgp_data.get('router_id')
            if bgp_router_id:
                if bgp_router_id not in field_values['bgp_router_id']:
                    field_values['bgp_router_id'][bgp_router_id] = []
                field_values['bgp_router_id'][bgp_router_id].append(device_info)

        # Find overlaps (values shared by multiple devices)
        overlaps = {}
        device_alerts = {}

        field_labels = {
            'isis_net': 'IGP Router-ID',
            'system_address': 'System/Loopback0 Address',
            'bgp_router_id': 'BGP Router-ID'
        }

        for field_type, values in field_values.items():
            field_overlaps = {}
            for value, devices in values.items():
                if len(devices) > 1:
                    # This value is used by multiple devices
                    field_overlaps[value] = [d['id'] for d in devices]

                    # Add alerts for each device involved
                    for device in devices:
                        device_id = device['id']
                        if device_id not in device_alerts:
                            device_alerts[device_id] = []

                        conflict_devices = [d for d in devices if d['id'] != device_id]
                        device_alerts[device_id].append({
                            'field': field_labels.get(field_type, field_type),
                            'field_key': field_type,
                            'value': value,
                            'conflicts_with': [{'id': d['id'], 'hostname': d['hostname']} for d in conflict_devices]
                        })

            if field_overlaps:
                overlaps[field_type] = field_overlaps

        return {
            'overlaps': overlaps,
            'device_alerts': device_alerts
        }

    def _to_pydantic(self, db_device: DeviceDB) -> Device:
        """Convert SQLAlchemy model to Pydantic model"""
        # Get metadata from JSON column
        # Note: The attribute is named 'device_metadata' in the model to avoid
        # conflict with SQLAlchemy's Base.metadata
        metadata = None
        try:
            raw_metadata = db_device.device_metadata
            if raw_metadata is not None:
                if isinstance(raw_metadata, dict):
                    metadata = raw_metadata
                elif isinstance(raw_metadata, (str, bytes)):
                    metadata = json.loads(raw_metadata) if raw_metadata else None
        except (TypeError, json.JSONDecodeError, AttributeError):
            metadata = None

        return Device(
            id=db_device.id,
            hostname=db_device.hostname,
            vendor=db_device.vendor,
            ip=db_device.ip,
            port=db_device.port,
            username=db_device.username,
            password=db_device.password,
            status=db_device.status,
            last_audit=db_device.last_audit.isoformat() if db_device.last_audit else None,
            compliance=int(db_device.compliance),
            metadata=metadata,
            backoff_status=BackoffManager.get_backoff_status(db_device)
        )
