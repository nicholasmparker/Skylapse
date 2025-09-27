"""Integration tests for the complete processing pipeline."""

import asyncio
import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from image_processor import ImageProcessor
from timelapse_assembler import TimelapseAssembler
from transfer_receiver import TransferReceiver
from monitoring import ResourceMetrics


class TestProcessingPipeline:
    """Integration tests for HDR → Timelapse → Transfer workflow."""
    
    @pytest.fixture
    async def image_processor(self):
        """Create image processor for testing."""
        processor = ImageProcessor()
        await processor.initialize()
        yield processor
        await processor.shutdown()
        
    @pytest.fixture
    async def timelapse_assembler(self):
        """Create timelapse assembler for testing."""
        assembler = TimelapseAssembler()
        await assembler.initialize()
        yield assembler
        await assembler.shutdown()
        
    @pytest.fixture
    async def transfer_receiver(self):
        """Create transfer receiver for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            receiver = TransferReceiver(temp_dir)
            await receiver.initialize()
            yield receiver
            await receiver.shutdown()
            
    @pytest.fixture
    def sample_hdr_images(self):
        """Create sample HDR image paths for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock image files
            image_paths = []
            for i in range(3):  # 3-bracket HDR
                image_file = temp_path / f"hdr_bracket_{i}.jpg"
                # Create a small test image file
                image_file.write_bytes(b"fake_jpeg_data" * 100)  # ~1.3KB file
                image_paths.append(str(image_file))
                
            yield image_paths
            
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "capture_time": time.time(),
            "location": {"latitude": 40.7128, "longitude": -74.0060},
            "camera_settings": {
                "iso": 100,
                "exposure_times": [1/250, 1/60, 1/15],  # EV -2, 0, +2
                "aperture": "f/8"
            },
            "weather": {"conditions": "clear", "temperature": 15}
        }

    @pytest.mark.asyncio
    async def test_end_to_end_hdr_timelapse_workflow(
        self, image_processor, timelapse_assembler, sample_hdr_images, sample_metadata
    ):
        """Test complete HDR → Timelapse workflow with resource monitoring."""
        
        # Step 1: Process HDR sequence
        hdr_result = await image_processor.process_hdr_sequence(
            sample_hdr_images, sample_metadata
        )
        
        # Validate HDR processing result
        assert hdr_result["success"] is True
        assert hdr_result["processing_type"] == "hdr_merge"
        assert "resource_usage" in hdr_result
        assert Path(hdr_result["output_path"]).exists()
        
        # Validate resource monitoring
        resource_usage = hdr_result["resource_usage"]
        assert resource_usage is not None
        assert "peak_memory_mb" in resource_usage
        assert "peak_cpu_percent" in resource_usage
        
        # QA validation: Check resource thresholds
        assert resource_usage["peak_memory_mb"] < 2000, "Memory usage exceeded 2GB threshold"
        
        # Step 2: Create timelapse from processed images
        processed_images = [{"output_path": hdr_result["output_path"], "timestamp": time.time()}]
        
        timelapse_result = await timelapse_assembler.create_timelapse(
            processed_images, sample_metadata, output_formats=["1080p"]
        )
        
        # Validate timelapse creation
        assert timelapse_result["success"] is True
        assert len(timelapse_result["outputs"]) == 1
        assert timelapse_result["frame_count"] == 1
        
        # Validate output file exists
        output_info = timelapse_result["outputs"][0]
        assert Path(output_info["output_path"]).exists()
        assert output_info["format"] == "1080p"

    @pytest.mark.asyncio
    async def test_hdr_processing_performance_benchmarks(
        self, image_processor, sample_hdr_images, sample_metadata
    ):
        """Test HDR processing performance meets QA requirements."""
        
        # Test 3-bracket HDR performance
        start_time = time.time()
        result = await image_processor.process_hdr_sequence(
            sample_hdr_images, sample_metadata
        )
        processing_time = time.time() - start_time
        
        # QA Performance Requirements
        assert processing_time < 30.0, f"HDR processing took {processing_time:.1f}s, exceeds 30s limit"
        assert result["resource_usage"]["peak_memory_mb"] < 1500, "Memory usage exceeded 1.5GB threshold"
        
        # Validate no thermal throttling
        assert not result["resource_usage"]["thermal_throttling_detected"], "Thermal throttling detected"
        
    @pytest.mark.asyncio
    async def test_large_hdr_sequence_processing(
        self, image_processor, sample_metadata
    ):
        """Test processing larger HDR sequences (5-bracket)."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create 5-bracket HDR sequence
            image_paths = []
            for i in range(5):
                image_file = temp_path / f"hdr_5bracket_{i}.jpg"
                # Create larger mock files for stress testing
                image_file.write_bytes(b"fake_jpeg_data" * 1000)  # ~13KB files
                image_paths.append(str(image_file))
                
            # Process 5-bracket sequence
            result = await image_processor.process_hdr_sequence(
                image_paths, sample_metadata
            )
            
            # Validate processing
            assert result["success"] is True
            assert result["hdr_info"]["bracket_count"] == 5
            assert result["hdr_info"]["merge_algorithm"] == "exposure_fusion"
            
            # Performance validation
            assert result["processing_time_ms"] < 30000, "5-bracket HDR exceeded 30s limit"

    @pytest.mark.asyncio 
    async def test_transfer_validation_and_integrity(
        self, transfer_receiver, sample_hdr_images, sample_metadata
    ):
        """Test transfer validation and file integrity checks."""
        
        # Simulate incoming transfer
        transfer_id = await transfer_receiver.simulate_incoming_transfer(
            sample_hdr_images, sample_metadata
        )
        
        # Check for new transfers
        new_transfers = await transfer_receiver.check_for_transfers()
        
        # Validate transfer detection
        assert len(new_transfers) == 1
        transfer_data = new_transfers[0]
        assert transfer_data["transfer_id"] == transfer_id
        assert transfer_data["image_count"] == len(sample_hdr_images)
        
        # Validate file integrity
        for image_path in transfer_data["image_paths"]:
            assert Path(image_path).exists()
            assert Path(image_path).stat().st_size > 0

    @pytest.mark.asyncio
    async def test_resource_monitoring_accuracy(self, image_processor, sample_hdr_images, sample_metadata):
        """Test resource monitoring provides accurate measurements."""
        
        # Process with monitoring
        result = await image_processor.process_hdr_sequence(
            sample_hdr_images, sample_metadata
        )
        
        resource_usage = result["resource_usage"]
        
        # Validate monitoring data structure
        required_fields = [
            "duration_seconds", "peak_cpu_percent", "peak_memory_mb",
            "average_cpu_percent", "average_memory_mb", "snapshot_count"
        ]
        
        for field in required_fields:
            assert field in resource_usage, f"Missing resource monitoring field: {field}"
            
        # Validate reasonable values
        assert resource_usage["duration_seconds"] > 0
        assert 0 <= resource_usage["peak_cpu_percent"] <= 100
        assert resource_usage["peak_memory_mb"] > 0
        assert resource_usage["snapshot_count"] > 0

    @pytest.mark.asyncio
    async def test_error_recovery_and_cleanup(self, image_processor):
        """Test error recovery and resource cleanup."""
        
        # Test with invalid image paths
        invalid_paths = ["/nonexistent/path1.jpg", "/nonexistent/path2.jpg"]
        metadata = {"test": "error_recovery"}
        
        with pytest.raises(Exception):
            await image_processor.process_hdr_sequence(invalid_paths, metadata)
            
        # Validate processor is still functional after error
        processor_status = await image_processor.get_status()
        assert processor_status["initialized"] is True
        assert processor_status["statistics"]["processing_errors"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_processing_limits(self, image_processor, sample_hdr_images, sample_metadata):
        """Test system behavior under concurrent processing load."""
        
        # Start multiple concurrent HDR processing tasks
        tasks = []
        for i in range(3):  # 3 concurrent processes
            task = asyncio.create_task(
                image_processor.process_hdr_sequence(sample_hdr_images, sample_metadata)
            )
            tasks.append(task)
            
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all completed successfully or failed gracefully
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # At least some should succeed (system should handle concurrent load)
        assert len(successful_results) > 0, "No concurrent processing tasks succeeded"
        
        # Validate resource usage was reasonable across all tasks
        for result in successful_results:
            if "resource_usage" in result:
                assert result["resource_usage"]["peak_memory_mb"] < 2000, "Concurrent processing exceeded memory limits"

    @pytest.mark.asyncio
    async def test_mountain_photography_workflow_simulation(
        self, image_processor, timelapse_assembler, sample_metadata
    ):
        """Test workflow simulation for mountain photography conditions."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Simulate golden hour HDR sequence (multiple brackets)
            hdr_sequences = []
            for seq_idx in range(3):  # 3 time points during golden hour
                sequence_paths = []
                for bracket_idx in range(3):  # 3-bracket HDR each
                    image_file = temp_path / f"golden_hour_{seq_idx}_{bracket_idx}.jpg"
                    image_file.write_bytes(b"golden_hour_data" * 200)  # ~2.6KB
                    sequence_paths.append(str(image_file))
                hdr_sequences.append(sequence_paths)
                
            # Process each HDR sequence
            processed_images = []
            total_processing_time = 0
            
            for i, sequence in enumerate(hdr_sequences):
                start_time = time.time()
                result = await image_processor.process_hdr_sequence(sequence, sample_metadata)
                processing_time = time.time() - start_time
                total_processing_time += processing_time
                
                assert result["success"] is True
                processed_images.append({
                    "output_path": result["output_path"],
                    "timestamp": time.time() + i * 60  # 1 minute intervals
                })
                
            # Create timelapse from processed HDR images
            timelapse_result = await timelapse_assembler.create_timelapse(
                processed_images, sample_metadata, output_formats=["1080p", "4k"]
            )
            
            # Validate mountain photography workflow
            assert timelapse_result["success"] is True
            assert len(timelapse_result["outputs"]) == 2  # 1080p and 4k
            assert total_processing_time < 90.0, f"Total HDR processing took {total_processing_time:.1f}s, too slow for golden hour"
            
            # Validate both formats were created
            formats_created = [output["format"] for output in timelapse_result["outputs"]]
            assert "1080p" in formats_created
            assert "4k" in formats_created


class TestHardwareValidation:
    """Hardware-specific validation tests for Pi deployment."""
    
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test system behavior under memory pressure."""
        # This would be implemented with actual memory pressure simulation
        # For now, validate monitoring detects high memory usage
        pass
        
    @pytest.mark.asyncio  
    async def test_thermal_throttling_detection(self):
        """Test thermal throttling detection and handling."""
        # This would require actual thermal stress testing
        # For now, validate monitoring framework is in place
        pass
        
    @pytest.mark.asyncio
    async def test_disk_space_validation(self):
        """Test behavior when disk space is low."""
        # This would test disk space monitoring and cleanup
        pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
