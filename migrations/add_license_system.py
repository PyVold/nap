"""
Database Migration: Add License System Tables

This migration adds the license management tables to support
tiered access control and feature gating.

Tables added:
- licenses: Customer license keys and quotas
- license_validation_logs: Audit trail for license checks

Run with:
    python migrations/add_license_system.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import engine, Base
from db_models import LicenseDB, LicenseValidationLogDB
from utils.logger import setup_logger

logger = setup_logger(__name__)


def run_migration():
    """Create license system tables"""
    try:
        logger.info("Starting license system migration...")
        
        # Create tables
        LicenseDB.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created 'licenses' table")
        
        LicenseValidationLogDB.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created 'license_validation_logs' table")
        
        logger.info("✅ License system migration completed successfully")
        
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Generate encryption keys:")
        print("   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        print("")
        print("2. Add to .env:")
        print("   LICENSE_ENCRYPTION_KEY=<your_key>")
        print("   LICENSE_SECRET_SALT=<your_salt>")
        print("")
        print("3. Generate a test license:")
        print("   python scripts/generate_license.py --customer \"Test\" --email \"test@test.com\" --tier professional --days 365")
        print("")
        print("4. Restart the application")
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
