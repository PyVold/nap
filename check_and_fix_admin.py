#!/usr/bin/env python3
"""
Check and fix admin user configuration
"""
import sqlite3
from utils.auth import get_password_hash

def check_and_fix_admin():
    db_path = 'network_audit.db'

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check all users
        cursor.execute("SELECT id, username, email, role, is_superuser FROM users")
        users = cursor.fetchall()

        print("Current users in database:")
        print("="*80)
        if users:
            for user in users:
                user_id, username, email, role, is_superuser = user
                print(f"ID: {user_id}, Username: {username}, Email: {email}, Role: {role}, Superuser: {bool(is_superuser)}")
        else:
            print("No users found in database!")
        print("="*80)

        # Find admin or first user
        admin_user = None
        for user in users:
            if user[1] in ['admin', 'administrator']:  # Check username
                admin_user = user
                break

        if not admin_user and users:
            # Use first user as admin
            admin_user = users[0]
            print(f"\nNo admin user found. Using first user: {admin_user[1]}")

        if admin_user:
            admin_id = admin_user[0]
            username = admin_user[1]
            is_superuser = admin_user[4]

            print(f"\nConfiguring user: {username} (ID: {admin_id})")

            # Set as superuser if not already
            if not is_superuser:
                cursor.execute("UPDATE users SET is_superuser = 1 WHERE id = ?", (admin_id,))
                print(f"✓ Set {username} as superuser")
            else:
                print(f"✓ {username} is already a superuser")

            # Add to Administrators group
            cursor.execute("SELECT id FROM user_groups WHERE name = 'Administrators'")
            admin_group = cursor.fetchone()

            if admin_group:
                admin_group_id = admin_group[0]

                # Check if already in group
                cursor.execute("""
                    SELECT 1 FROM user_group_memberships
                    WHERE user_id = ? AND group_id = ?
                """, (admin_id, admin_group_id))

                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO user_group_memberships (user_id, group_id)
                        VALUES (?, ?)
                    """, (admin_id, admin_group_id))
                    print(f"✓ Added {username} to 'Administrators' group")
                else:
                    print(f"✓ {username} already in 'Administrators' group")

            conn.commit()
            print(f"\n✓✓✓ User {username} is now properly configured!")
            print("\nPlease log out and log back in for changes to take effect.")
        else:
            print("\n❌ No users found in database. Please create a user first through the login/registration process.")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_and_fix_admin()
