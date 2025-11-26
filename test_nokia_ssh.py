#!/usr/bin/env python3
"""
Test script to debug Nokia SROS SSH connection
Run this directly to see if SSH works outside the application context
"""

import sys
import paramiko
import time
import re

def test_nokia_ssh(host, port, username, password):
    """Your exact working script"""
    print(f"[TEST] Connecting to {host}:{port} as {username}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("[TEST] Attempting SSH connection...")
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False
        )
        print("[TEST] SSH connected successfully")

        print("[TEST] Creating shell channel...")
        chan = ssh.invoke_shell(term='vt100', width=200, height=200)
        print("[TEST] Shell channel created")
        time.sleep(1)

        if chan.recv_ready():
            initial = chan.recv(65535)
            print(f"[TEST] Cleared initial output: {len(initial)} bytes")

        # Disable pagination
        print("[TEST] Disabling pagination...")
        chan.send("environment more false\n")
        time.sleep(0.5)
        if chan.recv_ready():
            env_resp = chan.recv(65535)
            print(f"[TEST] Environment command response: {len(env_resp)} bytes")

        # Request full config
        print("[TEST] Requesting configuration...")
        chan.send("admin show configuration\n")
        time.sleep(2)

        output = []
        last = time.time()
        chunks = 0

        while True:
            if chan.recv_ready():
                chunk = chan.recv(65535).decode(errors="ignore")
                output.append(chunk)
                chunks += 1
                last = time.time()

                # Check for SROS prompt
                if "A:" in chunk and (">" in chunk or "#" in chunk):
                    print(f"[TEST] Found prompt in chunk {chunks}")
                    break
            else:
                # If no data for 2 seconds consider finished
                if time.time() - last > 2:
                    print(f"[TEST] No data for 2 seconds, finishing (got {chunks} chunks)")
                    break
                time.sleep(0.2)

        ssh.close()
        print("[TEST] Connection closed")

        text = "".join(output)
        print(f"[TEST] Total output: {len(text)} bytes")

        # Clean output
        text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
        text = text.replace("\r", "")

        # Skip command echo and banner
        lines = text.split("\n")
        cfg = []
        started = False
        for line in lines:
            l = line.strip()

            if not started:
                if l.startswith("#"):
                    started = True
                    cfg.append(l)
                if "admin show configuration" in l:
                    started = True
                continue

            if "A:" in l and (l.endswith(">") or l.endswith("#")):
                break

            cfg.append(l)

        config = "\n".join(cfg)
        print(f"[TEST] Extracted config: {len(config)} bytes")
        print(f"[TEST] First 500 chars:\n{config[:500]}")
        print("[TEST] SUCCESS!")
        return config

    except Exception as e:
        print(f"[TEST] FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        ssh.close()
        return None


if __name__ == "__main__":
    # Test with your Nokia SROS device
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

    print("=" * 60)
    print("Nokia SROS SSH Connection Test")
    print("=" * 60)

    result = test_nokia_ssh(HOST, PORT, USERNAME, PASSWORD)

    if result:
        print("\n[TEST] Test completed successfully!")
        sys.exit(0)
    else:
        print("\n[TEST] Test failed!")
        sys.exit(1)
