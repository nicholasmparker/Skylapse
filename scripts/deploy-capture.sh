#!/bin/bash

# Skylapse Capture Service Deployment Script - Optimized for SSH
# Uses SSH connection multiplexing to avoid multiple password prompts

set -e  # Exit on any error

# Configuration
SERVICE_NAME="skylapse-capture"
SERVICE_USER="skylapse"
INSTALL_DIR="/opt/skylapse"
LOG_DIR="/var/log/skylapse"
TARGET_HOST=""
DRY_RUN=false
FORCE_INSTALL=false

# SSH connection multiplexing settings
SSH_CONTROL_PATH="/tmp/skylapse-deploy-%r@%h:%p"
SSH_OPTS="-o ControlMaster=auto -o ControlPath=$SSH_CONTROL_PATH -o ControlPersist=300"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Skylapse capture service to Raspberry Pi (Optimized SSH)

OPTIONS:
    -t, --target HOST      Target host (e.g., nicholasmparker@helios.local)
    -d, --dry-run         Show what would be done without executing
    -f, --force           Force reinstallation even if service exists
    -h, --help           Show this help message

EXAMPLES:
    $0 --target nicholasmparker@helios.local
    $0 --target nicholasmparker@192.168.1.100 --dry-run

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET_HOST="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE_INSTALL=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$TARGET_HOST" ]]; then
    print_error "Target host is required. Use -t or --target option."
    show_usage
    exit 1
fi

print_status "Starting Skylapse capture service deployment (Optimized)"
print_status "Target: $TARGET_HOST"
print_status "Dry run: $DRY_RUN"

# Establish SSH master connection
print_status "Establishing SSH master connection..."
if ! ssh $SSH_OPTS -o ConnectTimeout=10 "$TARGET_HOST" "echo 'SSH master connection established'" >/dev/null 2>&1; then
    print_error "Cannot connect to target host: $TARGET_HOST"
    print_error "Please check SSH connectivity and try again"
    exit 1
fi

print_success "SSH master connection established (will reuse for all commands)"

# Function to execute commands (with dry-run support and SSH multiplexing)
execute_remote() {
    local cmd="$1"
    local description="$2"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "[DRY RUN] Would execute: $description"
        echo "  Command: $cmd"
    else
        print_status "$description"
        if ! ssh $SSH_OPTS "$TARGET_HOST" "$cmd"; then
            print_error "Failed to execute: $description"
            # Close SSH master connection on error
            ssh $SSH_OPTS -O exit "$TARGET_HOST" 2>/dev/null || true
            exit 1
        fi
    fi
}

# Function to copy files (with dry-run support)
copy_files() {
    local source="$1"
    local destination="$2"
    local description="$3"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "[DRY RUN] Would copy: $description"
        echo "  From: $source"
        echo "  To: $TARGET_HOST:$destination"
    else
        print_status "$description"
        if ! rsync -avz --checksum --progress -e "ssh $SSH_OPTS" "$source" "$TARGET_HOST:$destination"; then
            print_error "Failed to copy: $description"
            # Close SSH master connection on error
            ssh $SSH_OPTS -O exit "$TARGET_HOST" 2>/dev/null || true
            exit 1
        fi
    fi
}

# Check if service already exists
if ! $FORCE_INSTALL; then
    if ssh $SSH_OPTS "$TARGET_HOST" "systemctl list-unit-files | grep -q $SERVICE_NAME" 2>/dev/null; then
        print_warning "Service $SERVICE_NAME already exists on target"
        read -p "Continue with deployment? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Deployment cancelled"
            ssh $SSH_OPTS -O exit "$TARGET_HOST" 2>/dev/null || true
            exit 0
        fi
    fi
fi

# Step 1: Create system user and directories
print_status "Setting up system user and directories"

execute_remote "sudo useradd -r -s /bin/false -d $INSTALL_DIR $SERVICE_USER || true" \
    "Create service user '$SERVICE_USER'"

execute_remote "sudo usermod -a -G video,gpio,i2c,spi $SERVICE_USER" \
    "Add service user to hardware access groups"

execute_remote "sudo mkdir -p $INSTALL_DIR/{capture,buffer,logs,config,transfers}" \
    "Create installation directories"

execute_remote "sudo mkdir -p $LOG_DIR" \
    "Create log directory"

# Temporarily set ownership to deploying user for file copy
execute_remote "sudo chown -R $(whoami):$(whoami) $INSTALL_DIR" \
    "Set temporary ownership for file copy"

# Step 2: Install system dependencies
print_status "Installing system dependencies"

execute_remote "sudo apt-get update" \
    "Update package lists"

execute_remote "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-pip python3-venv python3-dev libcamera-dev libcamera-tools git rsync curl" \
    "Install required system packages"

# Step 3: Copy source code
print_status "Copying source code"

copy_files "capture/" "$INSTALL_DIR/capture/" \
    "Copy capture service source code"

copy_files "common/" "$INSTALL_DIR/common/" \
    "Copy shared middleware and utilities"

# Step 4: Set proper ownership and permissions
print_status "Setting final ownership and permissions"

execute_remote "sudo chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR $LOG_DIR" \
    "Set service user ownership"

execute_remote "sudo chmod -R 755 $INSTALL_DIR" \
    "Set directory permissions"

# Step 5: Set up Python environment
print_status "Setting up Python virtual environment"

execute_remote "cd $INSTALL_DIR/capture && sudo -u $SERVICE_USER python3 -m venv venv" \
    "Create Python virtual environment"

execute_remote "cd $INSTALL_DIR/capture && sudo -u $SERVICE_USER ./venv/bin/pip install --upgrade pip" \
    "Upgrade pip in virtual environment"

execute_remote "cd $INSTALL_DIR/capture && sudo -u $SERVICE_USER ./venv/bin/pip install -r requirements.txt" \
    "Install Python dependencies"

# Step 6: Install systemd service
print_status "Installing systemd service"

execute_remote "sudo cp $INSTALL_DIR/capture/systemd/$SERVICE_NAME.service /etc/systemd/system/" \
    "Copy systemd service file"

execute_remote "sudo systemctl daemon-reload" \
    "Reload systemd configuration"

execute_remote "sudo systemctl enable $SERVICE_NAME" \
    "Enable service for automatic startup"

# Step 7: Create transfer directories
print_status "Setting up transfer directories"

execute_remote "sudo mkdir -p /opt/skylapse/transfers/{incoming,processing,completed}" \
    "Create transfer directories"

execute_remote "sudo chown -R $SERVICE_USER:$SERVICE_USER /opt/skylapse/transfers" \
    "Set transfer directory ownership"

# Step 8: Start the service (if not dry run)
if [[ "$DRY_RUN" != "true" ]]; then
    print_status "Starting capture service"

    # Stop service if it's running
    ssh $SSH_OPTS "$TARGET_HOST" "sudo systemctl stop $SERVICE_NAME || true"

    # Clear Python cache files to ensure fresh imports
    execute_remote "find $INSTALL_DIR -name '*.pyc' -delete -o -name '__pycache__' -type d -exec rm -rf {} + || true" \
        "Clear Python cache files"

    # Reload systemd to pick up any service file changes
    execute_remote "sudo systemctl daemon-reload" \
        "Reload systemd after service file update"

    # Start the service
    execute_remote "sudo systemctl start $SERVICE_NAME" \
        "Start capture service"

    # Wait a moment for service to start
    sleep 3

    # Check service status and show logs if failed
    if ssh $SSH_OPTS "$TARGET_HOST" "sudo systemctl is-active --quiet $SERVICE_NAME"; then
        print_success "Capture service is running"

        # Check service health
        print_status "Checking service health"
        sleep 5  # Give service time to initialize

        if ssh $SSH_OPTS "$TARGET_HOST" "curl -f http://localhost:8080/health" >/dev/null 2>&1; then
            print_success "Service health check passed"
        else
            print_warning "Service health check failed - service may still be starting"
        fi
    else
        print_error "Service failed to start. Recent logs:"
        ssh $SSH_OPTS "$TARGET_HOST" "sudo journalctl -u $SERVICE_NAME --no-pager -n 10"
        print_error ""
        print_error "Full logs available with: ssh $TARGET_HOST 'sudo journalctl -fu $SERVICE_NAME'"
    fi
fi

# Step 9: Display status and next steps
print_success "Deployment completed successfully!"

if [[ "$DRY_RUN" != "true" ]]; then
    echo
    print_status "Service Management Commands:"
    echo "  Start service:   ssh $TARGET_HOST 'sudo systemctl start $SERVICE_NAME'"
    echo "  Stop service:    ssh $TARGET_HOST 'sudo systemctl stop $SERVICE_NAME'"
    echo "  Restart service: ssh $TARGET_HOST 'sudo systemctl restart $SERVICE_NAME'"
    echo "  View logs:       ssh $TARGET_HOST 'sudo journalctl -fu $SERVICE_NAME'"
    echo "  Service status:  ssh $TARGET_HOST 'sudo systemctl status $SERVICE_NAME'"
    echo
    print_status "API Endpoints:"
    echo "  Health check:    http://$TARGET_HOST:8080/health"
    echo "  Service status:  http://$TARGET_HOST:8080/status"
    echo "  Manual capture:  POST http://$TARGET_HOST:8080/capture/manual"
    echo
    print_status "Configuration files are located at:"
    echo "  System config:   $INSTALL_DIR/capture/config/system/"
    echo "  Camera config:   $INSTALL_DIR/capture/config/cameras/"
    echo
else
    print_status "Dry run completed. Use --target $TARGET_HOST without --dry-run to perform actual deployment."
fi

# Close SSH master connection
print_status "Closing SSH master connection"
ssh $SSH_OPTS -O exit "$TARGET_HOST" 2>/dev/null || true

print_success "Skylapse capture service deployment finished!"
