# Knock

A Python web application for Wake-On-LAN (WoL) node management. Add your compute nodes once, then wake them up from any browser with a single click.

## Features

- **Node Management** — Add, edit, and delete compute nodes via the web UI
- **Wake-On-LAN** — Sends a standard 102-byte magic packet via UDP broadcast (no `sudo` required)
- **Network Interface View** — Lists all host interfaces and their IP addresses
- **Persistent Storage** — Nodes saved to a local JSON file; no database needed
- **REST API** — All operations available as JSON endpoints
- **Docker support** — Production and development compose files included

## Requirements

- Python 3.10 or higher
- Dependencies: `flask`, `psutil`, `pyyaml`, `python-dotenv`

## Quick Start

### With uv (recommended)

[uv](https://docs.astral.sh/uv/) manages the virtual environment and dependencies automatically from `pyproject.toml`.

```bash
# Install uv if you don't have it
pip install uv
# or on macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create the virtual environment and install all dependencies
uv sync

# Start the server (uses the entry point defined in pyproject.toml)
uv run wol-server
```

`uv run` activates the managed environment automatically — no manual `source .venv/bin/activate` needed.

You can also drop into the environment for one-off commands:

```bash
uv run python wol_server.py          # run directly
uv run wol-manager list              # CLI utility
```

### With pip

```bash
pip install flask psutil pyyaml python-dotenv
python wol_server.py
```

The web interface will be available at `http://localhost:5000`.

### Run with Docker (production)

```bash
docker compose up -d
```

The container uses `network_mode: host` so UDP broadcast packets reach the LAN. The server listens on port 5000 of the host machine.

### Run with Docker (development)

```bash
docker compose -f docker-compose.dev.yml up
```

Source files are bind-mounted into the container — restart the container to pick up changes.

## CLI Utility

`wol_manager.py` provides a simple command-line interface for scripting:

```bash
# List all configured nodes
python wol_manager.py list

# Wake a node by ID
python wol_manager.py wake 0
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web interface |
| GET | `/api/status` | Server status |
| GET | `/api/nodes` | List all nodes |
| GET | `/api/nodes?enabled_only=true` | List enabled nodes only |
| GET | `/api/nodes/<id>` | Get a specific node |
| POST | `/api/nodes` | Create a node |
| PUT | `/api/nodes/<id>` | Update a node |
| DELETE | `/api/nodes/<id>` | Delete a node |
| POST | `/api/nodes/<id>/wake` | Send WoL magic packet |
| GET | `/api/interfaces` | List network interfaces |

### Create a node (example)

```bash
curl -X POST http://localhost:5000/api/nodes \
  -H "Content-Type: application/json" \
  -d '{"mac_address": "00:11:22:33:44:55", "hostname": "server-01", "enabled": true}'
```

### Wake a node

```bash
curl -X POST http://localhost:5000/api/nodes/0/wake
```

## Accepted MAC Address Formats

All formats are normalized to `xx:xx:xx:xx:xx:xx` on save.

```
00:11:22:33:44:55
00-11-22-33-44-55
001122334455
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WOL_HOST` | `0.0.0.0` | Interface to bind to |
| `WOL_PORT` | `5000` | Port to listen on |

## Project Structure

```
Knock_web/
├── wol_server.py          # Flask application and REST API
├── wol_manager.py         # CLI utility
├── Dockerfile
├── docker-compose.yml     # Production deployment
├── docker-compose.dev.yml # Development (live source mount)
├── pyproject.toml
├── setup.sh               # First-time setup helper
├── templates/
│   └── index.html         # Web UI
├── static/
│   ├── wol_manager.js     # Front-end logic
│   └── style.css
├── data/
│   └── nodes.json         # Auto-created on first save
└── security/
    └── wol_config.json    # Auto-created on startup
```

## How WoL Works

The server sends a 102-byte magic packet over UDP broadcast (port 9):

- **Bytes 0–5**: `0xFF × 6` (synchronisation stream)
- **Bytes 6–101**: target MAC address repeated 16 times

The target machine must have Wake-On-LAN enabled in its BIOS/UEFI and network adapter settings.

## Waking Nodes Across Subnets

By default, UDP broadcast (`255.255.255.255`) is confined to the local subnet — routers drop it. If Knock is running on a different network segment than the target machine, you need one of the following approaches.

### Option 1 — Run Knock on the same subnet

The simplest solution. Deploy a Knock instance (or just the server script) on a machine that shares a Layer 2 segment with the targets. Broadcast stays local, everything works without router changes.

```
[Browser] ──HTTP──► [Knock on 192.168.10.x] ──UDP broadcast──► [Target on 192.168.10.y]
```

### Option 2 — Directed broadcast (router/switch config)

Instead of `255.255.255.255`, send the packet to the subnet's broadcast address (e.g. `192.168.20.255` for a `/24`). Many routers can be configured to forward directed broadcasts.

**On a Cisco IOS router**, enable forwarding on the target interface:

```
interface GigabitEthernet0/1
 ip directed-broadcast
```

> ⚠️ Directed broadcast forwarding is disabled by default on most routers as it can amplify DDoS attacks (Smurf attack). Only enable it on trusted internal interfaces.

Knock currently sends to `<broadcast>` (resolved to `255.255.255.255`). To target a specific subnet broadcast instead, you can send the packet manually:

```bash
# Send a magic packet directly to a subnet broadcast address
python3 - <<'EOF'
import socket, struct
mac = "00:11:22:33:44:55"
mac_bytes = bytes.fromhex(mac.replace(":", ""))
packet = b"\xff" * 6 + mac_bytes * 16
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(packet, ("192.168.20.255", 9))   # ← target subnet broadcast
EOF
```

### Option 3 — UDP relay / WoL proxy

Run a small relay agent on the remote subnet that listens for forwarded packets and re-broadcasts them locally. Tools that do this:

| Tool | Notes |
|------|-------|
| `wol-relay` (various) | Listens on a unicast port, rebroadcasts as WoL on the local subnet |
| `wakeonlan` daemon | Can be configured to bridge segments |
| Home Assistant | Has a built-in WoL integration that can be placed per-subnet |
| OpenWrt `etherwake` | Can be triggered via SSH from Knock's host using a post-wake hook |

A typical relay setup:

```
[Knock] ──UDP unicast──► [relay on 192.168.20.x] ──UDP broadcast──► [Target on 192.168.20.y]
         port 9 / 7                                  port 9
```

### Option 4 — SSH tunnel + remote etherwake

If you have SSH access to a machine on the remote subnet, you can trigger `etherwake` or `wakeonlan` over SSH without any relay daemon:

```bash
ssh user@remote-host "wakeonlan 00:11:22:33:44:55"
# or
ssh user@remote-host "etherwake -i eth0 00:11:22:33:44:55"
```

This can be wired into a wrapper script and called from the server after the magic packet is sent, or used as the primary wake mechanism for that subnet.

### Option 5 — VLAN-aware switches with WoL passthrough

Some managed switches (Ubiquiti, Cisco SG series, HP ProCurve) support passing WoL packets between VLANs at Layer 2. This is configured on the switch itself and is transparent to Knock — no code changes needed. Check your switch documentation for "WoL across VLANs" or "magic packet forwarding".

### Option 6 — IPsec / WireGuard VPN

If the remote subnet is connected via a site-to-site VPN, the VPN gateway on the remote side is usually a machine on that subnet — install Knock there, or use the SSH method above through the VPN tunnel.

### Summary

| Approach | Router change needed | Extra software | Complexity |
|---|---|---|---|
| Run Knock on same subnet | No | No | Low |
| Directed broadcast | Yes (per interface) | No | Low–Medium |
| UDP relay agent | No | Yes (on remote host) | Medium |
| SSH + etherwake | No | `wakeonlan`/`etherwake` | Low |
| Switch WoL passthrough | Switch config | No | Low–Medium |
| VPN gateway | No | VPN (already present) | Low |

## Troubleshooting

**Node does not wake up**
1. Confirm WoL is enabled in the target machine's BIOS/UEFI.
2. Confirm WoL is enabled on the NIC (`ethtool -s <iface> wol g` on Linux).
3. Verify the MAC address is correct.
4. Ensure the server and target are on the same subnet (or that your router forwards the broadcast).

**Port 5000 already in use**
```bash
WOL_PORT=8080 python wol_server.py
```

**Server not starting in Docker**
Make sure Docker has permission to use host networking. On Linux this works by default; on macOS/Windows, Docker's virtualization layer means `network_mode: host` is not supported — run the server directly with Python instead.

## License

MIT — free to use, modify, and distribute.
