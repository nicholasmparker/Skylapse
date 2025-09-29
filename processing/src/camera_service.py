"""
Camera Service for Skylapse Mountain Timelapse System
Handles camera control, streaming, and capture operations
"""

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

import aiofiles
import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CameraSettings:
    """Camera settings configuration"""

    iso: int = 800
    shutter_speed: str = "1/60"  # e.g., "1/60", "2", "30"
    aperture: str = "f/2.8"
    white_balance: str = "auto"  # auto, daylight, cloudy, tungsten
    focus_mode: str = "auto"  # auto, manual, infinity
    image_format: str = "JPEG"
    resolution: str = "1920x1080"  # width x height

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CameraStatus:
    """Current camera status"""

    connected: bool = False
    model: str = "Unknown"
    battery_level: Optional[int] = None
    storage_free: Optional[float] = None  # GB
    temperature: Optional[float] = None  # Celsius
    last_capture_time: Optional[str] = None
    captures_today: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MockCamera:
    """Mock camera for development - simulates real camera behavior"""

    def __init__(self):
        self.connected = False
        self.settings = CameraSettings()
        self.status = CameraStatus()
        self.capturing = False
        self.capture_count = 0

    async def connect(self) -> bool:
        """Connect to the camera"""
        try:
            # Simulate connection delay
            await asyncio.sleep(0.5)
            self.connected = True
            self.status.connected = True
            self.status.model = "Mock Camera Pro"
            self.status.battery_level = 85
            self.status.storage_free = 32.5
            self.status.temperature = 22.5
            logger.info("Mock camera connected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to mock camera: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the camera"""
        self.connected = False
        self.status.connected = False
        logger.info("Mock camera disconnected")

    async def get_live_frame(self) -> Optional[bytes]:
        """Get a live frame from the camera for streaming"""
        if not self.connected:
            return None

        try:
            # Generate a mock image with timestamp and settings overlay
            height, width = 720, 1280
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # Create gradient background (mountain-like)
            for y in range(height):
                intensity = int(50 + (y / height) * 100)
                frame[y, :] = [intensity // 3, intensity // 2, intensity]

            # Add timestamp overlay
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(
                frame,
                f"Live Preview - {timestamp}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            # Add settings overlay
            settings_text = (
                f"ISO:{self.settings.iso} {self.settings.shutter_speed} {self.settings.aperture}"
            )
            cv2.putText(
                frame,
                settings_text,
                (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2,
            )

            # Add capture indicator if capturing
            if self.capturing:
                cv2.circle(frame, (width - 50, 50), 20, (0, 0, 255), -1)
                cv2.putText(
                    frame,
                    "REC",
                    (width - 70, 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2,
                )

            # Encode frame as JPEG
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buffer.tobytes()

        except Exception as e:
            logger.error(f"Error generating live frame: {e}")
            return None

    async def capture_image(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Capture a high-resolution image"""
        if not self.connected:
            raise Exception("Camera not connected")

        self.capturing = True
        try:
            # Simulate capture delay
            await asyncio.sleep(0.2)

            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"

            # Create high-resolution mock image
            height, width = 2160, 3840  # 4K resolution
            image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

            # Add mountain-like gradient
            for y in range(height):
                intensity = int(30 + (y / height) * 150)
                image[y, :] = np.clip(
                    image[y, :] + [intensity // 4, intensity // 3, intensity // 2], 0, 255
                )

            # Save image
            capture_path = f"/tmp/{filename}"
            async with aiofiles.open(capture_path, "wb") as f:
                _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 95])
                await f.write(buffer.tobytes())

            # Update status
            self.capture_count += 1
            self.status.last_capture_time = datetime.now().isoformat()
            self.status.captures_today += 1

            capture_info = {
                "filename": filename,
                "path": capture_path,
                "timestamp": datetime.now().isoformat(),
                "settings": self.settings.to_dict(),
                "file_size": len(buffer.tobytes()),
                "resolution": f"{width}x{height}",
                "capture_number": self.capture_count,
            }

            logger.info(f"Image captured: {filename}")
            return capture_info

        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            raise
        finally:
            self.capturing = False

    async def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Update camera settings"""
        try:
            for key, value in new_settings.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
                    logger.info(f"Updated camera setting {key} = {value}")

            # Simulate settings application delay
            await asyncio.sleep(0.1)
            return True

        except Exception as e:
            logger.error(f"Error updating camera settings: {e}")
            return False

    def get_status(self) -> CameraStatus:
        """Get current camera status"""
        return self.status

    def get_settings(self) -> CameraSettings:
        """Get current camera settings"""
        return self.settings


class CameraService:
    """Main camera service for handling all camera operations"""

    def __init__(self):
        self.camera = MockCamera()  # In production, use real camera implementation
        self.streaming = False
        self.stream_clients = set()

    async def initialize(self) -> bool:
        """Initialize the camera service"""
        return await self.camera.connect()

    async def shutdown(self):
        """Shutdown the camera service"""
        await self.stop_streaming()
        await self.camera.disconnect()

    async def start_streaming(self):
        """Start MJPEG streaming"""
        if self.streaming:
            return

        self.streaming = True
        logger.info("Camera streaming started")

    async def stop_streaming(self):
        """Stop MJPEG streaming"""
        self.streaming = False
        self.stream_clients.clear()
        logger.info("Camera streaming stopped")

    async def generate_mjpeg_stream(self) -> AsyncGenerator[bytes, None]:
        """Generate MJPEG stream for web clients"""
        try:
            while self.streaming:
                frame = await self.camera.get_live_frame()
                if frame:
                    yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

                # Control frame rate (~30 FPS)
                await asyncio.sleep(1 / 30)

        except Exception as e:
            logger.error(f"Error in MJPEG stream generation: {e}")

    async def capture_image(
        self, settings_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Capture a single image with optional settings override"""
        # Apply temporary settings if provided
        original_settings = None
        if settings_override:
            original_settings = self.camera.get_settings()
            await self.camera.update_settings(settings_override)

        try:
            result = await self.camera.capture_image()
            logger.info(f"Manual capture completed: {result['filename']}")
            return result
        finally:
            # Restore original settings if they were overridden
            if original_settings:
                await self.camera.update_settings(original_settings.to_dict())

    async def update_settings(self, settings: Dict[str, Any]) -> bool:
        """Update camera settings"""
        return await self.camera.update_settings(settings)

    def get_status(self) -> Dict[str, Any]:
        """Get current camera status"""
        status = self.camera.get_status().to_dict()
        status["streaming"] = self.streaming
        status["connected_clients"] = len(self.stream_clients)
        return status

    def get_settings(self) -> Dict[str, Any]:
        """Get current camera settings"""
        return self.camera.get_settings().to_dict()

    def is_connected(self) -> bool:
        """Check if camera is connected"""
        return self.camera.connected


# Global camera service instance
camera_service = CameraService()
