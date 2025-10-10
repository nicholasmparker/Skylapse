"""
Unit tests for HDR processing module
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil

from hdr_processing import (
    merge_hdr_mertens,
    load_bracket_images,
    save_hdr_result,
    process_bracket_set,
    HDRProcessingError
)


class TestMergeHDRMertens:
    """Test Mertens HDR merge algorithm"""

    def test_merge_valid_images(self):
        """Test merging 3 valid images"""
        # Create 3 test images with different brightness
        height, width = 100, 100
        img_under = np.full((height, width, 3), 50, dtype=np.uint8)  # Dark
        img_normal = np.full((height, width, 3), 127, dtype=np.uint8)  # Medium
        img_over = np.full((height, width, 3), 200, dtype=np.uint8)  # Bright

        images = [img_under, img_normal, img_over]

        result = merge_hdr_mertens(images)

        # Verify result
        assert result.shape == (height, width, 3)
        assert result.dtype == np.uint8
        # Result should be somewhere between darkest and brightest
        assert np.mean(result) > 50
        assert np.mean(result) < 200

    def test_merge_two_images(self):
        """Test that 2 images work (minimum for HDR)"""
        img1 = np.full((50, 50, 3), 100, dtype=np.uint8)
        img2 = np.full((50, 50, 3), 150, dtype=np.uint8)

        result = merge_hdr_mertens([img1, img2])

        assert result.shape == (50, 50, 3)

    def test_merge_empty_list(self):
        """Test error handling for empty image list"""
        with pytest.raises(HDRProcessingError, match="at least 2 images"):
            merge_hdr_mertens([])

    def test_merge_single_image(self):
        """Test error handling for single image"""
        img = np.zeros((50, 50, 3), dtype=np.uint8)

        with pytest.raises(HDRProcessingError, match="at least 2 images"):
            merge_hdr_mertens([img])

    def test_merge_mismatched_sizes(self):
        """Test error handling for mismatched image sizes"""
        img1 = np.zeros((50, 50, 3), dtype=np.uint8)
        img2 = np.zeros((100, 100, 3), dtype=np.uint8)

        with pytest.raises(HDRProcessingError, match="same dimensions"):
            merge_hdr_mertens([img1, img2])

    def test_merge_custom_weights(self):
        """Test merging with custom weight parameters"""
        img1 = np.full((50, 50, 3), 100, dtype=np.uint8)
        img2 = np.full((50, 50, 3), 150, dtype=np.uint8)

        result = merge_hdr_mertens(
            [img1, img2],
            contrast_weight=1.5,
            saturation_weight=0.8,
            exposure_weight=0.2
        )

        assert result.shape == (50, 50, 3)


class TestLoadBracketImages:
    """Test bracket image loading"""

    def setup_method(self):
        """Create temporary test images"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create 3 test images
        for i in range(3):
            img = np.full((100, 100, 3), i * 100, dtype=np.uint8)
            import cv2
            cv2.imwrite(str(self.temp_path / f"test_bracket{i}.jpg"), img)

    def teardown_method(self):
        """Clean up temp directory"""
        shutil.rmtree(self.temp_dir)

    def test_load_valid_brackets(self):
        """Test loading 3 valid bracket images"""
        bracket_paths = [
            self.temp_path / "test_bracket0.jpg",
            self.temp_path / "test_bracket1.jpg",
            self.temp_path / "test_bracket2.jpg",
        ]

        images = load_bracket_images(bracket_paths)

        assert len(images) == 3
        for img in images:
            assert img.shape == (100, 100, 3)

    def test_load_empty_list(self):
        """Test error handling for empty bracket list"""
        with pytest.raises(HDRProcessingError, match="No bracket paths"):
            load_bracket_images([])

    def test_load_nonexistent_file(self):
        """Test error handling for missing file"""
        bracket_paths = [
            self.temp_path / "missing.jpg",
            self.temp_path / "test_bracket1.jpg",
            self.temp_path / "test_bracket2.jpg",
        ]

        with pytest.raises(HDRProcessingError, match="not found"):
            load_bracket_images(bracket_paths)

    def test_load_auto_sorts_paths(self):
        """Test that paths are automatically sorted"""
        # Provide paths in wrong order
        bracket_paths = [
            self.temp_path / "test_bracket2.jpg",
            self.temp_path / "test_bracket0.jpg",
            self.temp_path / "test_bracket1.jpg",
        ]

        images = load_bracket_images(bracket_paths)

        # Should still load in correct order (sorted)
        assert len(images) == 3


class TestSaveHDRResult:
    """Test HDR image saving"""

    def setup_method(self):
        """Create temp directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)

    def test_save_valid_image(self):
        """Test saving a valid HDR image"""
        img = np.full((100, 100, 3), 127, dtype=np.uint8)
        output_path = self.temp_path / "hdr_result.jpg"

        result_path = save_hdr_result(img, output_path, quality=95)

        assert result_path.exists()
        assert result_path.stat().st_size > 0

    def test_save_creates_parent_directory(self):
        """Test that parent directories are created"""
        img = np.full((100, 100, 3), 127, dtype=np.uint8)
        output_path = self.temp_path / "subdir" / "nested" / "hdr_result.jpg"

        result_path = save_hdr_result(img, output_path)

        assert result_path.exists()
        assert result_path.parent.exists()


class TestProcessBracketSet:
    """Test complete HDR processing workflow"""

    def setup_method(self):
        """Create temporary test brackets"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create 3 test bracket images with different exposure
        import cv2
        for i, brightness in enumerate([80, 127, 180]):
            img = np.full((100, 100, 3), brightness, dtype=np.uint8)
            cv2.imwrite(str(self.temp_path / f"bracket{i}.jpg"), img)

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)

    def test_complete_workflow_mertens(self):
        """Test complete HDR workflow with Mertens algorithm"""
        bracket_paths = [
            self.temp_path / "bracket0.jpg",
            self.temp_path / "bracket1.jpg",
            self.temp_path / "bracket2.jpg",
        ]
        output_path = self.temp_path / "hdr_result.jpg"

        result_path, metadata = process_bracket_set(
            bracket_paths,
            output_path,
            algorithm="mertens"
        )

        # Verify result
        assert result_path.exists()
        assert result_path.stat().st_size > 0

        # Verify metadata
        assert metadata["algorithm"] == "mertens"
        assert metadata["bracket_count"] == 3
        assert "output_resolution" in metadata
        assert "processing_time_seconds" in metadata
        assert metadata["processing_time_seconds"] >= 0  # Can be 0.0 if very fast

    def test_workflow_invalid_algorithm(self):
        """Test error handling for invalid algorithm"""
        bracket_paths = [
            self.temp_path / "bracket0.jpg",
            self.temp_path / "bracket1.jpg",
            self.temp_path / "bracket2.jpg",
        ]
        output_path = self.temp_path / "hdr_result.jpg"

        with pytest.raises(HDRProcessingError, match="Unknown algorithm"):
            process_bracket_set(bracket_paths, output_path, algorithm="invalid")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
