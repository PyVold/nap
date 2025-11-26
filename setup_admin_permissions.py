#!/usr/bin/env python3
"""
Setup script to configure admin user with proper permissions
"""
import sqlite3
import sys

def setup_admin():
    db_path = 'network_audit.db'

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Checking admin user...")

        # Get admin user
        cursor.execute("SELECT id, username, is_superuser FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()

        if not admin_user:
            print("❌ Admin user not found!")
            print("Please create an admin user first.")
            return

        admin_id, username, is_superuser = admin_user
        print(f"✓ Found user: {username} (ID: {admin_id})")
        print(f"  Superuser: {bool(is_superuser)}")

        # Check if admin is in Administrators group
        cursor.execute("""
            SELECT ug.id, ug.name
            FROM user_groups ug
            JOIN user_group_memberships ugm ON ug.id = ugm.group_id
            WHERE ugm.user_id = ? AND ug.name = 'Administrators'
        """, (admin_id,))
        admin_group = cursor.fetchone()

        if admin_group:
            print(f"✓ Admin is already in 'Administrators' group")
        else:
            print("Adding admin to 'Administrators' group...")
            # Get Administrators group
            cursor.execute("SELECT id FROM user_groups WHERE name = 'Administrators'")
            admin_group_result = cursor.fetchone()

            if admin_group_result:
                admin_group_id = admin_group_result[0]
                cursor.execute("""
                    INSERT INTO user_group_memberships (user_id, group_id)
                    VALUES (?, ?)
                """, (admin_id, admin_group_id))
                conn.commit()
                print("✓ Admin added to 'Administrators' group")
            else:
                print("❌ 'Administrators' group not found. Run migrate_user_management.py first.")
                return

        # Optionally set as superuser for extra safety
        if not is_superuser:
            print("Setting admin as superuser...")
            cursor.execute("UPDATE users SET is_superuser = 1 WHERE id = ?", (admin_id,))
            conn.commit()
            print("✓ Admin is now a superuser")

        # Show current permissions
        print("\n" + "="*60)
        print("Admin user permissions:")
        print("="*60)

        cursor.execute("""
            SELECT DISTINCT gp.permission
            FROM group_permissions gp
            JOIN user_group_memberships ugm ON gp.group_id = ugm.group_id
            WHERE ugm.user_id = ? AND gp.granted = 1
            ORDER BY gp.permission
        """, (admin_id,))

        permissions = cursor.fetchall()
        if permissions:
            for perm in permissions:
                print(f"  ✓ {perm[0]}")
            print(f"\nTotal permissions: {len(permissions)}")
        else:
            print("  (Superuser - has all permissions)")

        # Show accessible modules
        print("\n" + "="*60)
        print("Admin accessible modules:")
        print("="*60)

        cursor.execute("""
            SELECT DISTINCT gma.module_name
            FROM group_module_access gma
            JOIN user_group_memberships ugm ON gma.group_id = ugm.group_id
            WHERE ugm.user_id = ? AND gma.can_access = 1
            ORDER BY gma.module_name
        """, (admin_id,))

        modules = cursor.fetchall()
        if modules:
            for mod in modules:
                print(f"  ✓ {mod[0]}")
            print(f"\nTotal modules: {len(modules)}")
        else:
            print("  (Superuser - has access to all modules)")

        print("\n✓ Admin user is properly configured!")
        print("\nPlease log out and log back in for changes to take effect.")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    setup_admin()
