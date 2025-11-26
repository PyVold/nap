#!/usr/bin/env python3
"""
Initialize default admin user on first startup
Run this inside the admin-service container or as a startup script
"""

import sys
import os

# Add parent directory to path to import shared modules
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from shared.database import SessionLocal, init_db
from passlib.context import CryptContext

# Import models
sys.path.insert(0, '/app')
import db_models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin_user():
    """Create default admin user if not exists"""

    # Initialize database
    init_db()

    db = SessionLocal()
    try:
        # Check if admin user already exists
        admin_user = db.query(db_models.UserDB).filter(
            db_models.UserDB.username == "admin"
        ).first()

        if admin_user:
            print("✅ Admin user already exists")
            return

        # Create admin user
        hashed_password = pwd_context.hash("admin")

        admin_user = db_models.UserDB(
            username="admin",
            email="admin@example.com",
            full_name="System Administrator",
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("=" * 60)
        print("✅ Admin user created successfully!")
        print("=" * 60)
        print("Username: admin")
        print("Password: admin")
        print("=" * 60)
        print("⚠️  IMPORTANT: Change the default password immediately!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
