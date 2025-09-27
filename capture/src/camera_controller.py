"""Main camera controller for the capture service."""

# import asyncio  # Unused
import logging
import time
# from pathlib import Path  # Unused
from typing import Any, Dict, List, Optional

# Import camera implementations
from . import cameras  # This triggers camera registration
from .camera_interface import CameraFactory, CameraInterface
from .camera_types import (
    CameraCapability,
    CameraError,
    CameraInitializationError,
    CaptureResult,
    CaptureSettings,
    EnvironmentalConditions,
)
from .config_manager import CameraConfigManager, SystemConfigManager

logger = logging.getLogger(__name__)


class CameraController:
    """Main controller for camera operations in the capture service."""

    def __init__(self, config_dir: Optional[str] = None, system_config_file: Optional[str] = None):
        """Initialize camera controller."""
        self._camera: Optional[CameraInterface] = None
        self._camera_config_manager = CameraConfigManager(config_dir)
        self._system_config_manager = SystemConfigManager(system_config_file)
        self._is_running = False
        self._performance_metrics = {
            "total_captures": 0,
            "successful_captures": 0,
            "failed_captures": 0,
            "average_capture_time_ms": 0.0,
            "last_capture_time": None,
        }

    @property
    def is_initialized(self) -> bool:
        """Check if camera is initialized and ready."""
        return self._camera is not None and self._camera.is_initialized

    @property
    def camera(self) -> Optional[CameraInterface]:
        """Get the current camera instance."""
        return self._camera

    @property
    def performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._performance_metrics.copy()

    async def initialize_camera(self, camera_type: Optional[str] = None) -> None:
        """Initialize camera system."""
        logger.info("Initializing camera controller")

        try:
            if camera_type:
                # Initialize specific camera type
                config = self._camera_config_manager.get_config_for_camera(camera_type)
                self._camera = CameraFactory.create_camera(camera_type, config)
                await self._camera.initialize()
                logger.info(f"Initialized specific camera: {camera_type}")
            else:
                # Auto-detect camera
                self._camera = await CameraFactory.auto_detect_camera()
                logger.info(f"Auto-detected camera: {self._camera.specs.model}")

            # Log camera capabilities
            if self._camera.specs:
                capabilities = [cap.name for cap in self._camera.specs.capabilities]
                logger.info(f"Camera capabilities: {', '.join(capabilities)}")

            self._is_running = True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise CameraInitializationError(f"Camera initialization failed: {e}")

    async def shutdown(self) -> None:
        """Shutdown camera controller."""
        logger.info("Shutting down camera controller")
        self._is_running = False

        if self._camera:
            await self._camera.shutdown()
            self._camera = None

        logger.info("Camera controller shutdown complete")

    async def capture_optimized(
        self,
        conditions: Optional[EnvironmentalConditions] = None,
        base_settings: Optional[CaptureSettings] = None,
    ) -> CaptureResult:
        """
        Capture image with optimized settings based on environmental conditions.
        """
        if not self.is_initialized:
            raise CameraError("Camera not initialized")

        start_time = time.time()

        try:
            # Use default settings if none provided
            if base_settings is None:
                base_settings = CaptureSettings()

            # Optimize settings for current conditions
            if conditions and hasattr(self._camera, "optimize_settings_for_conditions"):
                optimized_settings = await self._camera.optimize_settings_for_conditions(
                    base_settings, conditions
                )
            else:
                optimized_settings = base_settings

            # Perform autofocus if needed
            if optimized_settings.autofocus_enabled:
                focus_timeout = self._system_config_manager.get("capture.focus_timeout_ms", 2000)
                focus_success = await self._camera.autofocus(timeout_ms=focus_timeout)
                if not focus_success:
                    logger.warning("Autofocus failed, continuing with current focus")

            # Apply settings to camera
            settings_applied = await self._camera.set_capture_settings(optimized_settings)
            if not settings_applied:
                logger.warning("Failed to apply all camera settings")

            # Capture image
            if optimized_settings.hdr_bracket_stops:
                # HDR sequence capture
                settings_sequence = self._create_hdr_sequence(optimized_settings)
                result = await self._camera.capture_sequence(settings_sequence)
            else:
                # Single image capture
                result = await self._camera.capture_single(optimized_settings)

            # Update performance metrics
            self._update_performance_metrics(True, result.capture_time_ms)

            logger.info(
                f"Capture successful: {len(result.file_paths)} images, "
                f"{result.capture_time_ms:.1f}ms"
            )

            return result

        except Exception as e:
            # Update performance metrics for failure
            capture_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(False, capture_time)

            logger.error(f"Capture failed: {e}")
            raise CameraError(f"Capture operation failed: {e}")

    def _create_hdr_sequence(self, base_settings: CaptureSettings) -> List[CaptureSettings]:
        """Create HDR bracketing sequence from base settings."""
        if not base_settings.hdr_bracket_stops:
            return [base_settings]

        sequence = []
        base_exposure = base_settings.exposure_time_us or 1000  # Default 1ms

        for stop in base_settings.hdr_bracket_stops:
            exposure_multiplier = 2**stop  # Each stop doubles/halves exposure
            bracketed_settings = CaptureSettings(
                exposure_time_us=int(base_exposure * exposure_multiplier),
                iso=base_settings.iso,
                exposure_compensation=base_settings.exposure_compensation,
                focus_distance_mm=base_settings.focus_distance_mm,
                autofocus_enabled=False,  # Disable AF after first frame
                white_balance_k=base_settings.white_balance_k,
                white_balance_mode=base_settings.white_balance_mode,
                quality=base_settings.quality,
                format=base_settings.format,
            )
            sequence.append(bracketed_settings)

        return sequence

    async def capture_single_image(self, settings: CaptureSettings) -> CaptureResult:
        """Capture a single image with specified settings."""
        if not self.is_initialized:
            raise CameraError("Camera not initialized")

        try:
            # Apply settings
            await self._camera.set_capture_settings(settings)

            # Capture
            result = await self._camera.capture_single(settings)

            # Update metrics
            self._update_performance_metrics(True, result.capture_time_ms)

            return result

        except Exception as e:
            self._update_performance_metrics(False, 0)
            raise CameraError(f"Single image capture failed: {e}")

    async def capture_hdr_sequence(
        self, stops: List[float], base_settings: CaptureSettings
    ) -> CaptureResult:
        """Capture HDR bracketed sequence."""
        if not self.is_initialized:
            raise CameraError("Camera not initialized")

        if not self._camera.supports_capability(CameraCapability.HDR_BRACKETING):
            raise CameraError("Camera does not support HDR bracketing")

        try:
            # Create HDR settings
            hdr_settings = CaptureSettings(
                exposure_time_us=base_settings.exposure_time_us,
                iso=base_settings.iso,
                exposure_compensation=base_settings.exposure_compensation,
                focus_distance_mm=base_settings.focus_distance_mm,
                autofocus_enabled=base_settings.autofocus_enabled,
                white_balance_k=base_settings.white_balance_k,
                white_balance_mode=base_settings.white_balance_mode,
                quality=base_settings.quality,
                format=base_settings.format,
                hdr_bracket_stops=stops,
            )

            return await self.capture_optimized(base_settings=hdr_settings)

        except Exception as e:
            raise CameraError(f"HDR sequence capture failed: {e}")

    async def get_live_preview(self) -> Optional[bytes]:
        """Get live preview frame from camera."""
        if not self.is_initialized:
            return None

        try:
            return await self._camera.get_preview_frame()
        except Exception as e:
            logger.error(f"Failed to get preview frame: {e}")
            return None

    def _update_performance_metrics(self, success: bool, capture_time_ms: float) -> None:
        """Update performance tracking metrics."""
        self._performance_metrics["total_captures"] += 1
        self._performance_metrics["last_capture_time"] = time.time()

        if success:
            self._performance_metrics["successful_captures"] += 1
        else:
            self._performance_metrics["failed_captures"] += 1

        # Update rolling average capture time
        total_successful = self._performance_metrics["successful_captures"]
        if total_successful > 0:
            current_avg = self._performance_metrics["average_capture_time_ms"]
            self._performance_metrics["average_capture_time_ms"] = (
                current_avg * (total_successful - 1) + capture_time_ms
            ) / total_successful

    async def get_camera_status(self) -> Dict[str, Any]:
        """Get detailed camera status information."""
        status = {
            "initialized": self.is_initialized,
            "running": self._is_running,
            "camera_model": None,
            "capabilities": [],
            "current_settings": None,
            "performance": self._performance_metrics,
        }

        if self._camera and self._camera.specs:
            status["camera_model"] = self._camera.specs.model
            status["capabilities"] = [cap.name for cap in self._camera.specs.capabilities]

            try:
                status["current_settings"] = await self._camera.get_current_settings()
            except Exception as e:
                logger.warning(f"Failed to get current settings: {e}")

        return status

    async def test_capture(self) -> Dict[str, Any]:
        """Perform a test capture and return results."""
        if not self.is_initialized:
            raise CameraError("Camera not initialized for testing")

        test_settings = CaptureSettings(quality=85, format="JPEG", iso=100)

        try:
            result = await self.capture_single_image(test_settings)

            return {
                "success": True,
                "capture_time_ms": result.capture_time_ms,
                "file_paths": result.file_paths,
                "image_count": len(result.file_paths),
                "metadata": result.metadata,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "capture_time_ms": 0,
                "file_paths": [],
                "image_count": 0,
            }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_camera()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
