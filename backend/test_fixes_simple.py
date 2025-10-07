"""
Simplified QA Validation for Technical Debt Fixes

Tests H1, H4, and H5 implementations (no external dependencies).
"""

import json
import sys
import tempfile
import time
from datetime import datetime
from datetime import time as dt_time
from pathlib import Path

from config import Config
from main import parse_time_range


def test_h1_atomic_config_saves():
    """H1: Test atomic config saves"""
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

        # Test 2: Verify file integrity
        print("\nTest 2: Verify file integrity after save...")
        with open(config_path, "r") as f:
            data = json.load(f)

        assert data["location"]["name"] == "Test Location"
        print("✓ Config data is correct and file is valid JSON")

        # Test 3: Multiple rapid saves
        print("\nTest 3: Multiple rapid saves (atomicity test)...")
        for i in range(20):
            config.set("test.counter", i)
            time.sleep(0.005)  # Simulate rapid writes

        assert config.get("test.counter") == 19

        # Verify no temp files accumulated
        temp_files = list(Path(tmpdir).glob(".config_*.tmp"))
        assert len(temp_files) == 0, f"Temp files after rapid saves: {temp_files}"
        print("✓ Rapid saves work correctly, no temp file accumulation")

        # Test 4: Verify cleanup behavior
        print("\nTest 4: Directory cleanup check...")
        config.set("final.test", "cleanup_check")

        all_files = list(Path(tmpdir).iterdir())
        assert len(all_files) == 1, f"Should only have config.json, found: {all_files}"
        assert all_files[0].name == "test_config.json"
        print("✓ Only config file present, cleanup working")

    print("\n✅ H1: All atomic save tests passed")
    return True


def test_h4_duplicate_time_parsing():
    """H4: Test time parsing centralization"""
    print("\n=== H4: Remove Duplicate Time Parsing ===")

    # Test 1: Valid time formats
    print("Test 1: Valid time formats...")
    config = {"start_time": "09:00", "end_time": "17:00"}
    start, end = parse_time_range(config, "test_schedule")
    assert start is not None and end is not None
    assert start.hour == 9 and start.minute == 0
    assert end.hour == 17 and end.minute == 0
    print("✓ Valid times parsed correctly")

    # Test 2: Invalid time formats
    print("\nTest 2: Invalid time formats...")
    invalid_configs = [
        {"start_time": "25:00", "end_time": "17:00"},  # Invalid hour
        {"start_time": "09:00", "end_time": "17:60"},  # Invalid minute
        {"start_time": "invalid", "end_time": "17:00"},  # Non-time string
    ]

    for invalid_config in invalid_configs:
        start, end = parse_time_range(invalid_config, "test_schedule")
        # Should return (None, None) for invalid formats
        assert start is None and end is None, f"Should reject invalid config: {invalid_config}"
        print(f"  ✓ Invalid format rejected: {invalid_config}")

    # Test 3: Edge times
    print("\nTest 3: Edge case times...")
    edge_config = {"start_time": "00:00", "end_time": "23:59"}
    start, end = parse_time_range(edge_config, "test_schedule")
    assert start.hour == 0 and start.minute == 0
    assert end.hour == 23 and end.minute == 59
    print("✓ Edge times (00:00, 23:59) parsed correctly")

    # Test 4: Missing time fields (should use defaults)
    print("\nTest 4: Missing time fields...")
    missing_config = {}
    start, end = parse_time_range(missing_config, "test_schedule")
    # Should use defaults "09:00" and "15:00"
    assert start.hour == 9 and start.minute == 0
    assert end.hour == 15 and end.minute == 0
    print("✓ Missing fields use defaults correctly")

    # Test 5: Verify DRY principle - function exists and is used
    print("\nTest 5: Verify DRY principle (function centralization)...")
    import inspect

    from main import get_status, should_capture_now

    # Check that parse_time_range is defined
    assert callable(parse_time_range), "parse_time_range should be a callable function"

    # Check function signature
    sig = inspect.signature(parse_time_range)
    params = list(sig.parameters.keys())
    assert params == ["schedule_config", "schedule_name"], f"Unexpected signature: {params}"

    print("✓ parse_time_range function properly defined")

    # Verify it returns tuple
    result = parse_time_range({"start_time": "10:00", "end_time": "16:00"}, "test")
    assert isinstance(result, tuple) and len(result) == 2
    print("✓ Function returns tuple of (start_time, end_time)")

    print("\n✅ H4: All time parsing tests passed")
    return True


def test_h5_bracket_validation():
    """H5: Test bracket validation using Pydantic model"""
    print("\n=== H5: Bracket Parameter Validation ===")

    # Import the Pydantic model
    sys.path.insert(0, str(Path(__file__).parent.parent / "pi"))
    from pi.main import CaptureSettings

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
        settings = CaptureSettings(**valid_bracket)
        print("✓ Valid bracket config accepted")
    except ValueError as e:
        print(f"✗ Valid config rejected: {e}")
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
        settings = CaptureSettings(**invalid_missing_ev)
        print("✗ Should have raised validation error for missing bracket_ev")
        return False
    except ValueError as e:
        if "bracket_ev required" in str(e):
            print(f"✓ Missing bracket_ev correctly rejected: {str(e)[:80]}")
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
        settings = CaptureSettings(**invalid_too_few)
        print("✗ Should have raised validation error for too few EV values")
        return False
    except ValueError as e:
        if "must have at least" in str(e):
            print(f"✓ Too few EV values correctly rejected: {str(e)[:80]}")
        else:
            print(f"✗ Wrong error message: {e}")
            return False

    # Test 4: EV values out of range
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
        settings = CaptureSettings(**invalid_out_of_range)
        print("✗ Should have raised validation error for out-of-range EV")
        return False
    except ValueError as e:
        if "range -2.0 to +2.0" in str(e):
            print(f"✓ Out-of-range EV correctly rejected: {str(e)[:80]}")
        else:
            print(f"✗ Wrong error message: {e}")
            return False

    # Test 5: Single-shot should not require bracket_ev
    print("\nTest 5: Single-shot (bracket_count=1) without bracket_ev...")
    valid_single_shot = {
        "iso": 100,
        "shutter_speed": "1/500",
        "exposure_compensation": 0.0,
        "profile": "a",
        "bracket_count": 1,
        # No bracket_ev - this is OK
    }

    try:
        settings = CaptureSettings(**valid_single_shot)
        print("✓ Single-shot without bracket_ev accepted")
    except ValueError as e:
        print(f"✗ Single-shot should not require bracket_ev: {e}")
        return False

    # Test 6: Extra EV values should be OK
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
        settings = CaptureSettings(**extra_ev_values)
        print("✓ Extra EV values accepted (will use first bracket_count)")
    except ValueError as e:
        print(f"✗ Extra EV values should be allowed: {e}")
        return False

    print("\n✅ H5: All bracket validation tests passed")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("QA VALIDATION: Technical Debt Fixes (H1, H4, H5)")
    print("=" * 70)

    results = {
        "H1: Atomic Config Saves": test_h1_atomic_config_saves(),
        "H4: Remove Duplicate Parsing": test_h4_duplicate_time_parsing(),
        "H5: Bracket Validation": test_h5_bracket_validation(),
    }

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

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
