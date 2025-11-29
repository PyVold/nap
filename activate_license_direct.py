#!/usr/bin/env python3
"""
Direct License Activation Script
Activates a license directly in the PostgreSQL database without needing the API running
"""

import os
import sys
from datetime import datetime

# Read database URL from environment or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://nap_user:nap_password@localhost:5432/nap_db')

try:
    from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("❌ Error: sqlalchemy not installed")
    print("Install it with: pip3 install sqlalchemy psycopg2-binary")
    sys.exit(1)

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("❌ Error: cryptography not installed")
    print("Install it with: pip3 install cryptography")
    sys.exit(1)

# Get license keys from environment
LICENSE_ENCRYPTION_KEY = os.getenv('LICENSE_ENCRYPTION_KEY')
LICENSE_SECRET_SALT = os.getenv('LICENSE_SECRET_SALT')

if not LICENSE_ENCRYPTION_KEY or not LICENSE_SECRET_SALT:
    print("❌ Error: LICENSE_ENCRYPTION_KEY and LICENSE_SECRET_SALT must be set in environment")
    print("\nMake sure you have these in your .env file:")
    print("  LICENSE_ENCRYPTION_KEY=...")
    print("  LICENSE_SECRET_SALT=...")
    print("\nOr export them:")
    print("  export LICENSE_ENCRYPTION_KEY='...'")
    print("  export LICENSE_SECRET_SALT='...'")
    sys.exit(1)

# Database models
Base = declarative_base()

class LicenseDB(Base):
    """Customer licenses for tiered access control"""
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=True)
    license_key = Column(Text, unique=True, nullable=False, index=True)
    license_tier = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    activated_at = Column(DateTime, nullable=True)
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    max_devices = Column(Integer, nullable=False)
    max_users = Column(Integer, nullable=False)
    max_storage_gb = Column(Integer, default=10)
    enabled_modules = Column(JSON, default=list)
    current_devices = Column(Integer, default=0)
    current_users = Column(Integer, default=0)
    current_storage_gb = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    order_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_validated = Column(DateTime, nullable=True)


def validate_license(license_key: str):
    """Validate and decode a license key"""
    import json
    import hashlib
    
    try:
        # Decrypt the license key
        cipher = Fernet(LICENSE_ENCRYPTION_KEY.encode() if isinstance(LICENSE_ENCRYPTION_KEY, str) else LICENSE_ENCRYPTION_KEY)
        decrypted = cipher.decrypt(license_key.encode())
        data = json.loads(decrypted.decode())
        
        # Verify signature
        signature = data.pop("signature", None)
        if not signature:
            return {"valid": False, "reason": "invalid", "message": "License signature missing", "data": None}
        
        data_str = json.dumps(data, sort_keys=True)
        expected_sig = hashlib.sha256(f"{data_str}{LICENSE_SECRET_SALT}".encode()).hexdigest()
        
        if signature != expected_sig:
            return {"valid": False, "reason": "tampered", "message": "License signature invalid", "data": None}
        
        # Check expiration
        expires_at_str = data.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.utcnow() > expires_at:
                return {"valid": False, "reason": "expired", "message": f"License expired on {expires_at.date()}", "data": data}
        
        return {"valid": True, "reason": "valid", "message": "License is valid and active", "data": data}
        
    except Exception as e:
        return {"valid": False, "reason": "invalid", "message": f"Invalid license format: {str(e)}", "data": None}


def activate_license(license_key: str, db_url: str):
    """Activate a license directly in the database"""
    
    # Create database connection
    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print(f"\nDatabase URL: {db_url}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials are correct")
        print("  3. Database exists")
        return False
    
    db = SessionLocal()
    try:
        # Validate the license key
        print("Validating license key...")
        validation = validate_license(license_key)
        
        if not validation["valid"]:
            print(f"❌ License validation failed: {validation['message']}")
            print(f"   Reason: {validation['reason']}")
            return False
        
        print("✓ License key is valid!")
        
        # Extract license data
        license_data = validation["data"]
        
        print(f"\n{'='*80}")
        print("LICENSE DETAILS")
        print('='*80)
        print(f"  Customer: {license_data.get('customer_name')}")
        print(f"  Email: {license_data.get('customer_email')}")
        if license_data.get('company_name'):
            print(f"  Company: {license_data.get('company_name')}")
        print(f"  Tier: {license_data.get('tier', 'unknown').upper()}")
        print(f"  Issued: {license_data.get('issued_at', 'N/A')[:10]}")
        print(f"  Expires: {license_data.get('expires_at', 'N/A')[:10]}")
        print(f"  Max Devices: {license_data.get('max_devices')}")
        print(f"  Max Users: {license_data.get('max_users')}")
        print(f"  Storage: {license_data.get('max_storage_gb')} GB")
        print('='*80)
        
        # Check if license already exists
        existing_license = db.query(LicenseDB).filter(
            LicenseDB.license_key == license_key
        ).first()
        
        if existing_license:
            print("\n⚠ License already exists in database, reactivating...")
            existing_license.is_active = True
            existing_license.last_validated = datetime.utcnow()
            db.commit()
            print("✓ License reactivated successfully!")
        else:
            # Deactivate all other licenses (single license mode)
            print("\nDeactivating any existing licenses...")
            db.query(LicenseDB).update({"is_active": False})
            
            # Create new license record
            print("Activating new license...")
            new_license = LicenseDB(
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
        print(f"\n{'='*80}")
        print("✅ LICENSE ACTIVATION COMPLETE")
        print('='*80)
        print(f"Status: ACTIVE")
        print(f"Tier: {license_data.get('tier', 'unknown').upper()}")
        print(f"Valid until: {license_data.get('expires_at', 'N/A')[:10]}")
        print(f"\nYour platform is now fully licensed and ready to use!")
        print('='*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error activating license: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("="*80)
        print("DIRECT LICENSE ACTIVATION")
        print("="*80)
        print("\nUsage:")
        print("  python3 activate_license_direct.py <license_key>")
        print("\nOr read from file:")
        print("  python3 activate_license_direct.py license_output/license_*.txt")
        print("\nExamples:")
        print("  python3 activate_license_direct.py gAAAAAB...")
        print("  python3 activate_license_direct.py license_output/license_osama_20251129.txt")
        print("\nNote: Make sure LICENSE_ENCRYPTION_KEY and LICENSE_SECRET_SALT")
        print("      are set in your environment or .env file")
        print("="*80)
        sys.exit(1)
    
    license_key_input = sys.argv[1]
    
    # Check if input is a file path
    if os.path.isfile(license_key_input):
        print(f"Reading license key from file: {license_key_input}\n")
        with open(license_key_input, 'r') as f:
            content = f.read()
            # Extract license key from file (find the long encrypted string)
            lines = content.split('\n')
            license_key = None
            for i, line in enumerate(lines):
                if 'gAAAAA' in line:  # Fernet encrypted keys start with this
                    license_key = line.strip()
                    break
            
            if not license_key:
                print("❌ Could not find license key in file")
                print("   Make sure the file contains a valid Fernet-encrypted license key")
                sys.exit(1)
    else:
        license_key = license_key_input.strip()
    
    print("="*80)
    print("DIRECT LICENSE ACTIVATION")
    print("="*80)
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    print("="*80 + "\n")
    
    success = activate_license(license_key, DATABASE_URL)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
