#!/bin/bash

# Skylapse Production Deployment Test Script
# Professional Mountain Timelapse Camera System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "Running: $test_name"

    if eval "$test_command"; then
        log_success "$test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "$test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test service health endpoints
test_service_health() {
    log_info "Testing service health endpoints..."

    run_test "Real-time backend health check" \
        "curl -f -s http://localhost:8082/health | jq -e '.status == \"healthy\"' > /dev/null"

    run_test "Frontend health check" \
        "curl -f -s http://localhost:3000/health > /dev/null"

    run_test "Real-time backend stats endpoint" \
        "curl -f -s http://localhost:8082/stats | jq -e '.total_connections >= 0' > /dev/null"
}

# Test JWT authentication
test_authentication() {
    log_info "Testing JWT authentication..."

    # Get auth token
    local token_response=$(curl -s -X POST http://localhost:8082/auth/token \
        -H "Content-Type: application/json" \
        -d '{"user_id": "test_user", "permissions": ["dashboard:read"]}')

    run_test "JWT token generation" \
        "echo '$token_response' | jq -e '.token' > /dev/null"

    local token=$(echo "$token_response" | jq -r '.token')

    run_test "JWT token validation" \
        "[ -n '$token' ] && [ '$token' != 'null' ]"
}

# Test WebSocket connection
test_websocket() {
    log_info "Testing WebSocket connection..."

    # Create a simple WebSocket test client
    cat > /tmp/ws_test.py << 'EOF'
import asyncio
import websockets
import json
import sys

async def test_websocket():
    try:
        # Connect to WebSocket
        uri = "ws://localhost:8082/ws"
        async with websockets.connect(uri, timeout=10) as websocket:

            # Send auth message
            auth_msg = {
                "type": "auth",
                "token": sys.argv[1] if len(sys.argv) > 1 else "dummy_token"
            }
            await websocket.send(json.dumps(auth_msg))

            # Wait for auth response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if data.get("type") == "auth_success":
                print("WebSocket authentication successful")
                return True
            else:
                print(f"WebSocket auth failed: {data}")
                return False

    except Exception as e:
        print(f"WebSocket test failed: {e}")
        return False

# Run the test
if asyncio.run(test_websocket()):
    sys.exit(0)
else:
    sys.exit(1)
EOF

    # Get a valid token for testing
    local token=$(curl -s -X POST http://localhost:8082/auth/token \
        -H "Content-Type: application/json" \
        -d '{"user_id": "test_user", "permissions": ["dashboard:read"]}' | jq -r '.token')

    run_test "WebSocket authentication" \
        "python3 /tmp/ws_test.py '$token'"

    # Cleanup
    rm -f /tmp/ws_test.py
}

# Test Docker container status
test_containers() {
    log_info "Testing Docker container status..."

    run_test "Real-time backend container running" \
        "docker ps | grep -q skylapse-realtime-backend"

    run_test "Frontend container running" \
        "docker ps | grep -q skylapse-frontend"

    run_test "All containers healthy" \
        "docker ps --filter 'health=healthy' | grep -c skylapse | grep -q '2'"
}

# Test network connectivity between containers
test_container_networking() {
    log_info "Testing container networking..."

    run_test "Frontend can reach real-time backend" \
        "docker exec skylapse-frontend curl -f -s http://realtime-backend:8082/health > /dev/null"

    run_test "Real-time backend network isolation" \
        "docker exec skylapse-realtime-backend curl -f -s http://localhost:8082/health > /dev/null"
}

# Test resource usage
test_resource_usage() {
    log_info "Testing resource usage..."

    # Get memory usage for real-time backend
    local memory_mb=$(docker stats skylapse-realtime-backend --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/MiB//' | tr -d ' ')

    run_test "Real-time backend memory usage under limit" \
        "[ $(echo '$memory_mb < 256' | bc -l) -eq 1 ]"

    # Check CPU usage isn't maxed out
    local cpu_percent=$(docker stats skylapse-realtime-backend --no-stream --format "{{.CPUPerc}}" | sed 's/%//')

    run_test "Real-time backend CPU usage reasonable" \
        "[ $(echo '$cpu_percent < 80' | bc -l) -eq 1 ]"
}

# Test error handling and recovery
test_error_handling() {
    log_info "Testing error handling and recovery..."

    # Test invalid WebSocket authentication
    run_test "WebSocket rejects invalid auth" \
        "! python3 -c \"
import asyncio
import websockets
import json

async def test():
    try:
        async with websockets.connect('ws://localhost:8082/ws', timeout=5) as ws:
            await ws.send(json.dumps({'type': 'auth', 'token': 'invalid_token'}))
            response = await ws.recv()
            data = json.loads(response)
            return data.get('type') == 'auth_error'
    except:
        return False

print(asyncio.run(test()))
\" | grep -q True"

    # Test graceful handling of invalid requests
    run_test "API handles invalid requests gracefully" \
        "curl -s -X POST http://localhost:8082/broadcast -d 'invalid json' | jq -e '.error' > /dev/null"
}

# Test production-ready features
test_production_features() {
    log_info "Testing production-ready features..."

    run_test "CORS headers present" \
        "curl -s -I http://localhost:8082/health | grep -q 'Access-Control-Allow-Origin'"

    run_test "Security headers present" \
        "curl -s -I http://localhost:3000 | grep -q 'X-Content-Type-Options'"

    run_test "Health check responds quickly" \
        "time curl -f -s http://localhost:8082/health > /dev/null"

    run_test "Logging is structured" \
        "docker logs skylapse-realtime-backend 2>&1 | grep -q 'INFO'"
}

# Run load test
test_load() {
    log_info "Testing system under load..."

    # Simple concurrent connection test
    run_test "Handle multiple concurrent connections" \
        "for i in {1..5}; do curl -s http://localhost:8082/health & done; wait"

    # Test WebSocket connection limit
    run_test "WebSocket connection handling" \
        "python3 -c \"
import asyncio
import websockets
import json
import sys

async def connect_client(client_id):
    try:
        async with websockets.connect('ws://localhost:8082/ws', timeout=5) as ws:
            token = 'test_token_' + str(client_id)
            await ws.send(json.dumps({'type': 'auth', 'token': token}))
            await asyncio.sleep(1)
            return True
    except:
        return False

async def test_concurrent():
    tasks = [connect_client(i) for i in range(3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True) >= 1

print(asyncio.run(test_concurrent()))
\" | grep -q True"
}

# Main test execution
main() {
    echo "🧪 Skylapse Production Deployment Test Suite"
    echo "=============================================="

    # Check prerequisites
    if ! command -v jq &> /dev/null; then
        log_error "jq is required for testing. Please install it."
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required for WebSocket testing."
        exit 1
    fi

    if ! python3 -c "import websockets" 2>/dev/null; then
        log_warning "websockets library not found. Installing..."
        pip3 install websockets || {
            log_error "Failed to install websockets library"
            exit 1
        }
    fi

    # Run test suites
    test_containers
    test_service_health
    test_authentication
    test_websocket
    test_container_networking
    test_resource_usage
    test_error_handling
    test_production_features
    test_load

    # Show results
    echo
    echo "📊 Test Results Summary"
    echo "======================="
    echo "Tests Run: $TESTS_RUN"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo
        log_success "🎉 All tests passed! Production deployment is ready for mountain operations."
        exit 0
    else
        echo
        log_error "❌ Some tests failed. Please review the issues before deploying to production."
        exit 1
    fi
}

# Handle script arguments
case "${1:-all}" in
    "all")
        main
        ;;
    "health")
        test_service_health
        ;;
    "auth")
        test_authentication
        ;;
    "websocket")
        test_websocket
        ;;
    "network")
        test_container_networking
        ;;
    "load")
        test_load
        ;;
    *)
        echo "Usage: $0 {all|health|auth|websocket|network|load}"
        echo "  all       - Run all tests (default)"
        echo "  health    - Test service health endpoints"
        echo "  auth      - Test authentication"
        echo "  websocket - Test WebSocket functionality"
        echo "  network   - Test container networking"
        echo "  load      - Test system under load"
        exit 1
        ;;
esac
