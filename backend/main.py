"""
Skylapse Backend - The Brain

Responsibilities:
1. Store schedules (managed by config.py)
2. Calculate sunrise/sunset times (solar.py)
3. Determine when to capture (scheduler loop)
4. Calculate optimal camera settings (exposure.py)
5. Send capture commands to Pi
6. Process and stack images
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, time
from pathlib import Path

import httpx
import uvicorn
from config import Config
from config_validator import ConfigValidationError, validate_config
from database import SessionDatabase
from exposure import ExposureCalculator
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis import Redis
from rq import Queue
from schedule_types import ScheduleType
from solar import SolarCalculator
from url_builder import get_url_builder

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown"""
    # Startup
    logger.info("Starting Skylapse Backend...")

    # Validate configuration before loading
    try:
        validate_config()
    except ConfigValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        logger.error("Please fix config.json and restart the service")
        sys.exit(1)

    # Initialize configuration
    config = Config()
    logger.info(f"Configuration loaded from {config.config_path}")

    # Initialize solar calculator
    location = config.get_location()
    solar_calc = SolarCalculator(
        latitude=location["latitude"],
        longitude=location["longitude"],
        timezone=location["timezone"],
    )

    # Initialize exposure calculator with Pi metering
    pi_config = config.get("pi", {})
    pi_host = pi_config.get("host", "192.168.0.124")
    pi_port = pi_config.get("port", 8080)
    exposure_calc = ExposureCalculator(solar_calc, pi_host=pi_host, pi_port=pi_port)

    # Initialize session database
    db = SessionDatabase()

    # Initialize Redis Queue for timelapse generation
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_conn = Redis.from_url(redis_url)
    timelapse_queue = Queue("timelapse", connection=redis_conn)
    logger.info(f"Connected to Redis at {redis_url}")

    # Backend name for Pi coordination (optional)
    backend_name = os.getenv("BACKEND_NAME", None)
    if backend_name:
        logger.info(f"🏷️  Backend name: '{backend_name}' (will be sent with capture requests)")
    else:
        logger.info(
            "🏷️  Backend name not set (BACKEND_NAME env var) - capture requests won't include backend_name"
        )

    # Store in app state (no more globals!)
    app.state.config = config
    app.state.solar_calc = solar_calc
    app.state.exposure_calc = exposure_calc
    app.state.timelapse_queue = timelapse_queue
    app.state.db = db
    app.state.backend_name = backend_name

    # Start scheduler loop
    scheduler_task = asyncio.create_task(scheduler_loop(app))
    app.state.scheduler_task = scheduler_task
    logger.info("Scheduler loop started")

    yield

    # Shutdown
    logger.info("Shutting down Skylapse Backend...")
    if app.state.scheduler_task:
        app.state.scheduler_task.cancel()
        try:
            await app.state.scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("Scheduler loop stopped")


app = FastAPI(title="Skylapse Backend", lifespan=lifespan)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Mount static files for serving local images
images_dir = Path("/data/images")
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")


async def scheduler_loop(app: FastAPI):
    """
    Main scheduler loop - checks every 30 seconds if capture is needed.

    This is the brain of the system. Every 30 seconds:
    1. Get current time
    2. Check each enabled schedule
    3. Determine if we should capture now
    4. Capture ALL 7 profiles rapidly in sequence (within ~15 seconds)
    5. Wait for next 30-second interval
    """
    logger.info("Scheduler loop running...")

    # Get references from app state
    config = app.state.config
    solar_calc = app.state.solar_calc
    exposure_calc = app.state.exposure_calc
    timelapse_queue = app.state.timelapse_queue
    db = app.state.db

    # Track last capture times per schedule to avoid duplicates
    last_captures = {}

    # Track last timelapse generation per schedule (in-memory for session, reset on restart)
    last_timelapse_dates = {}  # Prevents duplicate timelapse jobs within same backend session

    while True:
        try:
            # Get current time in local timezone
            current_time = datetime.now(solar_calc.timezone)
            logger.info(f"🔄 Scheduler check at {current_time.strftime('%H:%M:%S')}")

            # Check each schedule
            schedules = config.config.get("schedules", {})

            for schedule_name, schedule_config in schedules.items():
                # Get profiles for this specific schedule from config
                schedule_profiles = config.get_schedule_profiles(schedule_name)

                logger.info(
                    f"🔍 Checking schedule: {schedule_name}, enabled={schedule_config.get('enabled', True)}, profiles={schedule_profiles}"
                )

                if not schedule_config.get("enabled", True):
                    continue

                # Get current schedule window
                current_window = None
                is_active = False

                if ScheduleType.is_solar(schedule_name):
                    # Solar-based schedule
                    current_window = solar_calc.get_schedule_window(schedule_config, current_time)
                    is_active = current_window["start"] <= current_time <= current_window["end"]

                elif schedule_name == ScheduleType.DAYTIME:
                    # Time-based schedule
                    start_time, end_time = parse_time_range(schedule_config, schedule_name)

                    if start_time and end_time:
                        current_time_only = current_time.time()
                        is_active = start_time <= current_time_only <= end_time

                        logger.info(
                            f"🔍 {schedule_name}: current={current_time_only}, "
                            f"window={start_time}-{end_time}, "
                            f"is_active={is_active}"
                        )

                # Detect schedule end: check each profile's was_active state
                # (Profiles may have different states if backend restarted mid-capture)
                date_str = current_time.strftime("%Y-%m-%d")

                # Check if schedule just transitioned from active to inactive
                # We check the first profile as representative (all profiles share same schedule)
                if schedule_profiles:
                    was_active = db.get_was_active(schedule_profiles[0], date_str, schedule_name)
                else:
                    was_active = False

                if was_active and not is_active:
                    # Schedule ended - mark sessions complete and enqueue timelapse jobs
                    # Only generate once per day per schedule
                    last_date = last_timelapse_dates.get(schedule_name)
                    if last_date != date_str:
                        logger.info(
                            f"🎬 {schedule_name} schedule ended (was_active={was_active}, is_active={is_active}) "
                            f"- marking sessions complete and generating timelapses"
                        )

                        for profile in schedule_profiles:
                            # Construct session_id (matches format from get_or_create_session)
                            session_id = f"{profile}_{date_str.replace('-', '')}_{schedule_name}"

                            # Mark session as complete in database
                            db.mark_session_complete(session_id)

                            # Enqueue timelapse generation (use to_thread for sync RQ library)
                            job = await asyncio.to_thread(
                                timelapse_queue.enqueue,
                                "tasks.generate_timelapse",
                                profile=profile,
                                schedule=schedule_name,
                                date=date_str,
                                session_id=session_id,
                                job_timeout="20m",  # 20 min for 4K timelapses
                            )
                            logger.info(f"  ✓ {session_id}: marked complete, job {job.id} enqueued")

                        last_timelapse_dates[schedule_name] = date_str

                # Update was_active state in database for all profiles
                # This persists the state across backend restarts
                for profile in schedule_profiles:
                    db.update_was_active(profile, date_str, schedule_name, is_active)

                should_capture = await should_capture_now(
                    schedule_name, schedule_config, current_time, last_captures, solar_calc
                )

                if should_capture:
                    # Capture all configured profiles in rapid sequence
                    logger.info(f"📸 Triggering capture burst for {schedule_name} - {len(schedule_profiles)} profiles: {schedule_profiles}")

                    date_str = current_time.strftime("%Y-%m-%d")

                    for profile in schedule_profiles:
                        # Get or create session for this profile/date/schedule
                        session_id = db.get_or_create_session(profile, date_str, schedule_name)

                        # Determine exposure schedule type for calculator
                        # Use schedule name if it's a known type (sunrise/sunset),
                        # otherwise map time_of_day schedules to 'daytime'
                        if schedule_name in [ScheduleType.SUNRISE, ScheduleType.SUNSET]:
                            exposure_schedule_type = schedule_name
                        else:
                            exposure_schedule_type = ScheduleType.DAYTIME

                        # Get smoothing config from schedule
                        smoothing_config = schedule_config.get("smoothing", {})

                        # Calculate exposure settings for this profile
                        settings = await exposure_calc.calculate_settings(
                            exposure_schedule_type,
                            current_time,
                            profile=profile,
                            session_id=session_id,
                            smoothing_config=smoothing_config,
                        )

                        # DEBUG: Log all settings being sent to Pi
                        logger.info(f"🔧 Profile {profile.upper()} settings: {settings}")

                        # Send capture command to Pi and download image
                        success, filename = await trigger_capture(schedule_name, settings, config)

                        if success and filename:
                            # Record capture metadata in database with actual filename
                            db.record_capture(session_id, filename, current_time, settings)

                            logger.info(
                                f"✓ Profile {profile.upper()}: ISO {settings['iso']}, {settings['shutter_speed']}, EV{settings['exposure_compensation']:+.1f}"
                            )
                        else:
                            logger.error(f"✗ Profile {profile.upper()} failed")

                        # Small delay between profiles to let camera settle
                        await asyncio.sleep(0.5)

                    # Update last capture time after all profiles complete
                    last_captures[schedule_name] = current_time
                    logger.info(f"✓ Capture burst complete for {schedule_name}")

            # Find minimum interval from all enabled schedules
            min_interval = min(
                (
                    sch.get("interval_seconds", 30)
                    for sch in schedules.values()
                    if sch.get("enabled", True)
                ),
                default=30,
            )
            # Sleep for the minimum interval before next check
            await asyncio.sleep(min_interval)

        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            await asyncio.sleep(30)  # Continue even if there was an error


def parse_time_range(schedule_config: dict, schedule_name: str) -> tuple:
    """
    Parse start_time and end_time from schedule config.

    Args:
        schedule_config: Schedule configuration dict
        schedule_name: Name of schedule (for error logging)

    Returns:
        Tuple of (start_time, end_time) as time objects, or (None, None) if invalid
    """
    start_time_str = schedule_config.get("start_time", "09:00")
    end_time_str = schedule_config.get("end_time", "15:00")

    try:
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
        return (start_time, end_time)
    except ValueError as e:
        logger.error(
            f"Invalid time format for {schedule_name}: "
            f"start={start_time_str}, end={end_time_str}. Error: {e}"
        )
        return (None, None)


def get_active_schedules(
    config: Config, solar_calc: SolarCalculator, current_time: datetime, detailed: bool = False
):
    """
    Get currently active schedules.

    Args:
        config: Configuration object
        solar_calc: Solar calculator for sun times
        current_time: Current datetime to check against
        detailed: If True, return full schedule objects with windows/intervals.
                  If False, return just schedule names.

    Returns:
        List of active schedules (strings if detailed=False, dicts if detailed=True)
    """
    active_schedules = []

    for schedule_name, schedule_config in config.config["schedules"].items():
        if not schedule_config.get("enabled", True):
            continue

        is_active = False
        window_start = None
        window_end = None
        schedule_type = schedule_config.get(
            "type", "solar_relative"
        )  # Default for backward compatibility

        if schedule_type == "solar_relative":
            # Data-driven solar schedule (e.g., sunrise, sunset, civil_dusk)
            window = solar_calc.get_schedule_window(schedule_config, current_time)
            is_active = window["start"] <= current_time <= window["end"]
            window_start = window["start"]
            window_end = window["end"]
        elif schedule_type == "time_of_day":
            # Fixed time schedule (e.g., daytime 08:00-18:00)
            start_time, end_time = parse_time_range(schedule_config, schedule_name)
            if start_time is not None and end_time is not None:
                is_active = start_time <= current_time.time() <= end_time
                window_start = start_time
                window_end = end_time

        if is_active:
            if detailed:
                schedule_detail = {
                    "name": schedule_name,
                    "type": schedule_type,
                    "interval_seconds": schedule_config.get("interval_seconds", 30),
                }

                if schedule_type == "solar_relative":
                    schedule_detail["window"] = {
                        "start": window_start.isoformat(),
                        "end": window_end.isoformat(),
                    }
                else:  # time_of_day
                    schedule_detail["window"] = {
                        "start": str(window_start),
                        "end": str(window_end),
                    }

                active_schedules.append(schedule_detail)
            else:
                active_schedules.append(schedule_name)

    return active_schedules


async def should_capture_now(
    schedule_name: str,
    schedule_config: dict,
    current_time: datetime,
    last_captures: dict,
    solar_calc: SolarCalculator,
) -> bool:
    """
    Determine if we should capture for this schedule right now.

    Args:
        schedule_name: Name of the schedule
        schedule_config: Schedule configuration
        current_time: Current time
        last_captures: Dictionary of last capture times per schedule
        solar_calc: Solar calculator instance

    Returns:
        True if we should capture now, False otherwise
    """
    # Check if enough time has passed since last capture
    interval = schedule_config.get("interval_seconds", 30)
    last_capture = last_captures.get(schedule_name)

    if last_capture:
        seconds_since_last = (current_time - last_capture).total_seconds()
        if seconds_since_last < interval:
            return False  # Too soon since last capture

    # Check schedule type and time window using the "type" field
    schedule_type = schedule_config.get("type")

    if schedule_type == "solar_relative":
        # Solar-based schedule
        window = solar_calc.get_schedule_window(schedule_config, current_time)
        return window["start"] <= current_time <= window["end"]

    elif schedule_type == "time_of_day":
        # Time-of-day schedule
        start_time, end_time = parse_time_range(schedule_config, schedule_name)

        if start_time is None or end_time is None:
            return False  # Skip this schedule if times are invalid

        current_time_only = current_time.time()
        return start_time <= current_time_only <= end_time

    return False


async def trigger_capture(schedule_name: str, settings: dict, config: Config) -> tuple[bool, str]:
    """
    Send capture command to Raspberry Pi and download the image.

    Args:
        schedule_name: Name of the schedule (for logging)
        settings: Camera settings from exposure calculator

    Returns:
        Tuple of (success: bool, local_image_path: str)
    """
    pi_config = config.get_pi_config()
    pi_url = f"http://{pi_config['host']}:{pi_config['port']}/capture"

    # Add backend_name to settings if configured (for Pi coordination)
    if app.state.backend_name:
        settings["backend_name"] = app.state.backend_name

    try:
        async with httpx.AsyncClient(timeout=pi_config["timeout_seconds"]) as client:
            response = await client.post(pi_url, json=settings)
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Pi response: {result}")

            if result.get("status") != "success":
                return (False, "")

            # Extract filename from Pi's image_path (e.g., /home/user/skylapse-images/profile-a/capture_20251001_224401.jpg)
            pi_image_path = result.get("image_path", "")
            if not pi_image_path:
                logger.error("Pi did not return image_path")
                return (False, "")

            # Extract just the filename
            filename = Path(pi_image_path).name

            # Construct local storage path
            profile = settings.get("profile", "default")
            local_dir = Path("/data/images") / f"profile-{profile}"
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / filename

            # Download image from Pi
            # Pi serves images at /images/<profile>/<filename>
            profile_path = Path(pi_image_path).parent.name  # e.g., "profile-a"
            image_url = (
                f"http://{pi_config['host']}:{pi_config['port']}/images/{profile_path}/{filename}"
            )

            logger.debug(f"Downloading image from {image_url} to {local_path}")

            image_response = await client.get(image_url)
            image_response.raise_for_status()

            # Write image to local filesystem
            with open(local_path, "wb") as f:
                f.write(image_response.content)

            logger.info(
                f"✓ Image downloaded: {filename} ({len(image_response.content) / 1024:.1f} KB)"
            )

            return (True, filename)

    except httpx.TimeoutException:
        logger.error(f"Pi capture timeout for {schedule_name}")
        return (False, "")
    except httpx.HTTPError as e:
        logger.error(f"Pi capture HTTP error for {schedule_name}: {e}")
        return (False, "")
    except Exception as e:
        logger.error(f"Pi capture error for {schedule_name}: {e}")
        return (False, "")


# API Endpoints


@app.get("/")
async def root(request: Request):
    """Root endpoint with system info"""
    config = request.app.state.config
    solar_calc = request.app.state.solar_calc

    sun_times = solar_calc.get_sun_times()

    return {
        "app": "Skylapse Backend",
        "status": "running",
        "location": config.get_location(),
        "sun_times": {
            "sunrise": sun_times["sunrise"].isoformat(),
            "sunset": sun_times["sunset"].isoformat(),
        },
        "schedules": list(config.config["schedules"].keys()),
    }


@app.get("/schedules")
async def get_schedules(request: Request):
    """Get all schedule configurations"""
    config = request.app.state.config
    solar_calc = request.app.state.solar_calc

    schedules = config.config["schedules"]

    # Add calculated time windows for solar schedules
    for schedule_type in ScheduleType.solar_schedules():
        schedule_name = schedule_type.value
        if schedule_name in schedules:
            schedule_config = schedules[schedule_name]
            window = solar_calc.get_schedule_window(schedule_config)
            schedules[schedule_name]["calculated_window"] = {
                "start": window["start"].isoformat(),
                "end": window["end"].isoformat(),
            }

    return schedules


@app.get("/status")
async def get_status(request: Request):
    """Get current system status"""
    config = request.app.state.config
    solar_calc = request.app.state.solar_calc

    current_time = datetime.now(solar_calc.timezone)
    sun_times = solar_calc.get_sun_times()

    # Get active schedules using shared helper
    active_schedules = get_active_schedules(config, solar_calc, current_time, detailed=False)

    return {
        "current_time": current_time.isoformat(),
        "sun_times": {
            "sunrise": sun_times["sunrise"].isoformat(),
            "sunset": sun_times["sunset"].isoformat(),
        },
        "is_daytime": solar_calc.is_daytime(current_time),
        "active_schedules": active_schedules,
        "pi_host": config.get("pi.host"),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Web dashboard for monitoring"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/timelapses")
async def list_timelapses(
    request: Request,
    limit: int = None,
    profile: str = None,
    schedule: str = None,
    date: str = None,
):
    """
    List available timelapse videos from database with optional filters.

    Args:
        limit: Maximum number of results
        profile: Filter by profile (a-g)
        schedule: Filter by schedule (sunrise/daytime/sunset)
        date: Filter by date (YYYY-MM-DD)

    Returns:
        List of timelapse metadata sorted by creation time (newest first)
    """
    db = request.app.state.db

    # Query database for timelapses
    timelapses_db = db.get_timelapses(limit=limit, profile=profile, schedule=schedule, date=date)

    # Format for frontend
    timelapses = []
    for t in timelapses_db:
        timelapses.append(
            {
                "id": t["id"],
                "name": t["filename"].replace(".mp4", "").replace("_archive", ""),
                "filename": t["filename"],
                "url": f"/timelapses/{t['filename']}",
                "size": f"{t['file_size_mb']:.1f} MB",
                "created": t["created_at"],
                "profile": t["profile"],
                "schedule": t["schedule"],
                "date": t["date"],
                "frame_count": t["frame_count"],
                "fps": t["fps"],
                "quality": t["quality"],
                "quality_tier": t.get("quality_tier", "preview"),
                "session_id": t["session_id"],
            }
        )

    return timelapses


@app.get("/timelapses/{filename}")
async def download_timelapse(filename: str):
    """Serve timelapse video file for download/streaming"""
    video_path = Path("/data/timelapses") / filename

    if not video_path.exists() or not video_path.is_file():
        return {"error": "File not found"}, 404

    # Serve the file with appropriate MIME type for video streaming
    return FileResponse(path=video_path, media_type="video/mp4", filename=filename)


@app.get("/thumbnails/{filename}")
async def get_thumbnail(filename: str):
    """Serve thumbnail image for timelapse"""
    # Thumbnail filename: profile-a_sunset_2025-10-01_thumb.jpg
    thumb_path = Path("/data/timelapses") / filename

    if not thumb_path.exists() or not thumb_path.is_file():
        return {"error": "Thumbnail not found"}, 404

    return FileResponse(path=thumb_path, media_type="image/jpeg")


@app.post("/timelapses/{session_id}/archive")
async def generate_archive_timelapse(session_id: str, request: Request):
    """
    Generate archive-quality timelapse for a session.

    This creates a high-quality archival version with near-lossless encoding,
    separate from the preview quality timelapse.
    """
    db = request.app.state.db
    timelapse_queue = request.app.state.timelapse_queue

    # Verify session exists
    session = db.get_session_stats(session_id)
    if not session:
        return {"error": "Session not found"}, 404

    # Parse session_id to get profile, date, schedule
    # Format: a_20251002_sunrise
    parts = session_id.split("_")
    if len(parts) != 3:
        return {"error": "Invalid session_id format"}, 400

    profile = parts[0]
    date_compact = parts[1]
    schedule = parts[2]

    # Format date as YYYY-MM-DD
    date = f"{date_compact[:4]}-{date_compact[4:6]}-{date_compact[6:]}"

    # Check if archive already exists
    existing_archives = db.get_timelapses(profile=profile, schedule=schedule, date=date)
    archive_exists = any(t.get("quality_tier") == "archive" for t in existing_archives)

    if archive_exists:
        return {
            "status": "already_exists",
            "message": "Archive quality timelapse already exists for this session",
        }

    # Enqueue archive generation job
    job = timelapse_queue.enqueue(
        "tasks.generate_timelapse",
        profile=profile,
        schedule=schedule,
        date=date,
        session_id=session_id,
        quality="high",
        quality_tier="archive",
        job_timeout="30m",  # Archive quality takes longer
    )

    logger.info(f"🎬 Archive quality timelapse enqueued for {session_id}, job {job.id}")

    return {
        "status": "enqueued",
        "job_id": job.id,
        "session_id": session_id,
        "profile": profile,
        "schedule": schedule,
        "date": date,
    }


@app.get("/profiles")
async def get_all_profiles(request: Request):
    """Get latest images for all 7 profiles with descriptions and image counts"""
    config = request.app.state.config
    pi_host = config.get("pi.host")

    # Get all profile definitions from config
    all_profiles_config = config.get_profiles()

    profiles = []
    url_builder = get_url_builder()
    db = request.app.state.db

    # Use database to get latest capture for each profile (FAST!)
    with db._get_connection() as conn:
        for profile_id, profile_data in all_profiles_config.items():
            # Query database for latest capture and total count
            # Profile is encoded in session_id (e.g., "d_20251002_daytime")
            latest = conn.execute(
                """
                SELECT c.filename, c.timestamp
                FROM captures c
                JOIN sessions s ON c.session_id = s.session_id
                WHERE s.profile = ?
                ORDER BY c.timestamp DESC
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()

            count = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM captures c
                JOIN sessions s ON c.session_id = s.session_id
                WHERE s.profile = ?
                """,
                (profile_id,),
            ).fetchone()

            # Get description from config, with fallback
            description = profile_data.get("name", f"Profile {profile_id.upper()}")

            if latest:
                # Extract just the filename from the full path
                filename = Path(latest["filename"]).name

                # Parse ISO timestamp and convert to milliseconds
                from datetime import datetime

                dt = datetime.fromisoformat(latest["timestamp"])
                timestamp_ms = int(dt.timestamp() * 1000)

                profiles.append(
                    {
                        "profile": profile_id,
                        "description": description,
                        "image_url": url_builder.image(profile_id, filename, source="backend"),
                        "timestamp": timestamp_ms,
                        "image_count": count["count"] if count else 0,
                    }
                )

    return profiles


@app.get("/system")
async def get_system_info(request: Request):
    """Comprehensive system status - everything you need to know at a glance"""
    config = request.app.state.config
    solar_calc = request.app.state.solar_calc

    current_time = datetime.now(solar_calc.timezone)
    sun_times = solar_calc.get_sun_times(current_time)

    # Get all schedule configurations
    schedules_config = config.config.get("schedules", {})

    # Get active schedules using shared helper
    active_schedules = get_active_schedules(config, solar_calc, current_time, detailed=True)

    # Get Pi status
    pi_config = config.get_pi_config()
    pi_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"http://{pi_config['host']}:{pi_config['port']}/health")
            pi_status = "online" if response.status_code == 200 else "offline"
    except:
        pi_status = "offline"

    return {
        "timestamp": current_time.isoformat(),
        "timezone": str(solar_calc.timezone),
        "sun": {
            "sunrise": sun_times["sunrise"].isoformat(),
            "sunset": sun_times["sunset"].isoformat(),
            "is_daytime": solar_calc.is_daytime(current_time),
            "current_phase": "day" if solar_calc.is_daytime(current_time) else "night",
        },
        "location": config.get_location(),
        "schedules": {
            "active": active_schedules,
            "configured": list(schedules_config.keys()),
            "enabled_count": sum(1 for s in schedules_config.values() if s.get("enabled", True)),
        },
        "camera": {
            "host": pi_config["host"],
            "port": pi_config["port"],
            "status": pi_status,
            "profiles_configured": list(config.get_profiles().keys()),
        },
        "system": {"backend_version": "2.0.0", "mode": "development", "scheduler_running": True},
    }


# ============================================================================
# CONFIGURATION EDITOR ENDPOINTS
# ============================================================================
# WARNING: These endpoints have NO AUTHENTICATION
# - Safe for development on trusted networks
# - MUST ADD AUTH before production deployment (API key, session auth, etc)
# - Anyone with network access can view/modify configuration
# ============================================================================

@app.get("/config")
async def get_config(request: Request):
    """
    Get current configuration.

    WARNING: No authentication - suitable for development only.
    Add authentication before production deployment.
    """
    config = request.app.state.config
    return config.config


@app.post("/config")
async def update_config(request: Request, new_config: dict):
    """Validate and save new configuration"""
    import json
    from pathlib import Path
    from config_validator import ConfigValidator, ConfigValidationError

    config = request.app.state.config
    temp_path = config.config_path.with_suffix('.json.tmp')

    try:
        # Write config to temp file
        with open(temp_path, 'w') as f:
            json.dump(new_config, f, indent=2)

        # Validate using comprehensive ConfigValidator
        validator = ConfigValidator(str(temp_path))
        validator.validate()

        # Validation passed - use Config.save() for atomic write
        config.config = new_config
        config.save()

        # Clean up temp file
        temp_path.unlink(missing_ok=True)

        logger.info(f"Configuration saved successfully from {request.client.host}")

        return {"status": "success", "message": "Configuration saved. Call /config/reload to apply changes."}

    except ConfigValidationError as e:
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        logger.warning(f"Config validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")


@app.post("/config/reload")
async def reload_config(request: Request):
    """Reload configuration from file"""
    from config_validator import ConfigValidator, ConfigValidationError

    config = request.app.state.config

    try:
        # Validate config file BEFORE reloading into memory
        validator = ConfigValidator(str(config.config_path))
        validator.validate()

        # Only reload if validation passes
        config.reload()

        logger.info(f"Configuration reloaded successfully from {request.client.host}")

        return {"status": "success", "message": "Configuration reloaded successfully"}

    except ConfigValidationError as e:
        logger.warning(f"Config validation failed on reload: {e}")
        raise HTTPException(status_code=400, detail=f"Config validation failed: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload config: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
