"""
Migration: Add user management tables (user_groups, permissions, module_access)
"""
import sqlite3
import os

DB_PATH = "network_audit.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if user_groups table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_groups'")
        if cursor.fetchone():
            print("User management tables already exist")
            return

        print("Creating user management tables...")

        # Create user_groups table
        cursor.execute("""
            CREATE TABLE user_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                created_by VARCHAR(100)
            )
        """)
        cursor.execute("CREATE INDEX ix_user_groups_name ON user_groups(name)")

        # Create user_group_memberships table
        cursor.execute("""
            CREATE TABLE user_group_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX ix_user_group_membership ON user_group_memberships(user_id, group_id)")

        # Create group_permissions table
        cursor.execute("""
            CREATE TABLE group_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                permission VARCHAR(100) NOT NULL,
                granted BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX ix_group_permission ON group_permissions(group_id, permission)")

        # Create group_module_access table
        cursor.execute("""
            CREATE TABLE group_module_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                module_name VARCHAR(100) NOT NULL,
                can_access BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX ix_group_module_access ON group_module_access(group_id, module_name)")

        conn.commit()
        print("✓ User management tables created successfully")

        # Create default user groups
        print("Creating default user groups...")

        # Administrators group - full permissions
        cursor.execute("""
            INSERT INTO user_groups (name, description, created_by)
            VALUES ('Administrators', 'Full system access with all permissions', 'system')
        """)
        admin_group_id = cursor.lastrowid

        # Add all permissions to Administrators
        all_permissions = [
            'run_audits', 'view_audits',
            'modify_rules', 'view_rules', 'delete_rules',
            'modify_templates', 'view_templates', 'deploy_templates',
            'apply_fix', 'view_remediation',
            'create_users', 'modify_users', 'delete_users', 'view_users',
            'create_groups', 'modify_groups', 'delete_groups', 'view_groups',
            'create_devices', 'modify_devices', 'delete_devices', 'view_devices',
            'create_backups', 'view_backups', 'restore_backups',
            'manage_system', 'view_logs'
        ]

        for perm in all_permissions:
            cursor.execute("""
                INSERT INTO group_permissions (group_id, permission, granted)
                VALUES (?, ?, 1)
            """, (admin_group_id, perm))

        # Add all modules to Administrators
        all_modules = [
            'devices', 'device_groups', 'discovery_groups', 'device_import',
            'audit', 'audit_schedules', 'rules', 'rule_templates',
            'config_backups', 'config_templates', 'drift_detection',
            'notifications', 'health', 'integrations', 'licensing',
            'topology', 'analytics', 'admin'
        ]

        for module in all_modules:
            cursor.execute("""
                INSERT INTO group_module_access (group_id, module_name, can_access)
                VALUES (?, ?, 1)
            """, (admin_group_id, module))

        # Operators group - can run audits, apply fixes, view/modify devices
        cursor.execute("""
            INSERT INTO user_groups (name, description, created_by)
            VALUES ('Operators', 'Can run audits, apply fixes, and manage devices', 'system')
        """)
        operator_group_id = cursor.lastrowid

        operator_permissions = [
            'run_audits', 'view_audits',
            'view_rules',
            'view_templates', 'deploy_templates',
            'apply_fix', 'view_remediation',
            'create_devices', 'modify_devices', 'view_devices',
            'create_backups', 'view_backups'
        ]

        for perm in operator_permissions:
            cursor.execute("""
                INSERT INTO group_permissions (group_id, permission, granted)
                VALUES (?, ?, 1)
            """, (operator_group_id, perm))

        operator_modules = [
            'devices', 'device_groups', 'audit', 'audit_schedules',
            'rules', 'config_backups', 'config_templates', 'health'
        ]

        for module in operator_modules:
            cursor.execute("""
                INSERT INTO group_module_access (group_id, module_name, can_access)
                VALUES (?, ?, 1)
            """, (operator_group_id, module))

        # Auditors group - can only run audits and view results
        cursor.execute("""
            INSERT INTO user_groups (name, description, created_by)
            VALUES ('Auditors', 'Can run audits and view results (read-only)', 'system')
        """)
        auditor_group_id = cursor.lastrowid

        auditor_permissions = [
            'run_audits', 'view_audits',
            'view_rules',
            'view_templates',
            'view_remediation',
            'view_devices',
            'view_backups'
        ]

        for perm in auditor_permissions:
            cursor.execute("""
                INSERT INTO group_permissions (group_id, permission, granted)
                VALUES (?, ?, 1)
            """, (auditor_group_id, perm))

        auditor_modules = [
            'devices', 'audit', 'audit_schedules', 'rules',
            'config_backups', 'health', 'analytics'
        ]

        for module in auditor_modules:
            cursor.execute("""
                INSERT INTO group_module_access (group_id, module_name, can_access)
                VALUES (?, ?, 1)
            """, (auditor_group_id, module))

        # Viewers group - read-only access
        cursor.execute("""
            INSERT INTO user_groups (name, description, created_by)
            VALUES ('Viewers', 'Read-only access to view audit results and devices', 'system')
        """)
        viewer_group_id = cursor.lastrowid

        viewer_permissions = [
            'view_audits',
            'view_rules',
            'view_templates',
            'view_devices',
            'view_backups'
        ]

        for perm in viewer_permissions:
            cursor.execute("""
                INSERT INTO group_permissions (group_id, permission, granted)
                VALUES (?, ?, 1)
            """, (viewer_group_id, perm))

        viewer_modules = [
            'devices', 'audit', 'rules', 'health', 'analytics'
        ]

        for module in viewer_modules:
            cursor.execute("""
                INSERT INTO group_module_access (group_id, module_name, can_access)
                VALUES (?, ?, 1)
            """, (viewer_group_id, module))

        conn.commit()
        print("✓ Default user groups created successfully")
        print("  - Administrators (full access)")
        print("  - Operators (can run audits, apply fixes)")
        print("  - Auditors (can run audits, view results)")
        print("  - Viewers (read-only access)")

    except sqlite3.Error as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
