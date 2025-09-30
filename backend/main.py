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
from contextlib import asynccontextmanager
from datetime import datetime, time

import httpx
import uvicorn
from config import Config
from exposure import ExposureCalculator
from fastapi import FastAPI, Request
from schedule_types import ScheduleType
from solar import SolarCalculator

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


async def scheduler_loop(app: FastAPI):
    """
    Main scheduler loop - checks every 30 seconds if capture is needed.

    This is the brain of the system. Every 30 seconds:
    1. Get current time
    2. Check each enabled schedule
    3. Determine if we should capture now
    4. Calculate optimal camera settings (rotating through profiles A/B/C/D)
    5. Send capture command to Pi
    """
    logger.info("Scheduler loop running...")

    # Get references from app state
    config = app.state.config
    solar_calc = app.state.solar_calc
    exposure_calc = app.state.exposure_calc

    # Track last capture times per schedule to avoid duplicates
    last_captures = {}

    # Profile rotation counter (A → B → C → D → E → F → A...)
    profile_counter = 0
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
                    # Get current profile for this capture
                    current_profile = profiles[profile_counter % len(profiles)]

                    logger.info(
                        f"📸 Triggering capture for {schedule_name} [Profile {current_profile.upper()}]"
                    )

                    # Calculate exposure settings for current profile
                    settings = exposure_calc.calculate_settings(
                        schedule_name, current_time, profile=current_profile
                    )

                    # Send capture command to Pi
                    success = await trigger_capture(schedule_name, settings, config)

                    if success:
                        last_captures[schedule_name] = current_time
                        profile_counter += 1  # Rotate to next profile
                        logger.info(
                            f"✓ {schedule_name} capture successful [Profile {current_profile.upper()}] (ISO {settings['iso']}, {settings['shutter_speed']}, EV{settings['exposure_compensation']:+.1f})"
                        )
                    else:
                        logger.error(f"✗ {schedule_name} capture failed")

            # Sleep for 30 seconds before next check
            await asyncio.sleep(30)

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
