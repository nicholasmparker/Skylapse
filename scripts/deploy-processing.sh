#!/bin/bash

# Skylapse Processing Service Deployment Script
# Deploys the Docker-based processing service

set -e  # Exit on any error

# Configuration
SERVICE_NAME="skylapse-processing"
COMPOSE_FILE="docker-compose.yml"
TARGET_HOST=""
DRY_RUN=false
FORCE_REBUILD=false
ENVIRONMENT="production"

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

Deploy Skylapse processing service using Docker Compose

OPTIONS:
    -t, --target HOST      Target host (optional, defaults to local)
    -e, --environment ENV  Environment (development|production, default: production)
    -d, --dry-run         Show what would be done without executing
    -r, --rebuild         Force rebuild of Docker images
    -h, --help           Show this help message

EXAMPLES:
    $0                                    # Deploy locally
    $0 --target user@processing-server    # Deploy to remote host
    $0 --environment development --rebuild # Development deployment with rebuild
    $0 --dry-run                         # Show deployment plan

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET_HOST="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -r|--rebuild)
            FORCE_REBUILD=true
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

print_status "Starting Skylapse processing service deployment"
print_status "Environment: $ENVIRONMENT"
print_status "Dry run: $DRY_RUN"

if [[ -n "$TARGET_HOST" ]]; then
    print_status "Target: $TARGET_HOST"

    # Check if we can connect to target
    if ! ssh -o ConnectTimeout=10 "$TARGET_HOST" "echo 'Connection test'" >/dev/null 2>&1; then
        print_error "Cannot connect to target host: $TARGET_HOST"
        print_error "Please check SSH connectivity and try again"
        exit 1
    fi

    print_success "SSH connection to target established"
else
    print_status "Target: localhost"
fi

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
    if [[ -n "$TARGET_HOST" ]]; then
        if ! ssh "$TARGET_HOST" "$cmd"; then
            print_error "Failed to execute: $description"
            exit 1
        fi
    else
        if ! bash -c "$cmd"; then
            print_error "Failed to execute: $description"
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
        if [[ -n "$TARGET_HOST" ]]; then
            echo "  To: $TARGET_HOST:$destination"
        else
            echo "  To: $destination"
        fi
        return 0
    fi

    print_status "$description"
    if [[ -n "$TARGET_HOST" ]]; then
        if ! rsync -avz --progress "$source" "$TARGET_HOST:$destination"; then
            print_error "Failed to copy: $description"
            exit 1
        fi
    else
        if ! cp -r "$source" "$destination"; then
            print_error "Failed to copy: $description"
            exit 1
        fi
    fi
}

# Step 1: Check Docker availability
print_status "Checking Docker availability"

execute_command "docker --version" "Check Docker installation"
execute_command "docker-compose --version || docker compose version" "Check Docker Compose installation"

# Step 2: Create deployment directory
DEPLOY_DIR="/opt/skylapse/processing"

execute_command "sudo mkdir -p $DEPLOY_DIR" "Create deployment directory"

execute_command "sudo mkdir -p /opt/skylapse/processing/data /opt/skylapse/processing/logs /opt/skylapse/transfers/{incoming,processing,completed}" \
    "Create data and log directories"

# Step 3: Copy processing service files
print_status "Copying processing service files"

if [[ -n "$TARGET_HOST" ]]; then
    copy_files "processing/" "$DEPLOY_DIR/" "Copy processing service files"
else
    copy_files "processing/*" "$DEPLOY_DIR/" "Copy processing service files"
fi

# Step 4: Set up environment-specific configuration
print_status "Setting up environment configuration"

if [[ "$ENVIRONMENT" == "development" ]]; then
    COMPOSE_FILE="docker-compose.yml"
    print_status "Using development configuration"
elif [[ "$ENVIRONMENT" == "production" ]]; then
    COMPOSE_FILE="docker-compose.yml"
    print_status "Using production configuration"
else
    print_error "Unknown environment: $ENVIRONMENT"
    exit 1
fi

# Step 5: Stop existing services
print_status "Stopping existing services"

execute_command "cd $DEPLOY_DIR && (docker-compose down || docker compose down || true)" \
    "Stop existing containers"

# Step 6: Build/pull images
if [[ "$FORCE_REBUILD" == "true" ]]; then
    print_status "Building Docker images (forced rebuild)"

    execute_command "cd $DEPLOY_DIR && (docker-compose build --no-cache || docker compose build --no-cache)" \
        "Build Docker images with no cache"
else
    print_status "Building/updating Docker images"

    execute_command "cd $DEPLOY_DIR && (docker-compose build || docker compose build)" \
        "Build Docker images"
fi

# Step 7: Start services
if [[ "$DRY_RUN" != "true" ]]; then
    print_status "Starting processing services"

    # Start services in detached mode
    execute_command "cd $DEPLOY_DIR && (docker-compose up -d || docker compose up -d)" \
        "Start processing service containers"

    # Wait for services to start
    print_status "Waiting for services to initialize..."
    sleep 10

    # Check if containers are running
    if [[ -n "$TARGET_HOST" ]]; then
        CONTAINER_STATUS=$(ssh "$TARGET_HOST" "cd $DEPLOY_DIR && docker-compose ps -q | wc -l")
    else
        CONTAINER_STATUS=$(cd "$DEPLOY_DIR" && docker-compose ps -q | wc -l)
    fi

    if [[ "$CONTAINER_STATUS" -gt 0 ]]; then
        print_success "Processing service containers are running"
    else
        print_error "No containers are running. Check logs with:"
        if [[ -n "$TARGET_HOST" ]]; then
            print_error "ssh $TARGET_HOST 'cd $DEPLOY_DIR && docker-compose logs'"
        else
            print_error "cd $DEPLOY_DIR && docker-compose logs"
        fi
        exit 1
    fi

    # Health check
    print_status "Checking service health"
    sleep 5  # Give service time to initialize

    HEALTH_CHECK_HOST="localhost"
    if [[ -n "$TARGET_HOST" ]]; then
        HEALTH_CHECK_HOST=$(echo "$TARGET_HOST" | cut -d'@' -f2)
    fi

    if curl -f "http://$HEALTH_CHECK_HOST:8081/health" >/dev/null 2>&1; then
        print_success "Service health check passed"
    else
        print_warning "Service health check failed - service may still be starting"
        print_status "Checking container logs..."

        if [[ -n "$TARGET_HOST" ]]; then
            ssh "$TARGET_HOST" "cd $DEPLOY_DIR && docker-compose logs --tail=20"
        else
            cd "$DEPLOY_DIR" && docker-compose logs --tail=20
        fi
    fi
fi

# Step 8: Display status and next steps
print_success "Deployment completed successfully!"

if [[ "$DRY_RUN" != "true" ]]; then
    echo
    print_status "Service Management Commands:"
    if [[ -n "$TARGET_HOST" ]]; then
        echo "  View logs:       ssh $TARGET_HOST 'cd $DEPLOY_DIR && docker-compose logs -f'"
        echo "  Stop service:    ssh $TARGET_HOST 'cd $DEPLOY_DIR && docker-compose down'"
        echo "  Restart service: ssh $TARGET_HOST 'cd $DEPLOY_DIR && docker-compose restart'"
        echo "  View status:     ssh $TARGET_HOST 'cd $DEPLOY_DIR && docker-compose ps'"
    else
        echo "  View logs:       cd $DEPLOY_DIR && docker-compose logs -f"
        echo "  Stop service:    cd $DEPLOY_DIR && docker-compose down"
        echo "  Restart service: cd $DEPLOY_DIR && docker-compose restart"
        echo "  View status:     cd $DEPLOY_DIR && docker-compose ps"
    fi
    echo
    print_status "API Endpoints:"
    ENDPOINT_HOST="$HEALTH_CHECK_HOST"
    echo "  Health check:    http://$ENDPOINT_HOST:8081/health"
    echo "  Service status:  http://$ENDPOINT_HOST:8081/status"
    echo "  Job management:  http://$ENDPOINT_HOST:8081/jobs"
    echo "  Process images:  POST http://$ENDPOINT_HOST:8081/process/images"
    echo
    print_status "Data directories:"
    echo "  Processing data: $DEPLOY_DIR/data/"
    echo "  Logs:           $DEPLOY_DIR/logs/"
    echo "  Transfers:      /opt/skylapse/transfers/"
    echo
else
    DEPLOY_TARGET="localhost"
    if [[ -n "$TARGET_HOST" ]]; then
        DEPLOY_TARGET="$TARGET_HOST"
    fi
    print_status "Dry run completed. Run without --dry-run to perform actual deployment to $DEPLOY_TARGET."
fi

print_success "Skylapse processing service deployment finished!"
