#!/usr/bin/env python3
"""
Detailed License and Module Diagnostic

This script provides comprehensive diagnostics for license tier enforcement,
module access, and quota management.

Run from inside admin-service container:
    python3 /app/diagnose_detailed.py
"""

import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from db_models import LicenseDB, UserDB, GroupModuleAccessDB, UserGroupMembershipDB, DeviceDB
from services.user_group_service import user_group_service
from shared.license_manager import license_manager, LICENSE_TIERS
from datetime import datetime

def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def print_subsection(title):
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)

def diagnose():
    db = SessionLocal()
    try:
        print_section("LICENSE TIER & MODULE DIAGNOSTIC")

        # 1. Check active licenses
        print_subsection("1. ACTIVE LICENSES")
        active_licenses = db.query(LicenseDB).filter(LicenseDB.is_active == True).all()

        print(f"Found {len(active_licenses)} active license(s)")

        if len(active_licenses) == 0:
            print("❌ ERROR: No active license!")
            print("   Please activate a license through the UI")
            return

        if len(active_licenses) > 1:
            print("❌ ERROR: Multiple active licenses detected!")
            print("   This will cause license switching to fail!")
            print("\n   Licenses found:")
            for i, lic in enumerate(active_licenses, 1):
                print(f"   {i}. {lic.license_tier} - activated {lic.activated_at}")
            print("\n   FIX: Keep only the most recent license active")
            print("   SQL:")
            print("   UPDATE licenses SET is_active = false;")
            print("   UPDATE licenses SET is_active = true")
            print("   WHERE activated_at = (SELECT MAX(activated_at) FROM licenses);")
            active_license = active_licenses[0]  # Use first one for now
        else:
            active_license = active_licenses[0]
            print(f"✅ Single active license: {active_license.license_tier.upper()}")

        print(f"\n   License Details:")
        print(f"   Customer: {active_license.customer_name}")
        print(f"   Email: {active_license.customer_email}")
        print(f"   Tier: {active_license.license_tier}")
        print(f"   Activated: {active_license.activated_at}")
        print(f"   Expires: {active_license.expires_at}")
        print(f"   Max Devices: {active_license.max_devices}")
        print(f"   Max Users: {active_license.max_users}")
        print(f"   Max Storage: {active_license.max_storage_gb} GB")

        # 2. Validate license
        print_subsection("2. LICENSE VALIDATION")
        validation = license_manager.validate_license(active_license.license_key)

        if validation["valid"]:
            print(f"✅ License is VALID")
            print(f"   Message: {validation['message']}")
        else:
            print(f"❌ License is INVALID!")
            print(f"   Reason: {validation['reason']}")
            print(f"   Message: {validation['message']}")
            return

        license_data = validation["data"]

        # 3. Check tier modules
        print_subsection("3. LICENSE TIER MODULES")
        tier = active_license.license_tier
        tier_modules = license_manager.get_tier_modules(tier)

        print(f"Tier: {tier.upper()}")
        print(f"Available Modules ({len(tier_modules)}):")
        for module in sorted(tier_modules):
            print(f"   ✓ {module}")

        # Show what this tier should enable
        print(f"\nExpected Features for {tier.upper()}:")
        if tier == "starter":
            print("   ✓ Device Management")
            print("   ✓ Manual Audits")
            print("   ✓ Basic Rules")
            print("   ✓ Health Monitoring")
            print("   ✓ Hardware Inventory")
        elif tier == "professional":
            print("   ✓ All Starter features, plus:")
            print("   ✓ Device Groups")
            print("   ✓ Discovery Groups")
            print("   ✓ Scheduled Audits")
            print("   ✓ Rule Templates")
            print("   ✓ Config Backups")
            print("   ✓ Drift Detection")
            print("   ✓ Webhooks/Notifications")
        elif tier == "enterprise":
            print("   ✓ All Professional features, plus:")
            print("   ✓ Integrations")
            print("   ✓ Workflow Automation")
            print("   ✓ AI/ML Features")
            print("   ✓ Advanced Analytics")

        # 4. Check users and their module access
        print_subsection("4. USER MODULE ACCESS")
        users = db.query(UserDB).limit(5).all()

        print(f"Checking {len(users)} user(s):")

        for user in users:
            print(f"\n{'─' * 80}")
            print(f"User: {user.username} (ID: {user.id})")
            print(f"Is Superuser: {user.is_superuser}")
            print(f"Email: {user.email}")

            # Get user's groups
            memberships = db.query(UserGroupMembershipDB).filter(
                UserGroupMembershipDB.user_id == user.id
            ).all()

            print(f"Groups: {len(memberships)}")

            if len(memberships) == 0:
                print("   ⚠️  WARNING: User has no groups!")
                print("   Regular users need group membership to access modules")

            # Show group module access
            for membership in memberships:
                group_access = db.query(GroupModuleAccessDB).filter(
                    GroupModuleAccessDB.group_id == membership.group_id,
                    GroupModuleAccessDB.can_access == True
                ).all()

                if group_access:
                    module_names = sorted([ga.module_name for ga in group_access])
                    print(f"   Group {membership.group_id} grants access to: {module_names}")

            # Get user's actual modules from service
            print("\n   Testing get_user_modules()...")
            user_modules = user_group_service.get_user_modules(db, user.id)
            user_modules_sorted = sorted(user_modules)

            print(f"   Returns: {user_modules_sorted}")
            print(f"   Count: {len(user_modules)}")

            # Validate the modules are backend names
            backend_modules = ['manual_audits', 'scheduled_audits', 'basic_rules', 'health_checks',
                             'device_groups', 'discovery', 'webhooks', 'config_backups',
                             'drift_detection', 'rule_templates', 'devices']
            frontend_modules = ['audit', 'audit_schedules', 'rules', 'health',
                              'device_groups', 'discovery_groups', 'notifications']

            has_backend = any(m in user_modules for m in backend_modules)
            has_frontend = any(m in user_modules for m in frontend_modules
                             if m not in backend_modules)  # Exclude overlaps

            if has_backend and not has_frontend:
                print("   ✅ Correctly returning BACKEND module names")
            elif has_frontend and not has_backend:
                print("   ❌ ERROR: Returning FRONTEND module names!")
                print("   This means admin-service is NOT running the updated code")
                print("   Solution: Rebuild admin-service container")
            elif not user_modules:
                if user.is_superuser:
                    print("   ❌ ERROR: Superuser should have modules from license!")
                else:
                    print("   ⚠️  User has no modules (check groups or license)")

            # Check if modules are within license
            unlicensed = user_modules - set(tier_modules)
            if unlicensed:
                print(f"   ⚠️  WARNING: User has modules not in license tier: {unlicensed}")

            licensed_but_missing = set(tier_modules) - user_modules
            if licensed_but_missing and not user.is_superuser:
                print(f"   ℹ️  User could access these licensed modules via groups: {licensed_but_missing}")

        # 5. Check quotas
        print_subsection("5. QUOTA STATUS")

        device_count = db.query(DeviceDB).count()
        user_count = db.query(UserDB).count()

        print(f"Current Usage vs License Limits:")
        print(f"\n   Devices: {device_count} / {active_license.max_devices}", end="")
        if device_count > active_license.max_devices:
            print(" ❌ OVER LIMIT!")
        elif device_count == active_license.max_devices:
            print(" ⚠️  AT LIMIT")
        else:
            print(f" ✅ ({active_license.max_devices - device_count} remaining)")

        print(f"   Users: {user_count} / {active_license.max_users}", end="")
        if user_count > active_license.max_users:
            print(" ❌ OVER LIMIT!")
        elif user_count == active_license.max_users:
            print(" ⚠️  AT LIMIT")
        else:
            print(f" ✅ ({active_license.max_users - user_count} remaining)")

        # Check storage (need to query config_backups table)
        try:
            from db_models import ConfigBackupDB
            storage_bytes = db.query(
                db.func.sum(ConfigBackupDB.size_bytes)
            ).scalar() or 0
            storage_gb = storage_bytes / (1024 * 1024 * 1024)

            print(f"   Storage: {storage_gb:.2f} GB / {active_license.max_storage_gb} GB", end="")
            if storage_gb > active_license.max_storage_gb:
                print(" ❌ OVER LIMIT!")
            elif storage_gb >= active_license.max_storage_gb * 0.9:
                print(" ⚠️  NEAR LIMIT")
            else:
                print(f" ✅ ({active_license.max_storage_gb - storage_gb:.2f} GB remaining)")
        except Exception as e:
            print(f"   Storage: Unable to calculate (table may not exist)")

        # 6. Test endpoints
        print_subsection("6. ENDPOINT AVAILABILITY")

        try:
            from shared.license_manager import ROUTE_MODULE_MAP
            print(f"✅ ROUTE_MODULE_MAP loaded successfully")
            print(f"   Contains {len(ROUTE_MODULE_MAP)} route mappings")
            print(f"   Sample: {dict(list(ROUTE_MODULE_MAP.items())[:3])}")
        except Exception as e:
            print(f"❌ Failed to load ROUTE_MODULE_MAP: {e}")

        # 7. Recommendations
        print_subsection("7. RECOMMENDATIONS")

        issues_found = False

        if len(active_licenses) > 1:
            print("❌ FIX: Multiple active licenses - deactivate all but one")
            issues_found = True

        if has_frontend:
            print("❌ FIX: get_user_modules() returning frontend names - rebuild admin-service")
            print("   Run: docker-compose build admin-service && docker-compose up -d admin-service")
            issues_found = True

        if device_count > active_license.max_devices or user_count > active_license.max_users:
            print("⚠️  WARNING: Quotas exceeded - quota enforcement may not be working")
            print("   Check if device-service and admin-service have quota middleware")
            issues_found = True

        if not memberships and not user.is_superuser:
            print("⚠️  WARNING: Users without groups won't have module access")
            print("   Create user groups and assign users to them")
            issues_found = True

        if not issues_found:
            print("✅ No critical issues detected!")
            print("\nIf frontend still shows wrong modules:")
            print("1. Hard refresh browser (Ctrl+Shift+R)")
            print("2. Check browser console for errors")
            print("3. Verify API calls are returning correct data")

        print_section("DIAGNOSTIC COMPLETE")

    except Exception as e:
        print(f"\n❌ Error during diagnostic: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
