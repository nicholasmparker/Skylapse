#!/usr/bin/env python3
"""
HDR Merge Tool for Profile F Bracket Images

Merges 3-shot exposure brackets into single HDR image using Mertens fusion.
This is the algorithm used by professional timelapse photographers.

Usage:
    python3 hdr-merge.py <bracket0.jpg> <bracket1.jpg> <bracket2.jpg> <output.jpg>

    Or auto-find latest bracket set:
    python3 hdr-merge.py --latest
"""

import sys
from pathlib import Path

import cv2
import numpy as np


def merge_hdr_mertens(images):
    """
    Merge exposure bracket using Mertens algorithm.

    This is exposure fusion - no tone mapping needed.
    Creates natural-looking HDR without the typical "HDR look".

    Args:
        images: List of numpy arrays (BGR images)

    Returns:
        Merged HDR image (8-bit BGR)
    """
    # Create Mertens merge object
    merge = cv2.createMergeMertens()

    # Merge exposures
    # Note: Images should be in order: underexposed, normal, overexposed
    hdr = merge.process(images)

    # Convert to 8-bit (Mertens outputs float 0-1)
    hdr_8bit = np.clip(hdr * 255, 0, 255).astype(np.uint8)

    return hdr_8bit


def merge_hdr_debevec(images, exposure_times):
    """
    Merge using Debevec algorithm with tone mapping.

    More traditional HDR approach. Requires exposure times.

    Args:
        images: List of numpy arrays (BGR images)
        exposure_times: List of exposure times in seconds

    Returns:
        Tone-mapped HDR image (8-bit BGR)
    """
    # Create Debevec merge object
    merge = cv2.createMergeDebevec()

    # Merge to HDR
    hdr = merge.process(images, times=np.array(exposure_times, dtype=np.float32))

    # Tone mapping (Reinhard)
    tonemap = cv2.createTonemapReinhard(gamma=2.2)
    ldr = tonemap.process(hdr)

    # Convert to 8-bit
    ldr_8bit = np.clip(ldr * 255, 0, 255).astype(np.uint8)

    return ldr_8bit


def load_bracket_images(bracket0, bracket1, bracket2):
    """Load 3 bracket images."""
    print(f"Loading bracket images:")
    print(f"  Under: {bracket0}")
    print(f"  Normal: {bracket1}")
    print(f"  Over: {bracket2}")

    img0 = cv2.imread(str(bracket0))
    img1 = cv2.imread(str(bracket1))
    img2 = cv2.imread(str(bracket2))

    if img0 is None or img1 is None or img2 is None:
        raise ValueError("Failed to load one or more images")

    return [img0, img1, img2]


def find_latest_bracket(images_dir="/home/nicholasmparker/skylapse-images/profile-f"):
    """
    Find the latest bracket set from profile-f directory.

    Returns:
        Tuple of (bracket0, bracket1, bracket2) paths
    """
    images_dir = Path(images_dir)

    # Find all bracket sets (format: capture_YYYYMMDD_HHMMSS_bracket{0,1,2}.jpg)
    bracket_files = sorted(images_dir.glob("*_bracket*.jpg"))

    if len(bracket_files) < 3:
        raise ValueError(f"Not enough bracket images found in {images_dir}")

    # Get latest 3 (should be a set)
    latest = bracket_files[-3:]

    # Verify they're from the same timestamp
    base_names = [f.stem.rsplit("_bracket", 1)[0] for f in latest]
    if len(set(base_names)) != 1:
        raise ValueError(f"Latest 3 images are not from same bracket set: {latest}")

    return tuple(latest)


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--latest":
        # Auto-find latest bracket set
        print("Finding latest bracket set...")
        bracket0, bracket1, bracket2 = find_latest_bracket()
        output = Path("/tmp/hdr_merged_latest.jpg")
    elif len(sys.argv) == 5:
        # Manual file specification
        bracket0 = Path(sys.argv[1])
        bracket1 = Path(sys.argv[2])
        bracket2 = Path(sys.argv[3])
        output = Path(sys.argv[4])
    else:
        print(__doc__)
        sys.exit(1)

    # Load images
    images = load_bracket_images(bracket0, bracket1, bracket2)

    print("\nMerging HDR using Mertens algorithm...")
    hdr_mertens = merge_hdr_mertens(images)

    # Save result
    cv2.imwrite(str(output), hdr_mertens)
    print(f"\n✓ HDR merged image saved: {output}")
    print(f"  Size: {output.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"  Resolution: {hdr_mertens.shape[1]}x{hdr_mertens.shape[0]}")

    return output


if __name__ == "__main__":
    output_path = main()
    print(f"\nTo view: open {output_path}")
