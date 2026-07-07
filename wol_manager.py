#!/usr/bin/env python3
"""
wol_manager - CLI utility for Knock.
Interact with a running wol_server instance via HTTP.

Usage:
  wol_manager list
  wol_manager wake <node_id>
"""

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:5000"


def _get(path: str):
    with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
        return json.loads(resp.read())


def _post(path: str):
    req = urllib.request.Request(f"{BASE_URL}{path}", method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def cmd_list():
    nodes = _get("/api/nodes")
    if not nodes:
        print("No nodes configured.")
        return
    print(f"{'ID':<5} {'MAC Address':<20} {'Hostname':<20} {'Enabled'}")
    print("-" * 60)
    for n in nodes:
        print(
            f"{n['id']:<5} {n['mac_address']:<20} "
            f"{n.get('hostname', ''):<20} {n.get('enabled', False)}"
        )


def cmd_wake(node_id: int):
    result = _post(f"/api/nodes/{node_id}/wake")
    status = "OK" if result.get("success") else "FAILED"
    print(f"[{status}] {result.get('message', '')}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "list":
            cmd_list()
        elif cmd == "wake" and len(sys.argv) > 2:
            cmd_wake(int(sys.argv[2]))
        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot reach server at {BASE_URL}: {e.reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
