"""Camera interface abstraction for multi-camera support."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import asyncio

from .camera_types import (
    CameraCapability,
    CaptureSettings,
    CaptureResult,
    CameraSpecs,
    EnvironmentalConditions,
)


class CameraInterface(ABC):
    """Abstract base class for all camera implementations."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize camera with configuration."""
        self._config = config
        self._is_initialized = False
        self._specs: Optional[CameraSpecs] = None

    @property
    def is_initialized(self) -> bool:
        """Check if camera is initialized and ready."""
        return self._is_initialized

    @property
    def specs(self) -> Optional[CameraSpecs]:
        """Get camera specifications."""
        return self._specs

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize camera hardware and prepare for capture."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown camera and release resources."""
        pass

    @abstractmethod
    async def capture_single(self, settings: CaptureSettings) -> CaptureResult:
        """Capture a single image with the given settings."""
        pass

    @abstractmethod
    async def capture_sequence(self, settings_list: List[CaptureSettings]) -> CaptureResult:
        """Capture a sequence of images (HDR, focus stacking, etc.)."""
        pass

    @abstractmethod
    def supports_capability(self, capability: CameraCapability) -> bool:
        """Check if camera supports a specific capability."""
        pass

    @abstractmethod
    async def get_preview_frame(self) -> Optional[bytes]:
        """Get a preview frame for composition and monitoring."""
        pass

    @abstractmethod
    async def autofocus(self, timeout_ms: int = 2000) -> bool:
        """Perform autofocus operation. Returns success status."""
        pass

    @abstractmethod
    async def get_current_settings(self) -> CaptureSettings:
        """Get the current camera settings."""
        pass

    @abstractmethod
    async def set_capture_settings(self, settings: CaptureSettings) -> bool:
        """Apply capture settings to camera. Returns success status."""
        pass

    # Optional methods with default implementations

    async def optimize_settings_for_conditions(
        self, base_settings: CaptureSettings, conditions: EnvironmentalConditions
    ) -> CaptureSettings:
        """
        Optimize capture settings based on environmental conditions.
        Default implementation returns base settings unchanged.
        """
        return base_settings

    async def assess_image_quality(self, image_path: str) -> float:
        """
        Assess the quality of a captured image (0.0 to 1.0).
        Default implementation returns 0.5 (unknown quality).
        """
        return 0.5

    def get_processing_hints(self, settings: CaptureSettings) -> Dict[str, Any]:
        """
        Generate processing hints based on capture settings.
        Default implementation returns empty hints.
        """
        return {}

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._is_initialized:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._is_initialized:
            await self.shutdown()


class CameraFactory:
    """Factory class for camera creation and auto-detection."""

    _registered_cameras: Dict[str, type] = {}

    @classmethod
    def register_camera(cls, camera_type: str, camera_class: type) -> None:
        """Register a camera implementation."""
        cls._registered_cameras[camera_type] = camera_class

    @classmethod
    def create_camera(cls, camera_type: str, config: Dict[str, Any]) -> CameraInterface:
        """Create a camera instance of the specified type."""
        if camera_type not in cls._registered_cameras:
            raise ValueError(f"Unknown camera type: {camera_type}")

        camera_class = cls._registered_cameras[camera_type]
        return camera_class(config)

    @classmethod
    async def auto_detect_camera(cls, config_dir: Optional[str] = None) -> CameraInterface:
        """
        Auto-detect and initialize the first available camera.
        Returns the first successfully initialized camera.
        """
        import os
        from .config_manager import CameraConfigManager

        config_manager = CameraConfigManager(config_dir)

        # Check environment for camera preference
        skylapse_env = os.getenv("SKYLAPSE_ENV", "production").lower()
        mock_camera_enabled = os.getenv("MOCK_CAMERA", "false").lower() in ("true", "1", "yes")

        # In development environment, prefer mock camera
        if skylapse_env == "development" or mock_camera_enabled:
            detection_order = ["mock_camera", "arducam_imx519", "pi_camera_v3", "pi_camera_v2"]
        else:
            # Try cameras in priority order: Arducam IMX519, Pi Camera v3/v2, Mock
            detection_order = ["arducam_imx519", "pi_camera_v3", "pi_camera_v2", "mock_camera"]

        for camera_type in detection_order:
            if camera_type not in cls._registered_cameras:
                continue

            try:
                config = config_manager.get_config_for_camera(camera_type)
                camera = cls.create_camera(camera_type, config)
                await camera.initialize()
                return camera
            except Exception as e:
                # Log the error but continue trying other cameras
                print(f"Failed to initialize {camera_type}: {e}")
                continue

        raise RuntimeError("No supported camera found or all initialization attempts failed")

    @classmethod
    def list_registered_cameras(cls) -> List[str]:
        """List all registered camera types."""
        return list(cls._registered_cameras.keys())

    @classmethod
    def get_camera_info(cls, camera_type: str) -> Dict[str, Any]:
        """Get information about a specific camera type."""
        if camera_type not in cls._registered_cameras:
            raise ValueError(f"Unknown camera type: {camera_type}")

        camera_class = cls._registered_cameras[camera_type]
        return {
            "type": camera_type,
            "class": camera_class.__name__,
            "module": camera_class.__module__,
            "docstring": camera_class.__doc__,
        }
