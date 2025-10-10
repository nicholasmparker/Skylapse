#!/usr/bin/env python3
"""
HDR Merge Tool - CLI Wrapper

Merges exposure brackets into single HDR image using Mertens fusion.
This is the algorithm used by professional timelapse photographers.

Usage:
    python3 hdr-merge.py <bracket0.jpg> <bracket1.jpg> <bracket2.jpg> <output.jpg>

    Or auto-find latest bracket set:
    python3 hdr-merge.py --latest

Note: Core HDR processing logic is in backend/hdr_processing.py
      This script is a convenient CLI wrapper for manual testing.
"""

import sys
from pathlib import Path

# Import core HDR processing from backend module
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.hdr_processing import process_bracket_set, HDRProcessingError


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
    """CLI entry point for HDR merging"""
    if len(sys.argv) == 2 and sys.argv[1] == "--latest":
        # Auto-find latest bracket set
        print("Finding latest bracket set...")
        bracket0, bracket1, bracket2 = find_latest_bracket()
        brackets = [bracket0, bracket1, bracket2]
        output = Path("/tmp/hdr_merged_latest.jpg")
    elif len(sys.argv) == 5:
        # Manual file specification
        bracket0 = Path(sys.argv[1])
        bracket1 = Path(sys.argv[2])
        bracket2 = Path(sys.argv[3])
        brackets = [bracket0, bracket1, bracket2]
        output = Path(sys.argv[4])
    else:
        print(__doc__)
        sys.exit(1)

    try:
        # Process brackets using core module
        print("\n🚀 Starting HDR merge...")
        result_path, metadata = process_bracket_set(
            bracket_paths=brackets,
            output_path=output,
            algorithm="mertens"
        )

        # Display results
        print(f"\n✅ Success! HDR image saved to: {result_path}")
        print(f"\n📊 Metadata:")
        print(f"  Algorithm: {metadata['algorithm']}")
        print(f"  Brackets: {metadata['bracket_count']}")
        print(f"  Resolution: {metadata['output_resolution']}")
        print(f"  Size: {metadata['output_size_mb']:.1f} MB")
        print(f"  Processing time: {metadata['processing_time_seconds']}s")

        return result_path

    except HDRProcessingError as e:
        print(f"\n❌ HDR processing failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    output_path = main()
    print(f"\nTo view: open {output_path}")
