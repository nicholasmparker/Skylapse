#!/bin/bash

# Profile Deployment QA Test Suite
# Comprehensive validation of profile deployment implementation

set -e

PI_HOST="helios.local:8080"
BASE_URL="http://${PI_HOST}"

echo "========================================="
echo "Profile Deployment QA Test Suite"
echo "========================================="
echo ""
echo "Target: ${BASE_URL}"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Test result function
test_result() {
    local test_name="$1"
    local status="$2"

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        ((FAILED++))
    fi
}

# Test 1: API Endpoint Testing
echo "========================================="
echo "Section 1: API Endpoint Testing"
echo "========================================="
echo ""

# Test 1.1: Profile Deployment
echo "Test 1.1: Profile Deployment"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/profile/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "test_profile_v1",
    "version": "1.0.0",
    "settings": {
      "base": {
        "metering_mode": 1,
        "awb_mode": 1,
        "exposure_compensation": 0.7,
        "iso": 400,
        "shutter_speed": "1/500"
      },
      "adaptive_wb": {
        "enabled": false
      },
      "schedule_overrides": {
        "sunset": {"exposure_compensation": 0.9}
      }
    },
    "schedules": ["sunrise", "daytime", "sunset"]
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ]; then
    test_result "Test 1.1: Profile Deployment" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 1.1: Profile Deployment" "FAIL"
    echo "Expected: 200, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 1.2: Get Current Profile
echo "Test 1.2: Get Current Profile"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/profile/current")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "test_profile_v1"; then
    test_result "Test 1.2: Get Current Profile" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 1.2: Get Current Profile" "FAIL"
    echo "Expected: 200 with profile_id, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 1.3: Status with Profile
echo "Test 1.3: Status with Profile"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/status")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "deployed_profile" && echo "$BODY" | grep -q "deployed_profile"; then
    test_result "Test 1.3: Status with Profile" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 1.3: Status with Profile" "FAIL"
    echo "Expected: deployed_profile in status"
    echo "Response: $BODY"
fi
echo ""

# Test 2: Capture Mode Testing
echo "========================================="
echo "Section 2: Capture Mode Testing"
echo "========================================="
echo ""

# Test 2.1: Mode 1 - Explicit Settings
echo "Test 2.1: Mode 1 - Explicit Settings (Backward Compatibility)"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/capture" \
  -H "Content-Type: application/json" \
  -d '{
    "iso": 400,
    "shutter_speed": "1/500",
    "exposure_compensation": 0.5,
    "profile": "test"
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "success"; then
    test_result "Test 2.1: Explicit Settings Mode" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 2.1: Explicit Settings Mode" "FAIL"
    echo "Expected: 200 success, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 2.2: Mode 2 - Clear Profile First
echo "Test 2.2a: Clear Profile for Mode 2 test"
curl -s -X DELETE "${BASE_URL}/profile/current" > /dev/null
echo "Profile cleared"
echo ""

# Test 2.2b: Mode 2 - Deployed Profile (No Profile)
echo "Test 2.2b: Mode 2 - Deployed Profile (No Profile)"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/capture" \
  -H "Content-Type: application/json" \
  -d '{
    "use_deployed_profile": true,
    "schedule_type": "sunset"
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "400" ] && echo "$BODY" | grep -q "No profile deployed"; then
    test_result "Test 2.2b: Mode 2 Error Handling" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 2.2b: Mode 2 Error Handling" "FAIL"
    echo "Expected: 400 'No profile deployed', Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 2.3: Redeploy Profile for Mode 2 test
echo "Test 2.3a: Redeploy Profile for Mode 2 test"
curl -s -X POST "${BASE_URL}/profile/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "test_profile_v1",
    "version": "1.0.0",
    "settings": {
      "base": {
        "metering_mode": 1,
        "awb_mode": 1,
        "exposure_compensation": 0.7,
        "iso": 400,
        "shutter_speed": "1/500"
      },
      "adaptive_wb": {
        "enabled": false
      },
      "schedule_overrides": {
        "sunset": {"exposure_compensation": 0.9}
      }
    },
    "schedules": ["sunrise", "daytime", "sunset"]
  }' > /dev/null
echo "Profile redeployed"
echo ""

# Test 2.3b: Mode 2 - Deployed Profile (With Profile)
echo "Test 2.3b: Mode 2 - Deployed Profile (With Profile)"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/capture" \
  -H "Content-Type: application/json" \
  -d '{
    "use_deployed_profile": true,
    "schedule_type": "sunset"
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "success"; then
    test_result "Test 2.3b: Mode 2 Profile Execution" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 2.3b: Mode 2 Profile Execution" "FAIL"
    echo "Expected: 200 success, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 2.4: Mode 3 - Override Testing
echo "Test 2.4: Mode 3 - Override Testing"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/capture" \
  -H "Content-Type: application/json" \
  -d '{
    "use_deployed_profile": true,
    "schedule_type": "sunset",
    "override": {
      "exposure_compensation": 1.0
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "success"; then
    test_result "Test 2.4: Mode 3 Override Testing" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 2.4: Mode 3 Override Testing" "FAIL"
    echo "Expected: 200 success, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 3: Error Handling Testing
echo "========================================="
echo "Section 3: Error Handling Testing"
echo "========================================="
echo ""

# Test 3.1: Invalid Profile Deployment
echo "Test 3.1: Invalid Profile Deployment"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/profile/deploy" \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "400" ]; then
    test_result "Test 3.1: Invalid Profile Validation" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 3.1: Invalid Profile Validation" "FAIL"
    echo "Expected: 422 or 400, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 3.2: Missing schedule_type (should default to daytime)
echo "Test 3.2: Missing schedule_type (defaults to daytime)"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/capture" \
  -H "Content-Type: application/json" \
  -d '{
    "use_deployed_profile": true
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "success"; then
    test_result "Test 3.2: Default schedule_type" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 3.2: Default schedule_type" "FAIL"
    echo "Expected: 200 success with default schedule, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 4: Backward Compatibility Testing
echo "========================================="
echo "Section 4: Backward Compatibility Testing"
echo "========================================="
echo ""

# Test 4.1: ISO=0 Auto Mode
echo "Test 4.1: ISO=0 Auto Mode"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/capture" \
  -H "Content-Type: application/json" \
  -d '{
    "iso": 0,
    "shutter_speed": "auto",
    "exposure_compensation": 0.0,
    "awb_mode": 0,
    "ae_metering_mode": 0,
    "profile": "test"
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "success"; then
    test_result "Test 4.1: ISO=0 Auto Mode" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 4.1: ISO=0 Auto Mode" "FAIL"
    echo "Expected: 200 success, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 5: Profile Lifecycle Testing
echo "========================================="
echo "Section 5: Profile Lifecycle Testing"
echo "========================================="
echo ""

# Test 5.1: Clear Profile
echo "Test 5.1: Clear Profile (DELETE /profile/current)"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X DELETE "${BASE_URL}/profile/current")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "cleared"; then
    test_result "Test 5.1: Clear Profile" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 5.1: Clear Profile" "FAIL"
    echo "Expected: 200 cleared, Got: $HTTP_CODE"
    echo "Response: $BODY"
fi
echo ""

# Test 5.2: Verify Reversion to Live Mode
echo "Test 5.2: Verify Reversion to Live Orchestration Mode"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/status")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "live_orchestration"; then
    test_result "Test 5.2: Reversion to Live Mode" "PASS"
    echo "Response: $BODY"
else
    test_result "Test 5.2: Reversion to Live Mode" "FAIL"
    echo "Expected: live_orchestration in status"
    echo "Response: $BODY"
fi
echo ""

# Final Summary
echo "========================================="
echo "QA Test Suite Summary"
echo "========================================="
echo ""
echo -e "${GREEN}PASSED: ${PASSED}${NC}"
echo -e "${RED}FAILED: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
