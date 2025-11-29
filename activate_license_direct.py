#!/usr/bin/env python3
"""
Direct License Activation Script
Activates a license directly in the database without needing the API running
"""

import os
import sys
from datetime import datetime

# Override database URL to use SQLite for local activation
os.environ['DATABASE_URL'] = 'sqlite:///./network_audit.db'

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import db_models
from shared.license_manager import license_manager

# Create SQLite database
engine = create_engine('sqlite:///./network_audit.db', connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def activate_license(license_key: str):
    """Activate a license directly in the database"""
    db = SessionLocal()
    try:
        # Validate the license key
        print("Validating license key...")
        validation = license_manager.validate_license(license_key)
        
        if not validation["valid"]:
            print(f"❌ License validation failed: {validation['message']}")
            print(f"   Reason: {validation['reason']}")
            return False
        
        print("✓ License key is valid!")
        
        # Extract license data
        license_data = validation["data"]
        
        print(f"\nLicense Details:")
        print(f"  Customer: {license_data.get('customer_name')}")
        print(f"  Email: {license_data.get('customer_email')}")
        print(f"  Tier: {license_data.get('tier', 'unknown').upper()}")
        print(f"  Expires: {license_data.get('expires_at', 'N/A')[:10]}")
        print(f"  Max Devices: {license_data.get('max_devices')}")
        print(f"  Max Users: {license_data.get('max_users')}")
        
        # Check if license already exists
        existing_license = db.query(db_models.LicenseDB).filter(
            db_models.LicenseDB.license_key == license_key
        ).first()
        
        if existing_license:
            print("\n⚠ License already exists, reactivating...")
            existing_license.is_active = True
            existing_license.last_validated = datetime.utcnow()
            db.commit()
            print("✓ License reactivated successfully!")
        else:
            # Deactivate all other licenses
            db.query(db_models.LicenseDB).update({"is_active": False})
            
            # Create new license record
            print("\nActivating new license...")
            new_license = db_models.LicenseDB(
                customer_name=license_data.get("customer_name", "Unknown"),
                customer_email=license_data.get("customer_email", "unknown@example.com"),
                company_name=license_data.get("company_name"),
                license_key=license_key,
                license_tier=license_data.get("tier", "starter"),
                is_active=True,
                activated_at=datetime.utcnow(),
                issued_at=datetime.fromisoformat(license_data.get("issued_at")),
                expires_at=datetime.fromisoformat(license_data.get("expires_at")),
                max_devices=license_data.get("max_devices", 10),
                max_users=license_data.get("max_users", 2),
                max_storage_gb=license_data.get("max_storage_gb", 5),
                enabled_modules=license_data.get("modules", []),
                last_validated=datetime.utcnow()
            )
            
            db.add(new_license)
            db.commit()
            db.refresh(new_license)
            
            print("✓ License activated successfully!")
        
        # Show activation summary
        print("\n" + "="*80)
        print("LICENSE ACTIVATION COMPLETE")
        print("="*80)
        print(f"Status: ACTIVE")
        print(f"Tier: {license_data.get('tier', 'unknown').upper()}")
        print(f"Valid until: {license_data.get('expires_at', 'N/A')[:10]}")
        print(f"\nYour license is now active and ready to use!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error activating license: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 activate_license_direct.py <license_key>")
        print("\nOr read from file:")
        print("  python3 activate_license_direct.py license_output/license_*.txt")
        sys.exit(1)
    
    license_key_input = sys.argv[1]
    
    # Check if input is a file path
    if os.path.isfile(license_key_input):
        print(f"Reading license key from file: {license_key_input}")
        with open(license_key_input, 'r') as f:
            content = f.read()
            # Extract license key from file (find the long encrypted string)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'gAAAAA' in line:  # Fernet encrypted keys start with this
                    license_key = line.strip()
                    break
            else:
                print("❌ Could not find license key in file")
                sys.exit(1)
    else:
        license_key = license_key_input.strip()
    
    print("\n" + "="*80)
    print("DIRECT LICENSE ACTIVATION")
    print("="*80)
    
    success = activate_license(license_key)
    sys.exit(0 if success else 1)
