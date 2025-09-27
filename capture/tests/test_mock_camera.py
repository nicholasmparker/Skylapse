"""Tests for mock camera implementation."""

import pytest
import pytest_asyncio
import asyncio
import tempfile
from pathlib import Path

from src.cameras.mock_camera import MockCamera
from src.camera_types import CaptureSettings, CameraCapability, EnvironmentalConditions


class TestMockCamera:
    """Test cases for MockCamera class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock camera configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "mock_capture_delay_ms": 10,
                "mock_simulate_failures": False,
                "mock_failure_rate": 0.0,
                "mock_output_dir": temp_dir,
            }
            yield config

    @pytest_asyncio.fixture
    async def camera(self, mock_config):
        """Create and initialize a mock camera."""
        camera = MockCamera(mock_config)
        await camera.initialize()
        yield camera
        await camera.shutdown()

    @pytest.mark.asyncio
    async def test_initialization(self, mock_config):
        """Test mock camera initialization."""
        camera = MockCamera(mock_config)
        assert not camera.is_initialized

        await camera.initialize()
        assert camera.is_initialized
        assert camera.specs is not None
        assert camera.specs.model == "Mock Camera v1.0"

        await camera.shutdown()
        assert not camera.is_initialized

    @pytest.mark.asyncio
    async def test_capture_single(self, camera):
        """Test single image capture."""
        settings = CaptureSettings(quality=90, format="JPEG", iso=100, exposure_time_us=1000)

        result = await camera.capture_single(settings)

        assert len(result.file_paths) == 1
        assert result.capture_time_ms > 0
        assert result.quality_score > 0
        assert result.metadata["mock_capture"] is True

        # Check that file was created
        image_file = Path(result.file_paths[0])
        assert image_file.exists()
        assert image_file.suffix == ".jpg"

    @pytest.mark.asyncio
    async def test_capture_sequence(self, camera):
        """Test multi-image sequence capture."""
        settings_list = [
            CaptureSettings(exposure_time_us=500),  # -1 EV
            CaptureSettings(exposure_time_us=1000),  # Base
            CaptureSettings(exposure_time_us=2000),  # +1 EV
        ]

        result = await camera.capture_sequence(settings_list)

        assert len(result.file_paths) == 3
        assert result.capture_time_ms > 0
        assert result.metadata["sequence_count"] == 3
        assert result.metadata["sequence_type"] == "hdr_bracket"

        # Check that all files were created
        for file_path in result.file_paths:
            assert Path(file_path).exists()

    @pytest.mark.asyncio
    async def test_capabilities(self, camera):
        """Test capability checking."""
        assert camera.supports_capability(CameraCapability.AUTOFOCUS)
        assert camera.supports_capability(CameraCapability.MANUAL_FOCUS)
        assert camera.supports_capability(CameraCapability.HDR_BRACKETING)
        assert camera.supports_capability(CameraCapability.FOCUS_STACKING)
        assert camera.supports_capability(CameraCapability.RAW_CAPTURE)
        assert camera.supports_capability(CameraCapability.LIVE_PREVIEW)

    @pytest.mark.asyncio
    async def test_autofocus(self, camera):
        """Test autofocus functionality."""
        success = await camera.autofocus(timeout_ms=1000)
        assert success is True  # Mock camera should always succeed

    @pytest.mark.asyncio
    async def test_preview_frame(self, camera):
        """Test preview frame retrieval."""
        preview = await camera.get_preview_frame()
        assert preview is not None
        assert isinstance(preview, bytes)
        # Should return mock JPEG header
        assert preview.startswith(b"\xff\xd8\xff\xe0")

    @pytest.mark.asyncio
    async def test_settings_management(self, camera):
        """Test camera settings management."""
        # Test getting current settings
        current = await camera.get_current_settings()
        assert isinstance(current, CaptureSettings)

        # Test setting new settings
        new_settings = CaptureSettings(iso=400, quality=85, white_balance_k=5500)

        success = await camera.set_capture_settings(new_settings)
        assert success is True

        # Verify settings were applied
        updated = await camera.get_current_settings()
        assert updated.iso == 400
        assert updated.quality == 85
        assert updated.white_balance_k == 5500

    @pytest.mark.asyncio
    async def test_environmental_optimization(self, camera):
        """Test environmental condition optimization."""
        base_settings = CaptureSettings(iso=100, white_balance_k=4000)

        # Test golden hour optimization
        golden_conditions = EnvironmentalConditions(is_golden_hour=True, ambient_light_lux=2000)

        optimized = await camera.optimize_settings_for_conditions(base_settings, golden_conditions)

        assert optimized.white_balance_k == 3200  # Warmer for golden hour
        assert optimized.exposure_compensation > base_settings.exposure_compensation
        assert optimized.processing_hints.get("enhance_warmth") is True

        # Test blue hour optimization
        blue_conditions = EnvironmentalConditions(is_blue_hour=True, ambient_light_lux=50)

        blue_optimized = await camera.optimize_settings_for_conditions(
            base_settings, blue_conditions
        )

        assert blue_optimized.white_balance_k == 8500  # Cooler for blue hour
        assert blue_optimized.iso == 400  # Higher ISO for low light
        assert blue_optimized.processing_hints.get("enhance_blues") is True

    @pytest.mark.asyncio
    async def test_image_quality_assessment(self, camera):
        """Test image quality assessment."""
        # Capture an image first
        settings = CaptureSettings(quality=90)
        result = await camera.capture_single(settings)

        # Assess quality
        quality_score = await camera.assess_image_quality(result.file_paths[0])
        assert isinstance(quality_score, float)
        assert 0.0 <= quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_processing_hints(self, camera):
        """Test processing hints generation."""
        settings = CaptureSettings(iso=800, hdr_bracket_stops=[-1, 0, 1])

        hints = camera.get_processing_hints(settings)
        assert isinstance(hints, dict)
        assert hints.get("mock_processing") is True
        assert hints.get("use_noise_reduction") is True  # High ISO
        assert hints.get("apply_hdr_processing") is True  # Has HDR stops

    @pytest.mark.asyncio
    async def test_failure_simulation(self, mock_config):
        """Test failure simulation functionality."""
        # Configure for failure simulation
        failure_config = mock_config.copy()
        failure_config["mock_simulate_failures"] = True
        failure_config["mock_failure_rate"] = 1.0  # 100% failure rate

        camera = MockCamera(failure_config)
        await camera.initialize()

        try:
            settings = CaptureSettings()

            # Should fail due to failure simulation
            with pytest.raises(Exception):  # Should raise CaptureError
                await camera.capture_single(settings)

        finally:
            await camera.shutdown()

    @pytest.mark.asyncio
    async def test_focus_stacking_sequence_detection(self, camera):
        """Test focus stacking sequence detection."""
        # Create sequence with different focus distances
        settings_list = [
            CaptureSettings(focus_distance_mm=1000.0),
            CaptureSettings(focus_distance_mm=2000.0),
            CaptureSettings(focus_distance_mm=float("inf")),
        ]

        result = await camera.capture_sequence(settings_list)

        assert result.metadata["sequence_type"] == "focus_stack"
        assert len(result.file_paths) == 3

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config):
        """Test mock camera as async context manager."""
        async with MockCamera(mock_config) as camera:
            assert camera.is_initialized

            # Test capture within context
            result = await camera.capture_single(CaptureSettings())
            assert len(result.file_paths) == 1

        # Should be shutdown after context exit
        assert not camera.is_initialized

    @pytest.mark.asyncio
    async def test_capture_timing_simulation(self, mock_config):
        """Test that capture delay simulation works."""
        # Set higher delay
        delay_config = mock_config.copy()
        delay_config["mock_capture_delay_ms"] = 100

        camera = MockCamera(delay_config)
        await camera.initialize()

        try:
            import time

            start_time = time.time()

            await camera.capture_single(CaptureSettings())

            elapsed_ms = (time.time() - start_time) * 1000
            # Should take at least the simulated delay
            assert elapsed_ms >= 100

        finally:
            await camera.shutdown()

    @pytest.mark.asyncio
    async def test_file_naming_convention(self, camera):
        """Test that generated files follow naming convention."""
        # Single capture
        single_result = await camera.capture_single(CaptureSettings())
        single_path = Path(single_result.file_paths[0])
        assert single_path.name.startswith("mock_image_")
        assert single_path.suffix == ".jpg"

        # Sequence capture
        settings_list = [CaptureSettings(), CaptureSettings()]
        seq_result = await camera.capture_sequence(settings_list)

        for i, file_path in enumerate(seq_result.file_paths):
            seq_path = Path(file_path)
            assert seq_path.name.startswith("mock_image_")
            assert f"_{i:03d}.jpg" in seq_path.name  # Should have sequence index

    def test_camera_specs(self, mock_config):
        """Test camera specifications."""
        camera = MockCamera(mock_config)
        # Specs should be available even before initialization for testing
        asyncio.run(camera.initialize())

        specs = camera.specs
        assert specs is not None
        assert specs.model == "Mock Camera v1.0"
        assert specs.resolution_mp == 16.0
        assert specs.max_resolution == (4656, 3496)
        assert specs.base_iso == 100
        assert specs.max_iso == 800

        asyncio.run(camera.shutdown())
