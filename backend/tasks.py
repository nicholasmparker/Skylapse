"""
Background Tasks for Timelapse Generation

These tasks run in RQ worker containers, processing images into videos.
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from database import SessionDatabase

logger = logging.getLogger(__name__)


def generate_timelapse(
    profile: str,
    schedule: str,
    date: str,
    session_id: Optional[str] = None,
    fps: int = 30,
    quality: str = "high",
    job_timeout: int = 1200,  # 20 minutes for large timelapses
) -> dict:
    """
    Generate timelapse video from captured images.

    Args:
        profile: Profile identifier (a-g)
        schedule: Schedule type (sunrise/daytime/sunset)
        date: Date string (YYYY-MM-DD)
        session_id: Session ID to get exact image list from database
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

    # Get exact image list from database (if session_id provided)
    # Otherwise, use file-based glob pattern for ad-hoc generation
    if session_id:
        db = SessionDatabase()
        with db._get_connection() as conn:
            results = conn.execute(
                "SELECT filename FROM captures WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()
            filenames = [row["filename"] for row in results]

        if not filenames:
            logger.warning(f"No images found in database for session {session_id}")
            return {
                "status": "error",
                "message": f"No images found for session {session_id}",
                "image_count": 0,
            }

        # Build full paths
        images = [images_dir / filename for filename in filenames]
        logger.info(f"Found {len(images)} images for session {session_id}")
    else:
        # Ad-hoc generation: use all images matching date pattern
        date_compact = date.replace("-", "")
        pattern = f"capture_{date_compact}_*.jpg"
        images = sorted(images_dir.glob(pattern))
        logger.info(f"Ad-hoc generation: Found {len(images)} images matching {pattern}")

    # Create glob pattern for ffmpeg
    date_compact = date.replace("-", "")
    glob_pattern = f"capture_{date_compact}_*.jpg"

    # Quality presets - use medium for high res images
    quality_presets = {
        "low": {"crf": 28, "preset": "fast"},
        "medium": {"crf": 23, "preset": "medium"},
        "high": {"crf": 18, "preset": "medium"},  # medium preset for 4K+ images
    }

    preset = quality_presets.get(quality, quality_presets["high"])

    try:
        # Use glob pattern approach - more efficient than concat demuxer
        # Pattern must be absolute path for glob pattern matching
        input_pattern = str(images_dir / glob_pattern)

        # Build FFmpeg command with profile-specific filters
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-framerate",
            str(fps),
            "-pattern_type",
            "glob",
            "-i",
            input_pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            str(preset["crf"]),
            "-preset",
            preset["preset"],
        ]

        # Profile G: Add post-processing filters for enhanced landscape sharpness
        if profile == "g":
            # unsharp: Sharpen mountains and clouds (luma only)
            # eq: Boost contrast and saturation slightly
            filter_chain = "unsharp=5:5:1.0:5:5:0.0,eq=contrast=1.1:saturation=1.05"
            ffmpeg_cmd.extend(["-vf", filter_chain])
            logger.info(f"Applying Profile G post-processing: {filter_chain}")

        ffmpeg_cmd.append(str(output_path))

        logger.info(f"Running ffmpeg: {' '.join(ffmpeg_cmd)}")

        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout for 4K timelapses
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"ffmpeg failed: {result.stderr[:200]}",
                "image_count": len(images),
            }

        # Get video file size
        video_size_mb = output_path.stat().st_size / 1024 / 1024

        logger.info(
            f"✓ Timelapse generated: {output_filename} ({video_size_mb:.1f} MB, {len(images)} frames)"
        )

        # Mark session as timelapse_generated in database
        if session_id:
            try:
                db = SessionDatabase()
                db.mark_timelapse_generated(session_id)
            except Exception as e:
                logger.warning(f"Failed to mark session as generated: {e}")

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
