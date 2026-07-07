#!/bin/bash
#
# Knock - Setup and Deployment Script
# =============================================
# Easy setup script for the Wake-On-LAN web application
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Knock Setup Script         ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if already running
print_info "Checking if Knock is already running..."
if ps aux | grep -q "python.*wol_server"; then
    print_error "Knock is already running!"
    echo ""
    echo "To stop the running instance:"
    echo "  kill\$(pgrep -f wol_server)"
    echo ""
    exit 1
fi

print_success "Knock is not running"
echo ""

# WoL packets are sent via UDP broadcast — no sudo required.

# Setup environment
print_info "Setting up environment..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed!"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d',' -f1)
print_success "Python version: $PYTHON_VERSION"

# Install dependencies using UV or pip
print_info "Installing Python dependencies..."

# Check if UV is available
if uv --version &> /dev/null; then
    print_success "Using UV package manager..."
    uv sync
elif pip3 --version &> /dev/null; then
    print_success "Using pip package manager..."
    pip3 install flask psutil pyyaml python-dotenv
else
    print_error "Neither UV nor pip is available!"
    echo "Please install one of:"
    echo "  - uv (https://docs.astral.sh/uv/install/)"
    echo "  - pip3"
    exit 1
fi

print_success "Dependencies installed successfully!"
echo ""

# Create data directory
print_info "Creating data directories..."
mkdir -p data security logs

# Create sample nodes.json
if [ ! -f "data/nodes.json" ]; then
    echo "[]" > data/nodes.json
    print_success "Created empty nodes database"
fi

# Create security config
if [ ! -f "security/wol_config.json" ]; then
    echo '{"last_detection": null, "connections": [], "security_level": "normal"}' > security/wol_config.json
    print_success "Created security configuration"
fi

print_success "Directories created!"
echo ""

# Generate startup script
print_info "Generating startup script..."
cat > run.sh << 'EOF'
#!/bin/bash
# Knock Startup Script
# Run this to start the WoL server

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Starting Knock...           ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running
if ps aux | grep -q "python.*wol_server"; then
    echo -e "${YELLOW}Knock is already running${NC}"
    echo ""
    echo "To stop: kill \$(pgrep -f wol_server)"
    exit 1
fi

# Build directories first
mkdir -p data security logs

# Start the server
echo ""
echo "Knock is starting..."
echo "Web interface: http://localhost:5000"
echo ""

python3 wol_server.py &
SERVER_PID=$!

# Keep the script running
trap "kill $SERVER_PID 2>/dev/null" SIGINT SIGTERM EXIT

sleep 100
EOF

chmod +x run.sh
print_success "Created run.sh startup script"
echo ""

# Generate test script
if [ ! -f "test_wol.py" ]; then
    echo "test_wol.py already exists or not needed"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!                      ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Display usage instructions
echo "=================================="
echo "USAGE OPTIONS:"
echo "=================================="
echo ""
echo "1. Start the server:"
echo "   python3 wol_server.py"
echo ""
echo "2. Use the startup script:"
echo "   bash run.sh"
echo ""
echo "3. Test packet generation:"
echo "   python3 packet_test.py"
echo ""
echo "4. Access the web interface:"
echo "   http://localhost:5000"
echo ""
echo "5. Start server in background:"
echo "   python3 wol_server.py &"
echo ""
echo "6. Display uptime:"
echo "   ps aux | grep wol_server"
echo ""
echo "=================================="
echo ""

print_success "Knock is ready to use!"
echo ""
print_info "To stop the server, press Ctrl+C or run:"
echo "  pkill -f wol_server"
echo ""
