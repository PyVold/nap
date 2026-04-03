#!/usr/bin/env python3
"""
License Key Generator for Network Audit Platform

Generates encrypted, signed license keys for customers.
This script should be run by an administrator, NOT shipped to customers.

Usage:
    python scripts/generate_license.py \
        --customer "Acme Corp" \
        --email "admin@acme.com" \
        --company "Acme Corporation" \
        --tier enterprise \
        --days 365

    # Using custom quotas:
    python scripts/generate_license.py \
        --customer "Acme Corp" \
        --email "admin@acme.com" \
        --tier professional \
        --days 365 \
        --max-devices 200 \
        --max-users 25
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path so we can import shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("ERROR: cryptography package not installed.")
    print("Install with: pip install cryptography")
    sys.exit(1)


# License tier defaults (mirrors shared/license_manager.py)
TIER_DEFAULTS = {
    "starter": {"max_devices": 10, "max_users": 2, "max_storage_gb": 5},
    "professional": {"max_devices": 100, "max_users": 10, "max_storage_gb": 50},
    "enterprise": {"max_devices": 999999, "max_users": 999999, "max_storage_gb": 999999},
}


def generate_license(
    encryption_key: str,
    secret_salt: str,
    customer_name: str,
    customer_email: str,
    company_name: str,
    tier: str,
    days: int,
    max_devices: int = None,
    max_users: int = None,
    max_storage_gb: int = None,
) -> str:
    """Generate an encrypted, signed license key."""

    tier_config = TIER_DEFAULTS.get(tier)
    if not tier_config:
        raise ValueError(f"Unknown tier: {tier}. Must be one of: {list(TIER_DEFAULTS.keys())}")

    now = datetime.utcnow()
    expires_at = now + timedelta(days=days)

    # Build license payload
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "company_name": company_name,
        "tier": tier,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "max_devices": max_devices or tier_config["max_devices"],
        "max_users": max_users or tier_config["max_users"],
        "max_storage_gb": max_storage_gb or tier_config["max_storage_gb"],
        "modules": ["all"] if tier == "enterprise" else list(TIER_DEFAULTS.keys()),
    }

    # Sign the payload
    data_str = json.dumps(payload, sort_keys=True)
    signature = hashlib.sha256(f"{data_str}{secret_salt}".encode()).hexdigest()
    payload["signature"] = signature

    # Encrypt with Fernet
    cipher = Fernet(encryption_key.encode())
    encrypted = cipher.encrypt(json.dumps(payload).encode())

    return encrypted.decode()


def main():
    parser = argparse.ArgumentParser(
        description="Generate a license key for Network Audit Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enterprise license for 1 year
  python scripts/generate_license.py \\
      --customer "John Doe" --email "john@acme.com" \\
      --company "Acme Corp" --tier enterprise --days 365

  # Professional license with custom quotas
  python scripts/generate_license.py \\
      --customer "Jane Smith" --email "jane@example.com" \\
      --tier professional --days 180 --max-devices 200

Environment variables required:
  LICENSE_ENCRYPTION_KEY  - Fernet encryption key
  LICENSE_SECRET_SALT     - HMAC signing salt
        """,
    )
    parser.add_argument("--customer", required=True, help="Customer name")
    parser.add_argument("--email", required=True, help="Customer email")
    parser.add_argument("--company", default="", help="Company name")
    parser.add_argument(
        "--tier",
        required=True,
        choices=["starter", "professional", "enterprise"],
        help="License tier",
    )
    parser.add_argument("--days", type=int, default=365, help="Validity in days (default: 365)")
    parser.add_argument("--max-devices", type=int, default=None, help="Override max devices quota")
    parser.add_argument("--max-users", type=int, default=None, help="Override max users quota")
    parser.add_argument("--max-storage-gb", type=int, default=None, help="Override max storage (GB)")
    parser.add_argument(
        "--encryption-key",
        default=None,
        help="Fernet key (overrides LICENSE_ENCRYPTION_KEY env var)",
    )
    parser.add_argument(
        "--salt",
        default=None,
        help="Secret salt (overrides LICENSE_SECRET_SALT env var)",
    )
    parser.add_argument("--output", "-o", default=None, help="Write license key to file")

    args = parser.parse_args()

    # Get keys from args or environment
    encryption_key = args.encryption_key or os.getenv("LICENSE_ENCRYPTION_KEY")
    secret_salt = args.salt or os.getenv("LICENSE_SECRET_SALT")

    if not encryption_key:
        print("ERROR: LICENSE_ENCRYPTION_KEY not set.")
        print("Generate one with:")
        print('  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
        print("Then set it: export LICENSE_ENCRYPTION_KEY=<key>")
        sys.exit(1)

    if not secret_salt:
        print("ERROR: LICENSE_SECRET_SALT not set.")
        print("Generate one with:")
        print('  python -c "import secrets; print(secrets.token_hex(32))"')
        print("Then set it: export LICENSE_SECRET_SALT=<salt>")
        sys.exit(1)

    try:
        license_key = generate_license(
            encryption_key=encryption_key,
            secret_salt=secret_salt,
            customer_name=args.customer,
            customer_email=args.email,
            company_name=args.company,
            tier=args.tier,
            days=args.days,
            max_devices=args.max_devices,
            max_users=args.max_users,
            max_storage_gb=args.max_storage_gb,
        )
    except Exception as e:
        print(f"ERROR: Failed to generate license: {e}")
        sys.exit(1)

    # Output
    print("=" * 80)
    print("LICENSE KEY GENERATED SUCCESSFULLY")
    print("=" * 80)
    print(f"  Customer:  {args.customer} ({args.email})")
    print(f"  Company:   {args.company or 'N/A'}")
    print(f"  Tier:      {args.tier}")
    print(f"  Valid for: {args.days} days")
    if args.max_devices:
        print(f"  Devices:   {args.max_devices}")
    if args.max_users:
        print(f"  Users:     {args.max_users}")
    print("=" * 80)
    print()
    print("LICENSE KEY (copy the entire string below):")
    print()
    print(license_key)
    print()

    if args.output:
        with open(args.output, "w") as f:
            f.write(license_key)
        print(f"License key also written to: {args.output}")

    print("=" * 80)
    print("ACTIVATION:")
    print("  1. Log in to NAP as admin")
    print("  2. Go to Admin > License Management")
    print("  3. Paste the license key and click Activate")
    print("  -- or --")
    print("  curl -X POST http://localhost:3000/license/activate \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -H "Authorization: Bearer <token>" \\')
    print(f'    -d \'{{"license_key": "<paste_key_here>"}}\'')
    print("=" * 80)


if __name__ == "__main__":
    main()
