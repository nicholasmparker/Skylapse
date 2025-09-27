"""Mock camera implementation for testing and development."""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..camera_interface import CameraInterface
from ..camera_types import (
    CameraCapability,
    CameraInitializationError,
    CameraSpecs,
    CaptureError,
    CaptureResult,
    CaptureSettings,
    EnvironmentalConditions,
)

logger = logging.getLogger(__name__)


class MockCamera(CameraInterface):
    """Mock camera implementation for testing and development."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock camera with configuration."""
        super().__init__(config)
        self._current_settings = CaptureSettings()
        # Support both flat and nested config formats
        mock_config = config.get("mock", {})
        self._capture_delay_ms = config.get(
            "mock_capture_delay_ms", mock_config.get("capture_delay_ms", 10)
        )
        self._simulate_failures = config.get(
            "mock_simulate_failures", mock_config.get("simulate_failures", False)
        )
        self._failure_rate = config.get("mock_failure_rate", mock_config.get("failure_rate", 0.1))
        self._output_dir = Path(
            config.get("mock_output_dir", mock_config.get("output_dir", "/tmp/skylapse_mock"))
        )
        self._image_counter = 0

    async def initialize(self) -> None:
        """Initialize mock camera."""
        logger.info("Initializing mock camera")

        # Simulate initialization delay
        await asyncio.sleep(0.1)

        # Create output directory
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Set up camera specs
        self._specs = CameraSpecs(
            model="Mock Camera v1.0",
            resolution_mp=16.0,
            max_resolution=(4656, 3496),
            sensor_size_mm=(7.4, 5.6),
            focal_length_mm=4.28,
            base_iso=100,
            max_iso=800,
            iso_invariance_point=800,
            max_exposure_us=10_000_000,  # 10 seconds
            focus_range_mm=(100.0, float("inf")),
            hyperfocal_distance_mm=1830,
            capabilities=[
                CameraCapability.AUTOFOCUS,
                CameraCapability.MANUAL_FOCUS,
                CameraCapability.HDR_BRACKETING,
                CameraCapability.FOCUS_STACKING,
                CameraCapability.RAW_CAPTURE,
                CameraCapability.LIVE_PREVIEW,
            ],
        )

        self._is_initialized = True
        logger.info("Mock camera initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown mock camera."""
        logger.info("Shutting down mock camera")
        self._is_initialized = False
        await asyncio.sleep(0.05)  # Simulate shutdown delay

    async def capture_single(self, settings: CaptureSettings) -> CaptureResult:
        """Capture a single mock image."""
        if not self._is_initialized:
            raise CaptureError("Camera not initialized")

        # Simulate potential failures
        if self._simulate_failures and self._should_fail():
            raise CaptureError("Simulated capture failure")

        start_time = time.time()

        # Simulate capture delay
        await asyncio.sleep(self._capture_delay_ms / 1000)

        # Generate mock image file
        image_path = self._generate_mock_image(settings)

        capture_time_ms = (time.time() - start_time) * 1000

        # Create metadata
        metadata = {
            "camera_model": self._specs.model,
            "timestamp": time.time(),
            "settings_applied": settings,
            "mock_capture": True,
        }

        # Store current settings
        self._current_settings = settings

        return CaptureResult(
            file_paths=[str(image_path)],
            metadata=metadata,
            actual_settings=settings,
            capture_time_ms=capture_time_ms,
            quality_score=0.85,  # Mock quality score
        )

    async def capture_sequence(self, settings_list: List[CaptureSettings]) -> CaptureResult:
        """Capture a sequence of mock images."""
        if not self._is_initialized:
            raise CaptureError("Camera not initialized")

        if not settings_list:
            raise CaptureError("No capture settings provided for sequence")

        start_time = time.time()
        file_paths = []

        for i, settings in enumerate(settings_list):
            # Simulate inter-frame delay
            if i > 0:
                await asyncio.sleep(0.05)  # 50ms between frames

            # Generate mock image
            image_path = self._generate_mock_image(settings, sequence_index=i)
            file_paths.append(str(image_path))

        capture_time_ms = (time.time() - start_time) * 1000

        # Create metadata for sequence
        metadata = {
            "camera_model": self._specs.model,
            "timestamp": time.time(),
            "sequence_count": len(settings_list),
            "sequence_type": self._detect_sequence_type(settings_list),
            "mock_capture": True,
        }

        return CaptureResult(
            file_paths=file_paths,
            metadata=metadata,
            actual_settings=settings_list[0],  # Use first settings as primary
            capture_time_ms=capture_time_ms,
            quality_score=0.87,  # Slightly higher for sequences
        )

    def supports_capability(self, capability: CameraCapability) -> bool:
        """Check if mock camera supports a capability."""
        return capability in self._specs.capabilities

    async def get_preview_frame(self) -> Optional[bytes]:
        """Get mock preview frame."""
        if not self._is_initialized:
            return None

        # Return mock JPEG header bytes
        return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"

    async def autofocus(self, timeout_ms: int = 2000) -> bool:
        """Simulate autofocus operation."""
        if not self._is_initialized:
            return False

        # Simulate focus time
        focus_delay = min(timeout_ms / 1000 * 0.3, 0.5)  # 30% of timeout, max 500ms
        await asyncio.sleep(focus_delay)

        # Mock success rate (95%)
        return not (self._simulate_failures and self._should_fail(rate=0.05))

    async def get_current_settings(self) -> CaptureSettings:
        """Get current mock camera settings."""
        return self._current_settings

    async def set_capture_settings(self, settings: CaptureSettings) -> bool:
        """Set mock camera settings."""
        if not self._is_initialized:
            return False

        self._current_settings = settings
        await asyncio.sleep(0.01)  # Simulate settings application delay
        return True

    def _generate_mock_image(
        self, settings: CaptureSettings, sequence_index: Optional[int] = None
    ) -> Path:
        """Generate a mock image file."""
        self._image_counter += 1

        # Generate filename
        timestamp = int(time.time() * 1000)
        if sequence_index is not None:
            filename = f"mock_image_{timestamp}_{sequence_index:03d}.jpg"
        else:
            filename = f"mock_image_{timestamp}.jpg"

        image_path = self._output_dir / filename

        # Create a minimal JPEG file with metadata comment
        jpeg_header = bytearray(
            [
                0xFF,
                0xD8,  # SOI marker
                0xFF,
                0xE0,  # APP0 marker
                0x00,
                0x10,  # APP0 length
                0x4A,
                0x46,
                0x49,
                0x46,
                0x00,  # "JFIF\0"
                0x01,
                0x01,  # JFIF version
                0x01,  # Units (inches)
                0x00,
                0x48,
                0x00,
                0x48,  # X and Y density (72 DPI)
                0x00,
                0x00,  # Thumbnail width and height
            ]
        )

        # Add mock image data
        mock_data = f"Mock image #{self._image_counter} - {settings.format}".encode()
        jpeg_data = jpeg_header + mock_data

        # Add EOI marker
        jpeg_data.extend([0xFF, 0xD9])

        # Write to file
        with open(image_path, "wb") as f:
            f.write(jpeg_data)

        logger.debug(f"Generated mock image: {image_path}")
        return image_path

    def _detect_sequence_type(self, settings_list: List[CaptureSettings]) -> str:
        """Detect the type of capture sequence."""
        if len(settings_list) <= 1:
            return "single"

        # Check for HDR bracketing (different exposures)
        exposures = [s.exposure_time_us for s in settings_list if s.exposure_time_us is not None]
        if len(set(exposures)) > 1:
            return "hdr_bracket"

        # Check for focus stacking (different focus distances)
        focus_distances = [
            s.focus_distance_mm for s in settings_list if s.focus_distance_mm is not None
        ]
        if len(set(focus_distances)) > 1:
            return "focus_stack"

        return "sequence"

    def _should_fail(self, rate: Optional[float] = None) -> bool:
        """Determine if operation should fail (for testing)."""
        import random

        failure_rate = rate if rate is not None else self._failure_rate
        return random.random() < failure_rate

    async def optimize_settings_for_conditions(
        self, base_settings: CaptureSettings, conditions: EnvironmentalConditions
    ) -> CaptureSettings:
        """Mock optimization based on conditions."""
        optimized = CaptureSettings(
            exposure_time_us=base_settings.exposure_time_us,
            iso=base_settings.iso,
            exposure_compensation=base_settings.exposure_compensation,
            focus_distance_mm=base_settings.focus_distance_mm,
            autofocus_enabled=base_settings.autofocus_enabled,
            white_balance_k=base_settings.white_balance_k,
            white_balance_mode=base_settings.white_balance_mode,
            quality=base_settings.quality,
            format=base_settings.format,
            hdr_bracket_stops=base_settings.hdr_bracket_stops.copy(),
            processing_hints=base_settings.processing_hints.copy(),
        )

        # Mock golden hour optimization
        if conditions.is_golden_hour:
            optimized.white_balance_k = 3200  # Warmer
            optimized.exposure_compensation += 0.3
            optimized.processing_hints["enhance_warmth"] = True

        # Mock blue hour optimization
        if conditions.is_blue_hour:
            optimized.white_balance_k = 8500  # Cooler
            optimized.iso = 400  # Higher ISO for low light conditions
            optimized.processing_hints["enhance_blues"] = True

        return optimized

    async def assess_image_quality(self, image_path: str) -> float:
        """Mock image quality assessment."""
        # Simulate processing delay
        await asyncio.sleep(0.1)

        # Return mock quality score based on filename
        import random

        random.seed(hash(image_path))
        return 0.75 + random.random() * 0.2  # 0.75 to 0.95

    def get_processing_hints(self, settings: CaptureSettings) -> Dict[str, Any]:
        """Generate mock processing hints."""
        hints = {
            "mock_processing": True,
            "use_noise_reduction": (settings.iso or 100) > 400,
            "apply_hdr_processing": len(settings.hdr_bracket_stops) > 1,
            "suggested_sharpening": 0.3,
        }

        return hints
