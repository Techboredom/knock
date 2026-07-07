#!/usr/bin/env python3
"""
Knock - Wake-On-LAN Management Server
A lightweight web application for managing and waking compute nodes
using Wake-On-LAN magic packets.
"""

import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from flask import Flask, jsonify, render_template, request
except ImportError:
    print("Installing Flask...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
    from flask import Flask, jsonify, render_template, request

APP_DIR = Path(__file__).parent
SECURITY_DIR = APP_DIR / "security"
DATA_DIR = APP_DIR / "data"

app = Flask(__name__)

nodes = []
node_counter = 0


def load_nodes():
    """Load nodes from JSON file."""
    global nodes, node_counter
    nodes_file = DATA_DIR / "nodes.json"
    if nodes_file.exists():
        with open(nodes_file) as f:
            try:
                nodes = json.load(f)
            except Exception:
                nodes = []
    else:
        nodes = []
    node_counter = max((n.get("id", -1) for n in nodes), default=-1) + 1
    return nodes


def save_nodes():
    """Save nodes to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "nodes.json", "w") as f:
        json.dump(nodes, f, indent=2)


# ==================== MAC Address Helpers ====================


def normalize_mac(mac: str) -> str:
    """Strip separators and lowercase: '00:11:22:33:44:55' → '001122334455'."""
    return mac.replace(":", "").replace("-", "").replace(".", "").lower()


def format_mac(mac: str) -> str:
    """Return MAC in xx:xx:xx:xx:xx:xx form."""
    cleaned = normalize_mac(mac)
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))


def validate_mac_address(mac: str) -> bool:
    """Return True if mac is a valid 12-hex-digit MAC in any common format."""
    if not mac:
        return False
    cleaned = normalize_mac(mac)
    if len(cleaned) != 12:
        return False
    try:
        int(cleaned, 16)
        return True
    except ValueError:
        return False


# ==================== Routes ====================


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(
        {
            "server_status": "running",
            "start_time": datetime.now().isoformat(),
            "total_nodes": len(nodes),
        }
    )


@app.route("/api/nodes", methods=["GET"])
def api_get_nodes():
    enabled_only = request.args.get("enabled_only", "").lower() == "true"
    filtered = [n for n in nodes if n.get("enabled", False)] if enabled_only else nodes
    return jsonify(filtered)


@app.route("/api/nodes", methods=["POST"])
def api_create_node():
    global node_counter
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    raw_mac = data.get("mac_address", "").strip()
    if not validate_mac_address(raw_mac):
        return jsonify({"error": "Invalid MAC address format"}), 400

    node = {
        "id": node_counter,
        "mac_address": format_mac(raw_mac),
        "hostname": data.get("hostname", "").strip(),
        "ip_address": data.get("ip_address", "").strip(),
        "description": data.get("description", "").strip(),
        "enabled": bool(data.get("enabled", True)),
        "created_at": datetime.now().isoformat(),
        "last_wol": None,
    }
    nodes.append(node)
    node_counter += 1
    save_nodes()
    return jsonify({"success": True, "message": "Node created", "node": node}), 201


@app.route("/api/nodes/<int:node_id>", methods=["GET"])
def api_get_node(node_id):
    for node in nodes:
        if node["id"] == node_id:
            return jsonify(node)
    return jsonify({"error": "Node not found"}), 404


@app.route("/api/nodes/<int:node_id>", methods=["PUT"])
def api_update_node(node_id):
    for i, node in enumerate(nodes):
        if node["id"] == node_id:
            data = request.get_json()
            if "mac_address" in data:
                new_mac = data["mac_address"].strip()
                if not validate_mac_address(new_mac):
                    return jsonify({"error": "Invalid MAC address"}), 400
                nodes[i]["mac_address"] = format_mac(new_mac)
            for field in ("hostname", "ip_address", "description"):
                if field in data:
                    nodes[i][field] = data[field].strip()
            if "enabled" in data:
                nodes[i]["enabled"] = bool(data["enabled"])
            save_nodes()
            return jsonify({"success": True, "message": "Node updated", "node": nodes[i]})
    return jsonify({"error": "Node not found"}), 404


@app.route("/api/nodes/<int:node_id>", methods=["DELETE"])
def api_delete_node(node_id):
    for i, node in enumerate(nodes):
        if node["id"] == node_id:
            mac = node["mac_address"]
            nodes.pop(i)
            save_nodes()
            return jsonify({"success": True, "message": f"Node {mac} deleted"})
    return jsonify({"error": "Node not found"}), 404


@app.route("/api/nodes/<int:node_id>/wake", methods=["POST"])
def api_wake_node(node_id):
    for i, node in enumerate(nodes):
        if node["id"] == node_id:
            break
    else:
        return jsonify({"error": "Node not found"}), 404

    if not node.get("enabled", False):
        return jsonify({"error": "Node is disabled"}), 400

    packet = generate_magic_packet(node["mac_address"])
    if not packet:
        return jsonify({"error": "Failed to generate magic packet"}), 500

    result = send_wol_packet(packet)
    nodes[i]["last_wol"] = datetime.now().isoformat()
    save_nodes()

    return jsonify(
        {
            "success": result["success"],
            "message": result["message"],
            "interface": result["interface"],
            "node": {
                "id": node["id"],
                "mac_address": node["mac_address"],
                "hostname": node.get("hostname", ""),
            },
        }
    )


@app.route("/api/interfaces", methods=["GET"])
def api_get_interfaces():
    return jsonify(list(get_available_interfaces().values()))


# ==================== Utility Functions ====================


def generate_magic_packet(mac_address: str) -> bytes | None:
    """
    Generate a standard WoL magic packet.
    Structure: 6 × 0xFF (sync stream) + target MAC repeated 16 times = 102 bytes.
    """
    cleaned = normalize_mac(mac_address)
    if len(cleaned) != 12:
        return None
    try:
        mac_bytes = bytes.fromhex(cleaned)
    except ValueError:
        return None
    return b"\xff" * 6 + mac_bytes * 16


def get_available_interfaces() -> dict:
    """Return network interfaces via psutil."""
    try:
        import psutil

        result = {}
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for name, stat in stats.items():
            ip = None
            for addr in addrs.get(name, []):
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    break
            result[name] = {
                "name": name,
                "ip": ip,
                "state": "UP" if stat.isup else "DOWN",
            }
        return result
    except Exception as e:
        print(f"Error getting interfaces: {e}")
        return {}


def send_wol_packet(packet: bytes) -> dict:
    """Send magic packet via UDP broadcast on port 9."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, ("<broadcast>", 9))
        return {
            "success": True,
            "message": "Magic packet sent via UDP broadcast",
            "interface": "broadcast",
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "interface": "none",
        }


# ==================== Server Initialization ====================


def initialize_security():
    SECURITY_DIR.mkdir(exist_ok=True)
    config_file = SECURITY_DIR / "wol_config.json"
    try:
        with open(config_file, "w") as f:
            json.dump(
                {
                    "last_detection": datetime.now().isoformat(),
                    "connections": [],
                    "security_level": "normal",
                },
                f,
            )
    except Exception:
        pass


# Run at import time so Gunicorn workers start with data loaded.
initialize_security()
load_nodes()


def init_server():
    """Start the Flask dev server (used when running directly, not via Gunicorn)."""
    host = os.environ.get("WOL_HOST", "0.0.0.0")
    port = int(os.environ.get("WOL_PORT", "5000"))
    print("\n" + "=" * 60)
    print("Knock - WoL Management Server")
    print("=" * 60)
    print(f"Web interface: http://localhost:{port}")
    print(f"API endpoint:  http://localhost:{port}/api/")
    print("=" * 60 + "\n")
    app.run(host=host, port=port)


def main():
    init_server()


if __name__ == "__main__":
    main()
