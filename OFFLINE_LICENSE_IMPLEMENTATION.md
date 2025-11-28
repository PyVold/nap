# Offline License System - Implementation Guide

**Approach**: Separate license generation script + in-app validation
**Timeline**: 1-2 days
**Complexity**: Simple, no billing integration needed

---

## Overview

### Architecture

```
┌─────────────────────────────────────────────────┐
│  OFFLINE (Your Machine)                         │
│  ┌──────────────────────────────────────────┐  │
│  │  generate_license.py (Standalone Script) │  │
│  │  - Run manually when customer purchases  │  │
│  │  - Generates encrypted license key       │  │
│  │  - Outputs: license key + JSON file      │  │
│  └──────────────────────────────────────────┘  │
│                      │                           │
│                      ▼                           │
│             license_key.txt                      │
│         (Send to customer via email)             │
└─────────────────────────────────────────────────┘
                       │
                       │ Customer enters key
                       ▼
┌─────────────────────────────────────────────────┐
│  CUSTOMER'S DEPLOYMENT (Their Server)           │
│  ┌──────────────────────────────────────────┐  │
│  │  Network Audit Platform                   │  │
│  │  - License activation API                 │  │
│  │  - License validation on startup          │  │
│  │  - Feature gating based on license        │  │
│  │  - Quota enforcement                      │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Benefits of This Approach
- ✅ Simple: No payment gateway, no billing system
- ✅ Secure: License generation offline, not exposed to internet
- ✅ Flexible: Generate licenses on-demand for customers
- ✅ Manual Control: You decide when to issue/renew licenses
- ✅ Works for: On-premise deployments, enterprise sales, manual sales process

---

## Step 1: Database Schema (Day 1, 1 hour)

### Minimal License Table

```python
# Add to shared/db_models.py or db_models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class LicenseDB(Base):
    """Customer licenses"""
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Customer info (for your records)
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=True)
    
    # License details
    license_key = Column(Text, unique=True, nullable=False, index=True)
    license_tier = Column(String(50), nullable=False, index=True)  # starter, professional, enterprise
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    activated_at = Column(DateTime, nullable=True)  # When customer first activated
    
    # Validity
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Quotas
    max_devices = Column(Integer, nullable=False)
    max_users = Column(Integer, nullable=False)
    max_storage_gb = Column(Integer, default=10)
    
    # Features (JSON array)
    enabled_modules = Column(JSON, default=list)  # ["devices", "audits", "scheduled_audits", ...]
    
    # Current usage (updated by app)
    current_devices = Column(Integer, default=0)
    current_users = Column(Integer, default=0)
    current_storage_gb = Column(Integer, default=0)
    
    # Metadata
    notes = Column(Text, nullable=True)  # Internal notes
    order_id = Column(String(100), nullable=True)  # Your internal order/invoice ID
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_validated = Column(DateTime, nullable=True)


class LicenseValidationLog(Base):
    """Track license validation attempts"""
    __tablename__ = "license_validation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, index=True, nullable=True)
    license_key_attempted = Column(String(500))
    validation_result = Column(String(50))  # valid, expired, invalid, tampered
    validation_message = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(String(500), nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
```

### Apply Migration

```bash
cd /workspace

# Create migration
alembic revision --autogenerate -m "Add offline license system"

# Review the migration file
# migrations/versions/xxxx_add_offline_license_system.py

# Apply migration
alembic upgrade head
```

---

## Step 2: License Generation Script (Day 1, 2 hours)

### Create Standalone Script

```python
# scripts/generate_license.py

"""
Offline License Generation Script
Run this on YOUR machine to generate licenses for customers

Usage:
    python scripts/generate_license.py --customer "Acme Corp" --email "admin@acme.com" --tier professional --days 365

Output:
    - license_key.txt (send to customer)
    - license_record.json (import to your database)
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import argparse

# ============================================================================
# CONFIGURATION
# ============================================================================

# IMPORTANT: Generate this key ONCE and save it securely
# Run: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Then set as environment variable or hardcode here (for offline generation)

LICENSE_ENCRYPTION_KEY = os.getenv(
    "LICENSE_ENCRYPTION_KEY",
    "REPLACE_WITH_YOUR_KEY"  # Replace with actual key for offline use
)

LICENSE_SECRET_SALT = os.getenv(
    "LICENSE_SECRET_SALT",
    "REPLACE_WITH_SECRET_SALT"  # Replace with actual salt
)

# License tier definitions
LICENSE_TIERS = {
    "starter": {
        "max_devices": 10,
        "max_users": 2,
        "max_storage_gb": 5,
        "modules": ["devices", "manual_audits", "basic_rules", "health_checks"]
    },
    "professional": {
        "max_devices": 100,
        "max_users": 10,
        "max_storage_gb": 50,
        "modules": [
            "devices", "manual_audits", "scheduled_audits", "basic_rules",
            "rule_templates", "api_access", "config_backups", "drift_detection",
            "webhooks", "health_checks", "device_groups", "discovery"
        ]
    },
    "enterprise": {
        "max_devices": 999999,  # Unlimited
        "max_users": 999999,
        "max_storage_gb": 999999,
        "modules": ["all"]  # All modules enabled
    }
}


class LicenseGenerator:
    """Generate offline licenses"""
    
    def __init__(self):
        if LICENSE_ENCRYPTION_KEY == "REPLACE_WITH_YOUR_KEY":
            print("ERROR: LICENSE_ENCRYPTION_KEY not set!")
            print("Run this command to generate a key:")
            print("  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
            exit(1)
        
        self.cipher = Fernet(LICENSE_ENCRYPTION_KEY.encode())
    
    def generate_license(
        self,
        customer_name: str,
        customer_email: str,
        tier: str,
        duration_days: int = 365,
        company_name: str = None,
        order_id: str = None,
        notes: str = None,
        custom_quotas: dict = None
    ) -> tuple:
        """
        Generate a license key and metadata
        
        Returns: (license_key, license_data_dict)
        """
        
        if tier not in LICENSE_TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(LICENSE_TIERS.keys())}")
        
        # Get tier defaults
        tier_config = LICENSE_TIERS[tier]
        
        # Allow custom quotas to override defaults
        if custom_quotas:
            max_devices = custom_quotas.get("max_devices", tier_config["max_devices"])
            max_users = custom_quotas.get("max_users", tier_config["max_users"])
            max_storage_gb = custom_quotas.get("max_storage_gb", tier_config["max_storage_gb"])
            modules = custom_quotas.get("modules", tier_config["modules"])
        else:
            max_devices = tier_config["max_devices"]
            max_users = tier_config["max_users"]
            max_storage_gb = tier_config["max_storage_gb"]
            modules = tier_config["modules"]
        
        # Generate unique license ID
        license_id = secrets.token_hex(8)
        
        # Build license payload
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(days=duration_days)
        
        license_data = {
            "license_id": license_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "company_name": company_name,
            "tier": tier,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "max_devices": max_devices,
            "max_users": max_users,
            "max_storage_gb": max_storage_gb,
            "modules": modules,
            "order_id": order_id,
            "notes": notes,
        }
        
        # Create signature (prevents tampering)
        data_str = json.dumps(license_data, sort_keys=True)
        signature = hashlib.sha256(f"{data_str}{LICENSE_SECRET_SALT}".encode()).hexdigest()
        license_data["signature"] = signature
        
        # Encrypt the license
        encrypted = self.cipher.encrypt(json.dumps(license_data).encode())
        license_key = encrypted.decode()
        
        return license_key, license_data
    
    def validate_license(self, license_key: str) -> dict:
        """Validate a license key (for testing)"""
        try:
            # Decrypt
            decrypted = self.cipher.decrypt(license_key.encode())
            data = json.loads(decrypted.decode())
            
            # Verify signature
            signature = data.pop("signature")
            data_str = json.dumps(data, sort_keys=True)
            expected_sig = hashlib.sha256(f"{data_str}{LICENSE_SECRET_SALT}".encode()).hexdigest()
            
            if signature != expected_sig:
                return {"valid": False, "reason": "tampered"}
            
            # Check expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                return {"valid": False, "reason": "expired", "expires_at": expires_at}
            
            return {"valid": True, "reason": "valid", "data": data}
        
        except Exception as e:
            return {"valid": False, "reason": "invalid", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Generate offline license keys")
    
    # Required arguments
    parser.add_argument("--customer", required=True, help="Customer name")
    parser.add_argument("--email", required=True, help="Customer email")
    parser.add_argument("--tier", required=True, choices=["starter", "professional", "enterprise"],
                        help="License tier")
    
    # Optional arguments
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--days", type=int, default=365, help="License duration in days (default: 365)")
    parser.add_argument("--order", help="Internal order/invoice ID")
    parser.add_argument("--notes", help="Internal notes")
    parser.add_argument("--devices", type=int, help="Custom max devices (overrides tier default)")
    parser.add_argument("--users", type=int, help="Custom max users (overrides tier default)")
    parser.add_argument("--storage", type=int, help="Custom max storage GB (overrides tier default)")
    parser.add_argument("--output", default="./license_output", help="Output directory (default: ./license_output)")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Custom quotas if specified
    custom_quotas = {}
    if args.devices:
        custom_quotas["max_devices"] = args.devices
    if args.users:
        custom_quotas["max_users"] = args.users
    if args.storage:
        custom_quotas["max_storage_gb"] = args.storage
    
    # Generate license
    generator = LicenseGenerator()
    
    print("\n" + "="*60)
    print("GENERATING LICENSE")
    print("="*60)
    
    license_key, license_data = generator.generate_license(
        customer_name=args.customer,
        customer_email=args.email,
        tier=args.tier,
        duration_days=args.days,
        company_name=args.company,
        order_id=args.order,
        notes=args.notes,
        custom_quotas=custom_quotas if custom_quotas else None
    )
    
    # Validate (sanity check)
    validation = generator.validate_license(license_key)
    
    if not validation["valid"]:
        print(f"\n❌ ERROR: Generated license failed validation: {validation['reason']}")
        exit(1)
    
    # Output files
    license_key_file = os.path.join(args.output, f"license_{license_data['license_id']}.txt")
    license_json_file = os.path.join(args.output, f"license_{license_data['license_id']}.json")
    
    # Save license key (send to customer)
    with open(license_key_file, "w") as f:
        f.write(license_key)
    
    # Save license metadata (for your records)
    # Remove signature before saving (not needed in DB)
    license_record = {
        "customer_name": license_data["customer_name"],
        "customer_email": license_data["customer_email"],
        "company_name": license_data["company_name"],
        "license_key": license_key,
        "license_tier": license_data["tier"],
        "issued_at": license_data["issued_at"],
        "expires_at": license_data["expires_at"],
        "max_devices": license_data["max_devices"],
        "max_users": license_data["max_users"],
        "max_storage_gb": license_data["max_storage_gb"],
        "enabled_modules": license_data["modules"],
        "order_id": license_data["order_id"],
        "notes": license_data["notes"],
        "is_active": True
    }
    
    with open(license_json_file, "w") as f:
        json.dump(license_record, f, indent=2)
    
    # Display summary
    print("\n✅ LICENSE GENERATED SUCCESSFULLY\n")
    print(f"Customer:     {args.customer}")
    print(f"Email:        {args.email}")
    print(f"Company:      {args.company or 'N/A'}")
    print(f"Tier:         {args.tier.upper()}")
    print(f"Duration:     {args.days} days")
    print(f"Expires:      {license_data['expires_at'][:10]}")
    print(f"Max Devices:  {license_data['max_devices']}")
    print(f"Max Users:    {license_data['max_users']}")
    print(f"Max Storage:  {license_data['max_storage_gb']} GB")
    print(f"Modules:      {len(license_data['modules'])} modules")
    print(f"License ID:   {license_data['license_id']}")
    
    print("\n" + "="*60)
    print("OUTPUT FILES")
    print("="*60)
    print(f"\n📄 License Key (send to customer):")
    print(f"   {license_key_file}")
    print(f"\n📄 License Record (import to database):")
    print(f"   {license_json_file}")
    
    print("\n" + "="*60)
    print("LICENSE KEY (copy this)")
    print("="*60)
    print(f"\n{license_key}\n")
    
    print("="*60)
    print("NEXT STEPS")
    print("="*60)
    print("\n1. Send license key to customer via email")
    print("2. Import license record to database using import_license.py")
    print("3. Customer activates license in their deployment")
    print("")


if __name__ == "__main__":
    main()
```

### Install Dependencies

```bash
pip install cryptography
```

### Generate Encryption Keys (ONE TIME)

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print('LICENSE_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Generate secret salt
python -c "import secrets; print('LICENSE_SECRET_SALT=' + secrets.token_hex(32))"
```

**Save these keys securely!** Add them to your `.env` file or hardcode them in the script.

### Test License Generation

```bash
# Generate a test license
python scripts/generate_license.py \
  --customer "Acme Corporation" \
  --email "admin@acme.com" \
  --company "Acme Corp" \
  --tier professional \
  --days 365 \
  --order "ORD-2025-001" \
  --notes "First customer - 20% discount applied"

# Output will be in ./license_output/
```

---

## Step 3: License Import Script (Day 1, 30 minutes)

When you generate a license, you need to import it to your database.

```python
# scripts/import_license.py

"""
Import a generated license to the database

Usage:
    python scripts/import_license.py license_output/license_abc123.json
"""

import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import your DB models
sys.path.append("/workspace")
from db_models import LicenseDB
from database import DATABASE_URL

def import_license(json_file: str):
    """Import license from JSON file to database"""
    
    # Load license data
    with open(json_file, "r") as f:
        license_data = json.load(f)
    
    # Connect to database
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if license already exists
        existing = session.query(LicenseDB).filter(
            LicenseDB.license_key == license_data["license_key"]
        ).first()
        
        if existing:
            print(f"❌ License already exists in database (ID: {existing.id})")
            return
        
        # Create license record
        license = LicenseDB(
            customer_name=license_data["customer_name"],
            customer_email=license_data["customer_email"],
            company_name=license_data.get("company_name"),
            license_key=license_data["license_key"],
            license_tier=license_data["license_tier"],
            issued_at=datetime.fromisoformat(license_data["issued_at"]),
            expires_at=datetime.fromisoformat(license_data["expires_at"]),
            max_devices=license_data["max_devices"],
            max_users=license_data["max_users"],
            max_storage_gb=license_data["max_storage_gb"],
            enabled_modules=license_data["enabled_modules"],
            order_id=license_data.get("order_id"),
            notes=license_data.get("notes"),
            is_active=license_data.get("is_active", True)
        )
        
        session.add(license)
        session.commit()
        session.refresh(license)
        
        print("\n✅ LICENSE IMPORTED SUCCESSFULLY\n")
        print(f"Database ID:  {license.id}")
        print(f"Customer:     {license.customer_name}")
        print(f"Email:        {license.customer_email}")
        print(f"Tier:         {license.license_tier}")
        print(f"Expires:      {license.expires_at.date()}")
        print(f"Max Devices:  {license.max_devices}")
        print(f"Max Users:    {license.max_users}")
        print("")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR importing license: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_license.py <license_json_file>")
        print("Example: python scripts/import_license.py license_output/license_abc123.json")
        exit(1)
    
    json_file = sys.argv[1]
    import_license(json_file)
```

---

## Step 4: License Validation in App (Day 1-2, 3 hours)

### License Manager Service

```python
# shared/license_validator.py

"""
License validation service (runs in customer's deployment)
"""

import os
import json
import hashlib
from datetime import datetime
from cryptography.fernet import Fernet
from typing import Dict, Optional

# Same keys used for generation
LICENSE_ENCRYPTION_KEY = os.getenv("LICENSE_ENCRYPTION_KEY")
LICENSE_SECRET_SALT = os.getenv("LICENSE_SECRET_SALT")


class LicenseValidator:
    """Validate licenses in customer deployment"""
    
    def __init__(self):
        if not LICENSE_ENCRYPTION_KEY:
            raise ValueError("LICENSE_ENCRYPTION_KEY environment variable not set")
        if not LICENSE_SECRET_SALT:
            raise ValueError("LICENSE_SECRET_SALT environment variable not set")
        
        self.cipher = Fernet(LICENSE_ENCRYPTION_KEY.encode())
    
    def validate_license(self, license_key: str) -> Dict:
        """
        Validate a license key
        
        Returns: {
            "valid": bool,
            "reason": str,
            "message": str,
            "data": dict (if valid)
        }
        """
        try:
            # Decrypt
            decrypted = self.cipher.decrypt(license_key.encode())
            data = json.loads(decrypted.decode())
            
            # Verify signature (tamper detection)
            signature = data.pop("signature")
            data_str = json.dumps(data, sort_keys=True)
            expected_sig = hashlib.sha256(f"{data_str}{LICENSE_SECRET_SALT}".encode()).hexdigest()
            
            if signature != expected_sig:
                return {
                    "valid": False,
                    "reason": "tampered",
                    "message": "License has been tampered with or is invalid"
                }
            
            # Check expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            now = datetime.utcnow()
            
            if now > expires_at:
                days_expired = (now - expires_at).days
                return {
                    "valid": False,
                    "reason": "expired",
                    "message": f"License expired {days_expired} days ago on {expires_at.date()}",
                    "data": data
                }
            
            # Check if expiring soon (within 30 days)
            days_until_expiry = (expires_at - now).days
            expiring_soon = days_until_expiry <= 30
            
            return {
                "valid": True,
                "reason": "valid",
                "message": f"License is valid. Expires in {days_until_expiry} days.",
                "data": data,
                "expiring_soon": expiring_soon,
                "days_until_expiry": days_until_expiry
            }
        
        except Exception as e:
            return {
                "valid": False,
                "reason": "invalid",
                "message": f"Invalid license key: {str(e)}"
            }
    
    def check_quota(self, license_data: Dict, quota_type: str, current_value: int) -> bool:
        """Check if within quota limits"""
        quota_key = f"max_{quota_type}"
        max_allowed = license_data.get(quota_key, 0)
        
        # Unlimited check
        if max_allowed >= 999999:
            return True
        
        return current_value < max_allowed
    
    def has_module(self, license_data: Dict, module: str) -> bool:
        """Check if module is enabled"""
        modules = license_data.get("modules", [])
        
        # Enterprise has all modules
        if "all" in modules:
            return True
        
        return module in modules
    
    def get_tier_info(self, tier: str) -> Dict:
        """Get tier information"""
        tier_info = {
            "starter": {
                "name": "Starter",
                "display_name": "Starter Plan",
                "color": "blue",
                "description": "Perfect for small teams"
            },
            "professional": {
                "name": "Professional",
                "display_name": "Professional Plan",
                "color": "green",
                "description": "For growing organizations"
            },
            "enterprise": {
                "name": "Enterprise",
                "display_name": "Enterprise Plan",
                "color": "purple",
                "description": "Unlimited power for large deployments"
            }
        }
        
        return tier_info.get(tier, {"name": tier, "display_name": tier})


# Singleton instance
license_validator = LicenseValidator()
```

---

### License Activation API

```python
# api/routes/license.py

"""
License activation and validation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from database import get_db
import db_models
from shared.license_validator import license_validator

router = APIRouter(prefix="/license", tags=["License"])


class LicenseActivateRequest(BaseModel):
    license_key: str


class LicenseStatusResponse(BaseModel):
    is_active: bool
    is_valid: bool
    tier: str
    customer_name: str
    expires_at: str
    days_until_expiry: int
    expiring_soon: bool
    quotas: dict
    current_usage: dict
    features: dict


@router.post("/activate")
async def activate_license(
    request: LicenseActivateRequest,
    db: Session = Depends(get_db)
):
    """
    Activate a license key
    Customer enters license key in UI, this endpoint validates and activates it
    """
    
    # Validate license key
    validation = license_validator.validate_license(request.license_key)
    
    if not validation["valid"]:
        # Log failed attempt
        log = db_models.LicenseValidationLog(
            license_key_attempted=request.license_key[:50],  # Truncate for security
            validation_result=validation["reason"],
            validation_message=validation["message"]
        )
        db.add(log)
        db.commit()
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "License activation failed",
                "reason": validation["reason"],
                "message": validation["message"]
            }
        )
    
    # Check if license already activated
    existing = db.query(db_models.LicenseDB).filter(
        db_models.LicenseDB.license_key == request.license_key
    ).first()
    
    if existing:
        if not existing.is_active:
            # Reactivate
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            db.commit()
            
            return {
                "message": "License reactivated successfully",
                "license_id": existing.id,
                "already_activated": True
            }
        else:
            return {
                "message": "License already active",
                "license_id": existing.id,
                "already_activated": True
            }
    
    # Create new license record
    license_data = validation["data"]
    
    new_license = db_models.LicenseDB(
        customer_name=license_data["customer_name"],
        customer_email=license_data["customer_email"],
        company_name=license_data.get("company_name"),
        license_key=request.license_key,
        license_tier=license_data["tier"],
        issued_at=datetime.fromisoformat(license_data["issued_at"]),
        expires_at=datetime.fromisoformat(license_data["expires_at"]),
        activated_at=datetime.utcnow(),
        max_devices=license_data["max_devices"],
        max_users=license_data["max_users"],
        max_storage_gb=license_data["max_storage_gb"],
        enabled_modules=license_data["modules"],
        order_id=license_data.get("order_id"),
        notes=license_data.get("notes"),
        is_active=True
    )
    
    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    
    # Log successful activation
    log = db_models.LicenseValidationLog(
        license_id=new_license.id,
        validation_result="activated",
        validation_message="License activated successfully"
    )
    db.add(log)
    db.commit()
    
    return {
        "message": "License activated successfully",
        "license_id": new_license.id,
        "tier": license_data["tier"],
        "expires_at": license_data["expires_at"],
        "max_devices": license_data["max_devices"],
        "max_users": license_data["max_users"]
    }


@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(db: Session = Depends(get_db)):
    """
    Get current license status
    Shows license info, quotas, and current usage
    """
    
    # Get active license
    license = db.query(db_models.LicenseDB).filter(
        db_models.LicenseDB.is_active == True
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=404,
            detail="No active license found. Please activate a license."
        )
    
    # Validate license
    validation = license_validator.validate_license(license.license_key)
    
    # Update last validated timestamp
    license.last_validated = datetime.utcnow()
    db.commit()
    
    # Get current usage
    device_count = db.query(db_models.DeviceDB).count()
    user_count = db.query(db_models.UserDB).count()
    
    # Calculate storage (sum of config backup sizes)
    total_storage_bytes = db.query(
        db.func.sum(db_models.ConfigBackupDB.backup_size_bytes)
    ).scalar() or 0
    storage_gb = total_storage_bytes / (1024 ** 3)
    
    # Update current usage in database
    license.current_devices = device_count
    license.current_users = user_count
    license.current_storage_gb = int(storage_gb)
    db.commit()
    
    return {
        "is_active": license.is_active,
        "is_valid": validation["valid"],
        "tier": license.license_tier,
        "customer_name": license.customer_name,
        "expires_at": license.expires_at.isoformat(),
        "days_until_expiry": validation.get("days_until_expiry", 0),
        "expiring_soon": validation.get("expiring_soon", False),
        "quotas": {
            "max_devices": license.max_devices,
            "max_users": license.max_users,
            "max_storage_gb": license.max_storage_gb
        },
        "current_usage": {
            "devices": device_count,
            "users": user_count,
            "storage_gb": storage_gb
        },
        "features": {
            "modules": license.enabled_modules,
            "unlimited": license.max_devices >= 999999
        }
    }


@router.post("/deactivate")
async def deactivate_license(db: Session = Depends(get_db)):
    """
    Deactivate current license
    (For when customer wants to switch to a different license)
    """
    
    license = db.query(db_models.LicenseDB).filter(
        db_models.LicenseDB.is_active == True
    ).first()
    
    if not license:
        raise HTTPException(status_code=404, detail="No active license found")
    
    license.is_active = False
    license.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "License deactivated successfully"}
```

### Include Router in Main App

```python
# main.py or services/api-gateway/app/main.py

from api.routes import license

app.include_router(license.router)
```

---

## Step 5: Quota Enforcement (Day 2, 2 hours)

### Enforce Device Quota

```python
# api/routes/devices.py

from shared.license_validator import license_validator

@router.post("/", response_model=Device)
async def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db)
):
    """Create new device (checks license quota)"""
    
    # Get active license
    license = db.query(db_models.LicenseDB).filter(
        db_models.LicenseDB.is_active == True
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=402,
            detail="No active license. Please activate a license to add devices."
        )
    
    # Validate license
    validation = license_validator.validate_license(license.license_key)
    if not validation["valid"]:
        raise HTTPException(
            status_code=402,
            detail=f"License is {validation['reason']}: {validation['message']}"
        )
    
    # Check device quota
    current_device_count = db.query(db_models.DeviceDB).count()
    
    if not license_validator.check_quota(validation["data"], "devices", current_device_count):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Device quota exceeded",
                "current": current_device_count,
                "max": validation["data"]["max_devices"],
                "message": f"You have reached the maximum of {validation['data']['max_devices']} devices for your {license.license_tier} plan. Please upgrade your license or remove unused devices."
            }
        )
    
    # Proceed with device creation
    new_device = device_service.create_device(db, device)
    return new_device
```

### Similar for Users, Storage, etc.

---

## Step 6: Feature Gating (Day 2, 1 hour)

### Check Module Access

```python
# api/routes/audit_schedules.py

from shared.license_validator import license_validator

@router.post("/", response_model=AuditSchedule)
async def create_audit_schedule(
    schedule: AuditScheduleCreate,
    db: Session = Depends(get_db)
):
    """Create audit schedule (requires professional tier or higher)"""
    
    # Get active license
    license = db.query(db_models.LicenseDB).filter(
        db_models.LicenseDB.is_active == True
    ).first()
    
    if not license:
        raise HTTPException(status_code=402, detail="No active license")
    
    # Validate license
    validation = license_validator.validate_license(license.license_key)
    if not validation["valid"]:
        raise HTTPException(status_code=402, detail=validation["message"])
    
    # Check if module is enabled
    if not license_validator.has_module(validation["data"], "scheduled_audits"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Feature not available",
                "feature": "Scheduled Audits",
                "current_tier": license.license_tier,
                "required_tier": "professional",
                "message": "Scheduled audits are not available in your current plan. Please upgrade to Professional or Enterprise."
            }
        )
    
    # Proceed with schedule creation
    new_schedule = audit_schedule_service.create_schedule(db, schedule)
    return new_schedule
```

---

## Step 7: Frontend License Activation UI (Day 2, 2 hours)

### License Activation Page

```jsx
// frontend/src/components/LicenseActivation.jsx

import React, { useState } from 'react';
import {
  Box, Card, CardContent, TextField, Button, Typography,
  Alert, CircularProgress
} from '@mui/material';
import api from '../api/api';

export default function LicenseActivation() {
  const [licenseKey, setLicenseKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleActivate = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/license/activate', {
        license_key: licenseKey
      });

      setSuccess(true);
      setTimeout(() => {
        window.location.reload(); // Reload to apply license
      }, 2000);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        setError(detail.message || 'License activation failed');
      } else {
        setError(detail || 'License activation failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={3} display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
      <Card sx={{ maxWidth: 600, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom align="center">
            Activate License
          </Typography>
          
          <Typography variant="body1" color="text.secondary" paragraph align="center">
            Enter your license key to activate the platform.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 3 }}>
              License activated successfully! Reloading...
            </Alert>
          )}

          <TextField
            fullWidth
            label="License Key"
            multiline
            rows={4}
            value={licenseKey}
            onChange={(e) => setLicenseKey(e.target.value)}
            placeholder="Paste your license key here..."
            disabled={loading || success}
            sx={{ mb: 3 }}
          />

          <Button
            fullWidth
            variant="contained"
            size="large"
            onClick={handleActivate}
            disabled={!licenseKey || loading || success}
          >
            {loading ? <CircularProgress size={24} /> : 'Activate License'}
          </Button>

          <Box mt={3} p={2} bgcolor="grey.100" borderRadius={1}>
            <Typography variant="caption" color="text.secondary">
              <strong>Note:</strong> Your license key is provided by your sales representative.
              Contact support@yourcompany.com if you need assistance.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
```

### License Status Dashboard

```jsx
// frontend/src/components/LicenseStatus.jsx

import React, { useState, useEffect } from 'react';
import {
  Box, Card, CardContent, Typography, LinearProgress,
  Grid, Chip, Alert, Button
} from '@mui/material';
import api from '../api/api';

export default function LicenseStatus() {
  const [license, setLicense] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLicenseStatus();
  }, []);

  const fetchLicenseStatus = async () => {
    try {
      const response = await api.get('/license/status');
      setLicense(response.data);
    } catch (error) {
      console.error('Failed to fetch license status:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!license) return <div>No license activated</div>;

  const deviceUsage = (license.current_usage.devices / license.quotas.max_devices) * 100;
  const userUsage = (license.current_usage.users / license.quotas.max_users) * 100;

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        License & Usage
      </Typography>

      {/* Expiring Soon Warning */}
      {license.expiring_soon && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Your license expires in {license.days_until_expiry} days on{' '}
          {new Date(license.expires_at).toLocaleDateString()}.
          Please contact sales to renew.
        </Alert>
      )}

      {/* License Info */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6">Plan</Typography>
              <Chip
                label={license.tier.toUpperCase()}
                color="primary"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6">Status</Typography>
              <Chip
                label={license.is_valid ? 'ACTIVE' : 'EXPIRED'}
                color={license.is_valid ? 'success' : 'error'}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6">Expires In</Typography>
              <Typography variant="h4" color={license.expiring_soon ? 'error' : 'text.primary'}>
                {license.days_until_expiry} days
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Quotas */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Devices
              </Typography>
              <Box display="flex" alignItems="baseline" mb={1}>
                <Typography variant="h3">{license.current_usage.devices}</Typography>
                <Typography variant="h6" color="text.secondary" ml={1}>
                  / {license.quotas.max_devices === 999999 ? '∞' : license.quotas.max_devices}
                </Typography>
              </Box>
              {license.quotas.max_devices < 999999 && (
                <LinearProgress
                  variant="determinate"
                  value={Math.min(deviceUsage, 100)}
                  color={deviceUsage > 80 ? 'warning' : 'primary'}
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Users
              </Typography>
              <Box display="flex" alignItems="baseline" mb={1}>
                <Typography variant="h3">{license.current_usage.users}</Typography>
                <Typography variant="h6" color="text.secondary" ml={1}>
                  / {license.quotas.max_users === 999999 ? '∞' : license.quotas.max_users}
                </Typography>
              </Box>
              {license.quotas.max_users < 999999 && (
                <LinearProgress
                  variant="determinate"
                  value={Math.min(userUsage, 100)}
                  color={userUsage > 80 ? 'warning' : 'primary'}
                />
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Contact Sales CTA */}
      <Card sx={{ mt: 3, bgcolor: 'primary.main', color: 'white' }}>
        <CardContent>
          <Grid container alignItems="center">
            <Grid item xs={12} md={8}>
              <Typography variant="h6" gutterBottom>
                Need More Capacity?
              </Typography>
              <Typography>
                Contact sales to upgrade your plan or renew your license.
              </Typography>
            </Grid>
            <Grid item xs={12} md={4} textAlign="right">
              <Button
                variant="contained"
                color="secondary"
                href="mailto:sales@yourcompany.com"
              >
                Contact Sales
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}
```

---

## Step 8: Environment Setup

### Add to `.env` file

```bash
# License System Configuration
LICENSE_ENCRYPTION_KEY=your_generated_key_here
LICENSE_SECRET_SALT=your_generated_salt_here
```

**CRITICAL**: These keys must be the SAME on both:
1. Your machine (where you generate licenses)
2. Customer's deployment (where licenses are validated)

---

## Usage Workflow

### Scenario: New Customer Purchase

#### Step 1: Customer Buys License (Manual/Email/Website)
Customer contacts you, agrees to purchase Professional plan for 1 year.

#### Step 2: Generate License (Your Machine)
```bash
python scripts/generate_license.py \
  --customer "Acme Corporation" \
  --email "admin@acme.com" \
  --company "Acme Corp" \
  --tier professional \
  --days 365 \
  --order "ORD-2025-042" \
  --notes "Annual payment received, invoice #INV-2025-042"

# Output: license_output/license_abc123.txt
```

#### Step 3: Send License to Customer
Email the license key from `license_abc123.txt` to customer.

#### Step 4: (Optional) Import to Your Internal Database
If you want to track licenses in YOUR internal database:
```bash
python scripts/import_license.py license_output/license_abc123.json
```

#### Step 5: Customer Activates License
Customer pastes license key into their deployment's activation page.
License is validated and stored in THEIR database.

#### Step 6: Customer Uses Platform
Platform enforces quotas and features based on license tier.

---

## Testing Checklist

### Test License Generation
```bash
# Generate test license
python scripts/generate_license.py \
  --customer "Test User" \
  --email "test@test.com" \
  --tier starter \
  --days 30

# Should create license_output/license_*.txt and license_*.json
```

### Test License Activation
```bash
# Activate via API
curl -X POST http://localhost:3000/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "your_license_key_here"}'

# Should return success message
```

### Test License Status
```bash
curl http://localhost:3000/license/status

# Should return license details and quotas
```

### Test Quota Enforcement
```bash
# Try adding 11th device with Starter license (max 10)
# Should return 403 error with quota exceeded message
```

### Test Feature Gating
```bash
# Try creating scheduled audit with Starter license
# Should return 403 error saying feature not available
```

### Test Expired License
```bash
# Generate license with --days 0 (expired)
# Try to activate
# Should return error that license is expired
```

---

## Production Deployment

### Checklist
- [ ] Generate and save encryption keys securely
- [ ] Add keys to environment variables (not in code)
- [ ] Test license generation script
- [ ] Test license activation flow
- [ ] Test quota enforcement on all endpoints
- [ ] Test feature gating for premium features
- [ ] Create license activation documentation for customers
- [ ] Create internal sales documentation
- [ ] Set up license tracking spreadsheet/CRM

---

## Advantages of This Approach

✅ **Simple**: No complex billing system needed
✅ **Offline**: Generate licenses anytime, anywhere
✅ **Secure**: Encryption + signature prevents tampering
✅ **Flexible**: Custom quotas per customer
✅ **Manual Control**: You approve every license
✅ **Works Offline**: Customer doesn't need internet to validate
✅ **Audit Trail**: All activations logged in database
✅ **Enterprise-Friendly**: Common for on-premise B2B software

---

## Future Enhancements (Optional)

### Phase 2: Online License Portal
- Customer self-service portal to view licenses
- Automatic email delivery of license keys
- License renewal reminders

### Phase 3: Usage Reporting
- Customers can submit usage reports
- You can see how many devices they're managing
- Helps with upsell conversations

### Phase 4: License Server (Advanced)
- Central license server for validation
- Real-time license revocation
- Usage telemetry

**But start simple with offline approach!**

---

## Summary

**What You Get**:
1. Standalone license generation script (offline)
2. License activation API (in customer deployment)
3. License validation service
4. Quota enforcement
5. Feature gating
6. Frontend activation UI

**Time to Implement**: 1-2 days

**Complexity**: Low (no billing, no payment gateway)

**Ready for**: Manual sales, enterprise customers, on-premise deployments

---

## Next Steps

1. ✅ Review this document
2. ✅ Generate encryption keys
3. ✅ Add database migration
4. ✅ Create license generation script
5. ✅ Create license validation service
6. ✅ Add quota enforcement to APIs
7. ✅ Build frontend activation UI
8. ✅ Test end-to-end flow
9. ✅ Generate first real license
10. ✅ Start selling! 💰

**Ready to implement? Let me know if you want me to start creating these files!**
