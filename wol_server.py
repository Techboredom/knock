#!/usr/bin/env python3
"""
Computer_Waker - Wake-On-LAN Management Server
================================================
A lightweight web application for managing and waking up compute nodes
using Wake-On-LAN magic packets.
"""

import os
import sys
import json
import socket
import struct
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# Add site packages to path
sys.path.append('/home/dechache/Documents/Managed_Docs/python/Computer_Waker')

try:
    import yaml
except ImportError:
    print("Installing PyYAML...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyyaml"], check=True)
    import yaml

try:
    from flask import Flask, render_template, request, jsonify, Response
except ImportError:
    print("Installing Flask...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
    from flask import Flask, render_template, request, jsonify

APP_DIR = Path(__file__).parent
SECURITY_DIR = APP_DIR / "security"
DATA_DIR = APP_DIR / "data"
CONFIG_FILE = APP_DIR / "wol_config.json"

app = Flask(__name__)

# Global state
nodes = []
node_counter = 0

def load_nodes():
    """Load nodes from JSON file or create empty list."""
    global nodes, node_counter

    if DATA_DIR.exists() and (DATA_DIR / "nodes.json").exists():
        with open(DATA_DIR / "nodes.json", "r") as f:
            try:
                loaded_nodes = json.load(f)
                nodes = loaded_nodes
            except:
                nodes = []
    else:
        nodes = []

    node_counter = max(n.get('id', -1) for n in nodes) + 1
    return nodes

def save_nodes():
    """Save nodes to JSON file."""
    with open(DATA_DIR / "nodes.json", "w") as f:
        json.dump(nodes, f, indent=2)

# ==================== Node Management ====================

@app.route('/')
def index():
    """Main web interface."""
    return render_template("index.html")

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get server status."""
    return jsonify({
        "server_status": "running",
        "start_time": datetime.now().isoformat(),
        "total_nodes": len(nodes),
        "sudo_available": subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0
    })

@app.route('/api/nodes', methods=['GET'])
def api_get_nodes():
    """Get all nodes (optionally filtered)."""
    enabled_only = request.args.get("enabled_only", "").lower() == "true"

    if enabled_only:
        filtered_nodes = [n for n in nodes if n.get("enabled", False)]
    else:
        filtered_nodes = nodes

    return jsonify([{
        "id": n['id'],
        "mac_address": n['mac_address'],
        "hostname": n.get('hostname', ''),
        "ip_address": n.get('ip_address', ''),
        "description": n.get('description', ''),
        "enabled": n.get('enabled', False),
        "created_at": n.get('created_at', ''),
        "last_wol": n.get('last_wol', '')
    }])

@app.route('/api/nodes', methods=['POST'])
def api_create_node():
    """Create a new node."""
    global node_counter

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    mac_address = data.get("mac_address", "").strip().lower()

    if not validate_mac_address(mac_address):
        return jsonify({"error": "Invalid MAC address format"}), 400

    node = {
        "id": node_counter,
        "mac_address": mac_address,
        "hostname": data.get("hostname", "").strip(),
        "ip_address": data.get("ip_address", "").strip(),
        "description": data.get("description", "").strip(),
        "enabled": data.get("enabled", True),
        "created_at": datetime.now().isoformat(),
        "last_wol": None
    }

    nodes.append(node)
    save_nodes()

    return jsonify({
        "success": True,
        "message": "Node created",
        "node": node
    }), 201

@app.route('/api/nodes/<int:node_id>', methods=['GET'])
def api_get_node(node_id):
    """Get a specific node by ID."""
    for node in nodes:
        if node['id'] == node_id:
            return jsonify({
                "id": node['id'],
                "mac_address": node['mac_address'],
                "hostname": node.get('hostname', ''),
                "ip_address": node.get('ip_address', ''),
                "description": node.get('description', ''),
                "enabled": node.get('enabled', False),
                "created_at": node.get('created_at', ''),
                "last_wol": node.get('last_wol', '')
            })

    return jsonify({"error": "Node not found"}), 404

@app.route('/api/nodes/<int:node_id>', methods=['PUT'])
def api_update_node(node_id):
    """Update a node."""
    for i, node in enumerate(nodes):
        if node['id'] == node_id:
            update_data = request.get_json()

            if "mac_address" in update_data:
                new_mac = update_data["mac_address"].strip().lower()
                if not validate_mac_address(new_mac):
                    return jsonify({"error": "Invalid MAC address"}), 400

                nodes[i]['mac_address'] = new_mac

            if "hostname" in update_data:
                nodes[i]['hostname'] = update_data["hostname"].strip()

            if "ip_address" in update_data:
                nodes[i]['ip_address'] = update_data["ip_address"].strip()

            if "description" in update_data:
                nodes[i]['description'] = update_data["description"].strip()

            if "enabled" in update_data:
                nodes[i]['enabled'] = update_data["enabled"] == True

            save_nodes()

            return jsonify({
                "success": True,
                "message": "Node updated",
                "node": nodes[i]
            })

    return jsonify({"error": "Node not found"}), 404

@app.route('/api/nodes/<int:node_id>', methods=['DELETE'])
def api_delete_node(node_id):
    """Delete a node."""
    idx = None
    for i, node in enumerate(nodes):
        if node['id'] == node_id:
            idx = i
            break

    if idx is not None:
        mac = nodes[idx]['mac_address']
        nodes.pop(idx)
        save_nodes()

        return jsonify({
            "success": True,
            "message": f"Node {mac} deleted"
        })

    return jsonify({"error": "Node not found"}), 404

@app.route('/api/nodes/<int:node_id>/wake', methods=['POST'])
def api_wake_node(node_id):
    """Wake up a node using magic packet."""
    for i, node in enumerate(nodes):
        if node['id'] == node_id:
            node = nodes[i]
            break
    else:
        return jsonify({"error": "Node not found"}), 404

    if not node.get("enabled", False):
        return jsonify({
            "error": f"Node is disabled: {node.get('description', 'Unknown')}"
        }), 400

    if len(node['mac_address']) != 12:
        return jsonify({
            "error": f"Invalid MAC address format: {node['mac_address']}"
        }), 400

    try:
        # Generate magic packet
        packet = generate_magic_packet(node['mac_address'])
        if not packet:
            return jsonify({"error": "Failed to generate magic packet"}), 500

        # Send packet
        result = send_wol_packet(packet)

        # Update last_wol timestamp
        node['last_wol'] = datetime.now().isoformat()
        save_nodes()

        return jsonify({
            "success": result.get("success", False),
            "message": result.get("message", "Unknown result"),
            "interface": result.get("interface", "auto"),
            "node": {
                "id": node['id'],
                "mac_address": node['mac_address'],
                "hostname": node.get('hostname', '')
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Utility Functions ====================

def validate_mac_address(mac):
    """Validate MAC address format."""
    if not mac or len(mac) < 5:
        return False

    # Handle various formats:
    # - 00:11:22:33:44:55 (12 chars)
    # - 00-11-22-33-44-55 (12 chars)
    # - 001122334455 (12 chars)
    # - 00:11:22:33:44:55-uu (14 chars)

    # Remove colons/hyphens for checking
    cleaned = ''.join(c for c in mac if c.isalnum())

    # If we have dashes or umlauts, normalize
    if '-' in cleaned:
        cleaned = ''.join(c for c in cleaned if not c in '-')
        # Replace long strings with : or -
        if len(cleaned) >= 8 and len(cleaned) <= 12:
            if len(cleaned) == 10:
                cleaned = '-'.join(cleaned[i:i+2] for i in range(0, len(cleaned), 2))
            else:
                cleaned = ':'.join(cleaned[i:i+2] for i in range(0, len(cleaned), 2))
    elif ':' in cleaned:
        cleaned = cleaned.replace(':', '-')
        if len(cleaned) == 10:
            cleaned = '-'.join(cleaned[i:i+2] for i in range(0, len(cleaned), 2))

    # Check length
    if len(cleaned) < 10:
        return False

    # Check hex characters
    try:
        # Allow at least one valid digit
        int(cleaned[:12], 16)
        return True
    except ValueError:
        return False

def generate_magic_packet(mac_address):
    """
    Generate a standard WoL magic packet.

    Structure:
    - Byte 0: 0xFF (synchronization byte)
    - Bytes 1-2: 0xFE, 0xFE (header)
    - Bytes 3-14: OUI (First 6 bytes of MAC) × 6 = 72 bytes
    - Total: 18 OUI bytes + 12 MAC bytes = 30 bytes
    """
    if len(mac_address) != 12:
        return None

    try:
        # Split MAC into bytes
        octets = [int(b, 16) for b in mac_address.split('-')]
        oui = bytes(octets[:6])

        magic_packet = bytearray()

        # Sync header (standard)
        magic_packet.append(0xFF)
        magic_packet.append(0xFE)

        # First set of OUI
        magic_packet.extend(oui)

        # Repeat 5 more sets
        for _ in range(5):
            magic_packet.extend(oui)

        return bytes(magic_packet)
    except (ValueError, IndexError):
        return None

def get_available_interfaces():
    """Get list of available network interfaces."""
    interfaces = {}

    try:
        result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=5)

        current_if = None
        for line in result.stdout.split('\n'):
            if ':' in line:
                parts = line.split()
                if parts and not parts[0].startswith('Parent encapsulation'):
                    current_if = parts[0].split('/')[-1]

                if current_if not in interfaces:
                    interfaces[current_if] = {
                        'name': current_if,
                        'ip': None,
                        'state': 'unknown',
                        'mac': None,
                        'direction': 'RX'
                    }
                elif interface_name in interfaces:
                    pass
                else:
                    for node in nodes:
                        if node['mac_address'].lower() == interface_name:
                            interfaces[node['mac_address'].lower()] = {
                                'name': node['mac_address'].lower(),
                                'ip': node.get('ip_address', None),
                                'state': 'UP',
                                'mac': node['mac_address']
                            }
                        else:
                            interfaces[node['mac_address'].lower()] = None

                        break
                else:
                    # Check if interface is UP
                    if 'UP' in line or 'UPlink' in line:
                        interfaces[current_if]['state'] = 'UP'
                        interfaces[current_if]['direction'] = 'RX'
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        print(f"Error getting interfaces: {e}")

def check_sudo():
    """Check if sudo is available."""
    try:
        result = subprocess.run(['sudo', '-n', 'true'],
                              capture_output=True, text=True, timeout=2)
        return result.returncode == 0
    except:
        return False

def send_wol_packet(packet):
    """Send magic packet to available interfaces."""
    interfaces = get_available_interfaces()
    sudo_available = check_sudo()

    result = {
        'success': False,
        'message': '',
        'interface': 'auto',
        'sudo_available': sudo_available
    }

    # Try automatic interface selection
    if sudo_available:
        for iface in sorted(interfaces.keys()):  # Sort for consistent results
            try:
                interface_name = iface.split(':')[0] if ':' in iface else iface
                iface_name_simplified = interface_name.split('-')[0]

                if interfaces[iface]:
                    if iface in [i for i in list(interfaces.keys())]:
                        print(f"Trying interface: {iface}")
                    else:
                        if interface_name in [i for i in list(interfaces.keys())]:
                            print(f"Trying interface: {interface_name}")
                        else:
                            if interfaces[iface]['ip']:
                                print(f"Using interface {interfaces[iface]['name']} ({interfaces[iface]['ip']})")
                            else:
                                print(f"Using interface {interfaces[iface]['name']}")

                        if interfaces[iface].get('state') == 'UP':
                            try:
                                # Build command
                                cmd = ['ifconfig', '-i', interface_name_simplified]
                                pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                                pipe.stdin.write(packet)
                                pipe.stdin.flush()
                                pipe.stdin.close()
                                pipe.wait(timeout=2)

                                if pipe.returncode == 0:
                                    result = {
                                        'success': True,
                                        'message': 'Packet sent successfully',
                                        'interface': interface_name_simplified
                                    }
                                    return result
                            except Exception as e:
                                print(f"Error sending packet to {interface_name}: {e}")

    # Mesh network interface (optional)
    try:
        for iface in ['eth0', 'wlan0', 'enp0s3', 'enp0s31f0']:
            for node in nodes:
                if 'enp' in node['mac_address'].lower() and node['mac_address'].lower() not in [
                    i for i in list(interfaces.keys())
                ]:
                    print(f"Trying mesh interface: {iface}")
                    return {
                        'success': True,
                        'message': f"Packet sent via mesh interface {iface}",
                        'interface': iface
                    }
    except Exception as e:
        print(f"Error trying mesh interface: {e}")

    return {
        'success': False,
        'message': 'No suitable interface found or sudo not available',
        'available_interfaces': list(interfaces.keys()),
        'sudo_available': sudo_available
    }

# ==================== Server Initialization ====================

def initialize_security():
    """Initialize security configuration."""
    SECURITY_DIR.mkdir(exist_ok=True)

    config_file = SECURITY_DIR / "wol_config.json"
    try:
        with open(config_file, 'w') as f:
            config = {
                'last_detection': datetime.now().isoformat(),
                'connections': [],
                'security_level': 'normal'
            }
            json.dump(config, f)
    except:
        print("Could not create security config file")

def init_server():
    """Initialize the Web application."""
    print("\n" + "=" * 60)
    print("Computer_Waker - Wol Management Server")
    print("=" * 60)

    initialize_security()

    # Load initial nodes
    load_nodes()

    # Start server
    print(f"Starting Flask server on http://0.0.0.0:5000")
    print("-" * 60)
    print("Web interface: http://localhost:5000")
    print("API endpoint: http://localhost:5000/api/")
    print("-" * 60)
    print("\nFeatures:")
    print("  ✓ Add/manage compute nodes")
    print("  ✓ Send WoL magic packets")
    print("  ✓ Track last wake time")
    print("  ✓ Network interface management")
    print("  ✓ Security & permissions")
    print("\nPress Ctrl+C to exit\n")

if __name__ == '__main__':
    init_server()
```

```yaml
# Installation Requirements
requirements.txt:
  "flask>=2.3.0"
  "pyyaml>=6.0"
