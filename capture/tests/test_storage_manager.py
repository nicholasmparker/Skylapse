"""Tests for storage management functionality."""

import pytest
import pytest_asyncio
import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.storage_manager import StorageManager
from src.camera_types import CaptureResult, CaptureSettings


class TestStorageManager:
    """Test cases for StorageManager class."""

    @pytest_asyncio.fixture
    async def temp_storage_dir(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest_asyncio.fixture
    async def storage_manager(self, temp_storage_dir):
        """Create and initialize storage manager."""
        manager = StorageManager(
            buffer_path=temp_storage_dir,
            max_size_gb=1.0,  # Small for testing
            retention_hours=24  # Short for testing
        )
        await manager.initialize()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_initialization(self, temp_storage_dir):
        """Test storage manager initialization."""
        manager = StorageManager(temp_storage_dir)
        assert not manager._is_initialized

        await manager.initialize()
        assert manager._is_initialized

        # Check that directories were created
        assert manager.buffer_path.exists()
        assert manager.images_dir.exists()
        assert manager.metadata_dir.exists()
        assert manager.transfer_queue_dir.exists()

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_directory_structure(self, storage_manager):
        """Test that proper directory structure is created."""
        # Check main directories exist
        assert storage_manager.images_dir.exists()
        assert storage_manager.metadata_dir.exists()
        assert storage_manager.transfer_queue_dir.exists()

        # Check directory paths are correct
        assert storage_manager.images_dir.name == "images"
        assert storage_manager.metadata_dir.name == "metadata"
        assert storage_manager.transfer_queue_dir.name == "transfer_queue"

    @pytest.mark.asyncio
    async def test_store_capture_result(self, storage_manager, temp_storage_dir):
        """Test storing capture results with proper organization."""
        # Create mock capture result
        capture_result = CaptureResult(
            file_paths=[str(Path(temp_storage_dir) / "test_image.jpg")],
            capture_time_ms=45.0,
            quality_score=0.87,
            metadata={"iso": 100, "exposure_time_us": 1000},
            actual_settings=CaptureSettings(iso=100, quality=95)
        )

        # Create the test image file
        test_image_path = Path(capture_result.file_paths[0])
        test_image_path.parent.mkdir(parents=True, exist_ok=True)
        test_image_path.write_bytes(b"fake image data")

        # Store the capture result
        stored_paths = await storage_manager.store_capture_result(capture_result)

        assert len(stored_paths) == 1
        stored_path = Path(stored_paths[0])

        # Check that file was moved to proper location
        assert stored_path.exists()

        # Check date-based directory structure (YYYY/MM/DD)
        now = datetime.now()
        expected_date_path = storage_manager.images_dir / now.strftime("%Y/%m/%d")
        assert stored_path.parent == expected_date_path

        # Verify the directory hierarchy: images_dir/YYYY/MM/DD/file.jpg
        assert stored_path.parent.parent.parent.parent == storage_manager.images_dir

    @pytest.mark.asyncio
    async def test_store_multiple_files(self, storage_manager, temp_storage_dir):
        """Test storing capture result with multiple files (e.g., HDR sequence)."""
        # Create multiple test files
        file_paths = []
        for i in range(3):
            file_path = Path(temp_storage_dir) / f"hdr_test_{i}.jpg"
            file_path.write_bytes(f"fake image data {i}".encode())
            file_paths.append(str(file_path))

        capture_result = CaptureResult(
            file_paths=file_paths,
            capture_time_ms=125.0,
            quality_score=0.92,
            metadata={"sequence_type": "hdr_bracket", "exposures": 3},
            actual_settings=CaptureSettings()
        )

        stored_paths = await storage_manager.store_capture_result(capture_result)

        assert len(stored_paths) == 3
        # All files should be stored and exist
        for stored_path in stored_paths:
            assert Path(stored_path).exists()
            # Should be in date-organized directory
            assert "images" in str(stored_path)

    @pytest.mark.asyncio
    async def test_metadata_storage(self, storage_manager, temp_storage_dir):
        """Test that metadata is stored alongside images."""
        # Create test capture
        test_image = Path(temp_storage_dir) / "metadata_test.jpg"
        test_image.write_bytes(b"test image for metadata")

        capture_result = CaptureResult(
            file_paths=[str(test_image)],
            capture_time_ms=55.0,
            quality_score=0.75,
            metadata={
                "camera": "Mock Camera",
                "timestamp": "2025-09-25T10:30:00Z",
                "location": {"lat": 40.7128, "lon": -74.0060}
            },
            actual_settings=CaptureSettings(iso=200, quality=90)
        )

        stored_paths = await storage_manager.store_capture_result(capture_result)
        stored_image = Path(stored_paths[0])

        # Check that metadata file exists
        metadata_file = storage_manager.metadata_dir / stored_image.relative_to(storage_manager.images_dir).with_suffix('.json')
        assert metadata_file.exists()

        # Check metadata content
        with open(metadata_file, 'r') as f:
            saved_metadata = json.load(f)

        assert saved_metadata["capture_time_ms"] == 55.0
        assert saved_metadata["quality_score"] == 0.75
        assert saved_metadata["metadata"]["camera"] == "Mock Camera"
        assert "actual_settings" in saved_metadata

    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, storage_manager):
        """Test cleanup of files older than retention period."""
        # Create old test files
        old_date = datetime.now() - timedelta(hours=storage_manager.retention_hours + 1)
        old_date_str = old_date.strftime("%Y/%m/%d")
        old_dir = storage_manager.images_dir / old_date_str
        old_dir.mkdir(parents=True, exist_ok=True)

        old_file = old_dir / "old_image.jpg"
        old_file.write_bytes(b"old image data")

        # Create corresponding metadata
        old_metadata_dir = storage_manager.metadata_dir / old_date_str
        old_metadata_dir.mkdir(parents=True, exist_ok=True)
        old_metadata_file = old_metadata_dir / "old_image.json"
        old_metadata_file.write_text('{"test": "old metadata"}')

        # Set file modification times to the old date so they'll be cleaned up
        import os
        old_timestamp = old_date.timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))
        os.utime(old_metadata_file, (old_timestamp, old_timestamp))

        # Verify files exist
        assert old_file.exists()
        assert old_metadata_file.exists()

        # Run cleanup
        cleanup_result = await storage_manager.cleanup_old_files()

        # Files should be deleted
        assert not old_file.exists()
        assert not old_metadata_file.exists()
        assert cleanup_result['files_removed'] > 0

    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent_files(self, storage_manager, temp_storage_dir):
        """Test that cleanup preserves recent files within retention period."""
        # Create recent test file through normal storage
        test_image = Path(temp_storage_dir) / "recent_test.jpg"
        test_image.write_bytes(b"recent image data")

        capture_result = CaptureResult(
            file_paths=[str(test_image)],
            capture_time_ms=30.0,
            quality_score=0.8,
            metadata={"recent": True},
            actual_settings=CaptureSettings()
        )

        stored_paths = await storage_manager.store_capture_result(capture_result)
        stored_file = Path(stored_paths[0])

        # Run cleanup
        cleaned_count = await storage_manager.cleanup_old_files()

        # Recent file should still exist
        assert stored_file.exists()

    @pytest.mark.asyncio
    async def test_storage_usage_calculation(self, storage_manager, temp_storage_dir):
        """Test storage space usage calculation."""
        # Add some test files
        for i in range(3):
            test_image = Path(temp_storage_dir) / f"usage_test_{i}.jpg"
            test_image.write_bytes(b"X" * 1000)  # 1KB each

            capture_result = CaptureResult(
                file_paths=[str(test_image)],
                capture_time_ms=40.0,
                quality_score=0.8,
                metadata={},
                actual_settings=CaptureSettings()
            )
            await storage_manager.store_capture_result(capture_result)

        usage_info = await storage_manager.get_storage_usage()

        assert isinstance(usage_info, dict)
        assert "total_size_bytes" in usage_info
        assert "total_files" in usage_info
        assert "usage_percentage" in usage_info
        assert usage_info["total_files"] >= 3
        assert usage_info["total_size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_storage_full_cleanup(self, storage_manager):
        """Test automatic cleanup when storage approaches capacity."""
        # Mock storage to appear over capacity (1.1GB > 1.0GB limit)
        with patch.object(storage_manager, '_get_directory_size_bytes', return_value=int(1.1 * 1024 * 1024 * 1024)):  # 1.1GB
            with patch.object(storage_manager, 'cleanup_old_files', return_value=5) as mock_cleanup:
                # This should trigger cleanup since max_size_gb is 1.0GB
                await storage_manager._check_available_space()
                mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_files_by_date_range(self, storage_manager, temp_storage_dir):
        """Test retrieving files by date range."""
        # Create test files for different dates
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        # Store file for today
        today_image = Path(temp_storage_dir) / "today.jpg"
        today_image.write_bytes(b"today image")
        today_result = CaptureResult(
            file_paths=[str(today_image)],
            capture_time_ms=30.0,
            quality_score=0.8,
            metadata={"date": "today"},
            actual_settings=CaptureSettings()
        )
        await storage_manager.store_capture_result(today_result)

        # Create yesterday's files manually (simulate)
        yesterday_dir = storage_manager.images_dir / yesterday.strftime("%Y/%m/%d")
        yesterday_dir.mkdir(parents=True, exist_ok=True)
        yesterday_file = yesterday_dir / "yesterday.jpg"
        yesterday_file.write_bytes(b"yesterday image")

        # Get today's files
        today_files = await storage_manager.get_files_by_date_range(
            start_date=today.date(),
            end_date=today.date()
        )

        assert len(today_files) >= 1
        # Should contain today's date in the path (YYYY/MM/DD format)
        today_paths = [str(f) for f in today_files]
        today_date_str = today.strftime("%Y/%m/%d")
        assert any(today_date_str in path for path in today_paths)

    @pytest.mark.asyncio
    async def test_get_transfer_queue(self, storage_manager, temp_storage_dir):
        """Test transfer queue functionality."""
        # Create test capture
        test_image = Path(temp_storage_dir) / "transfer_test.jpg"
        test_image.write_bytes(b"transfer test image")

        capture_result = CaptureResult(
            file_paths=[str(test_image)],
            capture_time_ms=35.0,
            quality_score=0.85,
            metadata={"transfer_ready": True},
            actual_settings=CaptureSettings()
        )

        stored_paths = await storage_manager.store_capture_result(capture_result)

        # Mark for transfer
        await storage_manager.mark_for_transfer(stored_paths[0])

        # Check transfer queue
        transfer_queue = await storage_manager.get_transfer_queue()
        assert len(transfer_queue) > 0
        assert stored_paths[0] in [item["file_path"] for item in transfer_queue]

    @pytest.mark.asyncio
    async def test_mark_transfer_complete(self, storage_manager, temp_storage_dir):
        """Test marking transfers as complete."""
        # Create and store test file
        test_image = Path(temp_storage_dir) / "complete_test.jpg"
        test_image.write_bytes(b"complete test image")

        capture_result = CaptureResult(
            file_paths=[str(test_image)],
            capture_time_ms=42.0,
            quality_score=0.9,
            metadata={},
            actual_settings=CaptureSettings()
        )

        stored_paths = await storage_manager.store_capture_result(capture_result)
        file_path = stored_paths[0]

        # Mark for transfer and then complete
        await storage_manager.mark_for_transfer(file_path)
        await storage_manager.mark_transfer_complete(file_path)

        # Should no longer be in transfer queue
        transfer_queue = await storage_manager.get_transfer_queue()
        queued_paths = [item["file_path"] for item in transfer_queue]
        assert file_path not in queued_paths

    @pytest.mark.asyncio
    async def test_file_organization_by_date(self, storage_manager, temp_storage_dir):
        """Test that files are properly organized by capture date."""
        # Store multiple files over simulated time
        test_dates = [
            datetime.now(),
            datetime.now() - timedelta(days=1),
            datetime.now() - timedelta(days=2)
        ]

        stored_files = []
        for i, test_date in enumerate(test_dates):
            test_image = Path(temp_storage_dir) / f"date_test_{i}.jpg"
            test_image.write_bytes(f"date test {i}".encode())

            # Mock the datetime for proper date organization
            with patch('src.storage_manager.datetime') as mock_datetime:
                mock_datetime.now.return_value = test_date

                capture_result = CaptureResult(
                    file_paths=[str(test_image)],
                    capture_time_ms=30.0,
                    quality_score=0.8,
                    metadata={"test_date": i},
                    actual_settings=CaptureSettings()
                )

                stored_paths = await storage_manager.store_capture_result(capture_result)
                stored_files.extend(stored_paths)

        # Verify files are in correct date directories
        for i, stored_file in enumerate(stored_files):
            stored_path = Path(stored_file)
            expected_date = test_dates[i].strftime("%Y/%m/%d")
            assert expected_date in str(stored_path)

    @pytest.mark.asyncio
    async def test_error_handling_missing_source_file(self, storage_manager):
        """Test error handling when source file is missing."""
        # Try to store result with non-existent file
        capture_result = CaptureResult(
            file_paths=["/nonexistent/file.jpg"],
            capture_time_ms=30.0,
            quality_score=0.8,
            metadata={},
            actual_settings=CaptureSettings()
        )

        with pytest.raises(FileNotFoundError):
            await storage_manager.store_capture_result(capture_result)

    @pytest.mark.asyncio
    async def test_get_statistics(self, storage_manager, temp_storage_dir):
        """Test storage statistics retrieval."""
        # Add some test files
        for i in range(3):
            test_image = Path(temp_storage_dir) / f"stats_test_{i}.jpg"
            test_image.write_bytes(b"X" * 500)  # 500 bytes each

            capture_result = CaptureResult(
                file_paths=[str(test_image)],
                capture_time_ms=30.0,
                quality_score=0.8,
                metadata={},
                actual_settings=CaptureSettings()
            )
            await storage_manager.store_capture_result(capture_result)

        stats = await storage_manager.get_statistics()

        assert isinstance(stats, dict)
        assert "total_files" in stats
        assert "total_size_bytes" in stats
        assert "oldest_file_age_hours" in stats
        assert "cleanup_runs" in stats
        assert "files_cleaned" in stats

        assert stats["total_files"] >= 3

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_storage_dir):
        """Test storage manager as async context manager."""
        async with StorageManager(temp_storage_dir) as manager:
            assert manager._is_initialized
            assert manager.buffer_path.exists()

        # Should be cleaned up after context exit
        assert not manager._is_initialized


class TestStorageManagerIntegration:
    """Integration tests for storage manager with realistic workflows."""

    @pytest_asyncio.fixture
    async def realistic_storage_manager(self, temp_dir):
        """Create storage manager with realistic settings."""
        manager = StorageManager(
            buffer_path=temp_dir,
            max_size_gb=0.1,  # 100MB for testing
            retention_hours=48  # 48 hours like production
        )
        await manager.initialize()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_full_workflow_single_capture(self, realistic_storage_manager, temp_dir):
        """Test complete workflow for single image capture (CAP-004)."""
        # Simulate a real capture workflow
        original_image = Path(temp_dir) / "mountain_sunrise.jpg"
        original_image.write_bytes(b"beautiful mountain sunrise image" * 1000)  # ~32KB

        # Create realistic capture result
        capture_result = CaptureResult(
            file_paths=[str(original_image)],
            capture_time_ms=48.5,
            quality_score=0.89,
            metadata={
                "timestamp": "2025-09-25T06:15:00Z",
                "camera_model": "Arducam IMX519",
                "location": {"latitude": 45.8326, "longitude": -121.7113},  # Mt. Hood
                "weather": {"temperature_c": 5.2, "conditions": "clear"},
                "settings": {"iso": 100, "exposure_ms": 125, "aperture": "f/2.0"}
            },
            actual_settings=CaptureSettings(
                iso=100,
                exposure_time_us=125000,
                quality=95,
                format="JPEG"
            )
        )

        # Store the capture
        stored_paths = await realistic_storage_manager.store_capture_result(capture_result)

        # Verify storage
        assert len(stored_paths) == 1
        stored_file = Path(stored_paths[0])
        assert stored_file.exists()
        assert stored_file.suffix == '.jpg'

        # Verify date organization
        now = datetime.now()
        expected_path = realistic_storage_manager.images_dir / now.strftime("%Y/%m/%d")
        assert stored_file.parent == expected_path

        # Verify metadata storage
        metadata_file = realistic_storage_manager.metadata_dir / stored_file.relative_to(realistic_storage_manager.images_dir).with_suffix('.json')
        assert metadata_file.exists()

        # Verify metadata content
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        assert metadata["metadata"]["camera_model"] == "Arducam IMX519"
        assert metadata["metadata"]["location"]["latitude"] == 45.8326

    @pytest.mark.asyncio
    async def test_full_workflow_hdr_sequence(self, realistic_storage_manager, temp_dir):
        """Test complete workflow for HDR sequence capture."""
        # Create HDR sequence files
        hdr_files = []
        exposures = ["-2ev", "0ev", "+2ev"]

        for i, exposure in enumerate(exposures):
            hdr_file = Path(temp_dir) / f"hdr_mountain_{exposure}.jpg"
            hdr_file.write_bytes(f"HDR image {exposure}".encode() * 2000)  # ~24KB each
            hdr_files.append(str(hdr_file))

        # Create realistic HDR capture result
        hdr_result = CaptureResult(
            file_paths=hdr_files,
            capture_time_ms=145.2,  # Longer for sequence
            quality_score=0.94,  # Higher quality for HDR
            metadata={
                "sequence_type": "hdr_bracket",
                "sequence_count": 3,
                "exposure_stops": [-2, 0, 2],
                "base_exposure_us": 1000,
                "timestamp": "2025-09-25T19:30:00Z",
                "scene_type": "golden_hour"
            },
            actual_settings=CaptureSettings(
                iso=100,
                hdr_bracket_stops=[-2, 0, 2],
                quality=95
            )
        )

        # Store the HDR sequence
        stored_paths = await realistic_storage_manager.store_capture_result(hdr_result)

        # Verify all files stored
        assert len(stored_paths) == 3
        for stored_path in stored_paths:
            assert Path(stored_path).exists()

        # Verify they're in the same directory (same capture session)
        stored_dirs = {Path(p).parent for p in stored_paths}
        assert len(stored_dirs) == 1  # All in same directory

        # Verify metadata includes sequence information
        first_file = Path(stored_paths[0])
        # For sequence captures, metadata file uses base timestamp without sequence suffix
        first_file_name = first_file.stem
        # Remove sequence suffix (_000, _001, etc.) to get base timestamp
        if '_' in first_file_name:
            parts = first_file_name.split('_')
            if len(parts) >= 4 and parts[-1].isdigit() and len(parts[-1]) == 3:
                base_timestamp = '_'.join(parts[:-1])  # Remove the sequence number
            else:
                base_timestamp = first_file_name
        else:
            base_timestamp = first_file_name

        metadata_file = realistic_storage_manager.metadata_dir / first_file.relative_to(realistic_storage_manager.images_dir).parent / f"{base_timestamp}.json"

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        assert metadata["metadata"]["sequence_type"] == "hdr_bracket"
        assert metadata["metadata"]["sequence_count"] == 3

    @pytest.mark.asyncio
    async def test_storage_cleanup_lifecycle(self, realistic_storage_manager):
        """Test storage cleanup over simulated lifecycle."""
        # Create files from different time periods
        file_ages_hours = [1, 25, 49, 73]  # Within retention, just over, way over

        for age_hours in file_ages_hours:
            # Create old directory structure
            old_time = datetime.now() - timedelta(hours=age_hours)
            old_date_path = realistic_storage_manager.images_dir / old_time.strftime("%Y/%m/%d")
            old_date_path.mkdir(parents=True, exist_ok=True)

            # Create test file
            old_file = old_date_path / f"image_{age_hours}h_old.jpg"
            old_file.write_bytes(b"old image data")

            # Set file modification time to simulate age
            import os
            old_timestamp = (old_time).timestamp()
            os.utime(old_file, (old_timestamp, old_timestamp))

        # Run cleanup
        cleanup_result = await realistic_storage_manager.cleanup_old_files()

        # Should have cleaned files older than retention (48 hours)
        cleaned_count = cleanup_result['files_removed']
        assert cleaned_count >= 1  # Should clean at least the 73-hour old file

        # Verify recent files still exist
        recent_files = list(realistic_storage_manager.images_dir.rglob("image_1h_old.jpg"))
        assert len(recent_files) > 0

    @pytest.mark.asyncio
    async def test_transfer_queue_workflow(self, realistic_storage_manager, temp_dir):
        """Test realistic transfer queue workflow for processing pipeline."""
        # Store multiple captures
        capture_files = []
        for i in range(3):
            test_image = Path(temp_dir) / f"transfer_workflow_{i}.jpg"
            test_image.write_bytes(f"transfer test image {i}".encode() * 1000)

            capture_result = CaptureResult(
                file_paths=[str(test_image)],
                capture_time_ms=40.0 + i * 5,
                quality_score=0.8 + i * 0.05,
                metadata={"sequence": i},
                actual_settings=CaptureSettings()
            )

            stored_paths = await realistic_storage_manager.store_capture_result(capture_result)
            capture_files.extend(stored_paths)

            # Small delay to ensure unique timestamps
            import asyncio
            await asyncio.sleep(0.001)

        # Mark files for transfer (simulate processing pipeline pickup)
        for file_path in capture_files:
            await realistic_storage_manager.mark_for_transfer(file_path)

        # Check transfer queue
        transfer_queue = await realistic_storage_manager.get_transfer_queue()
        assert len(transfer_queue) == 3

        # Simulate processing completion
        for item in transfer_queue:
            await realistic_storage_manager.mark_transfer_complete(item["file_path"])

        # Queue should be empty
        final_queue = await realistic_storage_manager.get_transfer_queue()
        assert len(final_queue) == 0