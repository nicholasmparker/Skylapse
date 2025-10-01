#!/bin/bash
#
# Deploy capture service to Raspberry Pi
#
# Usage:
#   ./scripts/deploy-capture.sh [pi_host]
#
# Example:
#   ./scripts/deploy-capture.sh helios.local
#

set -e

PI_HOST="${1:-helios.local}"
PI_USER="${2:-nicholasmparker}"  # Updated: actual username is nicholasmparker
REMOTE_DIR="/home/${PI_USER}/skylapse-capture"

echo "🚀 Deploying Skylapse Capture to ${PI_HOST}..."

# Check if Pi is reachable
if ! ping -c 1 "${PI_HOST}" > /dev/null 2>&1; then
    echo "❌ Error: Cannot reach ${PI_HOST}"
    echo "   Make sure the Pi is powered on and connected to the network"
    exit 1
fi

echo "✓ Pi is reachable"

# Create remote directory
echo "📁 Creating remote directory..."
ssh "${PI_USER}@${PI_HOST}" "mkdir -p ${REMOTE_DIR}"

# Copy files
echo "📦 Copying files..."
# Copy pi/ files to remote directory
rsync -av --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'test_*.py' \
    --exclude 'data/' \
    pi/ "${PI_USER}@${PI_HOST}:${REMOTE_DIR}/"

# Copy shared/ module to remote directory
rsync -av --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    shared/ "${PI_USER}@${PI_HOST}:${REMOTE_DIR}/shared/"

# Install system dependencies
echo "📥 Installing system dependencies..."
ssh "${PI_USER}@${PI_HOST}" "sudo apt-get update -qq && sudo apt-get install -y -qq libcap-dev python3-full python3-venv python3-picamera2"

# Configure GPU memory for full resolution captures (16MP requires 256MB)
echo "🎛️  Configuring GPU memory for full resolution..."
ssh "${PI_USER}@${PI_HOST}" "
    # Backup config if not already backed up
    if [ ! -f /boot/firmware/config.txt.skylapse-backup ]; then
        sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.skylapse-backup
        echo '   Created backup: config.txt.skylapse-backup'
    fi

    # Check current GPU memory
    CURRENT_GPU=\$(vcgencmd get_mem gpu | cut -d= -f2 | cut -dM -f1)
    echo \"   Current GPU memory: \${CURRENT_GPU}MB\"

    if [ \"\$CURRENT_GPU\" -lt 256 ]; then
        echo '   Setting GPU memory to 256MB for full resolution captures...'
        if grep -q '^gpu_mem=' /boot/firmware/config.txt; then
            sudo sed -i 's/^gpu_mem=.*/gpu_mem=256/' /boot/firmware/config.txt
        else
            echo 'gpu_mem=256' | sudo tee -a /boot/firmware/config.txt > /dev/null
        fi
        echo '   ⚠️  GPU memory configured - REBOOT REQUIRED'
        echo 'needs_reboot' > /tmp/skylapse-needs-reboot
    else
        echo '   ✓ GPU memory already sufficient (\${CURRENT_GPU}MB)'
    fi
"

# Set up virtual environment with system packages access (for picamera2)
echo "📥 Setting up virtual environment (with system packages)..."
ssh "${PI_USER}@${PI_HOST}" "cd ${REMOTE_DIR} && rm -rf venv && python3 -m venv --system-site-packages venv && venv/bin/pip install --upgrade pip"

# Install Python dependencies (let pip handle dependency resolution)
echo "📥 Installing Python dependencies..."
ssh "${PI_USER}@${PI_HOST}" "cd ${REMOTE_DIR} && venv/bin/pip install fastapi uvicorn pydantic pillow"

# Stop existing service if running
echo "⏹️  Stopping existing service..."
ssh "${PI_USER}@${PI_HOST}" "sudo systemctl stop skylapse-capture || true"

# Create systemd service
echo "📝 Creating systemd service..."
ssh "${PI_USER}@${PI_HOST}" "sudo tee /etc/systemd/system/skylapse-capture.service > /dev/null << 'EOF'
[Unit]
Description=Skylapse Capture Service
After=network.target

[Service]
Type=simple
User=${PI_USER}
WorkingDirectory=${REMOTE_DIR}
Environment=\"PYTHONUNBUFFERED=1\"
ExecStart=${REMOTE_DIR}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
"

# Reload systemd and start service
echo "▶️  Starting service..."
ssh "${PI_USER}@${PI_HOST}" "sudo systemctl daemon-reload"
ssh "${PI_USER}@${PI_HOST}" "sudo systemctl enable skylapse-capture"
ssh "${PI_USER}@${PI_HOST}" "sudo systemctl start skylapse-capture"

# Wait a moment for service to start
sleep 2

# Check if reboot is needed
NEEDS_REBOOT=$(ssh "${PI_USER}@${PI_HOST}" "test -f /tmp/skylapse-needs-reboot && echo 'yes' || echo 'no'")

if [ "$NEEDS_REBOOT" = "yes" ]; then
    echo ""
    echo "⚠️  ⚠️  ⚠️  REBOOT REQUIRED  ⚠️  ⚠️  ⚠️"
    echo ""
    echo "GPU memory has been increased to 256MB for full resolution captures."
    echo "The Pi must be rebooted for this change to take effect."
    echo ""
    echo "Run: ssh ${PI_USER}@${PI_HOST} 'sudo reboot'"
    echo ""
    echo "After reboot, the service will start automatically and support full 16MP captures."
    echo ""

    # Clean up reboot flag
    ssh "${PI_USER}@${PI_HOST}" "rm -f /tmp/skylapse-needs-reboot"
else
    # Check service status
    echo ""
    echo "📊 Service status:"
    ssh "${PI_USER}@${PI_HOST}" "sudo systemctl status skylapse-capture --no-pager" || true

    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Check logs: ssh ${PI_USER}@${PI_HOST} 'sudo journalctl -u skylapse-capture -f'"
    echo "  2. Test capture: curl http://${PI_HOST}:8080/status"
    echo "  3. Update backend config.json to use pi.host: ${PI_HOST}"
fi
