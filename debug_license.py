#!/usr/bin/env python3
"""
Fix License Database Issues

This script:
1. Shows all active licenses
2. Deactivates all but the most recent license
3. Shows current user module access
"""

import sys
sys.path.insert(0, '/home/user/nap')

from database import SessionLocal
from db_models import LicenseDB, UserDB, GroupModuleAccessDB, UserGroupMembershipDB
from datetime import datetime

def fix_licenses():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("CHECKING LICENSE STATUS")
        print("=" * 70)

        # Get all active licenses
        active_licenses = db.query(LicenseDB).filter(LicenseDB.is_active == True).all()

        print(f"\nFound {len(active_licenses)} active license(s)\n")

        if len(active_licenses) == 0:
            print("❌ NO ACTIVE LICENSES FOUND!")
            print("   Please activate a license through the UI or using activate_license_direct.py")
            return

        # Show all active licenses
        for i, lic in enumerate(active_licenses, 1):
            print(f"License {i}:")
            print(f"  ID: {lic.id}")
            print(f"  Tier: {lic.license_tier.upper()}")
            print(f"  Customer: {lic.customer_name} ({lic.customer_email})")
            print(f"  Activated: {lic.activated_at}")
            print(f"  Expires: {lic.expires_at}")
            print(f"  Limits: {lic.max_devices} devices, {lic.max_users} users, {lic.max_storage_gb} GB")
            print(f"  Modules: {lic.enabled_modules}")
            print()

        # If multiple active licenses, keep only the most recent
        if len(active_licenses) > 1:
            print("⚠️  MULTIPLE ACTIVE LICENSES DETECTED!")
            print("   Deactivating all except the most recently activated...\n")

            # Sort by activated_at, keep the newest
            active_licenses.sort(key=lambda x: x.activated_at or datetime.min, reverse=True)
            most_recent = active_licenses[0]

            # Deactivate all others
            for lic in active_licenses[1:]:
                lic.is_active = False
                print(f"   ❌ Deactivated: {lic.license_tier} license (ID: {lic.id})")

            db.commit()
            print(f"\n   ✅ Kept active: {most_recent.license_tier.upper()} license (ID: {most_recent.id})")
            active_license = most_recent
        else:
            active_license = active_licenses[0]
            print(f"✅ Single active license: {active_license.license_tier.upper()}")

        print("\n" + "=" * 70)
        print("CURRENT LICENSE DETAILS")
        print("=" * 70)
        print(f"Tier: {active_license.license_tier.upper()}")
        print(f"Max Devices: {active_license.max_devices}")
        print(f"Max Users: {active_license.max_users}")
        print(f"Max Storage: {active_license.max_storage_gb} GB")
        print(f"Enabled Modules: {active_license.enabled_modules}")

        # Get tier modules from license_manager
        from shared.license_manager import license_manager
        tier_modules = license_manager.get_tier_modules(active_license.license_tier)
        print(f"\nTier Modules (from license_manager): {tier_modules}")

        print("\n" + "=" * 70)
        print("USER MODULE ACCESS")
        print("=" * 70)

        # Check first user's module access
        user = db.query(UserDB).first()
        if user:
            print(f"\nChecking module access for user: {user.username} (ID: {user.id})")
            print(f"Is superuser: {user.is_superuser}")

            # Get user's groups
            memberships = db.query(UserGroupMembershipDB).filter(
                UserGroupMembershipDB.user_id == user.id
            ).all()

            if memberships:
                print(f"User groups: {len(memberships)}")
                for m in memberships:
                    group_access = db.query(GroupModuleAccessDB).filter(
                        GroupModuleAccessDB.group_id == m.group_id,
                        GroupModuleAccessDB.can_access == True
                    ).all()
                    print(f"  Group {m.group_id} has access to: {[ga.module_name for ga in group_access]}")
            else:
                print("⚠️  User has no groups! This will block access even with valid license.")

            # Test get_user_modules
            from services.user_group_service import user_group_service
            user_modules = user_group_service.get_user_modules(db, user.id)
            print(f"\nget_user_modules() returns: {sorted(user_modules)}")

        print("\n" + "=" * 70)
        print("RECOMMENDATIONS")
        print("=" * 70)

        if len(active_licenses) > 1:
            print("✅ Fixed multiple active licenses")

        print("\n1. Restart the backend server:")
        print("   pkill -f 'uvicorn|fastapi|python.*main.py'")
        print("   cd /home/user/nap && python main.py")

        print("\n2. Clear browser cache (Ctrl+Shift+R)")

        print("\n3. Check the menu shows only these modules for", active_license.license_tier.upper() + ":")
        for module in tier_modules:
            print(f"   - {module}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_licenses()
