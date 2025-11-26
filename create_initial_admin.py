#!/usr/bin/env python3
"""
Create initial admin user for first-time setup
"""
import sqlite3
import sys
from utils.auth import get_password_hash

def create_initial_admin():
    db_path = 'network_audit.db'

    print("="*80)
    print("Initial Admin User Setup")
    print("="*80)

    # Get user input
    username = input("Enter admin username [admin]: ").strip() or "admin"
    email = input("Enter admin email [admin@example.com]: ").strip() or "admin@example.com"
    password = input("Enter admin password: ").strip()

    if not password:
        print("❌ Password cannot be empty!")
        sys.exit(1)

    full_name = input("Enter full name [Administrator]: ").strip() or "Administrator"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT id, username FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"\n❌ User '{username}' already exists! (ID: {existing_user[0]})")
            print("\nWould you like to update this user's password and make them admin? (yes/no)")
            response = input("> ").strip().lower()

            if response == 'yes':
                hashed_password = get_password_hash(password)
                cursor.execute("""
                    UPDATE users
                    SET hashed_password = ?, is_superuser = 1, role = 'admin', is_active = 1
                    WHERE username = ?
                """, (hashed_password, username))

                user_id = existing_user[0]
                print(f"✓ Updated user '{username}' password and set as admin")
            else:
                print("Aborted.")
                sys.exit(0)
        else:
            # Create new admin user
            hashed_password = get_password_hash(password)

            cursor.execute("""
                INSERT INTO users (username, email, full_name, hashed_password, role, is_active, is_superuser)
                VALUES (?, ?, ?, ?, 'admin', 1, 1)
            """, (username, email, full_name, hashed_password))

            user_id = cursor.lastrowid
            print(f"\n✓ Created admin user: {username} (ID: {user_id})")

        # Add to Administrators group
        cursor.execute("SELECT id FROM user_groups WHERE name = 'Administrators'")
        admin_group = cursor.fetchone()

        if admin_group:
            admin_group_id = admin_group[0]

            # Check if already in group
            cursor.execute("""
                SELECT 1 FROM user_group_memberships
                WHERE user_id = ? AND group_id = ?
            """, (user_id, admin_group_id))

            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO user_group_memberships (user_id, group_id)
                    VALUES (?, ?)
                """, (user_id, admin_group_id))
                print(f"✓ Added '{username}' to 'Administrators' group")
            else:
                print(f"✓ '{username}' already in 'Administrators' group")
        else:
            print("⚠ Warning: 'Administrators' group not found. Run migrate_user_management.py first.")

        conn.commit()

        print("\n" + "="*80)
        print("✓✓✓ Admin user successfully configured!")
        print("="*80)
        print(f"\nUsername: {username}")
        print(f"Email: {email}")
        print(f"Role: admin")
        print(f"Superuser: Yes")
        print("\nYou can now log in with these credentials.")
        print("="*80)

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    create_initial_admin()
