#!/usr/bin/env python3
"""
Test script for profile execution modes.

Tests all three capture modes:
1. Explicit settings (backward compatible)
2. Deployed profile execution
3. Override mode for testing
"""

import json
from pprint import pprint

import requests

# Pi capture service URL
PI_URL = "http://localhost:8080"  # Change to helios.local:8080 for real Pi


def test_mode_1_explicit():
    """Test Mode 1: Explicit settings (backward compatible)"""
    print("\n" + "=" * 70)
    print("MODE 1: Explicit Settings (Backward Compatible)")
    print("=" * 70)

    payload = {"iso": 400, "shutter_speed": "1/1000", "exposure_compensation": 0.7, "profile": "a"}

    print(f"\nRequest: POST {PI_URL}/capture")
    print(json.dumps(payload, indent=2))

    # Uncomment to actually test:
    # response = requests.post(f"{PI_URL}/capture", json=payload)
    # print(f"\nResponse: {response.status_code}")
    # pprint(response.json())

    print("\n✓ Mode 1: Uses explicit settings exactly as provided")


def test_mode_2_profile():
    """Test Mode 2: Use deployed profile"""
    print("\n" + "=" * 70)
    print("MODE 2: Deployed Profile Execution")
    print("=" * 70)

    payload = {"use_deployed_profile": True, "schedule_type": "sunset", "profile": "a"}

    print(f"\nRequest: POST {PI_URL}/capture")
    print(json.dumps(payload, indent=2))

    # Uncomment to actually test:
    # response = requests.post(f"{PI_URL}/capture", json=payload)
    # print(f"\nResponse: {response.status_code}")
    # pprint(response.json())

    print("\n✓ Mode 2: Pi calculates settings from deployed profile")
    print("  - Meters scene to get lux")
    print("  - Calls profile_executor.calculate_settings()")
    print("  - Uses profile's sunset schedule settings")


def test_mode_3_override():
    """Test Mode 3: Override deployed profile settings"""
    print("\n" + "=" * 70)
    print("MODE 3: Profile with Override (Testing Mode)")
    print("=" * 70)

    payload = {
        "use_deployed_profile": True,
        "schedule_type": "sunset",
        "override": {"exposure_compensation": 0.9},
        "profile": "a",
    }

    print(f"\nRequest: POST {PI_URL}/capture")
    print(json.dumps(payload, indent=2))

    # Uncomment to actually test:
    # response = requests.post(f"{PI_URL}/capture", json=payload)
    # print(f"\nResponse: {response.status_code}")
    # pprint(response.json())

    print("\n✓ Mode 3: Uses profile but applies override")
    print("  - Calculates base settings from profile")
    print("  - Applies override.exposure_compensation = 0.9")
    print("  - Useful for testing profile tweaks")


def test_error_no_profile():
    """Test error handling when profile not deployed"""
    print("\n" + "=" * 70)
    print("ERROR TEST: No Profile Deployed")
    print("=" * 70)

    payload = {"use_deployed_profile": True, "schedule_type": "sunset", "profile": "a"}

    print(f"\nRequest: POST {PI_URL}/capture")
    print(json.dumps(payload, indent=2))

    print("\n✗ Expected: 400 Bad Request")
    print("  Message: 'No profile deployed - cannot use profile execution mode'")


def check_status():
    """Check Pi status and deployed profile"""
    print("\n" + "=" * 70)
    print("CHECK STATUS")
    print("=" * 70)

    print(f"\nRequest: GET {PI_URL}/status")

    # Uncomment to actually test:
    # response = requests.get(f"{PI_URL}/status")
    # print(f"\nResponse: {response.status_code}")
    # pprint(response.json())

    print("\nExpected fields:")
    print("  - operational_mode: 'live_orchestration' or 'deployed_profile'")
    print("  - deployed_profile: {...} if profile is deployed")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PROFILE EXECUTION - TEST SCENARIOS")
    print("=" * 70)
    print("\nThis script demonstrates the three capture modes.")
    print("Uncomment the requests.post() lines to actually test.")

    check_status()
    test_mode_1_explicit()
    test_mode_2_profile()
    test_mode_3_override()
    test_error_no_profile()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Deploy a profile: POST /profile/deploy")
    print("2. Test Mode 2: use_deployed_profile=true")
    print("3. Test Mode 3: Add override dict")
    print("4. Verify backward compatibility: Test Mode 1")
