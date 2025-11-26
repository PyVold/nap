# ============================================================================
# services/device_group_service.py
# ============================================================================

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.device_group import DeviceGroup, DeviceGroupCreate, DeviceGroupUpdate
from db_models import DeviceGroupDB, DeviceGroupMembershipDB, DeviceDB
from shared.logger import setup_logger

logger = setup_logger(__name__)


class DeviceGroupService:
    """Service for device group management operations"""

    def get_all_groups(self, db: Session) -> List[DeviceGroup]:
        """Get all device groups"""
        db_groups = db.query(DeviceGroupDB).all()
        return [self._to_pydantic(db, g) for g in db_groups]

    def get_group_by_id(self, db: Session, group_id: int) -> Optional[DeviceGroup]:
        """Get device group by ID"""
        db_group = db.query(DeviceGroupDB).filter(DeviceGroupDB.id == group_id).first()
        return self._to_pydantic(db, db_group) if db_group else None

    def create_group(self, db: Session, group_create: DeviceGroupCreate) -> DeviceGroup:
        """Create a new device group"""
        db_group = DeviceGroupDB(
            name=group_create.name,
            description=group_create.description
        )

        db.add(db_group)
        db.commit()
        db.refresh(db_group)

        # Add devices to group
        if group_create.device_ids:
            self._update_group_devices(db, db_group.id, group_create.device_ids)

        logger.info(f"Created device group: {db_group.name} (ID: {db_group.id})")
        return self._to_pydantic(db, db_group)

    def update_group(self, db: Session, group_id: int, group_update: DeviceGroupUpdate) -> DeviceGroup:
        """Update an existing device group"""
        db_group = db.query(DeviceGroupDB).filter(DeviceGroupDB.id == group_id).first()
        if not db_group:
            raise ValueError(f"Device group with ID {group_id} not found")

        update_data = group_update.dict(exclude_unset=True)

        # Handle device_ids separately
        device_ids = update_data.pop('device_ids', None)

        # Update basic fields
        for field, value in update_data.items():
            setattr(db_group, field, value)

        db_group.updated_at = datetime.utcnow()
        db.commit()

        # Update group membership if device_ids provided
        if device_ids is not None:
            self._update_group_devices(db, group_id, device_ids)

        db.refresh(db_group)
        logger.info(f"Updated device group: {db_group.name} (ID: {db_group.id})")
        return self._to_pydantic(db, db_group)

    def delete_group(self, db: Session, group_id: int) -> bool:
        """Delete a device group"""
        db_group = db.query(DeviceGroupDB).filter(DeviceGroupDB.id == group_id).first()
        if not db_group:
            raise ValueError(f"Device group with ID {group_id} not found")

        db.delete(db_group)
        db.commit()

        logger.info(f"Deleted device group ID: {group_id}")
        return True

    def add_device_to_group(self, db: Session, group_id: int, device_id: int) -> bool:
        """Add a device to a group"""
        # Check if already exists
        existing = db.query(DeviceGroupMembershipDB).filter(
            DeviceGroupMembershipDB.group_id == group_id,
            DeviceGroupMembershipDB.device_id == device_id
        ).first()

        if existing:
            return False  # Already exists

        membership = DeviceGroupMembershipDB(
            group_id=group_id,
            device_id=device_id
        )
        db.add(membership)
        db.commit()

        logger.info(f"Added device {device_id} to group {group_id}")
        return True

    def remove_device_from_group(self, db: Session, group_id: int, device_id: int) -> bool:
        """Remove a device from a group"""
        membership = db.query(DeviceGroupMembershipDB).filter(
            DeviceGroupMembershipDB.group_id == group_id,
            DeviceGroupMembershipDB.device_id == device_id
        ).first()

        if not membership:
            return False

        db.delete(membership)
        db.commit()

        logger.info(f"Removed device {device_id} from group {group_id}")
        return True

    def get_group_devices(self, db: Session, group_id: int) -> List[int]:
        """Get all device IDs in a group"""
        memberships = db.query(DeviceGroupMembershipDB).filter(
            DeviceGroupMembershipDB.group_id == group_id
        ).all()
        return [m.device_id for m in memberships]

    def _update_group_devices(self, db: Session, group_id: int, device_ids: List[int]):
        """Replace all devices in a group"""
        # Remove existing memberships
        db.query(DeviceGroupMembershipDB).filter(
            DeviceGroupMembershipDB.group_id == group_id
        ).delete()

        # Add new memberships
        for device_id in device_ids:
            membership = DeviceGroupMembershipDB(
                group_id=group_id,
                device_id=device_id
            )
            db.add(membership)

        db.commit()

    def _to_pydantic(self, db: Session, db_group: DeviceGroupDB) -> DeviceGroup:
        """Convert SQLAlchemy model to Pydantic model"""
        # Get device IDs in this group
        device_ids = self.get_group_devices(db, db_group.id)

        return DeviceGroup(
            id=db_group.id,
            name=db_group.name,
            description=db_group.description,
            device_ids=device_ids,
            device_count=len(device_ids),
            created_at=db_group.created_at.isoformat() if db_group.created_at else None,
            updated_at=db_group.updated_at.isoformat() if db_group.updated_at else None
        )
