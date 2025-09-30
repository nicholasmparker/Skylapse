"""
Test script to validate Pi capture logic locally.
"""

import os
import sys

# Set mock mode
os.environ["MOCK_CAMERA"] = "true"

from main import CaptureSettings, parse_shutter_speed


def test_parse_shutter_speed():
    """Test shutter speed parsing"""
    print("\n=== Testing Shutter Speed Parsing ===")

    tests = [
        ("1/1000", 1000),
        ("1/500", 2000),
        ("1/250", 4000),
        ("1/125", 8000),
        ("0.5", 500000),
    ]

    for shutter_str, expected_us in tests:
        result = parse_shutter_speed(shutter_str)
        status = "✓" if result == expected_us else "✗"
        print(f"{status} {shutter_str} → {result}μs (expected {expected_us}μs)")


def test_settings_validation():
    """Test camera settings validation"""
    print("\n=== Testing Settings Validation ===")

    # Valid settings
    try:
        settings = CaptureSettings(iso=400, shutter_speed="1/1000", exposure_compensation=0.7)
        print(
            f"✓ Valid settings: ISO {settings.iso}, {settings.shutter_speed}, EV{settings.exposure_compensation:+.1f}"
        )
    except Exception as e:
        print(f"✗ Valid settings failed: {e}")

    # Invalid ISO
    try:
        settings = CaptureSettings(
            iso=300, shutter_speed="1/1000", exposure_compensation=0.7  # Invalid
        )
        print(f"✗ Invalid ISO should have failed but didn't")
    except ValueError as e:
        print(f"✓ Invalid ISO correctly rejected: {e}")

    # Invalid EV
    try:
        settings = CaptureSettings(
            iso=400, shutter_speed="1/1000", exposure_compensation=5.0  # Invalid
        )
        print(f"✗ Invalid EV should have failed but didn't")
    except ValueError as e:
        print(f"✓ Invalid EV correctly rejected: {e}")


if __name__ == "__main__":
    print("Testing Pi Capture Logic")
    print("=" * 50)

    test_parse_shutter_speed()
    test_settings_validation()

    print("\n" + "=" * 50)
    print("All tests completed!")
