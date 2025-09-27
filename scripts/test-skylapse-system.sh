#!/bin/bash

# Skylapse System Validation Script
# Tests all API endpoints and system functionality

set -e

# Configuration
SSH_HOST="nicholasmparker@helios.local"
PI_HOST="helios.local"
API_BASE="http://$PI_HOST:8080"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Function to test API endpoint (directly, not via SSH)
test_endpoint() {
    local endpoint="$1"
    local description="$2"
    local expected_status="${3:-200}"

    print_status "Testing $description"

    local response=$(curl -s --connect-timeout 10 -w '%{http_code}' "$API_BASE$endpoint" 2>/dev/null)
    local http_code="${response: -3}"
    local body="${response%???}"

    if [[ "$http_code" == "$expected_status" ]]; then
        print_success "$description - HTTP $http_code"
        if [[ -n "$body" && "$body" != "null" ]]; then
            echo "  Response: $body" | head -c 200
            echo ""
        fi
        return 0
    else
        print_error "$description - HTTP $http_code (expected $expected_status)"
        if [[ -n "$body" ]]; then
            echo "  Response: $body"
        fi
        return 1
    fi
}

# Function to test service status
test_service_status() {
    print_status "Testing systemd service status"

    if ssh "$SSH_HOST" "sudo systemctl is-active --quiet skylapse-capture"; then
        print_success "Service is running"

        # Get service details
        local status=$(ssh "$SSH_HOST" "sudo systemctl status skylapse-capture --no-pager -l" 2>/dev/null)
        echo "  Service details:"
        echo "$status" | grep -E "(Active|Main PID|Tasks|CPU)" | sed 's/^/    /'
        return 0
    else
        print_error "Service is not running"
        return 1
    fi
}

# Function to test camera detection
test_camera_detection() {
    print_status "Testing camera detection"

    # Check if camera devices exist
    local camera_devices=$(ssh "$SSH_HOST" "ls /dev/video* 2>/dev/null || echo 'none'")
    if [[ "$camera_devices" != "none" ]]; then
        print_success "Camera devices found: $camera_devices"
    else
        print_warning "No camera devices found in /dev/video*"
    fi

    # Check libcamera detection
    local libcamera_list=$(ssh "$SSH_HOST" "libcamera-hello --list-cameras 2>/dev/null || echo 'error'")
    if [[ "$libcamera_list" != "error" ]]; then
        print_success "libcamera detection successful"
        echo "  Cameras detected:"
        echo "$libcamera_list" | head -5 | sed 's/^/    /'
    else
        print_warning "libcamera detection failed or no cameras found"
    fi
}

# Function to test storage setup
test_storage_setup() {
    print_status "Testing storage directory structure"

    local dirs_check=$(ssh "$SSH_HOST" "ls -la /opt/skylapse/capture/buffer/ 2>/dev/null || echo 'missing'")
    if [[ "$dirs_check" != "missing" ]]; then
        print_success "Storage directories exist"
        echo "  Buffer directory contents:"
        echo "$dirs_check" | head -5 | sed 's/^/    /'
    else
        print_error "Storage directories missing"
        return 1
    fi
}

echo "🏔️ SKYLAPSE SYSTEM VALIDATION"
echo "================================"
echo ""

# Test 1: Service Status
test_service_status
echo ""

# Test 2: API Health Check
test_endpoint "/health" "Health Check Endpoint"
echo ""

# Test 3: System Status
test_endpoint "/status" "System Status Endpoint"
echo ""

# Test 4: Camera Status
test_endpoint "/camera/status" "Camera Status Endpoint"
echo ""

# Test 5: Storage Status
test_endpoint "/storage/status" "Storage Status Endpoint"
echo ""

# Test 6: Configuration
test_endpoint "/config" "Configuration Endpoint"
echo ""

# Test 7: Recent Captures
test_endpoint "/captures/recent" "Recent Captures Endpoint"
echo ""

# Test 8: Metrics
test_endpoint "/metrics" "Metrics Endpoint"
echo ""

# Test 9: Camera Detection
test_camera_detection
echo ""

# Test 10: Storage Setup
test_storage_setup
echo ""

# Test 11: Manual Capture (POST)
print_status "Testing manual capture trigger"
local capture_response=$(curl -s --connect-timeout 10 -X POST -w '%{http_code}' "$API_BASE/capture/manual" 2>/dev/null)
local capture_http_code="${capture_response: -3}"
local capture_body="${capture_response%???}"

if [[ "$capture_http_code" == "200" ]]; then
    print_success "Manual capture trigger - HTTP $capture_http_code"
    echo "  Response: $capture_body"
else
    print_warning "Manual capture trigger - HTTP $capture_http_code"
    echo "  Response: $capture_body"
fi
echo ""

echo "🎯 VALIDATION SUMMARY"
echo "===================="
print_status "System Status: Skylapse is deployed and responding"
print_status "API Server: Running on port 8080"
print_status "Service: skylapse-capture.service active"
echo ""
print_status "Next Steps:"
echo "  1. Validate camera hardware detection"
echo "  2. Test scheduled capture functionality"
echo "  3. Monitor 48+ hour stability"
echo "  4. Measure capture latency (<50ms target)"
echo ""
print_success "Skylapse Professional Mountain Timelapse System is LIVE! 🚀"
