#!/usr/bin/env python3
"""
Fix admin user superuser status from inside admin-service container
Run this inside the admin-service container
"""

import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://nap_user:nap_password@database:5432/nap_db')

print("=" * 50)
print("Admin User Superuser Status Fix")
print("=" * 50)
print()

try:
    # Create database connection
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check current status
    result = session.execute("""
        SELECT id, username, email, role, is_superuser, is_active
        FROM users
        WHERE username = 'admin'
    """)

    admin = result.fetchone()

    if not admin:
        print("❌ ERROR: Admin user not found in database!")
        sys.exit(1)

    print("Current admin user status:")
    print(f"  ID: {admin[0]}")
    print(f"  Username: {admin[1]}")
    print(f"  Email: {admin[2]}")
    print(f"  Role: {admin[3]}")
    print(f"  is_superuser: {admin[4]}")
    print(f"  is_active: {admin[5]}")
    print()

    if admin[4]:  # is_superuser is True
        print("✅ Admin user already has is_superuser = True")
        print("   No changes needed.")
    else:
        print("⚠️  Admin user has is_superuser = False")
        print("   Updating to True...")

        # Update to superuser
        session.execute("""
            UPDATE users
            SET is_superuser = true
            WHERE username = 'admin'
        """)
        session.commit()

        # Verify update
        result = session.execute("""
            SELECT is_superuser FROM users WHERE username = 'admin'
        """)
        updated = result.fetchone()

        if updated[0]:
            print("✅ Successfully updated admin user to is_superuser = True")
        else:
            print("❌ Failed to update admin user")
            sys.exit(1)

    session.close()

    print()
    print("=" * 50)
    print("Fix Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Clear browser cache or use incognito window")
    print("2. Logout and login again as admin")
    print("3. Navigate to /admin")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
