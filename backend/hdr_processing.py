"""
HDR Image Processing Module

Provides professional-grade exposure fusion for landscape timelapses.
Uses Mertens algorithm for natural-looking HDR without tone mapping artifacts.
"""

import logging
from pathlib import Path
from typing import List, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class HDRProcessingError(Exception):
    """Raised when HDR processing fails"""
    pass


def merge_hdr_mertens(
    images: List[np.ndarray],
    contrast_weight: float = 1.0,
    saturation_weight: float = 1.0,
    exposure_weight: float = 0.0
) -> np.ndarray:
    """
    Merge exposure bracket using Mertens exposure fusion algorithm.

    This is the algorithm used by professional timelapse photographers.
    Creates natural-looking HDR without tone mapping (no "HDR look").

    The Mertens algorithm weights each pixel based on:
    - Contrast: Favors well-defined edges
    - Saturation: Favors colorful pixels
    - Exposure: Favors well-exposed regions (middle gray)

    Args:
        images: List of numpy arrays (BGR images) in ascending exposure order
                (underexposed, normal, overexposed)
        contrast_weight: Weight for contrast metric (default: 1.0)
        saturation_weight: Weight for saturation metric (default: 1.0)
        exposure_weight: Weight for well-exposedness metric (default: 0.0)
                        Note: 0.0 works well for landscape photography

    Returns:
        Merged HDR image (8-bit BGR)

    Raises:
        HDRProcessingError: If images are invalid or merge fails
    """
    if not images or len(images) < 2:
        raise HDRProcessingError(f"Need at least 2 images for HDR merge, got {len(images)}")

    # Validate all images have same shape
    first_shape = images[0].shape
    for i, img in enumerate(images):
        if img.shape != first_shape:
            raise HDRProcessingError(
                f"Image {i} has shape {img.shape}, expected {first_shape}. "
                "All images must have same dimensions."
            )

    try:
        logger.info(f"🎨 Merging {len(images)} exposures using Mertens algorithm")
        logger.debug(f"   Weights - contrast: {contrast_weight}, saturation: {saturation_weight}, exposure: {exposure_weight}")

        # Create Mertens merge object with custom weights
        merge = cv2.createMergeMertens(
            contrast_weight=contrast_weight,
            saturation_weight=saturation_weight,
            exposure_weight=exposure_weight
        )

        # Merge exposures
        # Mertens outputs float values in range [0, 1]
        hdr_float = merge.process(images)

        # Convert to 8-bit (0-255)
        hdr_8bit = np.clip(hdr_float * 255, 0, 255).astype(np.uint8)

        logger.info(f"✓ HDR merge complete: {hdr_8bit.shape[1]}x{hdr_8bit.shape[0]}")

        return hdr_8bit

    except cv2.error as e:
        raise HDRProcessingError(f"OpenCV merge failed: {e}")
    except Exception as e:
        raise HDRProcessingError(f"Unexpected error during HDR merge: {e}")


def merge_hdr_debevec(
    images: List[np.ndarray],
    exposure_times: List[float],
    gamma: float = 2.2
) -> np.ndarray:
    """
    Merge using Debevec algorithm with Reinhard tone mapping.

    More traditional HDR approach. Requires accurate exposure times.
    Produces more dramatic "HDR look" than Mertens.

    Args:
        images: List of numpy arrays (BGR images)
        exposure_times: List of exposure times in seconds (must match image count)
        gamma: Gamma correction for tone mapping (default: 2.2)

    Returns:
        Tone-mapped HDR image (8-bit BGR)

    Raises:
        HDRProcessingError: If processing fails
    """
    if len(images) != len(exposure_times):
        raise HDRProcessingError(
            f"Image count ({len(images)}) must match exposure time count ({len(exposure_times)})"
        )

    try:
        logger.info(f"🎨 Merging {len(images)} exposures using Debevec + Reinhard")

        # Create Debevec merge object
        merge = cv2.createMergeDebevec()

        # Merge to HDR (32-bit float)
        times = np.array(exposure_times, dtype=np.float32)
        hdr = merge.process(images, times=times)

        # Tone mapping with Reinhard
        tonemap = cv2.createTonemapReinhard(gamma=gamma)
        ldr = tonemap.process(hdr)

        # Convert to 8-bit
        ldr_8bit = np.clip(ldr * 255, 0, 255).astype(np.uint8)

        logger.info(f"✓ HDR merge complete: {ldr_8bit.shape[1]}x{ldr_8bit.shape[0]}")

        return ldr_8bit

    except Exception as e:
        raise HDRProcessingError(f"Debevec merge failed: {e}")


def load_bracket_images(
    bracket_paths: List[Union[str, Path]]
) -> List[np.ndarray]:
    """
    Load exposure bracket images from disk.

    Args:
        bracket_paths: List of paths to bracket images (any order)
                      Will be sorted to ensure correct exposure order

    Returns:
        List of loaded images (BGR numpy arrays)

    Raises:
        HDRProcessingError: If any image fails to load
    """
    if not bracket_paths:
        raise HDRProcessingError("No bracket paths provided")

    # Sort paths to ensure consistent order (bracket0, bracket1, bracket2)
    sorted_paths = sorted([Path(p) for p in bracket_paths])

    logger.info(f"📁 Loading {len(sorted_paths)} bracket images:")
    images = []

    for i, path in enumerate(sorted_paths):
        logger.info(f"   [{i}] {path.name}")

        if not path.exists():
            raise HDRProcessingError(f"Bracket image not found: {path}")

        img = cv2.imread(str(path))

        if img is None:
            raise HDRProcessingError(f"Failed to load image: {path}")

        images.append(img)

    logger.info(f"✓ Loaded {len(images)} images successfully")
    return images


def save_hdr_result(
    image: np.ndarray,
    output_path: Union[str, Path],
    quality: int = 95
) -> Path:
    """
    Save HDR merged image to disk.

    Args:
        image: Merged HDR image (8-bit BGR)
        output_path: Where to save the image
        quality: JPEG quality (0-100, default: 95 for high quality)

    Returns:
        Path to saved image

    Raises:
        HDRProcessingError: If save fails
    """
    output_path = Path(output_path)

    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save with high quality
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        success = cv2.imwrite(str(output_path), image, encode_params)

        if not success:
            raise HDRProcessingError(f"Failed to write image to {output_path}")

        file_size_mb = output_path.stat().st_size / 1024 / 1024
        logger.info(f"💾 Saved HDR image: {output_path.name} ({file_size_mb:.1f} MB)")

        return output_path

    except Exception as e:
        raise HDRProcessingError(f"Failed to save image: {e}")


def process_bracket_set(
    bracket_paths: List[Union[str, Path]],
    output_path: Union[str, Path],
    algorithm: str = "mertens",
    **kwargs
) -> Tuple[Path, dict]:
    """
    Complete HDR processing workflow: load, merge, save.

    This is the main entry point for HDR processing in the worker.

    Args:
        bracket_paths: List of paths to bracket images
        output_path: Where to save merged HDR image
        algorithm: "mertens" (default) or "debevec"
        **kwargs: Additional arguments passed to merge function

    Returns:
        Tuple of (output_path, metadata_dict)
        metadata includes: algorithm, bracket_count, output_size, processing_time

    Raises:
        HDRProcessingError: If processing fails at any stage
    """
    import time
    start_time = time.time()

    logger.info(f"🚀 Starting HDR processing: {len(bracket_paths)} brackets → {Path(output_path).name}")

    try:
        # Load images
        images = load_bracket_images(bracket_paths)

        # Merge based on algorithm
        if algorithm == "mertens":
            hdr_image = merge_hdr_mertens(images, **kwargs)
        elif algorithm == "debevec":
            hdr_image = merge_hdr_debevec(images, **kwargs)
        else:
            raise HDRProcessingError(f"Unknown algorithm: {algorithm}. Use 'mertens' or 'debevec'")

        # Save result
        result_path = save_hdr_result(hdr_image, output_path)

        # Calculate metadata
        processing_time = time.time() - start_time
        metadata = {
            "algorithm": algorithm,
            "bracket_count": len(images),
            "output_resolution": f"{hdr_image.shape[1]}x{hdr_image.shape[0]}",
            "output_size_mb": result_path.stat().st_size / 1024 / 1024,
            "processing_time_seconds": round(processing_time, 2)
        }

        logger.info(f"✅ HDR processing complete in {processing_time:.2f}s")

        return result_path, metadata

    except HDRProcessingError:
        raise
    except Exception as e:
        raise HDRProcessingError(f"Unexpected error in HDR processing: {e}")
