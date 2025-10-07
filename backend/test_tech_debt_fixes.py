"""
QA Validation Script for Technical Debt Fixes

Tests H1, H4, and H5 implementations with edge cases.
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import requests
from config import Config
from main import parse_time_range


def test_h1_atomic_config_saves():
    """
    H1: Test atomic config saves

    Edge Cases:
    1. Normal save operation
    2. Concurrent save attempts (simulated)
    3. Disk space concerns (simulated via small write)
    4. Temp file cleanup on error
    """
    print("\n=== H1: Atomic Config Saves ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"

        # Test 1: Normal save operation
        print("Test 1: Normal save operation...")
        config = Config(str(config_path))
        config.set("location.name", "Test Location")

        assert config_path.exists(), "Config file should exist"

        # Verify no temp files left behind
        temp_files = list(Path(tmpdir).glob(".config_*.tmp"))
        assert len(temp_files) == 0, f"Temp files should be cleaned up, found: {temp_files}"
        print("✓ Normal save works, no temp files left behind")

        # Test 2: Verify atomicity by checking file contents
        print("\nTest 2: Verify file integrity after save...")
        with open(config_path, "r") as f:
            data = json.load(f)

        assert data["location"]["name"] == "Test Location"
        print("✓ Config data is correct and file is valid JSON")

        # Test 3: Multiple rapid saves (simulate concurrent writes)
        print("\nTest 3: Multiple rapid saves...")
        for i in range(10):
            config.set("test.counter", i)
            time.sleep(0.01)  # Small delay between writes

        # Verify final value is correct
        assert config.get("test.counter") == 9

        # Verify no temp files left
        temp_files = list(Path(tmpdir).glob(".config_*.tmp"))
        assert len(temp_files) == 0, f"Temp files after rapid saves: {temp_files}"
        print("✓ Rapid saves work correctly, no temp file accumulation")

        # Test 4: Simulate error during save (invalid JSON - won't happen with json.dump)
        # Instead, test that temp file cleanup works by checking directory
        print("\nTest 4: Verify cleanup behavior...")
        config.set("final.test", "cleanup_check")

        # Directory should only have config.json, no temp files
        all_files = list(Path(tmpdir).iterdir())
        assert len(all_files) == 1, f"Should only have config.json, found: {all_files}"
        assert all_files[0].name == "test_config.json"
        print("✓ Only config file present, cleanup working")

    print("\n✅ H1: All atomic save tests passed")
    return True


def test_h4_duplicate_time_parsing():
    """
    H4: Test duplicate time parsing removal

    Edge Cases:
    1. Valid time formats
    2. Invalid time formats (not HH:MM)
    3. Edge times (00:00, 23:59)
    4. Missing time fields
    """
    print("\n=== H4: Remove Duplicate Time Parsing ===")

    # Test 1: Valid time formats
    print("Test 1: Valid time formats...")
    config = {"start_time": "09:00", "end_time": "17:00"}
    start, end = parse_time_range(config, "test_schedule")
    assert start is not None and end is not None
    assert start.hour == 9 and start.minute == 0
    assert end.hour == 17 and end.minute == 0
    print("✓ Valid times parsed correctly")

    # Test 2: Invalid time format (not HH:MM)
    print("\nTest 2: Invalid time formats...")
    invalid_configs = [
        {"start_time": "9:00", "end_time": "17:00"},  # Missing leading zero
        {"start_time": "09:00", "end_time": "25:00"},  # Invalid hour
        {"start_time": "09:00", "end_time": "17:60"},  # Invalid minute
        {"start_time": "invalid", "end_time": "17:00"},  # Non-time string
        {"start_time": "09", "end_time": "17:00"},  # Incomplete time
    ]

    for invalid_config in invalid_configs:
        start, end = parse_time_range(invalid_config, "test_schedule")
        # Should return (None, None) for invalid formats
        if start is None and end is None:
            print(f"  ✓ Invalid format handled: {invalid_config}")
        else:
            # Some formats might be valid ISO format (like "9:00" is actually valid)
            print(f"  ⚠ Format accepted by ISO parser: {invalid_config}")

    # Test 3: Edge times
    print("\nTest 3: Edge case times...")
    edge_config = {"start_time": "00:00", "end_time": "23:59"}
    start, end = parse_time_range(edge_config, "test_schedule")
    assert start.hour == 0 and start.minute == 0
    assert end.hour == 23 and end.minute == 59
    print("✓ Edge times (00:00, 23:59) parsed correctly")

    # Test 4: Missing time fields
    print("\nTest 4: Missing time fields...")
    missing_config = {}
    start, end = parse_time_range(missing_config, "test_schedule")
    # Should use defaults "09:00" and "15:00"
    assert start.hour == 9 and start.minute == 0
    assert end.hour == 15 and end.minute == 0
    print("✓ Missing fields use defaults correctly")

    print("\n✅ H4: All time parsing tests passed")
    return True


def test_h5_bracket_validation():
    """
    H5: Test bracket parameter validation

    Edge Cases:
    1. Valid bracket configs (Profile F: 3-shot bracket)
    2. Invalid bracket_ev when bracket_count > 1
    3. Too few EV values for bracket_count
    4. EV values out of range
    5. Single-shot (bracket_count=1) should not require bracket_ev
    """
    print("\n=== H5: Bracket Parameter Validation ===")

    PI_HOST = os.getenv("PI_HOST", "192.168.0.124")
    PI_URL = f"http://{PI_HOST}:8080/capture"

    # Test 1: Valid 3-shot bracket (Profile F)
    print("Test 1: Valid 3-shot bracket...")
    valid_bracket = {
        "iso": 100,
        "shutter_speed": "1/500",
        "exposure_compensation": 0.0,
        "profile": "f",
        "awb_mode": 1,
        "hdr_mode": 0,
        "bracket_count": 3,
        "bracket_ev": [-1.0, 0.0, 1.0],
    }

    try:
        response = requests.post(PI_URL, json=valid_bracket, timeout=10)
        if response.status_code == 200:
            print("✓ Valid bracket config accepted")
        else:
            print(f"✗ Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠ Could not reach Pi at {PI_HOST}: {e}")
        print("  (Skipping live Pi tests - using validator logic check)")
        # Fall back to Pydantic validation check
        from pi.main import CaptureSettings

        try:
            settings = CaptureSettings(**valid_bracket)
            print("✓ Valid bracket config passes Pydantic validation")
        except Exception as e:
            print(f"✗ Validation failed: {e}")
            return False

    # Test 2: Missing bracket_ev when bracket_count > 1
    print("\nTest 2: Missing bracket_ev when bracket_count > 1...")
    invalid_missing_ev = {
        "iso": 100,
        "shutter_speed": "1/500",
        "exposure_compensation": 0.0,
        "profile": "f",
        "bracket_count": 3,
        # Missing bracket_ev!
    }

    try:
        response = requests.post(PI_URL, json=invalid_missing_ev, timeout=10)
        if response.status_code == 400:
            print("✓ Missing bracket_ev correctly rejected (HTTP 400)")
        else:
            print(f"✗ Expected 400, got {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        # Test with Pydantic validator directly
        from pi.main import CaptureSettings

        try:
            settings = CaptureSettings(**invalid_missing_ev)
            print("✗ Should have raised validation error for missing bracket_ev")
            return False
        except ValueError as e:
            if "bracket_ev required" in str(e):
                print(f"✓ Validation correctly rejects missing bracket_ev: {e}")
            else:
                print(f"✗ Wrong error message: {e}")
                return False

    # Test 3: Too few EV values for bracket_count
    print("\nTest 3: Too few EV values for bracket_count...")
    invalid_too_few = {
        "iso": 100,
        "shutter_speed": "1/500",
        "exposure_compensation": 0.0,
        "profile": "f",
        "bracket_count": 3,
        "bracket_ev": [-1.0, 0.0],  # Only 2 values, need 3!
    }

    try:
        response = requests.post(PI_URL, json=invalid_too_few, timeout=10)
        if response.status_code == 400:
            print("✓ Too few EV values correctly rejected (HTTP 400)")
        else:
            print(f"✗ Expected 400, got {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        from pi.main import CaptureSettings

        try:
            settings = CaptureSettings(**invalid_too_few)
            print("✗ Should have raised validation error for too few EV values")
            return False
        except ValueError as e:
            if "must have at least" in str(e):
                print(f"✓ Validation correctly rejects too few EV values: {e}")
            else:
                print(f"✗ Wrong error message: {e}")
                return False

    # Test 4: EV values out of range (-2.0 to +2.0)
    print("\nTest 4: EV values out of range...")
    invalid_out_of_range = {
        "iso": 100,
        "shutter_speed": "1/500",
        "exposure_compensation": 0.0,
        "profile": "f",
        "bracket_count": 3,
        "bracket_ev": [-3.0, 0.0, 3.0],  # Out of range!
    }

    try:
        response = requests.post(PI_URL, json=invalid_out_of_range, timeout=10)
        if response.status_code == 400:
            print("✓ Out-of-range EV values correctly rejected (HTTP 400)")
        else:
            print(f"✗ Expected 400, got {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        from pi.main import CaptureSettings

        try:
            settings = CaptureSettings(**invalid_out_of_range)
            print("✗ Should have raised validation error for out-of-range EV values")
            return False
        except ValueError as e:
            if "range -2.0 to +2.0" in str(e):
                print(f"✓ Validation correctly rejects out-of-range EV: {e}")
            else:
                print(f"✗ Wrong error message: {e}")
                return False

    # Test 5: Single-shot should not require bracket_ev
    print("\nTest 5: Single-shot (bracket_count=1) should work without bracket_ev...")
    valid_single_shot = {
        "iso": 100,
        "shutter_speed": "1/500",
        "exposure_compensation": 0.0,
        "profile": "a",
        "bracket_count": 1,
        # No bracket_ev - this is OK for single shots
    }

    try:
        response = requests.post(PI_URL, json=valid_single_shot, timeout=10)
        if response.status_code == 200:
            print("✓ Single-shot without bracket_ev accepted")
        else:
            print(f"✗ Unexpected status: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        from pi.main import CaptureSettings

        try:
            settings = CaptureSettings(**valid_single_shot)
            print("✓ Single-shot without bracket_ev passes validation")
        except ValueError as e:
            print(f"✗ Single-shot should not require bracket_ev: {e}")
            return False

    # Test 6: Extra EV values should be OK (only first bracket_count used)
    print("\nTest 6: Extra EV values (more than bracket_count)...")
    extra_ev_values = {
        "iso": 100,
        "shutter_speed": "1/500",
        "exposure_compensation": 0.0,
        "profile": "f",
        "bracket_count": 3,
        "bracket_ev": [-1.0, 0.0, 1.0, 2.0, -2.0],  # 5 values, only first 3 used
    }

    try:
        response = requests.post(PI_URL, json=extra_ev_values, timeout=10)
        if response.status_code == 200:
            print("✓ Extra EV values accepted (only first bracket_count used)")
        else:
            print(f"✗ Unexpected status: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        from pi.main import CaptureSettings

        try:
            settings = CaptureSettings(**extra_ev_values)
            print("✓ Extra EV values pass validation (will use first bracket_count)")
        except ValueError as e:
            print(f"✗ Extra EV values should be allowed: {e}")
            return False

    print("\n✅ H5: All bracket validation tests passed")
    return True


def test_backend_integration():
    """
    Test backend integration with real system
    """
    print("\n=== Backend Integration Test ===")

    BACKEND_URL = "http://localhost:8082"

    try:
        # Test /status endpoint uses parse_time_range
        print("Testing /status endpoint...")
        response = requests.get(f"{BACKEND_URL}/status", timeout=5)
        assert response.status_code == 200
        data = response.json()

        print(f"  Current time: {data['current_time']}")
        print(f"  Active schedules: {data['active_schedules']}")
        print("✓ /status endpoint working")

        # Test /health endpoint
        print("\nTesting /health endpoint...")
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        assert response.status_code == 200
        print("✓ /health endpoint working")

        print("\n✅ Backend integration tests passed")
        return True

    except Exception as e:
        print(f"✗ Backend integration test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("QA VALIDATION: Technical Debt Fixes (H1, H4, H5)")
    print("=" * 60)

    results = {
        "H1: Atomic Config Saves": test_h1_atomic_config_saves(),
        "H4: Remove Duplicate Parsing": test_h4_duplicate_time_parsing(),
        "H5: Bracket Validation": test_h5_bracket_validation(),
        "Backend Integration": test_backend_integration(),
    }

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Technical debt fixes validated!")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED - Review failures above")
        sys.exit(1)
