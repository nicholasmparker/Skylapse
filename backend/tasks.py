"""
Background Tasks for Timelapse Generation

These tasks run in RQ worker containers, processing images into videos.
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def generate_timelapse(
    profile: str,
    schedule: str,
    date: str,
    fps: int = 30,
    quality: str = "high",
) -> dict:
    """
    Generate timelapse video from captured images.

    Args:
        profile: Profile identifier (a-g)
        schedule: Schedule type (sunrise/daytime/sunset)
        date: Date string (YYYY-MM-DD)
        fps: Frames per second for output video
        quality: Video quality (low/medium/high)

    Returns:
        Dictionary with status and video path
    """
    logger.info(f"🎬 Starting timelapse generation: {profile}/{schedule}/{date}")

    # Paths
    images_dir = Path("/data/images") / f"profile-{profile}"
    output_dir = Path("/data/timelapses")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output filename: profile-a_sunset_2025-10-01.mp4
    output_filename = f"profile-{profile}_{schedule}_{date}.mp4"
    output_path = output_dir / output_filename

    # Find images for this date and schedule
    # Pattern: capture_2025-10-01_sunset_17-45-30_profile-a.jpg
    pattern = f"capture_{date}_{schedule}_*_profile-{profile}.jpg"
    images = sorted(images_dir.glob(pattern))

    if not images:
        logger.warning(f"No images found matching {pattern} in {images_dir}")
        return {
            "status": "error",
            "message": f"No images found for {profile}/{schedule}/{date}",
            "image_count": 0,
        }

    logger.info(f"Found {len(images)} images for timelapse")

    # Quality presets
    quality_presets = {
        "low": {"crf": 28, "preset": "fast"},
        "medium": {"crf": 23, "preset": "medium"},
        "high": {"crf": 18, "preset": "slow"},
    }

    preset = quality_presets.get(quality, quality_presets["high"])

    # Create temporary file list for ffmpeg
    filelist_path = output_dir / f".filelist_{profile}_{schedule}_{date}.txt"
    with open(filelist_path, "w") as f:
        for img in images:
            f.write(f"file '{img.absolute()}'\n")

    try:
        # ffmpeg command to generate video
        # -framerate: input framerate (how fast to read images)
        # -f concat: concatenate images
        # -c:v libx264: H.264 codec
        # -pix_fmt yuv420p: compatible pixel format
        # -crf: quality (lower = better, 18-28 recommended)
        # -preset: encoding speed/compression tradeoff
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-framerate",
            str(fps),
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(filelist_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            str(preset["crf"]),
            "-preset",
            preset["preset"],
            str(output_path),
        ]

        logger.info(f"Running ffmpeg: {' '.join(ffmpeg_cmd)}")

        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"ffmpeg failed: {result.stderr[:200]}",
                "image_count": len(images),
            }

        # Clean up temp filelist
        filelist_path.unlink()

        # Get video file size
        video_size_mb = output_path.stat().st_size / 1024 / 1024

        logger.info(
            f"✓ Timelapse generated: {output_filename} ({video_size_mb:.1f} MB, {len(images)} frames)"
        )

        return {
            "status": "success",
            "video_path": str(output_path),
            "video_filename": output_filename,
            "image_count": len(images),
            "video_size_mb": round(video_size_mb, 2),
            "fps": fps,
            "quality": quality,
        }

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timed out after 10 minutes")
        return {
            "status": "error",
            "message": "Video generation timed out",
            "image_count": len(images),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {"status": "error", "message": str(e), "image_count": len(images)}
