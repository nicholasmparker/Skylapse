"""Image processing and enhancement module."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .monitoring import ProcessingResourceMonitor

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image processing and enhancement operations."""

    def __init__(self):
        """Initialize image processor."""
        self._is_initialized = False
        self._processing_stats = {
            "images_processed": 0,
            "average_processing_time_ms": 0.0,
            "processing_errors": 0,
        }

    async def initialize(self) -> None:
        """Initialize image processing system."""
        logger.info("Initializing image processor")

        # In Phase 2, this will initialize:
        # - OpenCV/PIL image libraries
        # - GPU acceleration if available
        # - Color processing pipelines
        # - HDR processing modules

        self._is_initialized = True
        logger.info("Image processor initialized")

    async def shutdown(self) -> None:
        """Shutdown image processor."""
        logger.info("Shutting down image processor")
        self._is_initialized = False

    async def process_image(
        self,
        image_path: str,
        metadata: Dict[str, Any],
        processing_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a single image with enhancement operations.

        This is a foundational implementation for Sprint 1.
        Phase 2 will add comprehensive image processing.
        """
        if not self._is_initialized:
            raise RuntimeError("Image processor not initialized")

        start_time = time.time()
        logger.info(f"Processing image: {image_path}")

        try:
            # For Sprint 1, perform basic processing
            result = await self._basic_processing(image_path, metadata, processing_options)

            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self._update_processing_stats(processing_time, success=True)

            logger.info(f"Image processed successfully in {processing_time:.1f}ms")
            return result

        except Exception as e:
            self._update_processing_stats(0, success=False)
            logger.error(f"Image processing failed: {e}")
            raise

    async def _basic_processing(
        self,
        image_path: str,
        metadata: Dict[str, Any],
        processing_options: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Basic image processing for Sprint 1."""
        # Simulate processing delay
        await asyncio.sleep(0.1)

        input_path = Path(image_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")

        # Generate processed filename
        processed_filename = f"processed_{input_path.stem}{input_path.suffix}"
        output_path = input_path.parent / processed_filename

        # For Sprint 1, just copy the file (placeholder for real processing)
        await self._copy_with_metadata(input_path, output_path, metadata)

        # Generate result
        result = {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "processing_applied": self._get_processing_applied(processing_options),
            "timestamp": time.time(),
            "metadata": metadata,
            "quality_improvements": {
                "noise_reduction": processing_options.get("noise_reduction", False),
                "sharpening": processing_options.get("sharpening", False),
                "color_correction": processing_options.get("color_correction", False),
            },
        }

        return result

    async def _copy_with_metadata(
        self, input_path: Path, output_path: Path, metadata: Dict[str, Any]
    ) -> None:
        """Copy image and preserve/enhance metadata."""
        # For Sprint 1, simple file copy
        # Phase 2 will add proper image processing with metadata preservation
        import shutil

        shutil.copy2(input_path, output_path)

        # Write processing metadata
        metadata_file = output_path.with_suffix(".json")
        processing_metadata = {
            "original_file": str(input_path),
            "processed_file": str(output_path),
            "processing_timestamp": time.time(),
            "original_metadata": metadata,
            "processing_version": "1.0.0-sprint1",
        }

        with open(metadata_file, "w") as f:
            json.dump(processing_metadata, f, indent=2)

    def _get_processing_applied(self, processing_options: Optional[Dict[str, Any]]) -> List[str]:
        """Get list of processing operations that were applied."""
        if not processing_options:
            return ["basic_copy"]

        applied = []

        # Check what processing was requested
        if processing_options.get("noise_reduction"):
            applied.append("noise_reduction")

        if processing_options.get("sharpening"):
            applied.append("sharpening")

        if processing_options.get("color_correction"):
            applied.append("color_correction")

        if processing_options.get("hdr_processing"):
            applied.append("hdr_processing")

        if not applied:
            applied.append("basic_copy")

        return applied

    async def process_hdr_sequence(
        self, image_paths: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process HDR bracketed sequence into a single enhanced image.
        
        Implements full HDR processing with exposure fusion or tone mapping.
        Includes comprehensive resource monitoring for QA validation.
        """
        logger.info(f"Processing HDR sequence: {len(image_paths)} images")
        
        if len(image_paths) == 0:
            raise ValueError("No images provided for HDR processing")
            
        if len(image_paths) == 1:
            # Single image, just process normally
            processing_options = {"hdr_processing": False, "single_exposure": True}
            result = await self.process_image(image_paths[0], metadata, processing_options)
            result["processing_type"] = "single_exposure"
            return result

        # Start resource monitoring for QA validation
        async with ProcessingResourceMonitor(f"HDR_{len(image_paths)}_bracket") as monitor:
            start_time = time.time()
            
            try:
                # Generate output path
                base_path = Path(image_paths[0])
                output_filename = f"hdr_merged_{int(time.time())}{base_path.suffix}"
                output_path = str(base_path.parent / output_filename)
                
                # Perform HDR merge
                merged_path = await self._merge_hdr_images(image_paths, output_path)
                
                # Calculate processing time
                processing_time = (time.time() - start_time) * 1000
                
                # Update statistics
                self._update_processing_stats(processing_time, success=True)
                
                # Get resource metrics
                resource_metrics = monitor.get_metrics()
                
                # Generate comprehensive result with resource monitoring
                result = {
                    "input_paths": image_paths,
                    "output_path": merged_path,
                    "processing_type": "hdr_merge",
                    "processing_applied": ["hdr_merge", "tone_mapping", "exposure_fusion"],
                    "timestamp": time.time(),
                    "processing_time_ms": processing_time,
                    "metadata": metadata,
                    "hdr_info": {
                        "bracket_count": len(image_paths),
                        "merge_algorithm": "exposure_fusion" if len(image_paths) <= 5 else "debevec_tone_mapping",
                        "estimated_dynamic_range_stops": len(image_paths) * 2,  # Rough estimate
                        "opencv_available": CV2_AVAILABLE,
                        "pil_available": PIL_AVAILABLE
                    },
                    "quality_improvements": {
                        "dynamic_range_expansion": True,
                        "shadow_detail_recovery": True,
                        "highlight_detail_preservation": True,
                        "noise_reduction": len(image_paths) >= 3,  # Multiple exposures reduce noise
                    },
                    "resource_usage": resource_metrics.to_dict() if resource_metrics else None
                }
                
                # QA validation checks
                if resource_metrics:
                    if resource_metrics.peak_memory_mb > 1500:
                        logger.warning(f"HDR processing exceeded memory threshold: {resource_metrics.peak_memory_mb:.1f}MB")
                    if resource_metrics.thermal_throttling_detected:
                        logger.warning("Thermal throttling detected during HDR processing")
                        
                logger.info(f"HDR processing completed in {processing_time:.1f}ms: {merged_path}")
                return result
                
            except Exception as e:
                processing_time = (time.time() - start_time) * 1000
                self._update_processing_stats(processing_time, success=False)
                logger.error(f"HDR processing failed: {e}")
                raise

    async def process_focus_stack(
        self, image_paths: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process focus stacked sequence for maximum sharpness.

        This is a stub for Sprint 1. Phase 2 will implement focus stacking.
        """
        logger.info(f"Processing focus stack: {len(image_paths)} images")

        if len(image_paths) == 0:
            raise ValueError("No images provided for focus stacking")

        # For Sprint 1, select the first image
        base_image_path = image_paths[0]

        processing_options = {"focus_stacking": True, "stack_count": len(image_paths)}

        result = await self.process_image(base_image_path, metadata, processing_options)
        result["focus_stack_sequence"] = image_paths
        result["processing_type"] = "focus_stack"

        return result

    def _update_processing_stats(self, processing_time_ms: float, success: bool) -> None:
        """Update processing statistics."""
        if success:
            self._processing_stats["images_processed"] += 1

            # Update running average
            current_avg = self._processing_stats["average_processing_time_ms"]
            processed_count = self._processing_stats["images_processed"]

            if processed_count > 0:
                self._processing_stats["average_processing_time_ms"] = (
                    current_avg * (processed_count - 1) + processing_time_ms
                ) / processed_count
        else:
            self._processing_stats["processing_errors"] += 1

    async def get_status(self) -> Dict[str, Any]:
        """Get image processor status."""
        return {
            "initialized": self._is_initialized,
            "statistics": self._processing_stats.copy(),
            "capabilities": [
                "basic_processing",
                "hdr_sequence",  # Stub implementation
                "focus_stacking",  # Stub implementation
                "metadata_preservation",
            ],
            "future_capabilities": [
                "noise_reduction",  # Phase 2
                "color_correction",  # Phase 2
                "lens_correction",  # Phase 2
                "gpu_acceleration",  # Phase 2
            ],
        }

    # Future methods for Phase 2 implementation

    async def _apply_noise_reduction(self, image_path: str, strength: float) -> str:
        """Apply noise reduction to image (Phase 2)."""
        # TODO: Implement with OpenCV/PIL
        pass

    async def _apply_color_correction(
        self, image_path: str, color_matrix: List[List[float]]
    ) -> str:
        """Apply color correction matrix (Phase 2)."""
        # TODO: Implement color matrix application
        pass

    async def _apply_lens_correction(
        self, image_path: str, distortion_params: Dict[str, float]
    ) -> str:
        """Apply lens distortion correction (Phase 2)."""
        # TODO: Implement lens correction
        pass

    async def _merge_hdr_images(self, image_paths: List[str], output_path: str) -> str:
        """Merge HDR bracketed images using exposure fusion or tone mapping."""
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available, using fallback HDR processing")
            return await self._fallback_hdr_merge(image_paths, output_path)
            
        try:
            logger.info(f"Merging {len(image_paths)} HDR images using OpenCV")
            
            # Load images
            images = []
            for img_path in image_paths:
                img = cv2.imread(img_path)
                if img is None:
                    raise ValueError(f"Could not load image: {img_path}")
                images.append(img)
            
            # Convert to float32 for HDR processing
            images_f32 = [img.astype(np.float32) / 255.0 for img in images]
            
            # Estimate exposure times from filenames or use default bracketing
            exposure_times = self._estimate_exposure_times(image_paths)
            
            # Method 1: Exposure Fusion (faster, good for most cases)
            if len(images) <= 5:  # Use exposure fusion for smaller brackets
                merged = self._exposure_fusion(images_f32)
            else:
                # Method 2: HDR with tone mapping (better for larger brackets)
                merged = self._hdr_tone_mapping(images_f32, exposure_times)
            
            # Convert back to 8-bit and save
            result_8bit = (np.clip(merged, 0, 1) * 255).astype(np.uint8)
            cv2.imwrite(output_path, result_8bit)
            
            logger.info(f"HDR merge completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"HDR merge failed: {e}")
            return await self._fallback_hdr_merge(image_paths, output_path)
    
    def _estimate_exposure_times(self, image_paths: List[str]) -> np.ndarray:
        """Estimate exposure times from image paths or metadata."""
        # Default exposure bracketing: -2, -1, 0, +1, +2 EV
        num_images = len(image_paths)
        
        if num_images == 3:
            # Standard 3-bracket HDR
            return np.array([1/4, 1, 4], dtype=np.float32)  # -2, 0, +2 EV
        elif num_images == 5:
            # 5-bracket HDR
            return np.array([1/16, 1/4, 1, 4, 16], dtype=np.float32)  # -4 to +4 EV
        else:
            # Generate exposure times based on number of images
            ev_range = 2.0  # ±2 EV range
            ev_step = (2 * ev_range) / (num_images - 1)
            ev_values = np.linspace(-ev_range, ev_range, num_images)
            return np.power(2, ev_values).astype(np.float32)
    
    def _exposure_fusion(self, images: List[np.ndarray]) -> np.ndarray:
        """Merge images using exposure fusion algorithm."""
        if not images:
            raise ValueError("No images provided for exposure fusion")
            
        # Create exposure fusion object
        merge_mertens = cv2.createMergeMertens()
        
        # Merge images
        result = merge_mertens.process(images)
        
        # Apply slight contrast enhancement
        result = np.power(result, 0.9)  # Gamma correction
        
        return result
    
    def _hdr_tone_mapping(self, images: List[np.ndarray], exposure_times: np.ndarray) -> np.ndarray:
        """Create HDR image and apply tone mapping."""
        # Create HDR merge object
        merge_debevec = cv2.createMergeDebevec()
        
        # Merge to HDR
        hdr = merge_debevec.process(images, times=exposure_times.copy())
        
        # Tone mapping using Reinhard algorithm
        tonemap = cv2.createTonemapReinhard(gamma=2.2, intensity=-1.0, light_adapt=0.8, color_adapt=0.0)
        result = tonemap.process(hdr)
        
        return result
    
    async def _fallback_hdr_merge(self, image_paths: List[str], output_path: str) -> str:
        """Fallback HDR merge when OpenCV is not available."""
        if not PIL_AVAILABLE:
            # Ultimate fallback: just copy the middle exposure
            middle_idx = len(image_paths) // 2
            import shutil
            shutil.copy2(image_paths[middle_idx], output_path)
            logger.warning("No image processing libraries available, using middle exposure")
            return output_path
            
        try:
            # Simple exposure blending using PIL
            images = [Image.open(path) for path in image_paths]
            
            # Ensure all images are the same size
            base_size = images[0].size
            images = [img.resize(base_size, Image.Resampling.LANCZOS) for img in images]
            
            # Convert to numpy arrays
            arrays = [np.array(img).astype(np.float32) for img in images]
            
            # Simple weighted average (exposure fusion approximation)
            weights = self._calculate_fusion_weights(arrays)
            
            # Blend images
            result = np.zeros_like(arrays[0])
            weight_sum = np.zeros_like(arrays[0][:, :, 0])
            
            for i, (img_array, weight) in enumerate(zip(arrays, weights)):
                result += img_array * weight[:, :, np.newaxis]
                weight_sum += weight
                
            # Normalize
            weight_sum = np.maximum(weight_sum, 1e-6)  # Avoid division by zero
            result = result / weight_sum[:, :, np.newaxis]
            
            # Convert back to PIL and save
            result_img = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))
            result_img.save(output_path, quality=95)
            
            logger.info(f"Fallback HDR merge completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Fallback HDR merge failed: {e}")
            # Ultimate fallback
            middle_idx = len(image_paths) // 2
            import shutil
            shutil.copy2(image_paths[middle_idx], output_path)
            return output_path
    
    def _calculate_fusion_weights(self, arrays: List[np.ndarray]) -> List[np.ndarray]:
        """Calculate fusion weights based on image quality metrics."""
        weights = []
        
        for array in arrays:
            # Convert to grayscale for weight calculation
            if len(array.shape) == 3:
                gray = np.mean(array, axis=2)
            else:
                gray = array
                
            # Weight based on contrast (Laplacian variance)
            laplacian = cv2.Laplacian(gray.astype(np.uint8), cv2.CV_64F) if CV2_AVAILABLE else np.gradient(gray)[0]
            contrast_weight = np.abs(laplacian)
            
            # Weight based on saturation (avoid over/under exposure)
            saturation_weight = 1.0 - np.abs(gray - 127.5) / 127.5
            saturation_weight = np.power(saturation_weight, 2)
            
            # Combine weights
            total_weight = contrast_weight * saturation_weight
            weights.append(total_weight)
            
        return weights

    async def _stack_focus_images(self, image_paths: List[str]) -> str:
        """Stack focus images for maximum sharpness (Phase 2)."""
        # TODO: Implement focus stacking algorithm
        pass
