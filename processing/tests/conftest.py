"""Pytest configuration and shared fixtures for processing service tests."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path

# Configure pytest for async testing
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
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
def sample_image_files(temp_dir):
    """Create sample image files for testing."""
    image_dir = Path(temp_dir) / "test_images"
    image_dir.mkdir(exist_ok=True)

    image_files = []
    for i in range(5):
        image_path = image_dir / f"test_image_{i:03d}.jpg"

        # Create minimal JPEG-like content
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

        # Add test data with image index
        test_data = f"Test image {i} content".encode() * 50
        jpeg_data.extend(test_data)

        # Add EOI marker
        jpeg_data.extend([0xFF, 0xD9])

        with open(image_path, 'wb') as f:
            f.write(jpeg_data)

        image_files.append(str(image_path))

    return image_files


@pytest.fixture
def sample_metadata():
    """Create sample image metadata."""
    return {
        'capture_time': 1672531200.0,
        'camera_model': 'Mock Camera v1.0',
        'capture_settings': {
            'exposure_time_us': 1000,
            'iso': 100,
            'white_balance_k': 5500,
            'quality': 95,
            'format': 'JPEG'
        },
        'environmental_conditions': {
            'is_golden_hour': False,
            'ambient_light_lux': 10000.0,
            'temperature_c': 20.0
        }
    }


@pytest.fixture
def processing_config():
    """Create processing service configuration."""
    return {
        'api': {
            'port': 8081,
            'cors_enabled': True
        },
        'processing': {
            'max_concurrent_jobs': 2,
            'job_timeout_seconds': 300,
            'temp_dir': '/tmp/skylapse_processing_test',
            'output_dir': '/tmp/skylapse_output_test'
        },
        'image': {
            'supported_formats': ['JPEG', 'PNG', 'TIFF'],
            'quality_levels': {
                'high': 95,
                'medium': 85,
                'low': 75
            }
        },
        'video': {
            'output_formats': ['1080p', '4k'],
            'framerate': 24.0,
            'encoding': {
                'codec': 'h264',
                'quality': 'high'
            }
        }
    }


@pytest.fixture
def transfer_dirs(temp_dir):
    """Create transfer directories for testing."""
    transfer_base = Path(temp_dir) / "transfers"
    dirs = {
        'incoming': transfer_base / "incoming",
        'processing': transfer_base / "processing",
        'completed': transfer_base / "completed"
    }

    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dirs


@pytest.fixture
def sample_job_data():
    """Create sample job data for testing."""
    return {
        'type': 'image_processing',
        'image_paths': ['/tmp/test_image_001.jpg', '/tmp/test_image_002.jpg'],
        'metadata': {
            'capture_time': 1672531200.0,
            'camera_model': 'Test Camera'
        },
        'processing_options': {
            'noise_reduction': True,
            'sharpening': False,
            'color_correction': True
        },
        'priority': 'normal'
    }


@pytest.fixture
def sample_timelapse_data():
    """Create sample timelapse data for testing."""
    processed_images = []
    for i in range(10):
        processed_images.append({
            'input_path': f'/tmp/input_{i:03d}.jpg',
            'output_path': f'/tmp/processed_{i:03d}.jpg',
            'timestamp': 1672531200.0 + i * 60,  # 1 minute intervals
            'processing_applied': ['basic_processing'],
            'metadata': {
                'capture_time': 1672531200.0 + i * 60,
                'frame_index': i
            }
        })

    return processed_images


@pytest.fixture
def mock_transfer_manifest(temp_dir):
    """Create a mock transfer manifest for testing."""
    manifest = {
        'transfer_id': 'test_transfer_001',
        'created_at': 1672531200.0,
        'image_files': ['test_001.jpg', 'test_002.jpg', 'test_003.jpg'],
        'metadata': {
            'capture_session': 'test_session',
            'camera_model': 'Mock Camera'
        }
    }

    manifest_file = Path(temp_dir) / "transfer_test_001.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    return str(manifest_file)


@pytest.fixture
def performance_timer():
    """Utility for measuring performance in tests."""
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

        @property
        def elapsed_seconds(self):
            return self.elapsed_ms / 1000

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, *args):
            self.stop()

    return PerformanceTimer


@pytest.fixture
async def job_queue_with_jobs(temp_dir):
    """Create a job queue with sample jobs for testing."""
    from src.job_queue import JobQueue

    queue = JobQueue(queue_dir=temp_dir)
    await queue.initialize()

    # Add some test jobs
    job_ids = []
    for i in range(3):
        job_data = {
            'type': 'image_processing',
            'image_paths': [f'/tmp/test_{i}.jpg'],
            'metadata': {'test_job': i},
            'priority': 'normal' if i % 2 == 0 else 'high'
        }
        job_id = await queue.add_job(job_data)
        job_ids.append(job_id)

    yield queue, job_ids

    await queue.shutdown()


# Validation helpers
def validate_processing_result(result):
    """Validate processing result structure."""
    assert isinstance(result, dict)
    required_fields = ['input_path', 'output_path', 'processing_applied', 'timestamp', 'metadata']

    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

    assert isinstance(result['processing_applied'], list)
    assert len(result['processing_applied']) > 0
    assert isinstance(result['metadata'], dict)
    assert result['timestamp'] > 0


def validate_job_status(status):
    """Validate job status structure."""
    assert isinstance(status, dict)
    required_fields = ['id', 'status', 'created_at', 'updated_at']

    for field in required_fields:
        assert field in status, f"Missing required field: {field}"

    valid_statuses = ['pending', 'in_progress', 'completed', 'failed', 'cancelled']
    assert status['status'] in valid_statuses


def validate_timelapse_result(result):
    """Validate timelapse creation result."""
    assert isinstance(result, dict)
    assert 'success' in result
    assert 'outputs' in result

    if result['success']:
        assert len(result['outputs']) > 0
        for output in result['outputs']:
            assert 'format' in output
            assert 'output_path' in output
            assert 'resolution' in output


def validate_service_status(status):
    """Validate service status structure."""
    assert isinstance(status, dict)
    assert 'service' in status
    assert 'components' in status

    service_info = status['service']
    assert 'running' in service_info
    assert 'uptime_seconds' in service_info

    components = status['components']
    assert isinstance(components, dict)


# Mock data creators
def create_mock_hdr_images(temp_dir, count=3):
    """Create mock HDR sequence images."""
    hdr_dir = Path(temp_dir) / "hdr_sequence"
    hdr_dir.mkdir(exist_ok=True)

    image_paths = []
    for i in range(count):
        image_path = hdr_dir / f"hdr_exposure_{i}.jpg"

        # Different exposure simulation
        exposure_data = f"HDR exposure {i} - EV {(i-1)*2}".encode() * 30
        content = b'\xff\xd8' + exposure_data + b'\xff\xd9'

        with open(image_path, 'wb') as f:
            f.write(content)

        image_paths.append(str(image_path))

    return image_paths


def create_mock_focus_stack(temp_dir, count=5):
    """Create mock focus stack images."""
    stack_dir = Path(temp_dir) / "focus_stack"
    stack_dir.mkdir(exist_ok=True)

    image_paths = []
    for i in range(count):
        image_path = stack_dir / f"focus_distance_{i}.jpg"

        # Different focus simulation
        focus_data = f"Focus stack {i} - distance {100 + i * 500}mm".encode() * 25
        content = b'\xff\xd8' + focus_data + b'\xff\xd9'

        with open(image_path, 'wb') as f:
            f.write(content)

        image_paths.append(str(image_path))

    return image_paths


# Export validation helpers and creators
__all__ = [
    'validate_processing_result',
    'validate_job_status',
    'validate_timelapse_result',
    'validate_service_status',
    'create_mock_hdr_images',
    'create_mock_focus_stack'
]