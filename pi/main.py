"""
Skylapse Pi - Simple Capture Server

ONE JOB: Take photos when commanded to by the backend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from pathlib import Path
import logging
import os
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
            config = camera.create_still_configuration()
            camera.configure(config)

            # Set autofocus and white balance for best quality
            # AfMode: 2 = Continuous autofocus (keeps focus sharp)
            # AwbMode: 1 = Daylight white balance (consistent color across timelapse)
            camera.set_controls({
                "AfMode": 2,  # Continuous autofocus (0=manual, 1=auto, 2=continuous)
                "AwbMode": 1,  # Daylight white balance (1 = daylight, 0 = auto)
            })

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
    awb_mode: int = 1  # White balance mode (0=auto, 1=daylight)
    hdr_mode: int = 0  # HDR mode (0=off, 1=single exposure)
    bracket_count: int = 1  # Number of shots for bracketing (1=single, 3=bracket)
    bracket_ev: Optional[list] = None  # EV offsets for bracketing (e.g., [-1.0, 0.0, 1.0])

    @validator("iso")
    def validate_iso(cls, v):
        valid_isos = [100, 200, 400, 800, 1600, 3200]
        if v not in valid_isos:
            raise ValueError(f"ISO must be one of {valid_isos}")
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


@app.post("/capture", response_model=CaptureResponse)
async def capture_photo(settings: CaptureSettings):
    """
    Capture a single photo with the provided settings.

    Backend tells us EXACTLY what settings to use.
    We just execute and return the result.
    """
    # Check if camera is ready
    if not camera_ready:
        raise HTTPException(
            status_code=503,
            detail="Camera not ready - check service logs"
        )

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
                status="success",
                image_path=image_path,
                message="Capture successful (mock mode)"
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

                for i, ev_offset in enumerate(settings.bracket_ev[:settings.bracket_count]):
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
                    logger.info(f"✓ Bracket {i+1}/{settings.bracket_count} (EV{ev_offset:+.1f}): {image_path}")

                # Return path to the middle (properly exposed) image
                middle_idx = settings.bracket_count // 2
                image_path = bracket_paths[middle_idx]
                logger.info(f"✓ Bracketed capture complete: {settings.bracket_count} shots")

            else:
                # Single shot capture
                image_path = str(output_dir / f"capture_{timestamp}.jpg")
                shutter_us = parse_shutter_speed(settings.shutter_speed)

                controls = {
                    "ExposureTime": shutter_us,
                    "AnalogueGain": settings.iso / 100.0,
                    "AwbMode": settings.awb_mode,
                }

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
                status="success",
                image_path=image_path,
                message="Capture successful"
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
        "mock_mode": USE_MOCK_CAMERA
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

    # Return the most recent image
    return FileResponse(images[0], media_type="image/jpeg")


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
                "modified": datetime.fromtimestamp(img.stat().st_mtime).isoformat()
            }
            for img in images
        ]
    }


if __name__ == "__main__":
    # Run on all interfaces so backend can reach us
    uvicorn.run(app, host="0.0.0.0", port=8080)
