# Computer_Waker

A Python web application for Wake-On-LAN (WoL) node management. This tool allows you to remotely power on Ubuntu compute nodes using magic packets through an intuitive web interface.

## Features

- **Node Management**: Add, edit, and manage multiple compute nodes
- **Wake-On-LAN**: Send magic packets to wake up nodes from sleep
- **Network Interface Detection**: Automatically detects available network interfaces
- **Web Interface**: Clean, responsive web UI for managing nodes
- **JSON Storage**: Persistent node storage in JSON format
- **Status Monitoring**: Real-time server status and connection tracking

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install flask pyyaml
```

## Usage

### Run the Server

```bash
cd Computer_Waker
python wol_server.py
```

The web interface will be available at `http://localhost:5000`

### Manual API Usage

```bash
# List all nodes
curl http://localhost:5000/api/nodes

# Wake up a node by ID
curl -X POST http://localhost:5000/api/nodes/1/wake -H "Content-Type: application/json"

# Get status
curl http://localhost:5000/api/status
```

### Web Interface

Access the web interface in your browser:

```
Browser: http://localhost:5000
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web interface |
| GET | `/api/status` | Server status and info |
| GET | `/api/nodes` | Get all nodes |
| GET | `/api/nodes/<id>` | Get specific node |
| POST | `/api/nodes` | Create a new node |
| PUT | `/api/nodes/<id>` | Update a node |
| DELETE | `/api/nodes/<id>` | Delete a node |
| POST | `/api/nodes/<id>/wake` | Wake a node |

## Configuration

### File Structure

```
Computer_Waker/
├── wol_server.py          # Main application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── data/
│   └── nodes.json        # Node storage (auto-created)
└── security/
    └── wol_config.json   # Configuration (auto-created)
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WOL_PORT` | Server port | 5000 |
| `WOL_HOST` | Host to bind to | 0.0.0.0 |

## MAC Address Formats

This application supports multiple MAC address formats:

```
00:11:22:33:44:55
00-11-22-33-44-55
001122334455
00:11:22:33:44:55-uu
```

## Security Notes

- The application uses sudo commands to send magic packets (required on Linux)
- Sudo must be configured correctly on the server
- Node IDs are stored locally in the data directory
- No external database is used for persistence

## Troubleshooting

### Sudo Not Available

Make sure you have sudo properly configured on the server:

```bash
sudo -n true
```

### Node Not Waking

1. Verify WoL is enabled on the target machine
2. Check network connectivity
3. Verify the MAC address is correct

### Connection Issues

- Check if the server is running: `ps aux | grep wol_server`
- Ensure port 5000 is not blocked by a firewall
- Verify the server is accessible from your browser

## License

This project is free and open-source. Feel free to modify and distribute as needed.

## Author

For questions or issues, please open an issue in the repository.