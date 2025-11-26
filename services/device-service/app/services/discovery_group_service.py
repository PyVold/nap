# ============================================================================
# services/discovery_group_service.py
# ============================================================================

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.discovery_group import DiscoveryGroup, DiscoveryGroupCreate, DiscoveryGroupUpdate
from db_models import DiscoveryGroupDB
from utils.logger import setup_logger
from utils.crypto import encrypt_password, decrypt_password

logger = setup_logger(__name__)


class DiscoveryGroupService:
    """Service for discovery group management operations"""

    def get_all_groups(self, db: Session) -> List[DiscoveryGroup]:
        """Get all discovery groups"""
        db_groups = db.query(DiscoveryGroupDB).all()
        return [self._to_pydantic(g) for g in db_groups]

    def get_group_by_id(self, db: Session, group_id: int) -> Optional[DiscoveryGroup]:
        """Get discovery group by ID"""
        db_group = db.query(DiscoveryGroupDB).filter(DiscoveryGroupDB.id == group_id).first()
        return self._to_pydantic(db_group) if db_group else None

    def create_group(self, db: Session, group_create: DiscoveryGroupCreate) -> DiscoveryGroup:
        """Create a new discovery group"""
        # Encrypt password before storage
        encrypted_password = encrypt_password(group_create.password)

        db_group = DiscoveryGroupDB(
            name=group_create.name,
            description=group_create.description,
            subnet=group_create.subnet,
            excluded_ips=group_create.excluded_ips or [],
            username=group_create.username,
            password=encrypted_password,
            port=group_create.port,
            schedule_enabled=group_create.schedule_enabled,
            schedule_interval=group_create.schedule_interval,
            active=True
        )

        # Calculate next_run if schedule is enabled
        if group_create.schedule_enabled:
            db_group.next_run = datetime.utcnow() + timedelta(minutes=group_create.schedule_interval)

        db.add(db_group)
        db.commit()
        db.refresh(db_group)

        logger.info(f"Created discovery group: {db_group.name} (ID: {db_group.id})")
        return self._to_pydantic(db_group)

    def update_group(self, db: Session, group_id: int, group_update: DiscoveryGroupUpdate) -> DiscoveryGroup:
        """Update an existing discovery group"""
        db_group = db.query(DiscoveryGroupDB).filter(DiscoveryGroupDB.id == group_id).first()
        if not db_group:
            raise ValueError(f"Discovery group with ID {group_id} not found")

        update_data = group_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "password" and value:
                # Encrypt new password
                setattr(db_group, field, encrypt_password(value))
            else:
                setattr(db_group, field, value)

        # Update next_run if schedule settings changed
        if "schedule_enabled" in update_data or "schedule_interval" in update_data:
            if db_group.schedule_enabled:
                db_group.next_run = datetime.utcnow() + timedelta(minutes=db_group.schedule_interval)
            else:
                db_group.next_run = None

        db_group.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_group)

        logger.info(f"Updated discovery group: {db_group.name} (ID: {db_group.id})")
        return self._to_pydantic(db_group)

    def delete_group(self, db: Session, group_id: int) -> bool:
        """Delete a discovery group"""
        db_group = db.query(DiscoveryGroupDB).filter(DiscoveryGroupDB.id == group_id).first()
        if not db_group:
            raise ValueError(f"Discovery group with ID {group_id} not found")

        db.delete(db_group)
        db.commit()

        logger.info(f"Deleted discovery group ID: {group_id}")
        return True

    def get_scheduled_groups(self, db: Session) -> List[DiscoveryGroup]:
        """Get groups that are due for discovery"""
        now = datetime.utcnow()
        db_groups = db.query(DiscoveryGroupDB).filter(
            DiscoveryGroupDB.schedule_enabled == True,
            DiscoveryGroupDB.active == True,
            DiscoveryGroupDB.next_run <= now
        ).all()
        return [self._to_pydantic(g) for g in db_groups]

    def update_run_timestamps(self, db: Session, group_id: int):
        """Update last_run and next_run timestamps after discovery"""
        db_group = db.query(DiscoveryGroupDB).filter(DiscoveryGroupDB.id == group_id).first()
        if db_group:
            db_group.last_run = datetime.utcnow()
            if db_group.schedule_enabled:
                db_group.next_run = datetime.utcnow() + timedelta(minutes=db_group.schedule_interval)
            db.commit()

    def _to_pydantic(self, db_group: DiscoveryGroupDB) -> DiscoveryGroup:
        """Convert SQLAlchemy model to Pydantic model"""
        # Decrypt password for API response (in production, you might want to mask this)
        decrypted_password = decrypt_password(db_group.password)

        return DiscoveryGroup(
            id=db_group.id,
            name=db_group.name,
            description=db_group.description,
            subnet=db_group.subnet,
            excluded_ips=db_group.excluded_ips or [],
            username=db_group.username,
            password="****" if decrypted_password else "",  # Mask password in API responses
            port=db_group.port,
            schedule_enabled=db_group.schedule_enabled,
            schedule_interval=db_group.schedule_interval,
            last_run=db_group.last_run.isoformat() if db_group.last_run else None,
            next_run=db_group.next_run.isoformat() if db_group.next_run else None,
            active=db_group.active,
            created_at=db_group.created_at.isoformat() if db_group.created_at else None,
            updated_at=db_group.updated_at.isoformat() if db_group.updated_at else None
        )

    def get_decrypted_password(self, db: Session, group_id: int) -> str:
        """Get decrypted password for a group (internal use only)"""
        db_group = db.query(DiscoveryGroupDB).filter(DiscoveryGroupDB.id == group_id).first()
        if db_group:
            return decrypt_password(db_group.password)
        return ""
