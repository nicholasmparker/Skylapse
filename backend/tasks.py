"""
Background Tasks for Timelapse Generation and HDR Processing

These tasks run in RQ worker containers, processing images into videos.
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from database import SessionDatabase

logger = logging.getLogger(__name__)


def process_hdr_brackets(
    session_id: str,
    bracket_timestamp: str = None,
    cleanup_brackets: bool = False,
) -> dict:
    """
    Process HDR bracket sets for a session.

    Finds unprocessed bracket sets, merges them using HDR processing,
    and records the results in the database.

    Args:
        session_id: Session ID to process brackets for
        bracket_timestamp: Optional specific timestamp to process (for single bracket set)
        cleanup_brackets: If True, delete source bracket images after successful merge

    Returns:
        Dictionary with processing results and statistics
    """
    logger.info(f"🌅 Starting HDR bracket processing for session {session_id}")

    db = SessionDatabase()

    # Query for bracket sets that haven't been merged yet
    with db._get_connection() as conn:
        if bracket_timestamp:
            # Process specific bracket set
            query = """
                SELECT id, filename, timestamp, bracket_index, bracket_ev_offset, session_id
                FROM captures
                WHERE session_id = ?
                  AND is_bracket = 1
                  AND timestamp = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM captures hdr
                      WHERE hdr.is_hdr_result = 1
                      AND hdr.source_bracket_ids LIKE '%' || captures.id || '%'
                  )
                ORDER BY bracket_index ASC
            """
            params = (session_id, bracket_timestamp)
        else:
            # Process all unprocessed brackets in session
            query = """
                SELECT id, filename, timestamp, bracket_index, bracket_ev_offset, session_id
                FROM captures
                WHERE session_id = ?
                  AND is_bracket = 1
                  AND NOT EXISTS (
                      SELECT 1 FROM captures hdr
                      WHERE hdr.is_hdr_result = 1
                      AND hdr.source_bracket_ids LIKE '%' || captures.id || '%'
                  )
                ORDER BY timestamp ASC, bracket_index ASC
            """
            params = (session_id,)

        bracket_rows = conn.execute(query, params).fetchall()

    if not bracket_rows:
        logger.info(f"No unprocessed brackets found for session {session_id}")
        return {
            "status": "success",
            "message": "No unprocessed brackets found",
            "bracket_sets_processed": 0,
            "hdr_images_created": 0,
        }

    # Group brackets by timestamp (each timestamp = one bracket set)
    from collections import defaultdict
    bracket_sets = defaultdict(list)
    for row in bracket_rows:
        bracket_sets[row["timestamp"]].append(dict(row))

    logger.info(f"Found {len(bracket_sets)} bracket set(s) to process")

    # Process each bracket set
    processed_count = 0
    hdr_created_count = 0
    errors = []

    for timestamp, brackets in bracket_sets.items():
        try:
            # Sort by bracket_index to ensure correct order
            brackets = sorted(brackets, key=lambda b: b["bracket_index"])

            logger.info(
                f"Processing bracket set: {timestamp} ({len(brackets)} brackets)"
            )

            # Get profile from first bracket
            profile = brackets[0].get("session_id", "").split("_")[0] if brackets else "d"

            # Build paths to bracket images
            images_dir = Path("/data/images") / f"profile-{profile}"
            bracket_paths = [images_dir / b["filename"] for b in brackets]

            # Verify all bracket images exist
            missing = [p for p in bracket_paths if not p.exists()]
            if missing:
                error_msg = f"Missing bracket images: {missing}"
                logger.error(error_msg)
                errors.append({"timestamp": timestamp, "error": error_msg})
                continue

            # Generate HDR result filename
            # Format: capture_20251010_142734_hdr.jpg
            base_filename = brackets[0]["filename"]
            hdr_filename = base_filename.replace("_bracket0", "_hdr")
            hdr_output_path = images_dir / hdr_filename

            # Call HDR processing module
            from hdr_processing import process_bracket_set

            logger.info(f"Merging {len(bracket_paths)} brackets with Mertens fusion")
            result_path, metadata = process_bracket_set(
                bracket_paths=bracket_paths,
                output_path=hdr_output_path,
                algorithm="mertens",
                contrast_weight=1.0,
                saturation_weight=1.0,
                exposure_weight=0.0,
            )

            logger.info(
                f"✓ HDR merge complete: {hdr_filename} "
                f"({metadata['processing_time_seconds']:.2f}s)"
            )

            # Record HDR result in database
            bracket_ids = [str(b["id"]) for b in brackets]
            source_bracket_ids_json = json.dumps(bracket_ids)

            # Get settings from first bracket for metadata
            with db._get_connection() as conn:
                first_bracket_settings = conn.execute(
                    """
                    SELECT iso, shutter_speed, lux, wb_temp, wb_mode,
                           af_mode, lens_position, sharpness, contrast, saturation
                    FROM captures WHERE id = ?
                    """,
                    (brackets[0]["id"],)
                ).fetchone()

            # Record HDR result capture
            hdr_settings = {
                "profile": profile,
                "is_hdr_result": True,
                "source_bracket_ids": source_bracket_ids_json,
                "hdr_result_id": None,  # This IS the result
                # Copy settings from first bracket
                "iso": first_bracket_settings["iso"] if first_bracket_settings else None,
                "shutter_speed": first_bracket_settings["shutter_speed"] if first_bracket_settings else None,
                "lux": first_bracket_settings["lux"] if first_bracket_settings else None,
                "wb_temp": first_bracket_settings["wb_temp"] if first_bracket_settings else None,
                "awb_mode": first_bracket_settings["wb_mode"] if first_bracket_settings else None,
                "af_mode": first_bracket_settings["af_mode"] if first_bracket_settings else None,
                "lens_position": first_bracket_settings["lens_position"] if first_bracket_settings else None,
                "sharpness": first_bracket_settings["sharpness"] if first_bracket_settings else None,
                "contrast": first_bracket_settings["contrast"] if first_bracket_settings else None,
                "saturation": first_bracket_settings["saturation"] if first_bracket_settings else None,
            }

            db.record_capture(
                session_id=session_id,
                filename=hdr_filename,
                timestamp=datetime.fromisoformat(timestamp),
                settings=hdr_settings,
            )

            # Get the HDR result ID and update bracket records
            with db._get_connection() as conn:
                hdr_result = conn.execute(
                    "SELECT id FROM captures WHERE filename = ? AND session_id = ?",
                    (hdr_filename, session_id),
                ).fetchone()

                if hdr_result:
                    hdr_result_id = hdr_result["id"]

                    # Update all source brackets to point to HDR result
                    for bracket_id in bracket_ids:
                        conn.execute(
                            "UPDATE captures SET hdr_result_id = ? WHERE id = ?",
                            (hdr_result_id, bracket_id),
                        )

                    conn.commit()
                    logger.info(
                        f"✓ Linked {len(bracket_ids)} brackets to HDR result (id={hdr_result_id})"
                    )

            hdr_created_count += 1
            processed_count += 1

            # Cleanup bracket images if requested
            if cleanup_brackets:
                for bracket_path in bracket_paths:
                    try:
                        bracket_path.unlink()
                        logger.debug(f"Deleted bracket: {bracket_path.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete bracket {bracket_path}: {e}")

        except Exception as e:
            error_msg = f"Failed to process bracket set {timestamp}: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append({"timestamp": timestamp, "error": str(e)})

    result = {
        "status": "success" if processed_count > 0 else "error",
        "message": f"Processed {processed_count} bracket set(s)",
        "bracket_sets_processed": processed_count,
        "hdr_images_created": hdr_created_count,
        "errors": errors if errors else None,
    }

    logger.info(
        f"🌅 HDR processing complete: {hdr_created_count} HDR image(s) created "
        f"from {processed_count} bracket set(s)"
    )

    return result


def _build_debug_overlay(
    session_id: str, debug_config: Dict, fps: int = 30
) -> Optional[str]:
    """
    Build ffmpeg drawtext filter for debug overlay showing camera settings.

    Args:
        session_id: Session ID to query capture metadata
        debug_config: Debug configuration from schedule
        fps: Frames per second (for frame number calculation)

    Returns:
        ffmpeg filter string or None if debug disabled
    """
    if not debug_config.get("enabled", False):
        return None

    # Query all capture metadata from database
    db = SessionDatabase()
    with db._get_connection() as conn:
        results = conn.execute(
            """
            SELECT
                filename, timestamp, profile, iso, shutter_speed,
                exposure_compensation, lux, wb_temp, wb_mode,
                hdr_mode, bracket_count, ae_metering_mode,
                af_mode, lens_position, sharpness, contrast, saturation
            FROM captures
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        ).fetchall()

    if not results:
        logger.warning(f"No capture metadata found for session {session_id}")
        return None

    # Build drawtext filter for each frame
    # Format: Frame N: ISO 200 | 1/500s | EV+0.3 | 5200K | F:2.45mm | S:1.5 C:1.15 Sat:1.05 | Lux:1250
    font_size = debug_config.get("font_size", 16)
    position = debug_config.get("position", "bottom-left")
    background = debug_config.get("background", True)

    # Position coordinates (with padding)
    if position == "bottom-left":
        x, y = 10, "h-th-10"
    elif position == "top-left":
        x, y = 10, 10
    elif position == "bottom-right":
        x, y = "w-tw-10", "h-th-10"
    else:  # top-right
        x, y = "w-tw-10", 10

    # Build text for each frame
    drawtext_filters = []
    for frame_idx, row in enumerate(results):
        # Format capture settings into compact overlay text
        parts = [f"Frame {frame_idx+1}/{len(results)}"]

        if row["profile"]:
            parts.append(f"Profile {row['profile'].upper()}")

        if row["iso"]:
            parts.append(f"ISO {row['iso']}")

        if row["shutter_speed"]:
            parts.append(row["shutter_speed"])

        if row["exposure_compensation"] is not None:
            parts.append(f"EV{row['exposure_compensation']:+.1f}")

        if row["wb_temp"]:
            parts.append(f"{row['wb_temp']}K")

        if row["lens_position"] is not None:
            parts.append(f"F:{row['lens_position']:.2f}mm")

        # Enhancement settings on second line
        enhancements = []
        if row["sharpness"] is not None:
            enhancements.append(f"S:{row['sharpness']:.1f}")
        if row["contrast"] is not None:
            enhancements.append(f"C:{row['contrast']:.2f}")
        if row["saturation"] is not None:
            enhancements.append(f"Sat:{row['saturation']:.2f}")

        if row["lux"] is not None:
            parts.append(f"Lux:{row['lux']:.0f}")

        # Combine into text
        line1 = " | ".join(parts)
        line2 = " ".join(enhancements) if enhancements else ""

        # Escape special characters for ffmpeg
        line1 = line1.replace(":", "\\:")
        line2 = line2.replace(":", "\\:")

        # Build drawtext filter with frame timing
        # Show this text only during this frame's display time
        frame_start = frame_idx / fps
        frame_end = (frame_idx + 1) / fps

        box_param = ":box=1:boxcolor=black@0.7:boxborderw=5" if background else ""

        if line2:
            # Two lines
            filter_str = (
                f"drawtext=text='{line1}':fontsize={font_size}:fontcolor=white"
                f":x={x}:y={y}-{font_size+5}{box_param}"
                f":enable='between(t,{frame_start},{frame_end})',"
                f"drawtext=text='{line2}':fontsize={font_size}:fontcolor=white"
                f":x={x}:y={y}{box_param}"
                f":enable='between(t,{frame_start},{frame_end})'"
            )
        else:
            # Single line
            filter_str = (
                f"drawtext=text='{line1}':fontsize={font_size}:fontcolor=white"
                f":x={x}:y={y}{box_param}"
                f":enable='between(t,{frame_start},{frame_end})'"
            )

        drawtext_filters.append(filter_str)

    # Combine all drawtext filters
    return ",".join(drawtext_filters)


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

        # Build video filters (debug overlay + profile filters)
        from config import Config
        config = Config()

        all_filters = []

        # Add debug overlay if enabled (only works with session_id for metadata)
        if session_id:
            # Get schedule config to check for video_debug settings
            schedule_config = config.get_schedule(schedule)
            debug_config = schedule_config.get("video_debug", {})

            debug_filter = _build_debug_overlay(session_id, debug_config, fps)
            if debug_filter:
                all_filters.append(debug_filter)
                logger.info(f"Adding debug overlay for session {session_id}")

        # Add profile-specific video filters if defined
        profile_data = config.get_profile(profile)
        video_filters = profile_data.get("video_filters")
        if video_filters:
            all_filters.append(video_filters)
            logger.info(f"Applying Profile {profile.upper()} video filters: {video_filters}")

        # Combine all filters
        if all_filters:
            combined_filters = ",".join(all_filters)
            ffmpeg_cmd.extend(["-vf", combined_filters])
            logger.info(f"Combined video filters: {len(all_filters)} filter(s)")

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
