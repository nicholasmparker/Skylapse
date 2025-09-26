"""Pytest configuration and shared fixtures for capture service tests."""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import yaml
import os
from pathlib import Path

# Configure pytest for async testing
pytest_plugins = ('pytest_asyncio',)

# Set development environment for tests
os.environ['SKYLAPSE_ENV'] = 'development'
os.environ['MOCK_CAMERA'] = 'true'


@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_camera_config_dir(temp_dir):
    """Create a temporary directory with mock camera configuration."""
    config_dir = Path(temp_dir) / "config" / "cameras"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create mock camera configuration
    mock_config = {
        'sensor': {
            'model': 'Mock Camera v1.0',
            'bayer_pattern': 'RGGB',
            'base_iso': 100,
            'max_iso': 800,
            'iso_invariance_point': 800,
            'max_exposure_us': 10000000,
            'resolution_mp': 16.0,
            'max_resolution': [4656, 3496],
            'sensor_size_mm': [7.4, 5.6]
        },
        'optical': {
            'focal_length_mm': 4.28,
            'aperture': 'f/2.0',
            'hyperfocal_distance_mm': 1830,
            'focus_range_mm': [100.0, float('inf')]
        },
        'processing': {
            'demosaic_algorithm': 'DCB',
            'spatial_nr_strength': 0.2
        },
        'capture': {
            'default_quality': 95,
            'default_format': 'JPEG',
            'enable_raw_capture': False,
            'capture_timeout_ms': 5000
        },
        'performance': {
            'capture_buffer_size': 4,
            'max_capture_latency_ms': 10,
            'focus_timeout_ms': 500
        },
        'mock': {
            'capture_delay_ms': 10,
            'simulate_failures': False,
            'failure_rate': 0.0,
            'output_dir': temp_dir
        },
        'capabilities': [
            'AUTOFOCUS',
            'MANUAL_FOCUS',
            'HDR_BRACKETING',
            'FOCUS_STACKING',
            'RAW_CAPTURE',
            'LIVE_PREVIEW'
        ]
    }

    with open(config_dir / "mock_camera.yaml", 'w') as f:
        yaml.dump(mock_config, f, indent=2)

    return str(config_dir.parent.parent)


@pytest.fixture
def system_config_dir(temp_dir):
    """Create a temporary directory with system configuration."""
    config_dir = Path(temp_dir) / "config" / "system"
    config_dir.mkdir(parents=True, exist_ok=True)

    system_config = {
        'storage': {
            'capture_buffer_path': str(Path(temp_dir) / "buffer"),
            'buffer_retention_hours': 48,
            'max_buffer_size_gb': 100,
            'cleanup_interval_hours': 6
        },
        'network': {
            'processing_service_host': 'localhost',
            'processing_service_port': 8081,
            'use_rsync': False,
            'transfer_retry_attempts': 3,
            'transfer_timeout_seconds': 300
        },
        'capture': {
            'service_port': 8080,
            'max_concurrent_captures': 1,
            'health_check_interval_seconds': 30,
            'check_interval_seconds': 10
        },
        'monitoring': {
            'log_level': 'DEBUG',
            'metrics_enabled': True,
            'performance_tracking': True
        },
        'development': {
            'mock_camera_enabled': True,
            'debug_logging': True,
            'development_mode': True
        }
    }

    with open(config_dir / "system.yaml", 'w') as f:
        yaml.dump(system_config, f, indent=2)

    return str(config_dir.parent.parent)


@pytest.fixture
def sample_capture_settings():
    """Create sample capture settings for testing."""
    from src.camera_types import CaptureSettings

    return CaptureSettings(
        exposure_time_us=1000,
        iso=100,
        exposure_compensation=0.0,
        focus_distance_mm=None,
        autofocus_enabled=True,
        white_balance_k=5500,
        white_balance_mode="auto",
        quality=95,
        format="JPEG",
        hdr_bracket_stops=[],
        processing_hints={}
    )


@pytest.fixture
def sample_environmental_conditions():
    """Create sample environmental conditions for testing."""
    from src.camera_types import EnvironmentalConditions

    return EnvironmentalConditions(
        cloud_cover_pct=30.0,
        visibility_km=15.0,
        precipitation_prob_pct=20.0,
        wind_speed_kph=10.0,
        sun_elevation_deg=45.0,
        sun_azimuth_deg=180.0,
        is_golden_hour=False,
        is_blue_hour=False,
        ambient_light_lux=10000.0,
        color_temperature_k=5500,
        temperature_c=20.0,
        scene_brightness=None,
        focus_quality_score=None
    )


@pytest.fixture
def golden_hour_conditions(sample_environmental_conditions):
    """Create golden hour environmental conditions."""
    conditions = sample_environmental_conditions
    conditions.is_golden_hour = True
    conditions.sun_elevation_deg = 5.0
    conditions.ambient_light_lux = 2000.0
    conditions.color_temperature_k = 3200
    return conditions


@pytest.fixture
def blue_hour_conditions(sample_environmental_conditions):
    """Create blue hour environmental conditions."""
    conditions = sample_environmental_conditions
    conditions.is_blue_hour = True
    conditions.sun_elevation_deg = -8.0
    conditions.ambient_light_lux = 50.0
    conditions.color_temperature_k = 8500
    return conditions


@pytest_asyncio.fixture
async def mock_transfer_dirs(temp_dir):
    """Create mock transfer directories."""
    transfer_dirs = {
        'incoming': Path(temp_dir) / "transfers" / "incoming",
        'processing': Path(temp_dir) / "transfers" / "processing",
        'completed': Path(temp_dir) / "transfers" / "completed"
    }

    for dir_path in transfer_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return transfer_dirs


# Mock image files for testing
@pytest.fixture
def sample_image_files(temp_dir):
    """Create sample image files for testing."""
    image_dir = Path(temp_dir) / "test_images"
    image_dir.mkdir(exist_ok=True)

    # Create minimal JPEG-like files
    image_files = []
    for i in range(3):
        image_path = image_dir / f"test_image_{i:03d}.jpg"

        # Create minimal JPEG header + data
        jpeg_data = bytearray([
            0xFF, 0xD8,  # SOI marker
            0xFF, 0xE0,  # APP0 marker
            0x00, 0x10,  # APP0 length
            0x4A, 0x46, 0x49, 0x46, 0x00,  # "JFIF\0"
            0x01, 0x01,  # JFIF version
            0x01,  # Units
            0x00, 0x48, 0x00, 0x48,  # DPI
            0x00, 0x00,  # No thumbnail
        ])

        # Add some test data
        test_data = f"Test image {i}".encode() * 100
        jpeg_data.extend(test_data)

        # Add EOI marker
        jpeg_data.extend([0xFF, 0xD9])

        with open(image_path, 'wb') as f:
            f.write(jpeg_data)

        image_files.append(str(image_path))

    return image_files


# Performance testing helpers
@pytest.fixture
def performance_timer():
    """Utility for measuring test performance."""
    import time

    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, *args):
            self.stop()

    return PerformanceTimer


# Test data validation helpers
def validate_capture_result(result):
    """Validate that a CaptureResult contains expected data."""
    from src.camera_types import CaptureResult

    assert isinstance(result, CaptureResult)
    assert len(result.file_paths) > 0
    assert all(isinstance(path, str) for path in result.file_paths)
    assert result.capture_time_ms >= 0
    assert isinstance(result.metadata, dict)
    assert result.actual_settings is not None

    # Validate files exist
    for file_path in result.file_paths:
        assert Path(file_path).exists(), f"Capture result file not found: {file_path}"


def validate_service_status(status):
    """Validate service status response format."""
    assert isinstance(status, dict)
    assert 'initialized' in status
    assert 'running' in status

    if status.get('initialized'):
        assert 'camera_model' in status
        assert 'capabilities' in status
        assert isinstance(status['capabilities'], list)


# Export validation helpers
__all__ = [
    'validate_capture_result',
    'validate_service_status'
]