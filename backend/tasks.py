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
    quality_tier: str = "preview",
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
        quality_tier: Quality tier ('preview' for web-friendly, 'archive' for maximum quality)

    Returns:
        Dictionary with status and video path
    """
    logger.info(f"🎬 Starting timelapse generation: {profile}/{schedule}/{date} ({quality_tier})")

    # Paths
    images_dir = Path("/data/images") / f"profile-{profile}"
    output_dir = Path("/data/timelapses")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output filename: profile-a_sunset_2025-10-01.mp4 (preview) or profile-a_sunset_2025-10-01_archive.mp4
    if quality_tier == "archive":
        output_filename = f"profile-{profile}_{schedule}_{date}_archive.mp4"
    else:
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
        use_concat = True  # Use concat demuxer for exact file list
    else:
        # Ad-hoc generation: use all images matching date pattern
        date_compact = date.replace("-", "")
        pattern = f"capture_{date_compact}_*.jpg"
        images = sorted(images_dir.glob(pattern))
        logger.info(f"Ad-hoc generation: Found {len(images)} images matching {pattern}")
        use_concat = False  # Use glob pattern for ad-hoc

    if not images:
        logger.warning(f"No images found for {profile}/{schedule}/{date}")
        return {
            "status": "error",
            "message": "No images found",
            "image_count": 0,
        }

    # Quality presets - distinguish between preview and archive tiers
    if quality_tier == "archive":
        # Archive quality: Maximum quality for long-term storage
        quality_presets = {
            "low": {"crf": 20, "preset": "medium"},
            "medium": {"crf": 16, "preset": "slow"},
            "high": {"crf": 12, "preset": "slow"},  # Near-lossless for archival
        }
    else:
        # Preview quality: Web-friendly, smaller file sizes
        quality_presets = {
            "low": {"crf": 28, "preset": "fast"},
            "medium": {"crf": 23, "preset": "medium"},
            "high": {"crf": 18, "preset": "medium"},
        }

    preset = quality_presets.get(quality, quality_presets["high"])

    try:
        if use_concat:
            # Use concat demuxer for exact file list (session-based)
            # Create temporary file list for concat demuxer
            filelist_path = output_dir / f".filelist_{profile}_{schedule}_{date}.txt"
            with open(filelist_path, "w") as f:
                for img in images:
                    # Escape single quotes and write in concat format
                    f.write(f"file '{img}'\n")

            logger.info(f"Using concat demuxer with {len(images)} exact images")

            # Build FFmpeg command with concat demuxer
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(filelist_path),
                "-framerate",
                str(fps),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                str(preset["crf"]),
                "-preset",
                preset["preset"],
            ]
        else:
            # Use glob pattern for ad-hoc generation
            date_compact = date.replace("-", "")
            glob_pattern = f"capture_{date_compact}_*.jpg"
            input_pattern = str(images_dir / glob_pattern)

            logger.info(f"Using glob pattern: {glob_pattern}")

            # Build FFmpeg command with glob pattern
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

        # Apply profile-specific video filters if defined in config
        from config import Config
        config = Config()
        profile_data = config.get_profile(profile)
        video_filters = profile_data.get("video_filters")

        if video_filters:
            ffmpeg_cmd.extend(["-vf", video_filters])
            logger.info(f"Applying Profile {profile.upper()} video filters: {video_filters}")

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

        # Generate thumbnail from 1 second into video
        thumbnail_filename = output_filename.replace(".mp4", "_thumb.jpg")
        thumbnail_path = output_dir / thumbnail_filename

        thumbnail_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            "00:00:01",  # Seek to 1 second
            "-i",
            str(output_path),
            "-vframes",
            "1",
            "-q:v",
            "2",  # High quality JPEG
            str(thumbnail_path),
        ]

        try:
            subprocess.run(thumbnail_cmd, capture_output=True, timeout=30)
            logger.info(f"✓ Thumbnail generated: {thumbnail_filename}")
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")

        # Record timelapse in database
        if session_id:
            try:
                db = SessionDatabase()

                # Mark session as timelapse_generated
                db.mark_timelapse_generated(session_id)

                # Record timelapse metadata
                db.record_timelapse(
                    session_id=session_id,
                    filename=output_filename,
                    file_path=str(output_path),
                    file_size_mb=video_size_mb,
                    profile=profile,
                    schedule=schedule,
                    date=date,
                    frame_count=len(images),
                    fps=fps,
                    quality=quality,
                    quality_tier=quality_tier,
                )
            except Exception as e:
                logger.warning(f"Failed to record timelapse metadata: {e}")

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
