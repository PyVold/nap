#!/usr/bin/env python3
"""
Initialize database with all tables
Run this from the network-audit-platform-main directory
"""
import sys
import os

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

from database import init_db
from models.config_templates import ConfigTemplate, TemplateDeployment

print(f"Working directory: {os.getcwd()}")
print("Initializing database with all tables...")

init_db()

print("✓ Database initialized successfully")
print(f"✓ Database location: {os.path.join(os.getcwd(), 'network_audit.db')}")

# Verify config_templates table
import sqlite3
conn = sqlite3.connect('network_audit.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config_templates'")
if cursor.fetchone():
    cursor.execute("PRAGMA table_info(config_templates)")
    columns = cursor.fetchall()
    xpath_exists = any(col[1] == 'xpath' for col in columns)
    if xpath_exists:
        print("✓ config_templates table created with xpath column")
    else:
        print("✗ ERROR: xpath column missing!")
else:
    print("✗ ERROR: config_templates table not created!")

conn.close()
