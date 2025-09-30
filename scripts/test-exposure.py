#!/usr/bin/env python3
"""
Quick exposure testing script.

Usage:
    # Test current automatic settings
    ./scripts/test-exposure.py auto

    # Test specific settings
    ./scripts/test-exposure.py manual --iso 400 --shutter "1/500" --ev 0.7

    # Run bracket test (3 or 5 shots with variations)
    ./scripts/test-exposure.py bracket --iso 400 --shutter "1/500"

    # Run full golden hour test
    ./scripts/test-exposure.py golden-hour
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import requests

PI_HOST = "helios.local"
PI_PORT = 8080
PI_URL = f"http://{PI_HOST}:{PI_PORT}"

TEST_DIR = Path("test-captures")
TEST_DIR.mkdir(exist_ok=True)


def capture_shot(iso, shutter, ev, name_suffix=""):
    """Capture a single shot with given settings."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_name = f"test_{timestamp}{name_suffix}"

    print(f"\n📸 Capturing: {test_name}")
    print(f"   ISO: {iso}, Shutter: {shutter}, EV: {ev:+.1f}")

    try:
        response = requests.post(
            f"{PI_URL}/capture",
            json={
                "iso": iso,
                "shutter_speed": shutter,
                "exposure_compensation": ev,
            },
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

        print(f"   ✓ Success: {result.get('image_path')}")

        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "name": test_name,
            "settings": {"iso": iso, "shutter_speed": shutter, "exposure_value": ev},
            "result": result,
        }

        metadata_file = TEST_DIR / f"{test_name}.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return result

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return None


def test_auto():
    """Test with automatic settings (from backend algorithm)."""
    print("\n=== AUTO EXPOSURE TEST ===")
    print("Using backend's automatic settings...")

    # Get recommended settings from backend
    try:
        response = requests.get(f"http://localhost:8082/status", timeout=5)
        status = response.json()
        print(f"\nSun position: {status.get('current_time')}")
        print(f"Active schedules: {status.get('active_schedules')}")
    except Exception as e:
        print(f"Warning: Could not get backend status: {e}")

    # Capture with default algorithm settings
    # (This would need backend to calculate and return settings)
    print("\n⚠ Note: Need to implement backend settings calculation endpoint")
    print("For now, use 'manual' mode with specific settings")


def test_manual(iso, shutter, ev):
    """Test with manual settings."""
    print("\n=== MANUAL EXPOSURE TEST ===")
    capture_shot(iso, shutter, ev)


def test_bracket(base_iso, base_shutter, bracket_type="standard"):
    """Test bracketed exposure."""
    print("\n=== BRACKET TEST ===")

    if bracket_type == "standard":
        # ISO bracketing
        variations = [
            (base_iso // 2, base_shutter, -0.3, "_iso_low"),
            (base_iso, base_shutter, 0.0, "_baseline"),
            (base_iso, base_shutter, +0.3, "_ev_boost"),
            (base_iso * 2, base_shutter, 0.0, "_iso_high"),
        ]
    elif bracket_type == "ev":
        # EV bracketing
        variations = [
            (base_iso, base_shutter, -0.7, "_ev_minus_0.7"),
            (base_iso, base_shutter, -0.3, "_ev_minus_0.3"),
            (base_iso, base_shutter, 0.0, "_ev_0.0"),
            (base_iso, base_shutter, +0.3, "_ev_plus_0.3"),
            (base_iso, base_shutter, +0.7, "_ev_plus_0.7"),
        ]
    elif bracket_type == "shutter":
        # Shutter bracketing
        shutters = ["1/1000", "1/500", "1/250", "1/125"]
        variations = [(base_iso, s, 0.0, f"_shutter_{s.replace('/', '_')}") for s in shutters]

    print(f"Capturing {len(variations)} bracketed shots...")
    results = []

    for iso, shutter, ev, suffix in variations:
        result = capture_shot(iso, shutter, ev, suffix)
        if result:
            results.append(result)
        time.sleep(1)  # Brief pause between shots

    print(f"\n✓ Bracket complete: {len(results)}/{len(variations)} shots captured")
    print(f"   Results saved to: {TEST_DIR}/")

    return results


def test_golden_hour():
    """Run comprehensive golden hour test."""
    print("\n=== GOLDEN HOUR TEST ===")
    print("This will capture multiple settings suitable for golden hour.")
    print("Takes ~30 seconds.\n")

    # Test matrix for golden hour
    tests = [
        # (iso, shutter, ev, description)
        (200, "1/500", +0.3, "conservative"),
        (200, "1/500", +0.5, "conservative_bright"),
        (400, "1/500", +0.3, "balanced"),
        (400, "1/500", +0.5, "balanced_bright"),
        (400, "1/250", +0.5, "slower_bright"),
        (800, "1/1000", +0.3, "high_iso_fast"),
    ]

    results = []
    for iso, shutter, ev, desc in tests:
        print(f"\nTest: {desc}")
        result = capture_shot(iso, shutter, ev, f"_golden_{desc}")
        if result:
            results.append((desc, result))
        time.sleep(2)

    print(f"\n✓ Golden hour test complete: {len(results)} variations captured")
    print("\nReview images to find the best look for your scene.")

    return results


def main():
    parser = argparse.ArgumentParser(description="Test exposure settings on Pi")
    subparsers = parser.add_subparsers(dest="command", help="Test mode")

    # Auto test
    subparsers.add_parser("auto", help="Test with automatic settings")

    # Manual test
    manual_parser = subparsers.add_parser("manual", help="Test specific settings")
    manual_parser.add_argument("--iso", type=int, required=True, help="ISO value")
    manual_parser.add_argument(
        "--shutter", type=str, required=True, help="Shutter speed (e.g., 1/500)"
    )
    manual_parser.add_argument("--ev", type=float, default=0.0, help="Exposure value")

    # Bracket test
    bracket_parser = subparsers.add_parser("bracket", help="Run bracket test")
    bracket_parser.add_argument("--iso", type=int, required=True, help="Base ISO")
    bracket_parser.add_argument("--shutter", type=str, required=True, help="Shutter speed")
    bracket_parser.add_argument(
        "--type",
        choices=["standard", "ev", "shutter"],
        default="standard",
        help="Bracket type",
    )

    # Golden hour test
    subparsers.add_parser("golden-hour", help="Run comprehensive golden hour test")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Check Pi connectivity
    try:
        response = requests.get(f"{PI_URL}/status", timeout=3)
        status = response.json()
        print(f"✓ Pi connected: {status.get('camera_model')}")
    except Exception as e:
        print(f"✗ Cannot reach Pi at {PI_URL}")
        print(f"  Error: {e}")
        print(f"\nMake sure:")
        print(f"  1. Pi is powered on")
        print(f"  2. Capture service is running")
        print(f"  3. Network connection is good")
        return

    # Execute command
    if args.command == "auto":
        test_auto()
    elif args.command == "manual":
        test_manual(args.iso, args.shutter, args.ev)
    elif args.command == "bracket":
        test_bracket(args.iso, args.shutter, args.type)
    elif args.command == "golden-hour":
        test_golden_hour()

    print(f"\n{'='*50}")
    print(f"Test results saved to: {TEST_DIR.absolute()}/")
    print(f"View images and compare to find optimal settings.")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
