#!/usr/bin/env python3
# ============================================================================
# scripts/init_admin.py - Initialize admin user and system modules
# ============================================================================

import sys
import os

# Add parent directory to Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal, init_db
from db_models import UserDB, SystemModuleDB
from utils.auth import get_password_hash
from datetime import datetime

def init_admin_user():
    """Create default admin user if not exists"""
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(UserDB).filter(UserDB.username == "admin").first()
        if admin:
            print("Admin user already exists")
            return

        # Create admin user
        admin_user = UserDB(
            username="admin",
            email="admin@localhost",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin"),  # Change this password!
            role="admin",
            is_active=True,
            is_superuser=True
        )
        db.add(admin_user)
        db.commit()
        print("✓ Admin user created successfully!")
        print("  Username: admin")
        print("  Password: admin")
        print("  ⚠️  Please change the default password immediately!")

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def init_system_modules():
    """Initialize system modules"""
    db = SessionLocal()
    try:
        modules = [
            {
                "module_name": "devices",
                "display_name": "Device Management",
                "description": "Manage network devices and discovery",
                "enabled": True
            },
            {
                "module_name": "audit",
                "display_name": "Audit & Compliance",
                "description": "Run audits and check compliance",
                "enabled": True
            },
            {
                "module_name": "config_backups",
                "display_name": "Configuration Backups",
                "description": "Backup and version control for device configurations",
                "enabled": True
            },
            {
                "module_name": "drift_detection",
                "display_name": "Drift Detection",
                "description": "Detect configuration changes and drift from baseline",
                "enabled": True
            },
            {
                "module_name": "health_monitoring",
                "display_name": "Health Monitoring",
                "description": "Monitor device health and connectivity",
                "enabled": True
            },
            {
                "module_name": "notifications",
                "display_name": "Notifications & Webhooks",
                "description": "Send notifications via webhooks",
                "enabled": True
            },
            {
                "module_name": "rule_templates",
                "display_name": "Rule Templates",
                "description": "Pre-built compliance rule templates",
                "enabled": True
            },
            {
                "module_name": "integrations",
                "display_name": "External Integrations",
                "description": "Integrate with NetBox, Git, Ansible, etc.",
                "enabled": False
            },
            {
                "module_name": "topology",
                "display_name": "Network Topology",
                "description": "Discover and visualize network topology",
                "enabled": False
            },
            {
                "module_name": "licensing",
                "display_name": "License Management",
                "description": "Track software licenses and compliance",
                "enabled": False
            },
            {
                "module_name": "analytics",
                "display_name": "Analytics & Forecasting",
                "description": "Compliance trends and anomaly detection",
                "enabled": False
            }
        ]

        for module_data in modules:
            existing = db.query(SystemModuleDB).filter(
                SystemModuleDB.module_name == module_data["module_name"]
            ).first()

            if not existing:
                module = SystemModuleDB(**module_data)
                db.add(module)
                print(f"✓ Added module: {module_data['display_name']}")

        db.commit()
        print("✓ System modules initialized successfully!")

    except Exception as e:
        print(f"Error initializing modules: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("✓ Database initialized")

    print("\nCreating admin user...")
    init_admin_user()

    print("\nInitializing system modules...")
    init_system_modules()

    print("\n" + "="*60)
    print("Setup complete!")
    print("="*60)
    print("\nTo access the admin panel:")
    print("1. Start the application: python main.py")
    print("2. Login at: POST /admin/login")
    print("3. Use credentials:")
    print("   - Username: admin")
    print("   - Password: admin")
    print("\n⚠️  IMPORTANT: Change the default admin password!")
    print("="*60)
