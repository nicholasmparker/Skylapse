#!/bin/bash
# Skylapse Docker Compose Management Script
# Simplifies deployment across different environments

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
check_env() {
    if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
        log_warning ".env file not found. Using default values."
        log_info "Copy .env.example to .env and customize for your environment."
    fi
}

# Show usage
show_usage() {
    cat << EOF
Skylapse Docker Compose Management

Usage: $0 <command> [options]

Commands:
    dev                 Start development environment (frontend-dev + processing + redis)
    prod                Start production environment (all services)
    capture             Start with capture service enabled
    monitoring          Start with monitoring services (Prometheus + Grafana)

    stop                Stop all services
    down                Stop and remove all containers
    logs                Show logs for all services
    logs <service>      Show logs for specific service

    build               Build all images
    pull                Pull latest images

    status              Show status of all services
    health              Show health status of services

    clean               Remove all containers, networks, and volumes (DESTRUCTIVE)

Examples:
    $0 dev              # Start development environment
    $0 prod             # Start production environment
    $0 capture          # Start with capture service
    $0 logs processing  # Show processing service logs
    $0 status           # Show service status

EOF
}

# Main command handling
case "${1:-}" in
    "dev")
        check_env
        log_info "Starting Skylapse development environment..."
        docker compose --profile development up -d
        log_success "Development environment started!"
        log_info "Frontend (dev): http://localhost:3000"
        log_info "Processing API: http://localhost:8081"
        log_info "Redis: localhost:6379"
        ;;

    "prod")
        check_env
        log_info "Starting Skylapse production environment..."
        docker compose --profile production up -d
        log_success "Production environment started!"
        log_info "Frontend: http://localhost:3000"
        log_info "Processing API: http://localhost:8081"
        log_info "Database: localhost:5432"
        ;;

    "capture")
        check_env
        log_info "Starting Skylapse with capture service..."
        docker compose --profile development --profile capture up -d
        log_success "Skylapse with capture started!"
        log_info "Frontend (dev): http://localhost:3000"
        log_info "Processing API: http://localhost:8081"
        log_info "Capture API: http://localhost:8080"
        ;;

    "monitoring")
        check_env
        log_info "Starting Skylapse with monitoring..."
        docker compose --profile production --profile monitoring up -d
        log_success "Skylapse with monitoring started!"
        log_info "Frontend: http://localhost:3000"
        log_info "Prometheus: http://localhost:9090"
        log_info "Grafana: http://localhost:3001"
        ;;

    "stop")
        log_info "Stopping all Skylapse services..."
        docker compose stop
        log_success "All services stopped!"
        ;;

    "down")
        log_info "Stopping and removing all Skylapse containers..."
        docker compose down
        log_success "All containers removed!"
        ;;

    "logs")
        if [[ -n "${2:-}" ]]; then
            docker compose logs -f "$2"
        else
            docker compose logs -f
        fi
        ;;

    "build")
        log_info "Building all Skylapse images..."
        docker compose build
        log_success "All images built!"
        ;;

    "pull")
        log_info "Pulling latest images..."
        docker compose pull
        log_success "Images updated!"
        ;;

    "status")
        log_info "Skylapse service status:"
        docker compose ps
        ;;

    "health")
        log_info "Health check status:"
        docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        ;;

    "clean")
        log_warning "This will remove ALL containers, networks, and volumes!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Cleaning up all Skylapse resources..."
            docker compose down -v --remove-orphans
            docker system prune -f
            log_success "Cleanup complete!"
        else
            log_info "Cleanup cancelled."
        fi
        ;;

    *)
        show_usage
        exit 1
        ;;
esac
