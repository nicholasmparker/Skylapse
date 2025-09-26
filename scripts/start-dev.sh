#!/bin/bash

# Start Skylapse services in development mode
# This script starts both capture and processing services locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if we're in the right directory
if [[ ! -d "capture" || ! -d "processing" ]]; then
    print_error "Please run this script from the skylapse project root directory"
    exit 1
fi

print_status "Starting Skylapse development environment..."

# Create necessary directories
mkdir -p /tmp/skylapse_{mock,processing,transfers/{incoming,processing,completed}}

# Set environment variables
export SKYLAPSE_ENV=development
export MOCK_CAMERA=true

# Start processing service in background
print_status "Starting processing service..."
cd processing
if [[ -f "docker-compose.yml" ]]; then
    docker-compose up -d --build
    print_success "Processing service started with Docker"
else
    print_warning "Docker Compose not found, starting processing service directly"
    if [[ -d "venv" ]]; then
        source venv/bin/activate
        PYTHONPATH="$(pwd)/src" python -m processing_service &
        PROCESSING_PID=$!
        print_success "Processing service started (PID: $PROCESSING_PID)"
    else
        print_error "No virtual environment found for processing service"
        exit 1
    fi
fi

cd ..

# Wait a moment for processing service to start
sleep 3

# Start capture service in background
print_status "Starting capture service..."
cd capture
if [[ -d "venv" ]]; then
    source venv/bin/activate
    PYTHONPATH="$(pwd)/src" python -m capture_service &
    CAPTURE_PID=$!
    print_success "Capture service started (PID: $CAPTURE_PID)"
else
    print_error "No virtual environment found for capture service"
    exit 1
fi

cd ..

# Wait for services to initialize
print_status "Waiting for services to initialize..."
sleep 5

# Check service health
print_status "Checking service health..."

# Check capture service
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    print_success "Capture service is healthy"
else
    print_warning "Capture service health check failed"
fi

# Check processing service
if curl -f http://localhost:8081/health >/dev/null 2>&1; then
    print_success "Processing service is healthy"
else
    print_warning "Processing service health check failed"
fi

print_success "Skylapse development environment started!"
echo
print_status "Service URLs:"
echo "  Capture service:    http://localhost:8080"
echo "  Processing service: http://localhost:8081"
echo
print_status "API Endpoints:"
echo "  Health checks:      curl http://localhost:8080/health"
echo "                      curl http://localhost:8081/health"
echo "  Capture status:     curl http://localhost:8080/status"
echo "  Processing status:  curl http://localhost:8081/status"
echo "  Manual capture:     curl -X POST http://localhost:8080/capture/manual"
echo
print_status "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    print_status "Stopping services..."

    # Stop capture service
    if [[ -n "$CAPTURE_PID" ]]; then
        kill $CAPTURE_PID 2>/dev/null || true
    fi

    # Stop processing service
    if [[ -n "$PROCESSING_PID" ]]; then
        kill $PROCESSING_PID 2>/dev/null || true
    fi

    # Stop Docker containers
    cd processing && docker-compose down 2>/dev/null || true
    cd ..

    print_success "Services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for user interrupt
if [[ -n "$CAPTURE_PID" ]]; then
    wait $CAPTURE_PID
elif [[ -n "$PROCESSING_PID" ]]; then
    wait $PROCESSING_PID
else
    # If using Docker, wait for containers
    cd processing
    docker-compose logs -f
fi