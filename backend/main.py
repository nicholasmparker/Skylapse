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
from contextlib import asynccontextmanager
from datetime import datetime, time
from pathlib import Path

import httpx
import uvicorn
from config import Config
from exposure import ExposureCalculator
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

    # Store in app state (no more globals!)
    app.state.config = config
    app.state.solar_calc = solar_calc
    app.state.exposure_calc = exposure_calc

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
    4. Capture ALL 6 profiles rapidly in sequence (within ~10 seconds)
    5. Wait for next 30-second interval
    """
    logger.info("Scheduler loop running...")

    # Get references from app state
    config = app.state.config
    solar_calc = app.state.solar_calc
    exposure_calc = app.state.exposure_calc

    # Track last capture times per schedule to avoid duplicates
    last_captures = {}

    # All profiles to capture each cycle
    profiles = ["a", "b", "c", "d", "e", "f"]

    while True:
        try:
            # Get current time in local timezone
            current_time = datetime.now(solar_calc.timezone)

            # Check each schedule
            schedules = config.config.get("schedules", {})

            for schedule_name, schedule_config in schedules.items():
                if not schedule_config.get("enabled", True):
                    continue

                should_capture = await should_capture_now(
                    schedule_name, schedule_config, current_time, last_captures, solar_calc
                )

                if should_capture:
                    # Capture ALL profiles in rapid sequence
                    logger.info(f"📸 Triggering capture burst for {schedule_name} - all 6 profiles")

                    for profile in profiles:
                        # Calculate exposure settings for this profile
                        settings = await exposure_calc.calculate_settings(
                            schedule_name, current_time, profile=profile
                        )

                        # Send capture command to Pi
                        success = await trigger_capture(schedule_name, settings, config)

                        if success:
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

    # Check schedule type and time window
    if ScheduleType.is_solar(schedule_name):
        # Solar-based schedule
        window = solar_calc.get_schedule_window(schedule_name, current_time)
        return window["start"] <= current_time <= window["end"]

    elif schedule_name == ScheduleType.DAYTIME:
        # Time-of-day schedule
        start_time, end_time = parse_time_range(schedule_config, schedule_name)

        if start_time is None or end_time is None:
            return False  # Skip this schedule if times are invalid

        current_time_only = current_time.time()
        return start_time <= current_time_only <= end_time

    return False


async def trigger_capture(schedule_name: str, settings: dict, config: Config) -> bool:
    """
    Send capture command to Raspberry Pi.

    Args:
        schedule_name: Name of the schedule (for logging)
        settings: Camera settings from exposure calculator

    Returns:
        True if capture successful, False otherwise
    """
    pi_config = config.get_pi_config()
    pi_url = f"http://{pi_config['host']}:{pi_config['port']}/capture"

    try:
        async with httpx.AsyncClient(timeout=pi_config["timeout_seconds"]) as client:
            response = await client.post(pi_url, json=settings)
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Pi response: {result}")

            return result.get("status") == "success"

    except httpx.TimeoutException:
        logger.error(f"Pi capture timeout for {schedule_name}")
        return False
    except httpx.HTTPError as e:
        logger.error(f"Pi capture HTTP error for {schedule_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Pi capture error for {schedule_name}: {e}")
        return False


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
            window = solar_calc.get_schedule_window(schedule_name)
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

    # Check which schedules are active right now
    active_schedules = []
    for schedule_name, schedule_config in config.config["schedules"].items():
        if not schedule_config.get("enabled", True):
            continue

        if ScheduleType.is_solar(schedule_name):
            window = solar_calc.get_schedule_window(schedule_name)
            if window["start"] <= current_time <= window["end"]:
                active_schedules.append(schedule_name)
        elif schedule_name == ScheduleType.DAYTIME:
            start_time, end_time = parse_time_range(schedule_config, schedule_name)

            if start_time is not None and end_time is not None:
                if start_time <= current_time.time() <= end_time:
                    active_schedules.append(schedule_name)

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
async def list_timelapses():
    """List available timelapse videos"""
    video_dir = Path("/data/timelapses")

    if not video_dir.exists():
        return []

    timelapses = []
    for video_file in video_dir.glob("*.mp4"):
        stat = video_file.stat()
        timelapses.append(
            {
                "name": video_file.stem,
                "url": f"/timelapses/{video_file.name}",
                "size": f"{stat.st_size / 1024 / 1024:.1f} MB",
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    # Sort by creation time, newest first
    timelapses.sort(key=lambda x: x["created"], reverse=True)

    return timelapses


@app.get("/profiles")
async def get_all_profiles(request: Request):
    """Get latest images for all 6 profiles with descriptions and image counts"""
    config = request.app.state.config
    pi_host = config.get("pi.host")

    # Profile descriptions
    descriptions = {
        "a": "Auto + Center-Weighted",
        "b": "Daylight WB Fixed",
        "c": "Conservative Adaptive",
        "d": "Warm Dramatic",
        "e": "Balanced Adaptive",
        "f": "Spot Metering (Mountains)",
    }

    profiles = []
    local_images_dir = Path("/data/images")
    url_builder = get_url_builder()

    # Check local images first, fallback to Pi
    for profile in ["a", "b", "c", "d", "e", "f"]:
        profile_dir = local_images_dir / f"profile-{profile}"

        # Try local images first
        if profile_dir.exists():
            image_files = sorted(
                profile_dir.glob("capture_*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True
            )
            if image_files:
                latest_file = image_files[0]
                profiles.append(
                    {
                        "profile": profile,
                        "description": descriptions[profile],
                        "image_url": url_builder.image(profile, latest_file.name, source="backend"),
                        "timestamp": latest_file.stat().st_mtime * 1000,
                        "image_count": len(image_files),
                    }
                )
                continue

        # Fallback to Pi if no local images
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(url_builder.pi(f"/latest-image?profile={profile}"))
                if response.status_code == 200:
                    data = response.json()
                    if data.get("image_url"):
                        profiles.append(
                            {
                                "profile": profile,
                                "description": descriptions[profile],
                                "image_url": url_builder.pi(data["image_url"]),
                                "timestamp": data.get("timestamp"),
                                "image_count": data.get("image_count", 0),
                            }
                        )
        except Exception as e:
            logger.debug(f"Could not fetch profile {profile}: {e}")

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

    # Determine active schedules
    active_schedules = []
    for schedule_name, schedule_config in schedules_config.items():
        if not schedule_config.get("enabled", True):
            continue

        if ScheduleType.is_solar(schedule_name):
            window = solar_calc.get_schedule_window(schedule_name, current_time)
            is_active = window["start"] <= current_time <= window["end"]
            if is_active:
                active_schedules.append(
                    {
                        "name": schedule_name,
                        "type": "solar",
                        "window": {
                            "start": window["start"].isoformat(),
                            "end": window["end"].isoformat(),
                        },
                        "interval_seconds": schedule_config.get("interval_seconds", 30),
                    }
                )
        elif schedule_name == ScheduleType.DAYTIME:
            start_time, end_time = parse_time_range(schedule_config, schedule_name)
            if start_time and end_time:
                if start_time <= current_time.time() <= end_time:
                    active_schedules.append(
                        {
                            "name": schedule_name,
                            "type": "time_of_day",
                            "window": {"start": f"{start_time}", "end": f"{end_time}"},
                            "interval_seconds": schedule_config.get("interval_seconds", 30),
                        }
                    )

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
            "profiles_configured": ["a", "b", "c", "d", "e", "f"],
        },
        "system": {"backend_version": "2.0.0", "mode": "development", "scheduler_running": True},
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
