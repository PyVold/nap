#!/usr/bin/env python3
"""
Test calling the SSH connector from within the application context
"""

import sys
import asyncio

# Import from the application
from models.device import Device
from models.enums import VendorType
from connectors.ssh_connector import get_nokia_sros_config_sync

async def test_from_app(host, port, username, password):
    """Test calling the function from app context"""

    print("=" * 60)
    print("Test 1: Direct function call (sync)")
    print("=" * 60)

    try:
        config = get_nokia_sros_config_sync(host, port, username, password)
        print(f"[SUCCESS] Got config: {len(config)} bytes")
        print(f"First 500 chars:\n{config[:500]}")
        return True
    except Exception as e:
        print(f"[FAILED] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_executor(host, port, username, password):
    """Test calling via executor (how the app does it)"""

    print("\n" + "=" * 60)
    print("Test 2: Via asyncio executor (like application)")
    print("=" * 60)

    try:
        loop = asyncio.get_event_loop()
        config = await loop.run_in_executor(
            None,
            get_nokia_sros_config_sync,
            host, port, username, password
        )
        print(f"[SUCCESS] Got config: {len(config)} bytes")
        print(f"First 500 chars:\n{config[:500]}")
        return True
    except Exception as e:
        print(f"[FAILED] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    HOST = "10.10.10.10"  # Replace with your device IP
    PORT = 22
    USERNAME = "admin"    # Replace with your username
    PASSWORD = "password" # Replace with your password

    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        USERNAME = sys.argv[2]
    if len(sys.argv) > 3:
        PASSWORD = sys.argv[3]

    print("Testing Nokia SROS SSH from application context\n")

    # Run both tests
    loop = asyncio.get_event_loop()

    result1 = loop.run_until_complete(test_from_app(HOST, PORT, USERNAME, PASSWORD))
    result2 = loop.run_until_complete(test_with_executor(HOST, PORT, USERNAME, PASSWORD))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Direct call: {'PASSED' if result1 else 'FAILED'}")
    print(f"Via executor: {'PASSED' if result2 else 'FAILED'}")

    sys.exit(0 if (result1 and result2) else 1)
