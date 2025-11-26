#!/usr/bin/env python3
"""
Add workflows module to existing database
Run this script to add the workflows module to your system modules
"""

from database import SessionLocal
from db_models import SystemModuleDB, UserGroupDB, GroupModuleAccessDB
from utils.logger import setup_logger

logger = setup_logger(__name__)


def add_workflows_module():
    """Add workflows module to system modules"""
    db = SessionLocal()
    try:
        # Check if workflows module already exists
        workflows_module = db.query(SystemModuleDB).filter(
            SystemModuleDB.module_name == 'workflows'
        ).first()

        if not workflows_module:
            # Add workflows module
            workflows_module = SystemModuleDB(
                module_name='workflows',
                display_name='Workflows',
                enabled=True
            )
            db.add(workflows_module)
            db.commit()
            db.refresh(workflows_module)
            logger.info(f"Added workflows module (ID: {workflows_module.id})")
        else:
            logger.info(f"Workflows module already exists (ID: {workflows_module.id})")

        # Grant access to all existing user groups (especially Administrators)
        user_groups = db.query(UserGroupDB).all()
        for group in user_groups:
            # Check if permission already exists
            existing_perm = db.query(GroupModuleAccessDB).filter(
                GroupModuleAccessDB.group_id == group.id,
                GroupModuleAccessDB.module_name == 'workflows'
            ).first()

            if not existing_perm:
                group_module = GroupModuleAccessDB(
                    group_id=group.id,
                    module_name='workflows',
                    can_access=True
                )
                db.add(group_module)
                logger.info(f"Granted workflows access to group: {group.name}")

        db.commit()
        logger.info("Successfully added workflows module and granted permissions")

    except Exception as e:
        logger.error(f"Failed to add workflows module: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Adding workflows module to database...")
    add_workflows_module()
    print("Done! Restart the application and refresh the frontend.")
