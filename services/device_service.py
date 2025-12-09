
# ============================================================================
# services/device_service.py
# ============================================================================

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.device import Device, DeviceCreate, DeviceUpdate
from models.enums import DeviceStatus
from db_models import DeviceDB
from shared.logger import setup_logger
from shared.exceptions import DeviceNotFoundError
from shared.validators import validate_hostname, validate_ip
from shared.backoff import BackoffManager
from services.license_enforcement_service import license_enforcement_service

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

    def merge_discovered_devices(self, db: Session, discovered: List[Device]) -> int:
        """
        Merge discovered devices with existing ones
        
        Enforces device limits based on license tier - only adds devices within quota.
        """
        # First pass: separate new devices from updates
        new_devices_to_add = []
        
        for new_device in discovered:
            # First check if a device with this IP already exists (primary match)
            existing_by_ip = None
            if new_device.ip:
                existing_by_ip = db.query(DeviceDB).filter(DeviceDB.ip == new_device.ip).first()

            # Also check by hostname
            existing_by_hostname = db.query(DeviceDB).filter(DeviceDB.hostname == new_device.hostname).first()

            if existing_by_ip:
                # Device with this IP exists - update it (doesn't count against quota)
                if existing_by_ip.hostname != new_device.hostname:
                    # Hostname changed - need to handle UNIQUE constraint
                    # Check if another device already has the new hostname
                    conflict_device = db.query(DeviceDB).filter(
                        DeviceDB.hostname == new_device.hostname,
                        DeviceDB.id != existing_by_ip.id
                    ).first()

                    if conflict_device:
                        logger.info(f"Removing stale device '{conflict_device.hostname}' at {conflict_device.ip} (ID: {conflict_device.id}) - hostname now belongs to {new_device.ip}")
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
                logger.info(f"Updated existing device at {new_device.ip} (ID: {existing_by_ip.id})")
            elif existing_by_hostname:
                # Device with this hostname exists but different IP - update IP (doesn't count against quota)
                logger.info(f"IP changed for device {new_device.hostname}: {existing_by_hostname.ip} -> {new_device.ip}")
                existing_by_hostname.ip = new_device.ip
                existing_by_hostname.vendor = new_device.vendor
                existing_by_hostname.port = new_device.port or 830
                existing_by_hostname.username = new_device.username
                existing_by_hostname.password = new_device.password
                existing_by_hostname.status = DeviceStatus.DISCOVERED
                existing_by_hostname.updated_at = datetime.utcnow()
            else:
                # Brand new device - add to list for quota checking
                new_devices_to_add.append(new_device)

        # Enforce device limits using license enforcement service
        if new_devices_to_add:
            enforcement_result = license_enforcement_service.enforce_device_limit_on_discovery(
                db, [d.__dict__ for d in new_devices_to_add]
            )
            
            accepted_devices = enforcement_result["accepted"]
            rejected_devices = enforcement_result["rejected"]
            
            if rejected_devices:
                logger.warning(
                    f"Device quota exceeded: {len(rejected_devices)} discovered devices rejected. "
                    f"Upgrade license to add more devices."
                )
            
            # Add only the accepted devices
            added_count = 0
            for i, new_device in enumerate(new_devices_to_add):
                # Check if this device was accepted
                if i < len(accepted_devices):
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
                    added_count += 1
                    logger.info(f"Added new device: {new_device.hostname} at {new_device.ip}")
                else:
                    logger.info(f"Skipped device due to quota: {new_device.hostname} at {new_device.ip}")
        else:
            added_count = 0

        db.commit()
        
        # Update license usage stats
        license_enforcement_service.enforcer.update_license_usage(db)
        
        logger.info(f"Merged {added_count} new devices (quota enforced)")
        return added_count

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
        db_devices = db.query(DeviceDB).filter(DeviceDB.metadata.isnot(None)).all()

        # Track values by field type
        field_values = {
            'isis_net': {},          # ISIS NET address
            'system_address': {},    # System/Loopback0 address
            'bgp_router_id': {},     # BGP router-id
        }

        # Extract values from each device's metadata
        for device in db_devices:
            metadata = device.metadata
            if not metadata:
                continue

            device_info = {'id': device.id, 'hostname': device.hostname}

            # Check ISIS NET address
            isis_net = None
            if 'igp' in metadata:
                igp = metadata.get('igp', {})
                if 'isis' in igp:
                    isis_data = igp.get('isis', {})
                    isis_net = isis_data.get('net_address') or isis_data.get('net')
            if isis_net:
                if isis_net not in field_values['isis_net']:
                    field_values['isis_net'][isis_net] = []
                field_values['isis_net'][isis_net].append(device_info)

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
            'isis_net': 'ISIS NET Address',
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
        # Get metadata from JSON column - ensure it's a dict
        metadata = None
        if db_device.metadata:
            if isinstance(db_device.metadata, dict):
                metadata = db_device.metadata
            elif hasattr(db_device.metadata, '__dict__'):
                # Convert object to dict if it has __dict__
                metadata = {k: v for k, v in db_device.metadata.__dict__.items() if not k.startswith('_')}
            elif hasattr(db_device.metadata, 'dict'):
                # Pydantic model
                metadata = db_device.metadata.dict()

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
