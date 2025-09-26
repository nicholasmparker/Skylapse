#!/bin/bash

# Skylapse Development Environment Setup
# Sets up development environment for both capture and processing services

set -e  # Exit on any error

# Configuration
INSTALL_DIR="$HOME/skylapse-dev"
DRY_RUN=false
SKIP_DEPS=false

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

Set up Skylapse development environment

OPTIONS:
    -d, --dry-run         Show what would be done without executing
    -s, --skip-deps       Skip system dependency installation
    -i, --install-dir DIR Set installation directory (default: ~/skylapse-dev)
    -h, --help           Show this help message

EXAMPLES:
    $0                           # Standard development setup
    $0 --install-dir /opt/dev    # Custom installation directory
    $0 --dry-run                 # Show what would be done

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -s|--skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        -i|--install-dir)
            INSTALL_DIR="$2"
            shift 2
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

print_status "Setting up Skylapse development environment"
print_status "Installation directory: $INSTALL_DIR"
print_status "Dry run: $DRY_RUN"

# Function to execute commands (with dry-run support)
execute_command() {
    local cmd="$1"
    local description="$2"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "[DRY RUN] Would execute: $description"
        echo "  Command: $cmd"
        return 0
    fi

    print_status "$description"
    if ! bash -c "$cmd"; then
        print_error "Failed to execute: $description"
        exit 1
    fi
}

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if command -v apt-get >/dev/null; then
        PKG_MANAGER="apt"
    elif command -v yum >/dev/null; then
        PKG_MANAGER="yum"
    else
        print_warning "Unknown Linux package manager"
        PKG_MANAGER="unknown"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    PKG_MANAGER="brew"
else
    print_warning "Unsupported operating system: $OSTYPE"
    OS="unknown"
fi

print_status "Detected OS: $OS with package manager: $PKG_MANAGER"

# Step 1: Install system dependencies
if [[ "$SKIP_DEPS" != "true" ]]; then
    print_status "Installing system dependencies"

    if [[ "$OS" == "linux" && "$PKG_MANAGER" == "apt" ]]; then
        execute_command "sudo apt-get update" "Update package lists"
        execute_command "sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential git curl rsync docker.io docker-compose" \
            "Install Linux development packages"

        # Add user to docker group
        execute_command "sudo usermod -a -G docker \$USER" "Add user to docker group"

        # For Raspberry Pi development
        if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
            execute_command "sudo apt-get install -y libcamera-dev libcamera-tools" \
                "Install Raspberry Pi camera libraries"
        fi

    elif [[ "$OS" == "macos" && "$PKG_MANAGER" == "brew" ]]; then
        if ! command -v brew >/dev/null; then
            print_warning "Homebrew not found. Installing Homebrew first..."
            execute_command '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' \
                "Install Homebrew"
        fi

        execute_command "brew install python3 git curl rsync" "Install macOS development packages"

        if ! command -v docker >/dev/null; then
            print_warning "Docker not found. Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
        fi

    else
        print_warning "Skipping system dependencies - unsupported package manager"
    fi
else
    print_status "Skipping system dependency installation"
fi

# Step 2: Create development directory structure
print_status "Creating development directory structure"

execute_command "mkdir -p $INSTALL_DIR/{capture,processing,config,data,logs,transfers/{incoming,processing,completed}}" \
    "Create development directories"

# Step 3: Set up capture service development environment
print_status "Setting up capture service development environment"

execute_command "cd $INSTALL_DIR && cp -r $(pwd)/capture ." "Copy capture service code"

execute_command "cd $INSTALL_DIR/capture && python3 -m venv venv" \
    "Create Python virtual environment for capture service"

execute_command "cd $INSTALL_DIR/capture && source venv/bin/activate && pip install --upgrade pip" \
    "Upgrade pip in capture service venv"

execute_command "cd $INSTALL_DIR/capture && source venv/bin/activate && pip install -r requirements.txt" \
    "Install capture service Python dependencies"

# Step 4: Set up processing service development environment
print_status "Setting up processing service development environment"

execute_command "cd $INSTALL_DIR && cp -r $(pwd)/processing ." "Copy processing service code"

execute_command "cd $INSTALL_DIR/processing && python3 -m venv venv" \
    "Create Python virtual environment for processing service"

execute_command "cd $INSTALL_DIR/processing && source venv/bin/activate && pip install --upgrade pip" \
    "Upgrade pip in processing service venv"

execute_command "cd $INSTALL_DIR/processing && source venv/bin/activate && pip install -r requirements.txt" \
    "Install processing service Python dependencies"

# Step 5: Copy and customize configuration files
print_status "Setting up configuration files"

execute_command "cd $INSTALL_DIR && cp -r $(pwd)/capture/config/* config/" \
    "Copy configuration files"

# Step 6: Create development scripts
print_status "Creating development helper scripts"

cat > "$INSTALL_DIR/start-capture-dev.sh" << 'EOF'
#!/bin/bash
# Start capture service in development mode

cd "$(dirname "$0")/capture"
export SKYLAPSE_ENV=development
export MOCK_CAMERA=true
export PYTHONPATH="$(pwd)/src"

echo "Starting Skylapse capture service in development mode..."
source venv/bin/activate
python -m capture_service
EOF

cat > "$INSTALL_DIR/start-processing-dev.sh" << 'EOF'
#!/bin/bash
# Start processing service in development mode

cd "$(dirname "$0")/processing"
export SKYLAPSE_ENV=development
export PYTHONPATH="$(pwd)/src"

echo "Starting Skylapse processing service in development mode..."
source venv/bin/activate
python -m processing_service
EOF

cat > "$INSTALL_DIR/run-tests.sh" << 'EOF'
#!/bin/bash
# Run tests for both services

echo "Running Skylapse test suite..."

echo "Testing capture service..."
cd "$(dirname "$0")/capture"
source venv/bin/activate
python -m pytest tests/ -v

echo "Testing processing service..."
cd "$(dirname "$0")/processing"
source venv/bin/activate
python -m pytest tests/ -v

echo "All tests completed!"
EOF

cat > "$INSTALL_DIR/docker-dev.sh" << 'EOF'
#!/bin/bash
# Start processing service with Docker for development

cd "$(dirname "$0")/processing"

echo "Starting processing service with Docker Compose..."
docker-compose -f docker-compose.yml up --build
EOF

# Make scripts executable
if [[ "$DRY_RUN" != "true" ]]; then
    chmod +x "$INSTALL_DIR"/*.sh
fi

print_success "Development helper scripts created"

# Step 7: Create VS Code settings (if VS Code is detected)
if command -v code >/dev/null; then
    print_status "Creating VS Code workspace settings"

    execute_command "mkdir -p $INSTALL_DIR/.vscode" "Create VS Code settings directory"

    cat > "$INSTALL_DIR/.vscode/settings.json" << EOF
{
    "python.defaultInterpreterPath": "./capture/venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
EOF

    cat > "$INSTALL_DIR/.vscode/launch.json" << EOF
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Capture Service",
            "type": "python",
            "request": "launch",
            "module": "capture_service",
            "cwd": "\${workspaceFolder}/capture",
            "env": {
                "PYTHONPATH": "\${workspaceFolder}/capture/src",
                "SKYLAPSE_ENV": "development",
                "MOCK_CAMERA": "true"
            },
            "console": "integratedTerminal"
        },
        {
            "name": "Processing Service",
            "type": "python",
            "request": "launch",
            "module": "processing_service",
            "cwd": "\${workspaceFolder}/processing",
            "env": {
                "PYTHONPATH": "\${workspaceFolder}/processing/src",
                "SKYLAPSE_ENV": "development"
            },
            "console": "integratedTerminal"
        }
    ]
}
EOF

    print_success "VS Code workspace configured"
fi

# Step 8: Display completion message and next steps
print_success "Development environment setup completed!"

if [[ "$DRY_RUN" != "true" ]]; then
    echo
    print_status "Development Environment Ready!"
    echo "  Location: $INSTALL_DIR"
    echo
    print_status "Available Scripts:"
    echo "  Start capture service:    $INSTALL_DIR/start-capture-dev.sh"
    echo "  Start processing service: $INSTALL_DIR/start-processing-dev.sh"
    echo "  Run tests:               $INSTALL_DIR/run-tests.sh"
    echo "  Docker processing:       $INSTALL_DIR/docker-dev.sh"
    echo
    print_status "Quick Start:"
    echo "  1. cd $INSTALL_DIR"
    echo "  2. ./start-capture-dev.sh     # Terminal 1"
    echo "  3. ./start-processing-dev.sh  # Terminal 2 (or ./docker-dev.sh)"
    echo "  4. Test: curl http://localhost:8080/health"
    echo "  5. Test: curl http://localhost:8081/health"
    echo
    if command -v code >/dev/null; then
        print_status "Open in VS Code: code $INSTALL_DIR"
        echo
    fi

    if [[ "$OS" == "linux" && "$PKG_MANAGER" == "apt" ]]; then
        print_warning "Note: You may need to log out and log back in for Docker group membership to take effect."
    fi
else
    print_status "Dry run completed. Run without --dry-run to set up development environment in $INSTALL_DIR."
fi

print_success "Skylapse development environment setup finished!"