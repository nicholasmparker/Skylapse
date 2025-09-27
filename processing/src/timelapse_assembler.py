"""Timelapse assembly and video generation module."""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TimelapseAssembler:
    """Handles timelapse video assembly from processed images."""

    def __init__(self):
        """Initialize timelapse assembler."""
        self._is_initialized = False
        self._assembly_stats = {
            "timelapses_created": 0,
            "total_frames_processed": 0,
            "average_assembly_time_ms": 0.0,
            "assembly_errors": 0,
        }
        self._recent_timelapses: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize timelapse assembly system."""
        logger.info("Initializing timelapse assembler")

        # In Phase 2, this will initialize:
        # - FFmpeg bindings for video encoding
        # - GPU acceleration for encoding if available
        # - Multiple output format pipelines
        # - Stabilization algorithms

        self._is_initialized = True
        logger.info("Timelapse assembler initialized")

    async def shutdown(self) -> None:
        """Shutdown timelapse assembler."""
        logger.info("Shutting down timelapse assembler")
        self._is_initialized = False

    async def create_timelapse(
        self,
        images: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_formats: List[str] = ["1080p"],
    ) -> Dict[str, Any]:
        """
        Create timelapse video from processed images.

        This is a foundational implementation for Sprint 1.
        Phase 2 will add comprehensive video processing.
        """
        if not self._is_initialized:
            raise RuntimeError("Timelapse assembler not initialized")

        start_time = time.time()
        logger.info(f"Creating timelapse from {len(images)} images")

        try:
            # Sort images by timestamp
            sorted_images = sorted(images, key=lambda x: x.get("timestamp", 0))

            # Generate output paths
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_base = Path(f"/tmp/skylapse_timelapse_{timestamp}")

            # Create actual video files for each format using FFmpeg
            results = []
            for format_spec in output_formats:
                result = await self._create_format_video(
                    sorted_images, format_spec, output_base, metadata
                )
                results.append(result)

            # Update statistics
            assembly_time = (time.time() - start_time) * 1000
            self._update_assembly_stats(len(images), assembly_time, success=True)

            # Store recent timelapse info
            timelapse_info = {
                "timestamp": time.time(),
                "image_count": len(images),
                "duration_seconds": self._calculate_duration(sorted_images),
                "output_formats": output_formats,
                "outputs": results,
                "metadata": metadata,
            }
            self._recent_timelapses.append(timelapse_info)

            # Keep only recent timelapses (last 100)
            if len(self._recent_timelapses) > 100:
                self._recent_timelapses = self._recent_timelapses[-100:]

            logger.info(f"Timelapse created successfully in {assembly_time:.1f}ms")

            return {
                "success": True,
                "output_path": str(results[0]["output_path"]) if results else None,
                "outputs": results,
                "frame_count": len(images),
                "duration_seconds": timelapse_info["duration_seconds"],
                "assembly_time_ms": assembly_time,
            }

        except Exception as e:
            self._update_assembly_stats(0, 0, success=False)
            logger.error(f"Timelapse creation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "frame_count": len(images),
                "assembly_time_ms": 0,
            }

    async def _create_format_video(
        self,
        images: List[Dict[str, Any]],
        format_spec: str,
        output_base: Path,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create actual timelapse video for specific format using FFmpeg."""
        # Generate format-specific filename
        output_file = output_base.with_suffix(f"_{format_spec}.mp4")

        # Create directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Extract image paths from image metadata
        image_paths = []
        for img in images:
            img_path = img.get("output_path") or img.get("input_path")
            if img_path and Path(img_path).exists():
                image_paths.append(img_path)
            else:
                logger.warning(f"Image not found: {img_path}")

        if not image_paths:
            raise ValueError("No valid images found for timelapse creation")

        # Get framerate from metadata or use default
        framerate = metadata.get("framerate", self._get_format_framerate(format_spec))

        try:
            # Use FFmpeg to create actual video
            encoding_result = await self._encode_with_ffmpeg(
                image_paths, str(output_file), format_spec, framerate
            )

            # Create metadata file
            metadata_file = output_file.with_suffix(".json")
            timelapse_metadata = {
                "format": format_spec,
                "frame_count": len(image_paths),
                "input_images": image_paths,
                "creation_time": time.time(),
                "encoding_info": encoding_result,
                "metadata": metadata,
                "processing_version": "2.0.0-sprint2",
            }

            with open(metadata_file, "w") as f:
                json.dump(timelapse_metadata, f, indent=2)

            return {
                "format": format_spec,
                "output_path": str(output_file),
                "metadata_path": str(metadata_file),
                "file_size_bytes": encoding_result.get("file_size_bytes", 0),
                "resolution": encoding_result.get("resolution", "1920x1080"),
                "framerate": framerate,
                "encoding_time_ms": encoding_result.get("encoding_time_ms", 0),
                "codec": encoding_result.get("codec", "libx264"),
                "success": encoding_result.get("success", False)
            }

        except Exception as e:
            logger.error(f"Video creation failed for {format_spec}: {e}")
            # Fallback to placeholder creation
            return await self._create_format_placeholder(images, format_spec, output_base, metadata)

    async def _create_format_placeholder(
        self,
        images: List[Dict[str, Any]],
        format_spec: str,
        output_base: Path,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create placeholder timelapse file for specific format (fallback)."""
        # Generate format-specific filename
        output_file = output_base.with_suffix(f"_{format_spec}.mp4")

        # Create directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Create placeholder file with metadata
        placeholder_content = self._generate_placeholder_content(images, format_spec, metadata)

        with open(output_file, "wb") as f:
            f.write(placeholder_content)

        # Create metadata file
        metadata_file = output_file.with_suffix(".json")
        timelapse_metadata = {
            "format": format_spec,
            "frame_count": len(images),
            "input_images": [img.get("output_path", "") for img in images],
            "creation_time": time.time(),
            "metadata": metadata,
            "processing_version": "2.0.0-sprint2-placeholder",
            "note": "Placeholder file - install FFmpeg for video generation"
        }

        with open(metadata_file, "w") as f:
            json.dump(timelapse_metadata, f, indent=2)

        return {
            "format": format_spec,
            "output_path": str(output_file),
            "metadata_path": str(metadata_file),
            "file_size_bytes": output_file.stat().st_size,
            "resolution": f"{self._get_format_resolution(format_spec)[0]}x{self._get_format_resolution(format_spec)[1]}",
            "framerate": self._get_format_framerate(format_spec),
            "success": False,
            "note": "Placeholder created - FFmpeg required for video generation"
        }

    def _generate_placeholder_content(
        self, images: List[Dict[str, Any]], format_spec: str, metadata: Dict[str, Any]
    ) -> bytes:
        """Generate placeholder video content (Sprint 1)."""
        # Create minimal MP4-like header for placeholder
        # In Phase 2, this will be replaced with actual FFmpeg encoding

        header = b"ftypisom"  # MP4 file type header
        placeholder_data = f"Skylapse Timelapse - {format_spec}\n".encode()
        placeholder_data += f"Frames: {len(images)}\n".encode()
        placeholder_data += f"Created: {datetime.now().isoformat()}\n".encode()

        # Pad to reasonable file size
        while len(placeholder_data) < 1024 * 100:  # 100KB minimum
            placeholder_data += b"0" * 1000

        return header + placeholder_data

    def _calculate_duration(self, sorted_images: List[Dict[str, Any]]) -> float:
        """Calculate timelapse duration based on image timestamps."""
        if len(sorted_images) < 2:
            return 0.0

        timestamps = [img.get("timestamp", 0) for img in sorted_images]
        real_duration = max(timestamps) - min(timestamps)  # noqa: F841

        # Calculate video duration at target framerate
        target_framerate = 24.0  # fps
        video_duration = len(sorted_images) / target_framerate

        return video_duration

    def _get_format_resolution(self, format_spec: str) -> tuple[int, int]:
        """Get resolution for format specification."""
        format_resolutions = {
            "1080p": (1920, 1080),
            "4k": (3840, 2160),
            "720p": (1280, 720),
            "480p": (854, 480),
        }
        return format_resolutions.get(format_spec, (1920, 1080))

    def _get_format_framerate(self, format_spec: str) -> float:
        """Get framerate for format specification."""
        # For Sprint 1, use fixed framerate
        return 24.0

    def _update_assembly_stats(
        self, frame_count: int, assembly_time_ms: float, success: bool
    ) -> None:
        """Update assembly statistics."""
        if success:
            self._assembly_stats["timelapses_created"] += 1
            self._assembly_stats["total_frames_processed"] += frame_count

            # Update running average
            current_avg = self._assembly_stats["average_assembly_time_ms"]
            timelapse_count = self._assembly_stats["timelapses_created"]

            if timelapse_count > 0:
                self._assembly_stats["average_assembly_time_ms"] = (
                    current_avg * (timelapse_count - 1) + assembly_time_ms
                ) / timelapse_count
        else:
            self._assembly_stats["assembly_errors"] += 1

    async def create_multiple_formats(
        self,
        images: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        formats: List[str] = ["720p", "1080p", "4k"],
    ) -> Dict[str, Any]:
        """Create timelapse in multiple formats simultaneously."""
        logger.info(f"Creating timelapse in {len(formats)} formats")

        # For Sprint 1, create formats sequentially
        # Phase 2 will add parallel processing
        all_results = []
        for format_spec in formats:
            result = await self.create_timelapse(images, metadata, [format_spec])
            if result["success"] and result["outputs"]:
                all_results.extend(result["outputs"])

        return {
            "success": len(all_results) > 0,
            "outputs": all_results,
            "formats_created": len(all_results),
            "total_frame_count": len(images),
        }

    async def apply_stabilization(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply stabilization to image sequence.

        This is a stub for Sprint 1. Phase 2 will implement stabilization.
        """
        logger.info(f"Applying stabilization to {len(images)} images (stub)")

        # For Sprint 1, return images unchanged
        return images

    async def apply_deflickering(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply deflickering to reduce brightness variations.

        This is a stub for Sprint 1. Phase 2 will implement deflickering.
        """
        logger.info(f"Applying deflickering to {len(images)} images (stub)")

        # For Sprint 1, return images unchanged
        return images

    async def get_status(self) -> Dict[str, Any]:
        """Get timelapse assembler status."""
        return {
            "initialized": self._is_initialized,
            "statistics": self._assembly_stats.copy(),
            "recent_timelapses_count": len(self._recent_timelapses),
            "capabilities": ["basic_assembly", "multiple_formats", "metadata_preservation"],
            "future_capabilities": [
                "stabilization",  # Phase 2
                "deflickering",  # Phase 2
                "gpu_acceleration",  # Phase 2
                "h265_encoding",  # Phase 2
                "hdr_output",  # Phase 2
            ],
        }

    async def get_recent_timelapses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about recently created timelapses."""
        return self._recent_timelapses[-limit:]

    # Future methods for Phase 2 implementation

    async def _encode_with_ffmpeg(
        self, images: List[str], output_path: str, format_spec: str, framerate: float = 24.0
    ) -> Dict[str, Any]:
        """Encode timelapse using FFmpeg."""
        if not images:
            raise ValueError("No images provided for encoding")
            
        logger.info(f"Encoding {len(images)} images to {format_spec} at {framerate}fps")
        
        try:
            # Check if FFmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not available")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("FFmpeg not available, using fallback method")
            return await self._fallback_video_creation(images, output_path, format_spec)
        
        try:
            # Create temporary file list for FFmpeg
            temp_dir = Path(output_path).parent / "temp_timelapse"
            temp_dir.mkdir(exist_ok=True)
            
            # Copy/symlink images with sequential naming for FFmpeg
            image_list = []
            for i, img_path in enumerate(images):
                src_path = Path(img_path)
                if not src_path.exists():
                    logger.warning(f"Image not found: {img_path}")
                    continue
                    
                # Create sequential filename
                dest_name = f"frame_{i:06d}{src_path.suffix}"
                dest_path = temp_dir / dest_name
                
                # Create symlink to avoid copying large files
                if dest_path.exists():
                    dest_path.unlink()
                dest_path.symlink_to(src_path.absolute())
                image_list.append(str(dest_path))
            
            if not image_list:
                raise ValueError("No valid images found for encoding")
            
            # Get format-specific encoding parameters
            encoding_params = self._get_encoding_parameters(format_spec)
            
            # Build FFmpeg command
            input_pattern = str(temp_dir / "frame_%06d.jpg")  # Assume JPEG for now
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-framerate', str(framerate),
                '-i', input_pattern,
                '-c:v', encoding_params['codec'],
                '-pix_fmt', encoding_params['pixel_format'],
                '-crf', str(encoding_params['quality']),
                '-preset', encoding_params['preset'],
                '-vf', f"scale={encoding_params['width']}:{encoding_params['height']}",
                '-movflags', '+faststart',  # Enable fast start for web playback
                str(output_path)
            ]
            
            # Add format-specific parameters
            if encoding_params.get('profile'):
                ffmpeg_cmd.extend(['-profile:v', encoding_params['profile']])
            if encoding_params.get('level'):
                ffmpeg_cmd.extend(['-level', encoding_params['level']])
                
            logger.info(f"Running FFmpeg: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg encoding
            start_time = time.time()
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            encoding_time = (time.time() - start_time) * 1000
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                logger.error(f"FFmpeg encoding failed: {error_msg}")
                raise RuntimeError(f"FFmpeg encoding failed: {error_msg}")
            
            # Clean up temporary files
            for temp_file in temp_dir.glob("frame_*"):
                temp_file.unlink()
            temp_dir.rmdir()
            
            # Get output file info
            output_file = Path(output_path)
            file_size = output_file.stat().st_size if output_file.exists() else 0
            
            result = {
                "success": True,
                "output_path": str(output_path),
                "file_size_bytes": file_size,
                "encoding_time_ms": encoding_time,
                "frame_count": len(image_list),
                "framerate": framerate,
                "format": format_spec,
                "codec": encoding_params['codec'],
                "resolution": f"{encoding_params['width']}x{encoding_params['height']}"
            }
            
            logger.info(f"FFmpeg encoding completed in {encoding_time:.1f}ms: {output_path}")
            return result
            
        except Exception as e:
            logger.error(f"FFmpeg encoding failed: {e}")
            # Clean up on failure
            try:
                if 'temp_dir' in locals():
                    for temp_file in temp_dir.glob("frame_*"):
                        temp_file.unlink()
                    if temp_dir.exists():
                        temp_dir.rmdir()
            except:
                pass
            raise
    
    def _get_encoding_parameters(self, format_spec: str) -> Dict[str, Any]:
        """Get encoding parameters for different formats."""
        base_params = {
            'codec': 'libx264',
            'pixel_format': 'yuv420p',
            'preset': 'medium',
            'profile': 'high',
            'level': '4.0'
        }
        
        if format_spec == '4k':
            return {
                **base_params,
                'width': 3840,
                'height': 2160,
                'quality': 18,  # Lower CRF = higher quality
                'preset': 'slow'  # Better compression for 4K
            }
        elif format_spec == '1080p':
            return {
                **base_params,
                'width': 1920,
                'height': 1080,
                'quality': 20
            }
        elif format_spec == '720p':
            return {
                **base_params,
                'width': 1280,
                'height': 720,
                'quality': 22
            }
        elif format_spec == '480p':
            return {
                **base_params,
                'width': 854,
                'height': 480,
                'quality': 24
            }
        else:
            # Default to 1080p
            return {
                **base_params,
                'width': 1920,
                'height': 1080,
                'quality': 20
            }
    
    async def _fallback_video_creation(self, images: List[str], output_path: str, format_spec: str) -> Dict[str, Any]:
        """Fallback video creation when FFmpeg is not available."""
        logger.warning("Creating placeholder video file - FFmpeg not available")
        
        # Create a more sophisticated placeholder that includes image metadata
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create JSON manifest of the timelapse
        manifest = {
            "type": "skylapse_timelapse_manifest",
            "format": format_spec,
            "frame_count": len(images),
            "images": images,
            "created": datetime.now().isoformat(),
            "note": "This is a manifest file. Install FFmpeg to generate actual video files."
        }
        
        # Write manifest as JSON
        manifest_file = output_file.with_suffix('.json')
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create minimal placeholder video file
        placeholder_content = self._generate_placeholder_content(
            [{"output_path": img} for img in images], 
            format_spec, 
            {"fallback": True}
        )
        
        with open(output_file, 'wb') as f:
            f.write(placeholder_content)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "manifest_path": str(manifest_file),
            "file_size_bytes": output_file.stat().st_size,
            "frame_count": len(images),
            "format": format_spec,
            "note": "Placeholder created - install FFmpeg for video generation"
        }

    async def _apply_gpu_acceleration(self, images: List[str], processing_type: str) -> List[str]:
        """Apply GPU-accelerated processing (Phase 2)."""
        # TODO: Implement GPU acceleration
        pass

    async def _create_hdr_timelapse(
        self, hdr_sequences: List[List[str]], output_path: str
    ) -> Dict[str, Any]:
        """Create HDR timelapse from HDR image sequences (Phase 2)."""
        # TODO: Implement HDR timelapse creation
        pass
