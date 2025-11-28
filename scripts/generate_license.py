#!/usr/bin/env python3
"""
Offline License Generation Script for Network Audit Platform

This script generates encrypted license keys that can be sent to customers.
It runs OFFLINE on your machine - no internet connection required.

Usage:
    python scripts/generate_license.py --customer "Acme Corp" --email "admin@acme.com" --tier professional --days 365

    # With custom quotas
    python scripts/generate_license.py \
        --customer "Big Enterprise" \
        --email "it@bigcorp.com" \
        --tier enterprise \
        --days 730 \
        --devices 500 \
        --users 50

Output:
    license_output/
    ├── license_<timestamp>.txt       # Send this to customer
    └── license_<timestamp>.json      # Keep for your records

Environment Variables:
    LICENSE_ENCRYPTION_KEY - Encryption key (generate once, keep secret)
    LICENSE_SECRET_SALT    - Salt for signatures (generate once, keep secret)
"""

import os
import sys
import json
import hashlib
import secrets
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("Error: cryptography library not found")
    print("Install it with: pip install cryptography")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

# These should match your production values
# Generate once and store securely!
LICENSE_ENCRYPTION_KEY = os.getenv(
    "LICENSE_ENCRYPTION_KEY",
    None  # Will prompt to generate if not set
)

LICENSE_SECRET_SALT = os.getenv(
    "LICENSE_SECRET_SALT", 
    None  # Will prompt to generate if not set
)

# License tier definitions (must match backend)
LICENSE_TIERS = {
    "starter": {
        "name": "Starter",
        "max_devices": 10,
        "max_users": 2,
        "max_storage_gb": 5,
        "modules": ["devices", "manual_audits", "basic_rules", "health_checks"]
    },
    "professional": {
        "name": "Professional",
        "max_devices": 100,
        "max_users": 10,
        "max_storage_gb": 50,
        "modules": [
            "devices", "manual_audits", "scheduled_audits", "basic_rules",
            "rule_templates", "api_access", "config_backups", "drift_detection",
            "webhooks", "device_groups", "discovery"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "max_devices": 999999,
        "max_users": 999999,
        "max_storage_gb": 999999,
        "modules": ["all"]
    }
}


# ============================================================================
# License Generation Functions
# ============================================================================

def generate_encryption_key():
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key().decode()


def generate_salt():
    """Generate a new secret salt"""
    return secrets.token_hex(32)


def setup_keys():
    """Interactive setup for encryption keys"""
    print("\n" + "="*80)
    print("LICENSE SYSTEM - FIRST TIME SETUP")
    print("="*80)
    print("\nNo encryption keys found. Let's generate them now.")
    print("IMPORTANT: Save these keys securely - you'll need them to validate licenses!\n")
    
    encryption_key = generate_encryption_key()
    secret_salt = generate_salt()
    
    print("Generated Encryption Key:")
    print(f"  {encryption_key}\n")
    
    print("Generated Secret Salt:")
    print(f"  {secret_salt}\n")
    
    print("Add these to your environment (save to .env file):")
    print("-" * 80)
    print(f'LICENSE_ENCRYPTION_KEY="{encryption_key}"')
    print(f'LICENSE_SECRET_SALT="{secret_salt}"')
    print("-" * 80)
    
    print("\nFor this session, I'll use these keys to generate your license.")
    response = input("Continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Setup cancelled.")
        sys.exit(0)
    
    return encryption_key, secret_salt


def generate_license(
    customer_name: str,
    customer_email: str,
    tier: str,
    duration_days: int,
    company_name: str = None,
    max_devices: int = None,
    max_users: int = None,
    max_storage_gb: int = None,
    order_id: str = None,
    encryption_key: str = None,
    secret_salt: str = None
):
    """
    Generate an encrypted license key
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
        tier: License tier (starter, professional, enterprise)
        duration_days: License validity in days
        company_name: Company name (optional)
        max_devices: Override default device quota
        max_users: Override default user quota
        max_storage_gb: Override default storage quota
        order_id: Internal order/invoice ID
        encryption_key: Fernet encryption key
        secret_salt: Signature salt
    
    Returns:
        (license_key, license_data)
    """
    # Validate tier
    if tier.lower() not in LICENSE_TIERS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of: {', '.join(LICENSE_TIERS.keys())}")
    
    tier = tier.lower()
    tier_config = LICENSE_TIERS[tier]
    
    # Use tier defaults or custom values
    max_devices = max_devices or tier_config["max_devices"]
    max_users = max_users or tier_config["max_users"]
    max_storage_gb = max_storage_gb or tier_config["max_storage_gb"]
    
    # Build license payload
    now = datetime.utcnow()
    expires_at = now + timedelta(days=duration_days)
    
    license_data = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "company_name": company_name,
        "tier": tier,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "max_devices": max_devices,
        "max_users": max_users,
        "max_storage_gb": max_storage_gb,
        "modules": tier_config["modules"],
        "order_id": order_id,
        "version": "1.0"
    }
    
    # Create signature to prevent tampering
    data_str = json.dumps(license_data, sort_keys=True)
    signature = hashlib.sha256(f"{data_str}{secret_salt}".encode()).hexdigest()
    license_data["signature"] = signature
    
    # Encrypt the license data
    cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
    encrypted = cipher.encrypt(json.dumps(license_data).encode())
    license_key = encrypted.decode()
    
    return license_key, license_data


def save_license(license_key: str, license_data: dict, output_dir: str = "license_output"):
    """
    Save license to files
    
    Args:
        license_key: Encrypted license key (send to customer)
        license_data: License metadata (keep for records)
        output_dir: Directory to save files
    
    Returns:
        (key_file_path, json_file_path)
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    customer_slug = license_data["customer_email"].split("@")[0].lower().replace(".", "_")
    base_name = f"license_{customer_slug}_{timestamp}"
    
    # Save license key (for customer)
    key_file = output_path / f"{base_name}.txt"
    with open(key_file, "w") as f:
        f.write("="*80 + "\n")
        f.write("NETWORK AUDIT PLATFORM - LICENSE KEY\n")
        f.write("="*80 + "\n\n")
        f.write(f"Customer: {license_data['customer_name']}\n")
        f.write(f"Email: {license_data['customer_email']}\n")
        if license_data.get('company_name'):
            f.write(f"Company: {license_data['company_name']}\n")
        f.write(f"Tier: {LICENSE_TIERS[license_data['tier']]['name']}\n")
        f.write(f"Issued: {license_data['issued_at'][:10]}\n")
        f.write(f"Expires: {license_data['expires_at'][:10]}\n")
        f.write(f"\nMax Devices: {license_data['max_devices']}\n")
        f.write(f"Max Users: {license_data['max_users']}\n")
        f.write(f"Storage: {license_data['max_storage_gb']} GB\n")
        f.write("\n" + "="*80 + "\n")
        f.write("LICENSE KEY (copy this to activate):\n")
        f.write("="*80 + "\n\n")
        f.write(license_key)
        f.write("\n\n" + "="*80 + "\n")
        f.write("ACTIVATION INSTRUCTIONS:\n")
        f.write("="*80 + "\n")
        f.write("1. Log into your Network Audit Platform\n")
        f.write("2. Navigate to Settings > License\n")
        f.write("3. Paste the license key above\n")
        f.write("4. Click 'Activate'\n")
        f.write("\nFor support: support@yourcompany.com\n")
        f.write("="*80 + "\n")
    
    # Save metadata (for your records)
    json_file = output_path / f"{base_name}.json"
    
    # Remove signature from saved metadata
    metadata = license_data.copy()
    metadata.pop("signature", None)
    metadata["license_key_preview"] = license_key[:50] + "..."
    
    with open(json_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    return str(key_file), str(json_file)


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate offline licenses for Network Audit Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Starter license for 1 year
  python scripts/generate_license.py \\
    --customer "John Doe" \\
    --email "john@example.com" \\
    --tier starter \\
    --days 365

  # Professional license with custom quotas
  python scripts/generate_license.py \\
    --customer "Acme Corp" \\
    --email "admin@acme.com" \\
    --company "Acme Corporation" \\
    --tier professional \\
    --days 365 \\
    --devices 200 \\
    --users 20

  # Enterprise license for 2 years
  python scripts/generate_license.py \\
    --customer "Big Enterprise" \\
    --email "it@bigcorp.com" \\
    --tier enterprise \\
    --days 730
        """
    )
    
    parser.add_argument(
        "--customer",
        required=True,
        help="Customer name"
    )
    
    parser.add_argument(
        "--email",
        required=True,
        help="Customer email address"
    )
    
    parser.add_argument(
        "--tier",
        required=True,
        choices=["starter", "professional", "enterprise"],
        help="License tier"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="License duration in days (default: 365)"
    )
    
    parser.add_argument(
        "--company",
        help="Company name (optional)"
    )
    
    parser.add_argument(
        "--devices",
        type=int,
        help="Max devices (overrides tier default)"
    )
    
    parser.add_argument(
        "--users",
        type=int,
        help="Max users (overrides tier default)"
    )
    
    parser.add_argument(
        "--storage",
        type=int,
        help="Max storage in GB (overrides tier default)"
    )
    
    parser.add_argument(
        "--order-id",
        help="Internal order/invoice ID"
    )
    
    parser.add_argument(
        "--output",
        default="license_output",
        help="Output directory (default: license_output)"
    )
    
    args = parser.parse_args()
    
    # Check for encryption keys
    encryption_key = LICENSE_ENCRYPTION_KEY
    secret_salt = LICENSE_SECRET_SALT
    
    if not encryption_key or not secret_salt:
        encryption_key, secret_salt = setup_keys()
    
    # Display generation info
    print("\n" + "="*80)
    print("GENERATING LICENSE")
    print("="*80)
    print(f"Customer: {args.customer}")
    print(f"Email: {args.email}")
    if args.company:
        print(f"Company: {args.company}")
    print(f"Tier: {args.tier.upper()}")
    print(f"Duration: {args.days} days")
    
    tier_config = LICENSE_TIERS[args.tier]
    print(f"\nQuotas:")
    print(f"  Devices: {args.devices or tier_config['max_devices']}")
    print(f"  Users: {args.users or tier_config['max_users']}")
    print(f"  Storage: {args.storage or tier_config['max_storage_gb']} GB")
    print(f"  Modules: {len(tier_config['modules'])} enabled")
    print("="*80 + "\n")
    
    try:
        # Generate license
        license_key, license_data = generate_license(
            customer_name=args.customer,
            customer_email=args.email,
            tier=args.tier,
            duration_days=args.days,
            company_name=args.company,
            max_devices=args.devices,
            max_users=args.users,
            max_storage_gb=args.storage,
            order_id=args.order_id,
            encryption_key=encryption_key,
            secret_salt=secret_salt
        )
        
        # Save to files
        key_file, json_file = save_license(license_key, license_data, args.output)
        
        print("✓ License generated successfully!\n")
        print(f"License key saved to: {key_file}")
        print(f"Metadata saved to: {json_file}\n")
        
        print("Next steps:")
        print("  1. Send the .txt file to the customer")
        print("  2. Keep the .json file for your records")
        print("  3. Customer activates the license in their platform\n")
        
        print("License key preview:")
        print("-" * 80)
        print(license_key[:100] + "...")
        print("-" * 80)
        
    except Exception as e:
        print(f"\n✗ Error generating license: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
