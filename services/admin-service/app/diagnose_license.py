#!/usr/bin/env python3
"""
Diagnostic script to check license and user module state
Run inside Docker container
"""

import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from db_models import LicenseDB, UserDB, GroupModuleAccessDB, UserGroupMembershipDB
from services.user_group_service import user_group_service
from shared.license_manager import license_manager

def diagnose():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("DIAGNOSTIC REPORT")
        print("=" * 80)

        # 1. Check active licenses
        print("\n1. ACTIVE LICENSES:")
        print("-" * 80)
        active_licenses = db.query(LicenseDB).filter(LicenseDB.is_active == True).all()
        print(f"Found {len(active_licenses)} active license(s)")

        if len(active_licenses) == 0:
            print("❌ ERROR: No active license!")
            return

        if len(active_licenses) > 1:
            print("❌ ERROR: Multiple active licenses detected!")
            print("   This will cause license switching to fail!")
            print("\n   FIX: Run this SQL command:")
            print("   UPDATE licenses SET is_active = false;")
            print("   UPDATE licenses SET is_active = true")
            print("   WHERE activated_at = (SELECT MAX(activated_at) FROM licenses);")
            print()

        for lic in active_licenses:
            print(f"\n   License ID: {lic.id}")
            print(f"   Tier: {lic.license_tier}")
            print(f"   Customer: {lic.customer_name}")
            print(f"   Activated: {lic.activated_at}")
            print(f"   Enabled Modules: {lic.enabled_modules}")

        active_license = active_licenses[0]

        # 2. Check tier modules
        print("\n2. LICENSE TIER MODULES:")
        print("-" * 80)
        tier_modules = license_manager.get_tier_modules(active_license.license_tier)
        print(f"Tier: {active_license.license_tier.upper()}")
        print(f"Modules from license_manager: {sorted(tier_modules)}")

        # 3. Check first user
        print("\n3. USER MODULE ACCESS:")
        print("-" * 80)
        users = db.query(UserDB).limit(3).all()

        for user in users:
            print(f"\nUser: {user.username} (ID: {user.id})")
            print(f"Is Superuser: {user.is_superuser}")

            # Get user's groups
            memberships = db.query(UserGroupMembershipDB).filter(
                UserGroupMembershipDB.user_id == user.id
            ).all()

            print(f"Number of groups: {len(memberships)}")

            if memberships:
                for membership in memberships:
                    # Get group module access
                    group_access = db.query(GroupModuleAccessDB).filter(
                        GroupModuleAccessDB.group_id == membership.group_id,
                        GroupModuleAccessDB.can_access == True
                    ).all()

                    module_names = [ga.module_name for ga in group_access]
                    print(f"  Group {membership.group_id} modules: {sorted(module_names)}")

            # Get user's actual modules from service
            user_modules = user_group_service.get_user_modules(db, user.id)
            print(f"get_user_modules() returns: {sorted(user_modules)}")

            # Check if these are backend or frontend names
            backend_modules = ['manual_audits', 'scheduled_audits', 'basic_rules', 'health_checks',
                             'device_groups', 'discovery', 'webhooks', 'config_backups',
                             'drift_detection', 'rule_templates']
            frontend_modules = ['audit', 'audit_schedules', 'rules', 'health',
                              'device_groups', 'discovery_groups', 'notifications']

            has_backend = any(m in user_modules for m in backend_modules)
            has_frontend = any(m in user_modules for m in frontend_modules)

            print(f"  Contains backend names: {has_backend}")
            print(f"  Contains frontend names: {has_frontend}")

            if has_frontend and not has_backend:
                print("  ⚠️  WARNING: Returning frontend names! Should return backend names!")

        # 4. Check quotas
        print("\n4. QUOTA STATUS:")
        print("-" * 80)
        device_count = db.query(db.query(UserDB).statement.alias()).count() if hasattr(db, 'query') else 0
        user_count = len(users)

        print(f"Devices: (check manually in database)")
        print(f"Users: {user_count} / {active_license.max_users}")
        print(f"Max Devices: {active_license.max_devices}")
        print(f"Max Users: {active_license.max_users}")
        print(f"Max Storage: {active_license.max_storage_gb} GB")

        # 5. Recommendations
        print("\n5. RECOMMENDATIONS:")
        print("-" * 80)

        if len(active_licenses) > 1:
            print("❌ Fix multiple active licenses (see SQL above)")
        else:
            print("✅ Single active license")

        if user_modules and has_frontend:
            print("❌ get_user_modules() returning frontend names instead of backend names")
            print("   Check if admin-service is using the updated user_group_service.py")
        elif user_modules and has_backend:
            print("✅ get_user_modules() returning backend names (correct)")

        print("\nExpected menu items for", active_license.license_tier.upper() + ":")
        for module in tier_modules:
            print(f"  - {module}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
