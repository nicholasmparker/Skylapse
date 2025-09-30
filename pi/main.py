"""
Skylapse Pi - Simple Capture Server

ONE JOB: Take photos when commanded to by the backend.

IMPORTANT: Camera implementation details are in CAMERA_IMPLEMENTATION.md
Current camera: ArduCam IMX519 (requires system-level picamera2)
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Skylapse Capture")

# Add CORS middleware to allow browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local viewer
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine if we're running on real hardware or in mock mode
USE_MOCK_CAMERA = os.getenv("MOCK_CAMERA", "false").lower() == "true"

# Initialize camera (global, will be started at app startup)
camera = None
camera_model = "Unknown"
camera_ready = False


def initialize_camera():
    """Initialize and start the camera once at application startup."""
    global camera, camera_model, camera_ready, USE_MOCK_CAMERA

    try:
        if not USE_MOCK_CAMERA:
            from picamera2 import Picamera2

            camera = Picamera2()
            camera_model = camera.camera_properties.get("Model", "Raspberry Pi Camera")

            # Configure camera for FULL RESOLUTION still images
            # IMX519: 4656x3496 (16MP) - requires gpu_mem=256 in /boot/firmware/config.txt
            # This Pi is dedicated to photography - maximum quality
            still_config = camera.create_still_configuration()
            camera.configure(still_config)

            # Set autofocus and white balance for best quality
            # AfMode: 2 = Continuous autofocus (keeps focus sharp)
            # AwbMode: 1 = Daylight white balance (consistent color across timelapse)
            camera.set_controls(
                {
                    "AfMode": 2,  # Continuous autofocus (0=manual, 1=auto, 2=continuous)
                    "AwbMode": 1,  # Daylight white balance (1 = daylight, 0 = auto)
                }
            )

            # Let autofocus settle before starting
            import time

            time.sleep(2)

            # Start camera once - it stays running
            camera.start()

            camera_ready = True
            logger.info(f"✓ Camera started: {camera_model}")
        else:
            camera_ready = True
            camera_model = "Mock Camera"
            logger.info("Running in MOCK mode - no real camera")

    except ImportError:
        logger.warning("picamera2 not available - running in MOCK mode")
        USE_MOCK_CAMERA = True
        camera_ready = True
        camera_model = "Mock Camera"
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}", exc_info=True)
        USE_MOCK_CAMERA = True
        camera_ready = False
        camera_model = "Mock Camera (Error)"


# Initialize at module load
initialize_camera()


class CaptureSettings(BaseModel):
    """Camera settings for a single capture"""

    iso: int
    shutter_speed: str  # e.g., "1/1000"
    exposure_compensation: float  # e.g., +0.7
    profile: str = "default"  # Profile name for folder organization (a, b, c, d, e, f)
    awb_mode: int = 1  # White balance mode (0=auto, 1=daylight, 2=cloudy, 6=custom)
    wb_temp: Optional[int] = None  # Color temperature in Kelvin (for awb_mode=6 custom)
    hdr_mode: int = 0  # HDR mode (0=off, 1=single exposure)
    bracket_count: int = 1  # Number of shots for bracketing (1=single, 3=bracket)
    bracket_ev: Optional[list] = None  # EV offsets for bracketing (e.g., [-1.0, 0.0, 1.0])

    @validator("iso")
    def validate_iso(cls, v):
        # ISO=0 means full auto mode
        if v == 0:
            return v
        valid_isos = [100, 200, 400, 800, 1600, 3200]
        if v not in valid_isos:
            raise ValueError(f"ISO must be 0 (auto) or one of {valid_isos}")
        return v

    @validator("exposure_compensation")
    def validate_ev(cls, v):
        if not -2.0 <= v <= 2.0:
            raise ValueError("Exposure compensation must be between -2.0 and +2.0")
        return v

    @validator("profile")
    def validate_profile(cls, v):
        valid_profiles = ["default", "a", "b", "c", "d", "e", "f"]
        if v not in valid_profiles:
            raise ValueError(f"Profile must be one of {valid_profiles}")
        return v

    @validator("bracket_count")
    def validate_bracket(cls, v):
        if v not in [1, 3, 5]:
            raise ValueError("bracket_count must be 1, 3, or 5")
        return v

    @validator("bracket_ev", always=True)
    def validate_bracket_ev(cls, v, values):
        """
        Validate bracket_ev list has correct length and values.

        Checks:
        - If bracket_count > 1, bracket_ev must exist
        - bracket_ev must have at least bracket_count values
        - All EV values must be floats in range -2.0 to +2.0
        """
        bracket_count = values.get("bracket_count", 1)

        # If bracketing is enabled, bracket_ev must be provided
        if bracket_count > 1:
            if v is None:
                raise ValueError(f"bracket_ev required when bracket_count={bracket_count}")

            if len(v) < bracket_count:
                raise ValueError(
                    f"bracket_ev must have at least {bracket_count} values, got {len(v)}"
                )

            # Validate each EV value is in valid range
            for ev in v:
                if not isinstance(ev, (int, float)):
                    raise ValueError(f"bracket_ev values must be numbers, got {type(ev)}")
                if not -2.0 <= ev <= 2.0:
                    raise ValueError(f"bracket_ev values must be in range -2.0 to +2.0, got {ev}")

        return v


class CaptureResponse(BaseModel):
    """Response from a capture request"""

    status: str
    image_path: Optional[str] = None
    message: Optional[str] = None


def parse_shutter_speed(shutter_str: str) -> int:
    """
    Convert shutter speed string to microseconds.

    Args:
        shutter_str: String like "1/1000" or "1/250"

    Returns:
        Shutter speed in microseconds
    """
    if "/" in shutter_str:
        numerator, denominator = shutter_str.split("/")
        seconds = int(numerator) / int(denominator)
    else:
        seconds = float(shutter_str)

    return int(seconds * 1_000_000)  # Convert to microseconds


class MeterResponse(BaseModel):
    """Metering data from camera auto-exposure"""

    lux: float  # Scene brightness
    exposure_time_us: int  # Auto-calculated exposure time (microseconds)
    analogue_gain: float  # Auto-calculated ISO gain (ISO = gain * 100)
    suggested_iso: int  # ISO value (100, 200, 400, etc)
    suggested_shutter: str  # Human-readable shutter (e.g., "1/500")


@app.get("/meter", response_model=MeterResponse)
async def meter_scene():
    """
    Meter the scene using camera's auto-exposure.

    Returns suggested exposure settings based on current scene brightness.
    Backend can use these as a starting point for profile-specific adjustments.
    """
    if not camera_ready:
        raise HTTPException(status_code=503, detail="Camera not ready")

    if USE_MOCK_CAMERA:
        # Mock metering data
        return MeterResponse(
            lux=800.0,
            exposure_time_us=2000,
            analogue_gain=4.0,
            suggested_iso=400,
            suggested_shutter="1/500",
        )

    try:
        # Capture metadata with camera in auto mode
        # The camera will meter the scene and tell us what exposure it would use
        metadata = camera.capture_metadata()

        # Extract metering values
        lux = metadata.get("Lux", 0.0)
        exposure_time = metadata.get("ExposureTime", 0)  # microseconds
        analogue_gain = metadata.get("AnalogueGain", 1.0)

        # Convert to readable ISO (gain * 100)
        raw_iso = int(analogue_gain * 100)

        # Round to nearest valid ISO
        valid_isos = [100, 200, 400, 800, 1600, 3200]
        suggested_iso = min(valid_isos, key=lambda x: abs(x - raw_iso))

        # Convert exposure time to shutter speed string
        if exposure_time > 0:
            # Calculate fraction (e.g., 2000μs = 1/500s)
            shutter_seconds = exposure_time / 1_000_000
            shutter_fraction = int(1 / shutter_seconds)
            suggested_shutter = f"1/{shutter_fraction}"
        else:
            suggested_shutter = "1/500"  # fallback

        logger.info(
            f"📊 Scene metered: Lux={lux:.1f}, " f"ISO={suggested_iso}, Shutter={suggested_shutter}"
        )

        return MeterResponse(
            lux=lux,
            exposure_time_us=exposure_time,
            analogue_gain=analogue_gain,
            suggested_iso=suggested_iso,
            suggested_shutter=suggested_shutter,
        )

    except Exception as e:
        logger.error(f"Metering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metering failed: {str(e)}")


@app.post("/capture", response_model=CaptureResponse)
async def capture_photo(settings: CaptureSettings):
    """
    Capture a single photo with the provided settings.

    Backend tells us EXACTLY what settings to use.
    We just execute and return the result.
    """
    # Check if camera is ready
    if not camera_ready:
        raise HTTPException(status_code=503, detail="Camera not ready - check service logs")

    try:
        logger.info(
            f"📸 Capture request: ISO {settings.iso}, "
            f"shutter {settings.shutter_speed}, EV {settings.exposure_compensation:+.1f}"
        )

        if USE_MOCK_CAMERA:
            # Mock mode: Just simulate capture
            image_path = f"/tmp/mock_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            logger.info(f"Mock capture complete: {image_path}")

            return CaptureResponse(
                status="success", image_path=image_path, message="Capture successful (mock mode)"
            )

        else:
            # Real camera capture
            # Create output directory based on profile
            home_dir = Path.home()
            if settings.profile == "default":
                output_dir = home_dir / "skylapse-images"
            else:
                output_dir = home_dir / "skylapse-images" / f"profile-{settings.profile}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate base timestamp for this capture sequence
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Handle bracketing (multiple exposures)
            if settings.bracket_count > 1 and settings.bracket_ev:
                # HDR Bracketing: capture multiple shots at different exposures
                bracket_paths = []
                shutter_us = parse_shutter_speed(settings.shutter_speed)

                for i, ev_offset in enumerate(settings.bracket_ev[: settings.bracket_count]):
                    image_path = str(output_dir / f"capture_{timestamp}_bracket{i}.jpg")

                    controls = {
                        "ExposureTime": shutter_us,
                        "AnalogueGain": settings.iso / 100.0,
                        "AwbMode": settings.awb_mode,
                        "ExposureValue": settings.exposure_compensation + ev_offset,
                    }

                    camera.set_controls(controls)
                    camera.capture_file(image_path)
                    bracket_paths.append(image_path)
                    logger.info(
                        f"✓ Bracket {i+1}/{settings.bracket_count} (EV{ev_offset:+.1f}): {image_path}"
                    )

                # Return path to the middle (properly exposed) image
                middle_idx = settings.bracket_count // 2
                image_path = bracket_paths[middle_idx]
                logger.info(f"✓ Bracketed capture complete: {settings.bracket_count} shots")

            else:
                # Single shot capture
                image_path = str(output_dir / f"capture_{timestamp}.jpg")

                # Check if using auto mode (ISO=0 means full auto)
                if settings.iso == 0:
                    # Full auto mode - let camera decide everything
                    controls = {
                        "AwbMode": settings.awb_mode,  # Still respect WB setting
                        "AeEnable": True,  # Enable auto-exposure
                    }
                    logger.info("📸 Using full auto-exposure mode")
                else:
                    # Manual exposure mode
                    shutter_us = parse_shutter_speed(settings.shutter_speed)
                    controls = {
                        "ExposureTime": shutter_us,
                        "AnalogueGain": settings.iso / 100.0,
                        "AwbMode": settings.awb_mode,
                    }

                    # Add custom WB temperature if using custom mode (awb_mode=6)
                    if settings.awb_mode == 6 and settings.wb_temp:
                        controls["ColourTemperature"] = settings.wb_temp
                        logger.info(f"🎨 Using custom WB: {settings.wb_temp}K")

                    # Add HDR mode if requested
                    if settings.hdr_mode > 0:
                        controls["HdrMode"] = settings.hdr_mode

                    # IMX519 supports ExposureValue for fine-tuning (±8 stops)
                    if settings.exposure_compensation != 0.0:
                        controls["ExposureValue"] = settings.exposure_compensation

                camera.set_controls(controls)
                camera.capture_file(image_path)
                logger.info(f"✓ Capture complete: {image_path}")

            return CaptureResponse(
                status="success", image_path=image_path, message="Capture successful"
            )

    except ValueError as e:
        logger.error(f"Invalid settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Capture failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Report camera status to backend"""
    return {
        "status": "online",
        "camera_model": camera_model,
        "camera_ready": camera_ready,
        "mock_mode": USE_MOCK_CAMERA,
    }


@app.get("/health")
async def health_check():
    """Simple health check for monitoring"""
    return {"status": "ok"}


@app.get("/images/profile-{profile}/latest.jpg")
async def get_latest_image(profile: str):
    """Get the latest captured image from a profile folder"""
    home_dir = Path.home()
    profile_dir = home_dir / "skylapse-images" / f"profile-{profile}"

    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile {profile} folder not found")

    # Get all jpg files sorted by modification time
    images = sorted(profile_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not images:
        raise HTTPException(status_code=404, detail=f"No images found in profile {profile}")

    # For bracketed captures, find the middle exposure (bracket1)
    # Bracket files are named: capture_TIMESTAMP_bracket0.jpg, capture_TIMESTAMP_bracket1.jpg, etc.
    latest_image = images[0]

    # Check if this is a bracketed image
    if "_bracket" in latest_image.name:
        # Extract the timestamp and find bracket1 (middle exposure)
        base_name = latest_image.name.split("_bracket")[0]
        middle_bracket = profile_dir / f"{base_name}_bracket1.jpg"

        if middle_bracket.exists():
            latest_image = middle_bracket
            logger.info(f"Serving middle bracket exposure for {profile}: {middle_bracket.name}")

    # Return the most recent non-bracketed image, or middle bracket if bracketed
    return FileResponse(latest_image, media_type="image/jpeg")


@app.get("/images/profile-{profile}/info")
async def get_latest_image_info(profile: str):
    """Get metadata about the latest image in a profile folder"""
    home_dir = Path.home()
    profile_dir = home_dir / "skylapse-images" / f"profile-{profile}"

    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile {profile} folder not found")

    # Get all jpg files sorted by modification time
    images = sorted(profile_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not images:
        raise HTTPException(status_code=404, detail=f"No images found in profile {profile}")

    latest_image = images[0]

    # Check if this is a bracketed image - if so, use middle bracket
    if "_bracket" in latest_image.name:
        base_name = latest_image.name.split("_bracket")[0]
        middle_bracket = profile_dir / f"{base_name}_bracket1.jpg"
        if middle_bracket.exists():
            latest_image = middle_bracket

    stat = latest_image.stat()

    return {
        "filename": latest_image.name,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "profile": profile,
    }


@app.get("/images/profile-{profile}/list")
async def list_profile_images(profile: str):
    """List all images in a profile folder"""
    home_dir = Path.home()
    profile_dir = home_dir / "skylapse-images" / f"profile-{profile}"

    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile {profile} folder not found")

    # Get all jpg files sorted by modification time
    images = sorted(profile_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)

    return {
        "profile": profile,
        "count": len(images),
        "images": [
            {
                "filename": img.name,
                "size_bytes": img.stat().st_size,
                "modified": datetime.fromtimestamp(img.stat().st_mtime).isoformat(),
            }
            for img in images
        ],
    }


if __name__ == "__main__":
    # Run on all interfaces so backend can reach us
    uvicorn.run(app, host="0.0.0.0", port=8080)
