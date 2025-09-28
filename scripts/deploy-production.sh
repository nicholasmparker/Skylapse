#!/bin/bash

# Skylapse Production Deployment Script
# Professional Mountain Timelapse Camera System

set -e

echo "🎬 Skylapse Production Deployment"
echo "=================================="

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
NETWORK_NAME="skylapse-network"
JWT_SECRET="${JWT_SECRET:-skylapse_jwt_$(openssl rand -hex 32)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    if ! command -v openssl &> /dev/null; then
        log_warning "OpenSSL not found - using default JWT secret"
    fi

    log_success "Prerequisites checked"
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."

    # Create .env file for production
    cat > .env << EOF
# Skylapse Production Environment Configuration
JWT_SECRET=${JWT_SECRET}
COMPOSE_PROJECT_NAME=skylapse
COMPOSE_FILE=${COMPOSE_FILE}
EOF

    log_success "Environment configured"
}

# Build and deploy
deploy_services() {
    log_info "Building and deploying services..."

    # Create network if it doesn't exist
    if ! docker network ls | grep -q ${NETWORK_NAME}; then
        log_info "Creating Docker network: ${NETWORK_NAME}"
        docker network create ${NETWORK_NAME}
    fi

    # Build and start services
    log_info "Building Docker images..."
    docker-compose -f ${COMPOSE_FILE} build

    log_info "Starting services..."
    docker-compose -f ${COMPOSE_FILE} up -d

    log_success "Services deployed"
}

# Health checks
perform_health_checks() {
    log_info "Performing health checks..."

    services=("realtime-backend:8082" "frontend:3000")

    for service_port in "${services[@]}"; do
        service=$(echo $service_port | cut -d: -f1)
        port=$(echo $service_port | cut -d: -f2)

        log_info "Checking ${service} health..."

        for i in {1..30}; do
            if curl -f http://localhost:${port}/health &> /dev/null; then
                log_success "${service} is healthy"
                break
            fi

            if [ $i -eq 30 ]; then
                log_error "${service} health check failed"
                return 1
            fi

            sleep 2
        done
    done

    log_success "All health checks passed"
}

# Display status
show_status() {
    log_info "Deployment Status:"
    echo

    docker-compose -f ${COMPOSE_FILE} ps

    echo
    log_info "Service URLs:"
    echo "  🌐 Frontend Dashboard: http://localhost:3000"
    echo "  🔗 Real-time WebSocket: ws://localhost:8082/ws"
    echo "  🏥 Health Endpoints:"
    echo "    - Real-time: http://localhost:8082/health"
    echo "    - Frontend: http://localhost:3000/health"
    echo

    log_info "Log Commands:"
    echo "  View all logs: docker-compose -f ${COMPOSE_FILE} logs -f"
    echo "  Real-time logs: docker-compose -f ${COMPOSE_FILE} logs -f realtime-backend"
    echo "  Frontend logs: docker-compose -f ${COMPOSE_FILE} logs -f frontend"
    echo

    log_info "Management Commands:"
    echo "  Stop services: docker-compose -f ${COMPOSE_FILE} down"
    echo "  Restart: docker-compose -f ${COMPOSE_FILE} restart"
    echo "  Update: ./scripts/deploy-production.sh"
}

# Cleanup function
cleanup_on_error() {
    log_error "Deployment failed. Cleaning up..."
    docker-compose -f ${COMPOSE_FILE} down
    exit 1
}

# Main deployment flow
main() {
    # Set error trap
    trap cleanup_on_error ERR

    log_info "Starting Skylapse production deployment..."

    check_prerequisites
    setup_environment
    deploy_services
    perform_health_checks
    show_status

    log_success "🚀 Skylapse production deployment completed successfully!"
    log_info "The system is now running and ready for mountain timelapse operations."
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log_info "Stopping Skylapse services..."
        docker-compose -f ${COMPOSE_FILE} down
        log_success "Services stopped"
        ;;
    "logs")
        docker-compose -f ${COMPOSE_FILE} logs -f
        ;;
    "status")
        show_status
        ;;
    "restart")
        log_info "Restarting Skylapse services..."
        docker-compose -f ${COMPOSE_FILE} restart
        log_success "Services restarted"
        ;;
    *)
        echo "Usage: $0 {deploy|stop|logs|status|restart}"
        echo "  deploy  - Deploy production system (default)"
        echo "  stop    - Stop all services"
        echo "  logs    - Show service logs"
        echo "  status  - Show system status"
        echo "  restart - Restart all services"
        exit 1
        ;;
esac
