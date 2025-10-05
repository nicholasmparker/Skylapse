#!/usr/bin/env python3
"""
Test script to find the correct LensPosition value for infinity focus on IMX519.

Usage: python3 test_focus.py <lens_position>
Example: python3 test_focus.py 0.5
"""

import sys
import time
from pathlib import Path

from picamera2 import Picamera2

if len(sys.argv) != 2:
    print("Usage: python3 test_focus.py <lens_position>")
    print("Example: python3 test_focus.py 0.5")
    print("\nRecommended test values for IMX519:")
    print("  0.0  - Closest focus")
    print("  0.5  - Try this first")
    print("  1.0  - Mid range")
    print("  2.0  - Further")
    print("  3.0  - Even further")
    print("  4.0  - Distant")
    print("  5.0  - Very distant")
    print("  6.0  - Maximum (may be infinity)")
    sys.exit(1)

lens_pos = float(sys.argv[1])

# Initialize camera
camera = Picamera2()
still_config = camera.create_still_configuration()
camera.configure(still_config)
camera.start()

# Set manual focus with specified lens position
camera.set_controls({"AfMode": 0, "LensPosition": lens_pos})  # Manual focus

# Wait for focus to settle
time.sleep(2)

# Capture test image
output_dir = Path.home() / "skylapse-images" / "focus-test"
output_dir.mkdir(parents=True, exist_ok=True)

filename = f"focus_test_lens_{lens_pos:.1f}.jpg"
filepath = output_dir / filename

camera.capture_file(str(filepath))

print(f"✓ Captured test image with LensPosition={lens_pos}")
print(f"  Saved to: {filepath}")
print(f"\nView the image and check if distant mountains are sharp.")
print(f"If blurry, try a different value (usually between 0.5-6.0 for IMX519)")

camera.close()
