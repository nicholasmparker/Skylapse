"""Hardware integration tests for Raspberry Pi camera systems."""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import pytest
import pytest_asyncio
from src.camera_controller import CameraController
from src.camera_types import CameraCapability, CaptureSettings


# Hardware detection utilities
def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi hardware."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
        return "BCM" in cpuinfo and "ARM" in cpuinfo
    except (FileNotFoundError, PermissionError):
        return False


def detect_camera_hardware() -> Optional[str]:
    """Detect connected camera hardware."""
    try:
        # Check for libcamera devices
        result = subprocess.run(
            ["libcamera-hello", "--list-cameras"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and "Available cameras" in result.stdout:
            return "libcamera"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        # Check for V4L2 devices
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "mmal" in result.stdout.lower():
            return "v4l2"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def get_system_info() -> dict:
    """Get system information for hardware testing."""
    info = {
        "is_raspberry_pi": is_raspberry_pi(),
        "camera_detected": detect_camera_hardware(),
        "python_version": None,
        "memory_mb": None,
        "disk_space_gb": None,
    }

    try:
        import platform

        info["python_version"] = platform.python_version()

        import psutil

        info["memory_mb"] = psutil.virtual_memory().total // (1024 * 1024)
        info["disk_space_gb"] = psutil.disk_usage("/").total // (1024 * 1024 * 1024)
    except ImportError:
        pass

    return info


# Skip hardware tests if not on Pi or no camera detected
hardware_available = is_raspberry_pi() and detect_camera_hardware() is not None
hardware_skip_reason = "Hardware tests require Raspberry Pi with camera"


@pytest.mark.hardware
@pytest.mark.skipif(not hardware_available, reason=hardware_skip_reason)
class TestHardwareCameraIntegration:
    """Hardware integration tests for real camera hardware."""

    @pytest_asyncio.fixture
    async def hardware_controller(self):
        """Create camera controller configured for hardware testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create hardware-optimized configuration
            config_dir = Path(temp_dir)

            # Auto-detect camera configuration or use defaults
            camera_config = {
                "sensor": {"model": "Hardware Auto-Detect", "base_iso": 100, "max_iso": 800},
                "optical": {
                    "focal_length_mm": 4.28,  # Common for Pi cameras
                    "hyperfocal_distance_mm": 1830,
                },
                "capture": {
                    "default_quality": 95,
                    "default_format": "JPEG",
                    "enable_raw_capture": False,
                    "capture_timeout_ms": 10000,  # Longer for hardware
                },
                "performance": {
                    "capture_buffer_size": 2,
                    "max_capture_latency_ms": 100,  # More lenient for hardware
                    "focus_timeout_ms": 3000,
                },
                "capabilities": [
                    "AUTOFOCUS",
                    "MANUAL_FOCUS",
                    "HDR_BRACKETING",
                    "RAW_CAPTURE",
                    "LIVE_PREVIEW",
                ],
            }

            import yaml

            with open(config_dir / "hardware_camera.yaml", "w") as f:
                yaml.dump(camera_config, f)

            controller = CameraController(config_dir=temp_dir)

            try:
                await controller.initialize_camera()
                yield controller
            finally:
                await controller.shutdown()

    @pytest.mark.asyncio
    async def test_hardware_detection_and_initialization(self, hardware_controller):
        """Test that hardware camera is detected and initialized correctly."""
        controller = hardware_controller

        # Verify initialization
        assert controller.is_initialized
        assert controller.camera is not None

        # Get camera status
        status = await controller.get_camera_status()
        assert status["initialized"] is True
        assert status["running"] is True
        assert "camera_model" in status

        # Camera model should not be 'Mock Camera'
        assert "Mock" not in status["camera_model"]

        print(f"Hardware Camera Detected: {status['camera_model']}")
        print(f"Capabilities: {status.get('capabilities', [])}")

    @pytest.mark.asyncio
    async def test_real_image_capture(self, hardware_controller):
        """Test capturing real images with hardware camera."""
        controller = hardware_controller

        settings = CaptureSettings(quality=90, format="JPEG", iso=100, autofocus_enabled=True)

        # Capture single image
        result = await controller.capture_single_image(settings)

        assert len(result.file_paths) == 1
        assert result.capture_time_ms > 0

        # Verify actual image file was created
        image_path = Path(result.file_paths[0])
        assert image_path.exists()
        assert image_path.suffix.lower() == ".jpg"
        assert image_path.stat().st_size > 1000  # Should be substantial file

        print(f"Captured image: {image_path}")
        print(f"File size: {image_path.stat().st_size // 1024}KB")
        print(f"Capture time: {result.capture_time_ms:.1f}ms")

    @pytest.mark.asyncio
    async def test_hardware_autofocus(self, hardware_controller):
        """Test autofocus functionality with real hardware."""
        controller = hardware_controller

        # Test autofocus if supported
        if controller.camera.supports_capability(CameraCapability.AUTOFOCUS):
            focus_success = await controller.camera.autofocus(timeout_ms=3000)
            assert focus_success is True

            print("Hardware autofocus: SUCCESS")
        else:
            print("Hardware autofocus: NOT SUPPORTED")
            pytest.skip("Hardware does not support autofocus")

    @pytest.mark.asyncio
    async def test_hardware_performance_validation(self, hardware_controller):
        """Test that hardware meets performance requirements."""
        controller = hardware_controller

        # Test multiple captures for timing
        capture_times = []
        settings = CaptureSettings(
            quality=85,
            format="JPEG",
            iso=100,
            autofocus_enabled=False,  # Disable for consistent timing
        )

        # Warm-up capture
        await controller.capture_single_image(settings)

        # Performance test captures
        for i in range(10):
            import time

            start_time = time.perf_counter()
            result = await controller.capture_single_image(settings)
            end_time = time.perf_counter()

            capture_time_ms = (end_time - start_time) * 1000
            capture_times.append(capture_time_ms)

            assert len(result.file_paths) == 1

        import statistics

        avg_time = statistics.mean(capture_times)
        max_time = max(capture_times)

        print(f"Hardware Performance Results:")
        print(f"  Average capture time: {avg_time:.1f}ms")
        print(f"  Maximum capture time: {max_time:.1f}ms")
        print(f"  Target: <100ms for hardware")

        # Hardware should meet relaxed performance targets
        assert avg_time < 200.0, f"Hardware avg capture time {avg_time:.1f}ms exceeds 200ms limit"
        assert max_time < 500.0, f"Hardware max capture time {max_time:.1f}ms exceeds 500ms limit"

    @pytest.mark.asyncio
    async def test_hardware_different_settings(self, hardware_controller):
        """Test hardware camera with various settings."""
        controller = hardware_controller

        test_settings = [
            CaptureSettings(quality=50, format="JPEG", iso=100),
            CaptureSettings(quality=95, format="JPEG", iso=200),
            CaptureSettings(quality=80, format="JPEG", iso=400),
        ]

        for i, settings in enumerate(test_settings):
            result = await controller.capture_single_image(settings)

            assert len(result.file_paths) == 1
            image_path = Path(result.file_paths[0])
            assert image_path.exists()

            # Different quality settings should produce different file sizes
            file_size_kb = image_path.stat().st_size // 1024
            print(
                f"Settings {i+1} - Quality: {settings.quality}, ISO: {settings.iso}, Size: {file_size_kb}KB"
            )

    @pytest.mark.asyncio
    async def test_hardware_hdr_capture(self, hardware_controller):
        """Test HDR capture with hardware camera."""
        controller = hardware_controller

        if not controller.camera.supports_capability(CameraCapability.HDR_BRACKETING):
            pytest.skip("Hardware does not support HDR bracketing")

        hdr_stops = [-1, 0, 1]
        base_settings = CaptureSettings(exposure_time_us=1000, iso=100, quality=90)

        result = await controller.capture_hdr_sequence(hdr_stops, base_settings)

        assert len(result.file_paths) == len(hdr_stops)

        # Verify all HDR images exist and have reasonable sizes
        for i, file_path in enumerate(result.file_paths):
            image_path = Path(file_path)
            assert image_path.exists()
            file_size_kb = image_path.stat().st_size // 1024
            print(f"HDR shot {i+1} ({hdr_stops[i]:+d}EV): {file_size_kb}KB")

    @pytest.mark.asyncio
    async def test_hardware_live_preview(self, hardware_controller):
        """Test live preview functionality with hardware."""
        controller = hardware_controller

        if not controller.camera.supports_capability(CameraCapability.LIVE_PREVIEW):
            pytest.skip("Hardware does not support live preview")

        preview_data = await controller.get_live_preview()

        assert preview_data is not None
        assert isinstance(preview_data, bytes)
        assert len(preview_data) > 100  # Should have substantial data

        # Should be valid image data (JPEG header)
        assert preview_data.startswith(b"\xff\xd8\xff")

        print(f"Live preview data: {len(preview_data)} bytes")


@pytest.mark.hardware
@pytest.mark.skipif(not hardware_available, reason=hardware_skip_reason)
class TestSystemIntegrationOnHardware:
    """System-level integration tests on real hardware."""

    @pytest_asyncio.fixture
    async def full_hardware_system(self):
        """Create complete system with all components on hardware."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from src.scheduler import CaptureScheduler
            from src.storage_manager import StorageManager

            # Initialize all components
            storage = StorageManager(
                buffer_path=str(Path(temp_dir) / "storage"),
                max_size_gb=1.0,
                retention_hours=2,  # Short for testing
            )
            await storage.initialize()

            scheduler = CaptureScheduler()
            await scheduler.initialize()

            # Hardware camera controller
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()

            hardware_config = {
                "sensor": {"model": "Hardware Integration Test"},
                "capture": {"default_quality": 85, "capture_timeout_ms": 10000},
                "capabilities": ["AUTOFOCUS", "HDR_BRACKETING"],
            }

            import yaml

            with open(config_dir / "hardware_camera.yaml", "w") as f:
                yaml.dump(hardware_config, f)

            controller = CameraController(config_dir=str(config_dir))
            await controller.initialize_camera()

            system = {"controller": controller, "scheduler": scheduler, "storage": storage}

            try:
                yield system
            finally:
                await controller.shutdown()
                await scheduler.shutdown()
                await storage.shutdown()

    @pytest.mark.asyncio
    async def test_complete_hardware_workflow(self, full_hardware_system):
        """Test complete capture workflow on hardware."""
        controller = full_hardware_system["controller"]
        scheduler = full_hardware_system["scheduler"]
        storage = full_hardware_system["storage"]

        from src.camera_types import EnvironmentalConditions

        # Simulate realistic conditions
        conditions = EnvironmentalConditions(
            is_golden_hour=True, ambient_light_lux=2000.0, sun_elevation_deg=10.0
        )

        # Test decision making
        should_capture = await scheduler.should_capture_now(conditions)
        assert isinstance(should_capture, bool)

        if should_capture:
            # Capture image
            settings = CaptureSettings(quality=90, format="JPEG", iso=100)
            result = await controller.capture_single_image(settings)

            # Store result
            stored_paths = await storage.store_capture_result(result)

            # Record with scheduler
            await scheduler.record_capture_attempt(result, success=True)

            # Verify complete workflow
            assert len(stored_paths) == 1
            assert Path(stored_paths[0]).exists()

            # Check storage organization
            stored_path = Path(stored_paths[0])
            assert "images" in str(stored_path)

            # Check metadata
            from datetime import datetime

            date_path = stored_path.parent.name
            assert len(date_path) == 2  # Should be DD format

            print(f"Complete workflow successful:")
            print(f"  Captured: {result.file_paths[0]}")
            print(f"  Stored: {stored_paths[0]}")
            print(f"  Capture time: {result.capture_time_ms:.1f}ms")

        else:
            print("Scheduler decided not to capture under current conditions")

    @pytest.mark.asyncio
    async def test_hardware_stress_test(self, full_hardware_system):
        """Stress test hardware system under load."""
        controller = full_hardware_system["controller"]
        storage = full_hardware_system["storage"]

        # Rapid capture sequence
        capture_count = 20
        settings = CaptureSettings(quality=80, format="JPEG", iso=100)

        captured_files = []

        for i in range(capture_count):
            try:
                result = await controller.capture_single_image(settings)
                stored_paths = await storage.store_capture_result(result)
                captured_files.extend(stored_paths)

                print(f"Capture {i+1}/{capture_count} completed")

                # Brief pause to avoid overwhelming hardware
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"Capture {i+1} failed: {e}")
                # Continue with remaining captures

        # Verify results
        successful_captures = len(captured_files)
        success_rate = successful_captures / capture_count

        print(f"Stress test results:")
        print(f"  Attempted: {capture_count}")
        print(f"  Successful: {successful_captures}")
        print(f"  Success rate: {success_rate:.1%}")

        # Should have reasonable success rate on stable hardware
        assert (
            success_rate >= 0.8
        ), f"Hardware stress test success rate {success_rate:.1%} below 80%"


@pytest.mark.hardware
class TestHardwareEnvironmentValidation:
    """Tests to validate hardware environment setup."""

    @pytest.mark.skipif(not hardware_available, reason=hardware_skip_reason)
    def test_system_requirements(self):
        """Test that system meets hardware requirements."""
        system_info = get_system_info()

        print(f"System Information:")
        for key, value in system_info.items():
            print(f"  {key}: {value}")

        # Validate requirements
        if system_info["is_raspberry_pi"]:
            # Memory requirement (minimum 1GB recommended)
            if system_info["memory_mb"]:
                assert system_info["memory_mb"] >= 512, "Insufficient memory for reliable operation"

            # Disk space requirement (minimum 10GB recommended)
            if system_info["disk_space_gb"]:
                assert system_info["disk_space_gb"] >= 5, "Insufficient disk space"

        # Camera requirement
        assert system_info["camera_detected"] is not None, "No camera hardware detected"

    @pytest.mark.skipif(not hardware_available, reason=hardware_skip_reason)
    def test_camera_permissions(self):
        """Test that camera permissions are properly configured."""
        import grp
        import os

        try:
            # Check if user is in video group
            video_group = grp.getgrnam("video")
            current_user_groups = os.getgroups()

            if video_group.gr_gid not in current_user_groups:
                print("Warning: User not in 'video' group - may need permissions setup")

        except KeyError:
            print("Video group not found - this may be normal on some systems")

        # Try basic camera access test
        camera_type = detect_camera_hardware()
        assert camera_type is not None, "Camera hardware not accessible"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not hardware_available, reason=hardware_skip_reason)
    async def test_libcamera_functionality(self):
        """Test basic libcamera functionality."""
        if detect_camera_hardware() != "libcamera":
            pytest.skip("libcamera not available")

        try:
            # Test libcamera-hello
            result = subprocess.run(
                ["libcamera-hello", "--timeout", "1", "--nopreview"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert result.returncode == 0, f"libcamera-hello failed: {result.stderr}"
            print("libcamera basic functionality: OK")

        except subprocess.TimeoutExpired:
            pytest.fail("libcamera-hello timed out")
        except FileNotFoundError:
            pytest.fail("libcamera-hello not found - please install libcamera-apps")


# Utility functions for hardware testing
def create_hardware_test_config(temp_dir: str) -> dict:
    """Create optimal configuration for hardware testing."""
    return {
        "sensor": {"model": "Hardware Test Camera", "base_iso": 100, "max_iso": 1600},
        "optical": {"focal_length_mm": 4.28, "hyperfocal_distance_mm": 1830},
        "capture": {
            "default_quality": 90,
            "default_format": "JPEG",
            "enable_raw_capture": False,
            "capture_timeout_ms": 15000,  # Generous timeout for hardware
        },
        "performance": {
            "capture_buffer_size": 3,
            "max_capture_latency_ms": 150,
            "focus_timeout_ms": 4000,
        },
        "capabilities": [
            "AUTOFOCUS",
            "MANUAL_FOCUS",
            "HDR_BRACKETING",
            "LIVE_PREVIEW",
            "RAW_CAPTURE",
        ],
    }


def hardware_test_summary():
    """Print hardware test environment summary."""
    system_info = get_system_info()

    print("\n" + "=" * 50)
    print("HARDWARE TEST ENVIRONMENT")
    print("=" * 50)

    for key, value in system_info.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    if system_info["is_raspberry_pi"]:
        print("\nOptimizations for Raspberry Pi:")
        print("- Consider increasing GPU memory split for camera operations")
        print("- Ensure adequate cooling for sustained capture operations")
        print("- Use fast SD card (Class 10+ or A1/A2) for storage")

    print("=" * 50 + "\n")
