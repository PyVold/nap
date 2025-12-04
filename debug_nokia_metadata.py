#!/usr/bin/env python3
"""
Debug script to capture actual pysros response structure for Nokia SROS devices.
Run this to see what data structure pysros returns for metadata collection.
"""

import json
import sys
from pysros.management import connect

# Connection parameters - update these
HOST = "172.20.20.2"  # sros2
PORT = 830
USERNAME = "admin"
PASSWORD = "admin"

def convert_pysros_to_dict(obj):
    """Recursively convert pysros Container objects to dictionaries"""
    type_name = type(obj).__name__

    if obj is None or type_name == '_Empty':
        return {}

    if type_name == 'Container' or hasattr(obj, 'data'):
        if hasattr(obj, 'data'):
            return convert_pysros_to_dict(obj.data)
        elif isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                key = str(k) if not isinstance(k, str) else k
                result[key] = convert_pysros_to_dict(v)
            return result
        return {}

    if type_name == 'Leaf':
        return str(obj) if obj is not None else None

    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            key = str(k) if not isinstance(k, str) else k
            result[key] = convert_pysros_to_dict(v)
        return result

    if isinstance(obj, (list, tuple)):
        return [convert_pysros_to_dict(item) for item in obj]

    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    return str(obj)

def main():
    print(f"Connecting to {HOST}:{PORT}...")

    try:
        connection = connect(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            port=PORT,
            hostkey_verify=False
        )
        print("Connected successfully!\n")

        # Test paths
        paths = [
            ('/state/router[router-name="Base"]/bgp', "BGP State"),
            ('/state/system', "System State"),
            ('/state/router[router-name="Base"]/interface[interface-name="system"]', "System Interface State"),
            # Also try configure paths
            ('/configure/router[router-name="Base"]/bgp', "BGP Config"),
            ('/configure/router[router-name="Base"]/interface[interface-name="system"]', "System Interface Config"),
        ]

        for path, description in paths:
            print(f"\n{'='*60}")
            print(f"PATH: {path}")
            print(f"DESCRIPTION: {description}")
            print('='*60)

            try:
                result = connection.running.get(path)
                result_dict = convert_pysros_to_dict(result)
                print(f"RAW TYPE: {type(result).__name__}")
                print(f"CONVERTED JSON:")
                print(json.dumps(result_dict, indent=2))
            except Exception as e:
                print(f"ERROR: {e}")

        connection.disconnect()
        print("\n\nDisconnected.")

    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
