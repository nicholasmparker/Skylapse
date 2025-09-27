"""Tests for image processor functionality."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path

from src.image_processor import ImageProcessor


class TestImageProcessor:
    """Test cases for ImageProcessor class."""

    @pytest.fixture
    async def processor(self):
        """Create and initialize an ImageProcessor."""
        processor = ImageProcessor()
        await processor.initialize()
        yield processor
        await processor.shutdown()

    @pytest.fixture
    def sample_image(self):
        """Create a sample image file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            # Create minimal JPEG-like content
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
                    0x01,  # Version
                    0x01,
                    0x00,
                    0x48,
                    0x00,
                    0x48,  # DPI
                    0x00,
                    0x00,  # No thumbnail
                ]
            )

            # Add sample data
            sample_data = b"Sample image data for testing" * 100
            jpeg_header.extend(sample_data)

            # Add EOI marker
            jpeg_header.extend([0xFF, 0xD9])

            temp_file.write(jpeg_header)
            temp_file.flush()

            yield temp_file.name

        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)

    @pytest.fixture
    def sample_metadata(self):
        """Create sample image metadata."""
        return {
            "capture_time": 1672531200.0,
            "camera_model": "Mock Camera",
            "exposure_time_us": 1000,
            "iso": 100,
            "white_balance_k": 5500,
        }

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test processor initialization and shutdown."""
        processor = ImageProcessor()
        assert not processor._is_initialized

        await processor.initialize()
        assert processor._is_initialized

        await processor.shutdown()
        assert not processor._is_initialized

    @pytest.mark.asyncio
    async def test_basic_image_processing(self, processor, sample_image, sample_metadata):
        """Test basic image processing functionality."""
        processing_options = {"quality_enhancement": True}

        result = await processor.process_image(
            image_path=sample_image, metadata=sample_metadata, processing_options=processing_options
        )

        # Validate result structure
        assert isinstance(result, dict)
        assert "input_path" in result
        assert "output_path" in result
        assert "processing_applied" in result
        assert "timestamp" in result
        assert "metadata" in result

        assert result["input_path"] == sample_image
        assert Path(result["output_path"]).exists()
        assert isinstance(result["processing_applied"], list)
        assert len(result["processing_applied"]) > 0

    @pytest.mark.asyncio
    async def test_processing_with_options(self, processor, sample_image, sample_metadata):
        """Test processing with various options."""
        processing_options = {
            "noise_reduction": True,
            "sharpening": True,
            "color_correction": True,
            "hdr_processing": False,
        }

        result = await processor.process_image(
            image_path=sample_image, metadata=sample_metadata, processing_options=processing_options
        )

        # Check that processing options influenced the applied operations
        applied = result["processing_applied"]
        assert "noise_reduction" in applied
        assert "sharpening" in applied
        assert "color_correction" in applied

        quality_improvements = result["quality_improvements"]
        assert quality_improvements["noise_reduction"] is True
        assert quality_improvements["sharpening"] is True
        assert quality_improvements["color_correction"] is True

    @pytest.mark.asyncio
    async def test_hdr_sequence_processing(self, processor, sample_metadata):
        """Test HDR sequence processing."""
        # Create multiple sample images for HDR
        hdr_images = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=f"_hdr_{i}.jpg", delete=False) as temp_file:
                # Simple JPEG-like content
                content = f"HDR image {i} data".encode() * 50
                temp_file.write(b"\xff\xd8" + content + b"\xff\xd9")
                temp_file.flush()
                hdr_images.append(temp_file.name)

        try:
            result = await processor.process_hdr_sequence(
                image_paths=hdr_images, metadata=sample_metadata
            )

            assert isinstance(result, dict)
            assert "output_path" in result
            assert "hdr_sequence" in result
            assert "processing_type" in result
            assert result["processing_type"] == "hdr_merge"
            assert result["hdr_sequence"] == hdr_images

        finally:
            # Cleanup
            for image_path in hdr_images:
                Path(image_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_focus_stack_processing(self, processor, sample_metadata):
        """Test focus stacking processing."""
        # Create multiple sample images for focus stacking
        stack_images = []
        for i in range(4):
            with tempfile.NamedTemporaryFile(suffix=f"_focus_{i}.jpg", delete=False) as temp_file:
                content = f"Focus stack image {i} data".encode() * 40
                temp_file.write(b"\xff\xd8" + content + b"\xff\xd9")
                temp_file.flush()
                stack_images.append(temp_file.name)

        try:
            result = await processor.process_focus_stack(
                image_paths=stack_images, metadata=sample_metadata
            )

            assert isinstance(result, dict)
            assert "output_path" in result
            assert "focus_stack_sequence" in result
            assert "processing_type" in result
            assert result["processing_type"] == "focus_stack"
            assert result["focus_stack_sequence"] == stack_images

        finally:
            # Cleanup
            for image_path in stack_images:
                Path(image_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_processing_statistics(self, processor, sample_image, sample_metadata):
        """Test that processing statistics are updated correctly."""
        # Get initial statistics
        initial_stats = (await processor.get_status())["statistics"]
        initial_processed = initial_stats["images_processed"]

        # Process an image
        await processor.process_image(image_path=sample_image, metadata=sample_metadata)

        # Check updated statistics
        updated_stats = (await processor.get_status())["statistics"]
        assert updated_stats["images_processed"] == initial_processed + 1
        assert updated_stats["average_processing_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_processing_error_handling(self, processor, sample_metadata):
        """Test error handling for invalid inputs."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            await processor.process_image(
                image_path="/nonexistent/file.jpg", metadata=sample_metadata
            )

        # Check that error was recorded in statistics
        stats = (await processor.get_status())["statistics"]
        assert stats["processing_errors"] > 0

    @pytest.mark.asyncio
    async def test_empty_sequence_handling(self, processor, sample_metadata):
        """Test handling of empty image sequences."""
        # Test HDR with empty list
        with pytest.raises(ValueError):
            await processor.process_hdr_sequence([], sample_metadata)

        # Test focus stack with empty list
        with pytest.raises(ValueError):
            await processor.process_focus_stack([], sample_metadata)

    @pytest.mark.asyncio
    async def test_metadata_preservation(self, processor, sample_image, sample_metadata):
        """Test that metadata is properly preserved and enhanced."""
        result = await processor.process_image(image_path=sample_image, metadata=sample_metadata)

        # Check that original metadata is preserved
        assert result["metadata"] == sample_metadata

        # Check that processing metadata file exists
        output_path = Path(result["output_path"])
        metadata_file = output_path.with_suffix(".json")
        assert metadata_file.exists()

        # Load and verify processing metadata
        with open(metadata_file, "r") as f:
            processing_metadata = json.load(f)

        assert "original_file" in processing_metadata
        assert "processed_file" in processing_metadata
        assert "processing_timestamp" in processing_metadata
        assert "original_metadata" in processing_metadata
        assert processing_metadata["original_metadata"] == sample_metadata

    @pytest.mark.asyncio
    async def test_get_status(self, processor):
        """Test processor status retrieval."""
        status = await processor.get_status()

        assert isinstance(status, dict)
        assert status["initialized"] is True
        assert "statistics" in status
        assert "capabilities" in status
        assert "future_capabilities" in status

        # Check capabilities
        capabilities = status["capabilities"]
        assert "basic_processing" in capabilities
        assert "hdr_sequence" in capabilities
        assert "focus_stacking" in capabilities

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processor, sample_metadata):
        """Test concurrent image processing."""
        # Create multiple sample images
        image_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(
                suffix=f"_concurrent_{i}.jpg", delete=False
            ) as temp_file:
                content = f"Concurrent test image {i}".encode() * 30
                temp_file.write(b"\xff\xd8" + content + b"\xff\xd9")
                temp_file.flush()
                image_files.append(temp_file.name)

        try:
            # Process images concurrently
            tasks = []
            for image_path in image_files:
                task = processor.process_image(image_path=image_path, metadata=sample_metadata)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # Verify all processing completed successfully
            assert len(results) == 3
            for result in results:
                assert "output_path" in result
                assert Path(result["output_path"]).exists()

        finally:
            # Cleanup
            for image_path in image_files:
                Path(image_path).unlink(missing_ok=True)

    def test_processing_applied_logic(self, processor):
        """Test the logic for determining applied processing operations."""
        # Test with no processing options
        applied = processor._get_processing_applied(None)
        assert applied == ["basic_copy"]

        # Test with processing options
        options = {
            "noise_reduction": True,
            "sharpening": True,
            "color_correction": False,
            "hdr_processing": True,
        }

        applied = processor._get_processing_applied(options)
        assert "noise_reduction" in applied
        assert "sharpening" in applied
        assert "hdr_processing" in applied
        assert "color_correction" not in applied

        # Test with empty processing options
        applied = processor._get_processing_applied({})
        assert applied == ["basic_copy"]


class TestImageProcessorIntegration:
    """Integration tests for image processor."""

    @pytest.mark.asyncio
    async def test_complete_processing_workflow(self):
        """Test complete processing workflow from initialization to cleanup."""
        processor = ImageProcessor()

        # Initialize
        await processor.initialize()
        assert processor._is_initialized

        # Create test image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            content = b"Integration test image data" * 100
            temp_file.write(b"\xff\xd8" + content + b"\xff\xd9")
            temp_file.flush()
            image_path = temp_file.name

        try:
            # Process with various options
            metadata = {"test": "integration"}
            options = {"noise_reduction": True, "sharpening": True, "hdr_processing": False}

            result = await processor.process_image(
                image_path=image_path, metadata=metadata, processing_options=options
            )

            # Verify result
            assert Path(result["output_path"]).exists()
            assert result["processing_applied"] == ["noise_reduction", "sharpening"]

            # Check statistics
            stats = (await processor.get_status())["statistics"]
            assert stats["images_processed"] >= 1

        finally:
            # Cleanup
            Path(image_path).unlink(missing_ok=True)
            if "output_path" in locals() and Path(result["output_path"]).exists():
                Path(result["output_path"]).unlink(missing_ok=True)

            await processor.shutdown()
            assert not processor._is_initialized
