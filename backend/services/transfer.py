"""
Image Transfer Service

Periodically syncs images from Raspberry Pi to backend storage.
Runs as a separate Docker container.
"""

import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment
PI_HOST = os.getenv("PI_HOST", "helios.local")
PI_USER = os.getenv("PI_USER", "nicholasmparker")
PI_SOURCE = os.getenv("PI_SOURCE", "~/skylapse-images/")
LOCAL_DEST = Path(os.getenv("LOCAL_DEST", "/data/images"))
TRANSFER_INTERVAL = int(os.getenv("TRANSFER_INTERVAL_MINUTES", "60"))  # Default: hourly
DELETE_AFTER_DAYS = int(os.getenv("DELETE_AFTER_DAYS", "7"))  # Keep 7 days on Pi


def run_rsync_transfer():
    """
    Transfer images from Pi to backend using rsync.

    Uses rsync with:
    - Archive mode (-a): preserves timestamps, permissions
    - Verbose (-v): shows progress
    - Human-readable (-h): easier to read sizes
    - Progress: shows transfer progress
    """
    logger.info(f"Starting transfer from {PI_USER}@{PI_HOST}:{PI_SOURCE}")

    # Ensure destination exists
    LOCAL_DEST.mkdir(parents=True, exist_ok=True)

    # Build rsync command
    rsync_cmd = [
        "rsync",
        "-avh",
        "--progress",
        "--stats",
        f"{PI_USER}@{PI_HOST}:{PI_SOURCE}",
        str(LOCAL_DEST) + "/",
    ]

    try:
        result = subprocess.run(
            rsync_cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout for large initial transfers
        )

        if result.returncode == 0:
            logger.info("✓ Transfer completed successfully")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"✗ Transfer failed with code {result.returncode}")
            logger.error(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        logger.error("✗ Transfer timed out after 10 minutes")
        return False
    except Exception as e:
        logger.error(f"✗ Transfer error: {e}")
        return False


def cleanup_old_images_on_pi():
    """
    Delete images older than DELETE_AFTER_DAYS from Pi to free space.
    Only runs after successful transfer.
    """
    logger.info(f"Cleaning up images older than {DELETE_AFTER_DAYS} days on Pi")

    # SSH command to find and delete old images
    cleanup_cmd = [
        "ssh",
        f"{PI_USER}@{PI_HOST}",
        f"find {PI_SOURCE} -name 'capture_*.jpg' -type f -mtime +{DELETE_AFTER_DAYS} -delete",
    ]

    try:
        result = subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            logger.info("✓ Cleanup completed")
            return True
        else:
            logger.error(f"✗ Cleanup failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"✗ Cleanup error: {e}")
        return False


def get_transfer_stats():
    """Get statistics about transferred images"""
    total_images = 0
    total_size = 0

    if LOCAL_DEST.exists():
        for profile_dir in LOCAL_DEST.glob("profile-*"):
            if profile_dir.is_dir():
                images = list(profile_dir.glob("capture_*.jpg"))
                profile_images = len(images)
                profile_size = sum(img.stat().st_size for img in images)

                total_images += profile_images
                total_size += profile_size

                logger.info(
                    f"  {profile_dir.name}: {profile_images} images, {profile_size / 1024 / 1024:.1f} MB"
                )

    return total_images, total_size


def run_transfer_loop():
    """Main transfer loop - runs continuously"""
    logger.info("🚀 Image Transfer Service Starting")
    logger.info(f"Source: {PI_USER}@{PI_HOST}:{PI_SOURCE}")
    logger.info(f"Destination: {LOCAL_DEST}")
    logger.info(f"Interval: Every {TRANSFER_INTERVAL} minutes")
    logger.info(f"Pi Cleanup: Delete after {DELETE_AFTER_DAYS} days")

    while True:
        try:
            logger.info("=" * 60)
            logger.info(f"Transfer cycle starting at {datetime.now().isoformat()}")

            # Run transfer
            success = run_rsync_transfer()

            if success:
                # Show stats
                total_images, total_size = get_transfer_stats()
                logger.info(f"Total: {total_images} images, {total_size / 1024 / 1024:.1f} MB")

                # Clean up old images on Pi
                cleanup_old_images_on_pi()

            # Wait for next cycle
            logger.info(f"Next transfer in {TRANSFER_INTERVAL} minutes")
            time.sleep(TRANSFER_INTERVAL * 60)

        except KeyboardInterrupt:
            logger.info("Transfer service stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            logger.info("Retrying in 5 minutes...")
            time.sleep(300)


if __name__ == "__main__":
    run_transfer_loop()
