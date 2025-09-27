"""Tests for camera controller functionality."""

import asyncio  # noqa: F401
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest
import pytest_asyncio
from src.camera_controller import CameraController
from src.camera_types import CaptureResult, CaptureSettings, EnvironmentalConditions
from src.config_manager import CameraConfigManager  # noqa: F401


class TestCameraController:
    """Test cases for CameraController class."""

    @pytest_asyncio.fixture
    async def temp_config_dir(self):
        """Create a temporary configuration directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest_asyncio.fixture
    async def controller(self, temp_config_dir):
        """Create a CameraController instance for testing."""
        controller = CameraController(config_dir=temp_config_dir)
        yield controller
        # Cleanup
        if controller.is_initialized:
            await controller.shutdown()

    @pytest.fixture
    def mock_camera_config(self, temp_config_dir):
        """Create mock camera configuration files."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(exist_ok=True)

        # Create mock camera config
        mock_config = {
            "sensor": {"model": "Mock Camera", "base_iso": 100, "max_iso": 800},
            "optical": {"focal_length_mm": 4.28, "hyperfocal_distance_mm": 1830},
            "mock": {
                "capture_delay_ms": 10,
                "simulate_failures": False,
                "output_dir": str(temp_config_dir),
            },
            "capabilities": ["AUTOFOCUS", "MANUAL_FOCUS", "HDR_BRACKETING"],
        }

        import yaml

        with open(config_dir / "mock_camera.yaml", "w") as f:
            yaml.dump(mock_config, f)

        return temp_config_dir

    @pytest.mark.asyncio
    async def test_initialize_camera_auto_detect(self, controller, mock_camera_config):
        """Test camera initialization with auto-detection."""
        await controller.initialize_camera()

        assert controller.is_initialized
        assert controller.camera is not None
        assert controller.camera.specs is not None
        assert "Mock Camera" in controller.camera.specs.model

    @pytest.mark.asyncio
    async def test_initialize_specific_camera(self, controller, mock_camera_config):
        """Test camera initialization with specific camera type."""
        await controller.initialize_camera("mock_camera")

        assert controller.is_initialized
        assert controller.camera is not None
        assert "Mock Camera" in controller.camera.specs.model

    @pytest.mark.asyncio
    async def test_capture_optimized_basic(self, controller, mock_camera_config):
        """Test basic optimized capture functionality."""
        await controller.initialize_camera()

        settings = CaptureSettings(quality=90, format="JPEG", iso=100)

        result = await controller.capture_optimized(base_settings=settings)

        assert isinstance(result, CaptureResult)
        assert len(result.file_paths) > 0
        assert result.capture_time_ms > 0
        assert result.quality_score is not None

    @pytest.mark.asyncio
    async def test_capture_with_environmental_conditions(self, controller, mock_camera_config):
        """Test capture with environmental conditions."""
        await controller.initialize_camera()

        conditions = EnvironmentalConditions(
            is_golden_hour=True, ambient_light_lux=5000, sun_elevation_deg=5
        )

        result = await controller.capture_optimized(conditions=conditions)

        assert isinstance(result, CaptureResult)
        assert len(result.file_paths) > 0

    @pytest.mark.asyncio
    async def test_hdr_capture_sequence(self, controller, mock_camera_config):
        """Test HDR bracketed capture."""
        await controller.initialize_camera()

        hdr_stops = [-2, -1, 0, 1, 2]
        base_settings = CaptureSettings(exposure_time_us=1000, iso=100)

        result = await controller.capture_hdr_sequence(hdr_stops, base_settings)

        assert isinstance(result, CaptureResult)
        assert len(result.file_paths) > 1  # Should have multiple exposures

    @pytest.mark.asyncio
    async def test_capture_single_image(self, controller, mock_camera_config):
        """Test single image capture."""
        await controller.initialize_camera()

        settings = CaptureSettings(quality=95, format="JPEG", iso=200, autofocus_enabled=True)

        result = await controller.capture_single_image(settings)

        assert isinstance(result, CaptureResult)
        assert len(result.file_paths) == 1
        assert result.capture_time_ms > 0

    @pytest.mark.asyncio
    async def test_get_camera_status(self, controller, mock_camera_config):
        """Test camera status retrieval."""
        await controller.initialize_camera()

        status = await controller.get_camera_status()

        assert isinstance(status, dict)
        assert status["initialized"] is True
        assert status["running"] is True
        assert "camera_model" in status
        assert "capabilities" in status
        assert "performance" in status

    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, controller, mock_camera_config):
        """Test that performance metrics are tracked correctly."""
        await controller.initialize_camera()

        # Perform multiple captures
        settings = CaptureSettings(quality=85, format="JPEG")

        for _ in range(3):
            await controller.capture_single_image(settings)

        metrics = controller.performance_metrics

        assert metrics["total_captures"] == 3
        assert metrics["successful_captures"] == 3
        assert metrics["failed_captures"] == 0
        assert metrics["average_capture_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_test_capture(self, controller, mock_camera_config):
        """Test the test capture functionality."""
        await controller.initialize_camera()

        result = await controller.test_capture()

        assert isinstance(result, dict)
        assert result["success"] is True
        assert "capture_time_ms" in result
        assert "file_paths" in result
        assert len(result["file_paths"]) > 0

    @pytest.mark.asyncio
    async def test_get_live_preview(self, controller, mock_camera_config):
        """Test live preview functionality."""
        await controller.initialize_camera()

        preview = await controller.get_live_preview()

        # Mock camera should return some preview data
        assert preview is not None
        assert isinstance(preview, bytes)

    @pytest.mark.asyncio
    async def test_controller_context_manager(self, temp_config_dir, mock_camera_config):
        """Test CameraController as async context manager."""
        async with CameraController(config_dir=temp_config_dir) as controller:
            assert controller.is_initialized
            assert controller.camera is not None

        # Should be cleaned up after context exit
        assert not controller.is_initialized

    @pytest.mark.asyncio
    async def test_capture_failure_handling(self, controller, mock_camera_config):
        """Test handling of capture failures."""
        # Create a controller with failure simulation
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Mock config with failure simulation enabled
            failure_config = {
                "sensor": {"model": "Mock Camera"},
                "mock": {
                    "simulate_failures": True,
                    "failure_rate": 1.0,  # 100% failure rate
                    "output_dir": temp_dir,
                },
                "capabilities": ["AUTOFOCUS"],
            }

            import yaml

            with open(config_dir / "mock_camera.yaml", "w") as f:
                yaml.dump(failure_config, f)

            failure_controller = CameraController(config_dir=temp_dir)

            try:
                await failure_controller.initialize_camera(camera_type="mock_camera")

                settings = CaptureSettings(quality=85)

                # Should handle failure gracefully
                with pytest.raises(Exception):  # Should raise a CameraError
                    await failure_controller.capture_single_image(settings)

                # Performance metrics should track the failure
                metrics = failure_controller.performance_metrics
                assert metrics["failed_captures"] > 0

            finally:
                await failure_controller.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_without_initialization(self, controller):
        """Test that shutdown works even if not initialized."""
        # Should not raise an exception
        await controller.shutdown()

        assert not controller.is_initialized

    @pytest.mark.asyncio
    async def test_camera_capabilities_check(self, controller, mock_camera_config):
        """Test camera capability checking."""
        await controller.initialize_camera()

        # Mock camera should support these capabilities
        from src.camera_types import CameraCapability

        assert controller.camera.supports_capability(CameraCapability.AUTOFOCUS)
        assert controller.camera.supports_capability(CameraCapability.HDR_BRACKETING)

    def test_performance_metrics_initial_state(self, controller):
        """Test initial state of performance metrics."""
        metrics = controller.performance_metrics

        assert metrics["total_captures"] == 0
        assert metrics["successful_captures"] == 0
        assert metrics["failed_captures"] == 0
        assert metrics["average_capture_time_ms"] == 0.0
        assert metrics["last_capture_time"] is None


# Integration-style tests
class TestCameraControllerIntegration:
    """Integration tests for camera controller with real-world scenarios."""

    @pytest_asyncio.fixture
    async def controller_with_config(self):
        """Create controller with full configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create comprehensive config
            config_dir = Path(temp_dir)

            full_config = {
                "sensor": {
                    "model": "Mock IMX519",
                    "bayer_pattern": "RGGB",
                    "base_iso": 100,
                    "max_iso": 800,
                    "resolution_mp": 16.0,
                },
                "optical": {
                    "focal_length_mm": 4.28,
                    "hyperfocal_distance_mm": 1830,
                    "focus_range_mm": [100.0, float("inf")],
                },
                "processing": {"demosaic_algorithm": "DCB", "noise_reduction_strength": 0.2},
                "mock": {
                    "capture_delay_ms": 10,
                    "simulate_failures": False,
                    "output_dir": temp_dir,
                },
                "capabilities": [
                    "AUTOFOCUS",
                    "MANUAL_FOCUS",
                    "HDR_BRACKETING",
                    "FOCUS_STACKING",
                    "RAW_CAPTURE",
                    "LIVE_PREVIEW",
                ],
            }

            import yaml

            with open(config_dir / "mock_camera.yaml", "w") as f:
                yaml.dump(full_config, f)

            controller = CameraController(config_dir=temp_dir)
            yield controller

            if controller.is_initialized:
                await controller.shutdown()

    @pytest.mark.asyncio
    async def test_complete_capture_workflow(self, controller_with_config):
        """Test a complete capture workflow from initialization to cleanup."""
        controller = controller_with_config

        # Initialize
        await controller.initialize_camera()
        assert controller.is_initialized

        # Get status
        status = await controller.get_camera_status()
        assert status["initialized"]

        # Perform various types of captures
        basic_result = await controller.capture_optimized()
        assert basic_result.capture_time_ms > 0

        # HDR capture
        hdr_result = await controller.capture_hdr_sequence(
            stops=[-1, 0, 1], base_settings=CaptureSettings(exposure_time_us=1000)
        )
        assert len(hdr_result.file_paths) >= 3

        # Test capture
        test_result = await controller.test_capture()
        assert test_result["success"]

        # Check performance metrics
        metrics = controller.performance_metrics
        assert metrics["total_captures"] >= 3
        assert metrics["successful_captures"] >= 3

        # Cleanup
        await controller.shutdown()
        assert not controller.is_initialized
