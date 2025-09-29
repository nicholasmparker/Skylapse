"""Arducam IMX519 16MP camera implementation using rpicam-still."""

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..camera_interface import CameraInterface
from ..camera_types import (
    CameraCapability,
    CameraInitializationError,
    CameraSpecs,
    CameraStatus,
    CaptureError,
    CaptureResult,
    CaptureSettings,
    EnvironmentalConditions,
)

logger = logging.getLogger(__name__)


class ArducamIMX519Camera(CameraInterface):
    """Arducam IMX519 16MP camera implementation using rpicam-still."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize IMX519 camera with configuration."""
        super().__init__(config)
        self._current_settings = CaptureSettings()

        # Extract configuration
        self._sensor_config = config.get("sensor", {})
        self._optical_config = config.get("optical", {})
        self._capture_config = config.get("capture", {})
        self._performance_config = config.get("performance", {})

        # Camera command configuration
        self._rpicam_cmd = "rpicam-still"
        self._capture_timeout_ms = self._capture_config.get(
            "capture_timeout_ms", 10000
        )  # Increased to 10s
        self._focus_timeout_ms = self._performance_config.get("focus_timeout_ms", 2000)

    async def initialize(self) -> None:
        """Initialize IMX519 camera hardware."""
        logger.info("Initializing Arducam IMX519 camera")

        try:
            # Test camera availability
            await self._test_camera_availability()

            # Set up camera specifications
            self._setup_camera_specs()

            # Initialize with default settings
            await self._apply_initial_settings()

            self._is_initialized = True
            logger.info("Arducam IMX519 camera initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize IMX519 camera: {e}")
            raise CameraInitializationError(f"IMX519 initialization failed: {e}")

    async def shutdown(self) -> None:
        """Shutdown IMX519 camera."""
        logger.info("Shutting down Arducam IMX519 camera")
        self._is_initialized = False
        # No specific shutdown needed for rpicam-still

    async def capture_single(self, settings: CaptureSettings) -> CaptureResult:
        """Capture a single image with IMX519."""
        if not self._is_initialized:
            raise CaptureError("Camera not initialized")

        start_time = time.time()

        try:
            # Generate output filename
            timestamp = int(time.time() * 1000)
            output_path = f"/tmp/skylapse_capture_{timestamp}.jpg"

            # Build rpicam-still command
            cmd = await self._build_capture_command(settings, output_path)

            # Execute capture
            logger.debug(f"Executing capture command: {' '.join(cmd)}")
            result = await self._execute_capture_command(cmd)

            capture_time_ms = (time.time() - start_time) * 1000

            # Verify image was created
            if not Path(output_path).exists():
                raise CaptureError("Image file was not created")

            # Create metadata
            metadata = {
                "camera_model": self._specs.model,
                "timestamp": time.time(),
                "settings_applied": settings,
                "capture_command": " ".join(cmd),
                "rpicam_output": result.get("stdout", ""),
                "hardware_capture": True,
            }

            # Store current settings
            self._current_settings = settings

            # Assess image quality (basic file size check)
            quality_score = await self._assess_capture_quality(output_path)

            return CaptureResult(
                file_paths=[output_path],
                metadata=metadata,
                actual_settings=settings,
                capture_time_ms=capture_time_ms,
                quality_score=quality_score,
            )

        except subprocess.CalledProcessError as e:
            capture_time_ms = (time.time() - start_time) * 1000
            logger.error(f"rpicam-still command failed: {e}")
            raise CaptureError(f"Capture command failed: {e}")
        except Exception as e:
            capture_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Capture failed: {e}")
            raise CaptureError(f"Capture operation failed: {e}")

    async def capture_sequence(self, settings_list: List[CaptureSettings]) -> CaptureResult:
        """Capture a sequence of images (HDR bracketing)."""
        if not self._is_initialized:
            raise CaptureError("Camera not initialized")

        if not settings_list:
            raise CaptureError("No capture settings provided for sequence")

        start_time = time.time()
        file_paths = []

        try:
            for i, settings in enumerate(settings_list):
                # Add small delay between captures
                if i > 0:
                    await asyncio.sleep(0.1)

                # Capture individual frame
                result = await self.capture_single(settings)
                file_paths.extend(result.file_paths)

            capture_time_ms = (time.time() - start_time) * 1000

            # Create sequence metadata
            metadata = {
                "camera_model": self._specs.model,
                "timestamp": time.time(),
                "sequence_count": len(settings_list),
                "sequence_type": self._detect_sequence_type(settings_list),
                "hardware_capture": True,
            }

            return CaptureResult(
                file_paths=file_paths,
                metadata=metadata,
                actual_settings=settings_list[0],  # Use first settings as primary
                capture_time_ms=capture_time_ms,
                quality_score=0.9,  # Assume good quality for sequences
            )

        except Exception as e:
            logger.error(f"Sequence capture failed: {e}")
            raise CaptureError(f"Sequence capture failed: {e}")

    def supports_capability(self, capability: CameraCapability) -> bool:
        """Check if IMX519 supports a capability."""
        return capability in self._specs.capabilities

    async def get_preview_frame(self) -> Optional[bytes]:
        """Get preview frame from IMX519."""
        if not self._is_initialized:
            return None

        try:
            # Use rpicam-still for high-quality preview with proper autofocus
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_path = temp_file.name

            cmd = [
                self._rpicam_cmd,
                "-t",
                "2000",  # 2 seconds - enough time for autofocus but not hanging
                "-n",  # No preview window
                "--width",
                "1920",  # 4:3 aspect ratio to match full captures
                "--height",
                "1440",  # Matches 4:3 aspect ratio (4656x3496)
                "-o",
                temp_path,
            ]

            # Apply current rotation setting to preview
            logger.info(f"Preview: checking rotation={self._current_settings.rotation_degrees}")
            if (
                self._current_settings.rotation_degrees
                and self._current_settings.rotation_degrees in [180]
            ):
                cmd.extend(["--rotation", str(self._current_settings.rotation_degrees)])
                logger.info(
                    f"Preview: Added --rotation "
                    f"{self._current_settings.rotation_degrees} to command"
                )
            else:
                logger.info(
                    f"Preview: No rotation applied "
                    f"(rotation={self._current_settings.rotation_degrees})"
                )

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await asyncio.wait_for(process.wait(), timeout=10.0)

            if process.returncode == 0 and Path(temp_path).exists():
                with open(temp_path, "rb") as f:
                    preview_data = f.read()
                Path(temp_path).unlink()  # Clean up
                return preview_data
            else:
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
                return None

        except Exception as e:
            logger.warning(f"Failed to get preview frame: {e}")
            return None

    async def autofocus(self, timeout_ms: int = 2000) -> bool:
        """Perform autofocus operation."""
        if not self._is_initialized:
            return False

        try:
            # rpicam-still handles autofocus automatically
            # We can test it by taking a quick capture
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_path = temp_file.name

            cmd = [
                self._rpicam_cmd,
                "-t",
                "1000",  # 1 second for focus
                "-n",  # No preview
                "--width",
                "640",  # Small test image
                "--height",
                "480",
                "-o",
                temp_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await asyncio.wait_for(process.wait(), timeout=timeout_ms / 1000)

            success = process.returncode == 0 and Path(temp_path).exists()

            # Clean up test file
            if Path(temp_path).exists():
                Path(temp_path).unlink()

            return success

        except Exception as e:
            logger.warning(f"Autofocus failed: {e}")
            return False

    async def get_current_settings(self) -> CaptureSettings:
        """Get current camera settings."""
        return self._current_settings

    async def set_capture_settings(self, settings: CaptureSettings) -> bool:
        """Set camera settings (applied during next capture)."""
        if not self._is_initialized:
            return False

        # Store settings for next capture
        self._current_settings = settings
        logger.info(f"Camera settings updated: rotation={settings.rotation_degrees}")
        return True

    def get_status(self) -> CameraStatus:
        """Get current camera status."""
        return CameraStatus(
            connected=self._is_initialized,
            model=self._specs.model if self._specs else "Arducam IMX519 16MP",
            battery_level=None,  # Camera doesn't report battery
            storage_free=None,  # Will be handled by storage manager
            temperature=None,  # Would need thermal monitoring
            last_capture_time=None,  # Would need to track captures
            captures_today=0,  # Would need to track captures
        )

    async def _test_camera_availability(self) -> None:
        """Test if camera is available and working."""
        try:
            # Test basic camera detection
            cmd = [self._rpicam_cmd, "--list-cameras"]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)

            if process.returncode != 0:
                raise CameraInitializationError(f"Camera not detected: {stderr.decode()}")

            # Check if IMX519 is mentioned in output
            output = stdout.decode().lower()
            if "imx519" not in output:
                logger.warning("IMX519 not explicitly detected, but camera is available")

        except asyncio.TimeoutError:
            raise CameraInitializationError("Camera detection timed out")
        except Exception as e:
            raise CameraInitializationError(f"Camera availability test failed: {e}")

    def _setup_camera_specs(self) -> None:
        """Set up camera specifications from config."""
        capabilities = []
        for cap_name in self._config.get("capabilities", []):
            try:
                capabilities.append(CameraCapability[cap_name])
            except KeyError:
                logger.warning(f"Unknown capability: {cap_name}")

        self._specs = CameraSpecs(
            model="Arducam IMX519 16MP",
            resolution_mp=self._sensor_config.get("resolution_mp", 16.0),
            max_resolution=tuple(self._sensor_config.get("max_resolution", [4656, 3496])),
            sensor_size_mm=tuple(self._sensor_config.get("sensor_size_mm", [7.4, 5.6])),
            focal_length_mm=self._optical_config.get("focal_length_mm", 4.28),
            base_iso=self._sensor_config.get("base_iso", 100),
            max_iso=self._sensor_config.get("max_iso", 800),
            iso_invariance_point=self._sensor_config.get("iso_invariance_point", 800),
            max_exposure_us=self._sensor_config.get("max_exposure_us", 10_000_000),
            focus_range_mm=tuple(self._optical_config.get("focus_range_mm", [100.0, float("inf")])),
            hyperfocal_distance_mm=self._optical_config.get("hyperfocal_distance_mm", 1830),
            capabilities=capabilities,
        )

    async def _apply_initial_settings(self) -> None:
        """Apply initial camera settings."""
        initial_settings = CaptureSettings(
            quality=self._capture_config.get("default_quality", 95),
            format=self._capture_config.get("default_format", "JPEG"),
            iso=self._sensor_config.get("base_iso", 100),
            rotation_degrees=self._capture_config.get(
                "default_rotation", 180
            ),  # Fix upside-down mount
        )

        await self.set_capture_settings(initial_settings)

    async def _build_capture_command(
        self, settings: CaptureSettings, output_path: str
    ) -> List[str]:
        """Build rpicam-still command from capture settings."""
        cmd = [self._rpicam_cmd]

        # Basic parameters
        cmd.extend(["-t", str(self._capture_timeout_ms)])  # Timeout
        cmd.extend(["-n"])  # No preview window
        cmd.extend(["-o", output_path])  # Output file

        # Resolution (use max resolution for quality)
        max_res = self._specs.max_resolution
        cmd.extend(["--width", str(max_res[0])])
        cmd.extend(["--height", str(max_res[1])])

        # Quality setting
        if settings.quality:
            cmd.extend(["-q", str(settings.quality)])

        # ISO setting
        if settings.iso:
            cmd.extend(["--gain", str(settings.iso / 100.0)])  # Convert ISO to gain

        # Exposure time
        if settings.exposure_time_us:
            cmd.extend(["--shutter", str(settings.exposure_time_us)])

        # Exposure compensation
        if settings.exposure_compensation != 0.0:
            cmd.extend(["--ev", str(settings.exposure_compensation)])

        # White balance
        if settings.white_balance_k:
            # Convert Kelvin to rpicam-still awb gains (approximate)
            if settings.white_balance_k < 4000:
                cmd.extend(["--awb", "tungsten"])
            elif settings.white_balance_k < 5500:
                cmd.extend(["--awb", "fluorescent"])
            elif settings.white_balance_k < 7000:
                cmd.extend(["--awb", "daylight"])
            else:
                cmd.extend(["--awb", "cloudy"])
        elif settings.white_balance_mode != "auto":
            cmd.extend(["--awb", settings.white_balance_mode])

        # Focus settings
        if not settings.autofocus_enabled and settings.focus_distance_mm:
            # Convert focus distance to lens position (0.0 = infinity, 1.0 = close)
            if settings.focus_distance_mm == float("inf"):
                lens_pos = 0.0
            else:
                # Approximate conversion (would need calibration for precision)
                lens_pos = min(1.0, 1000.0 / settings.focus_distance_mm)
            cmd.extend(["--lens-position", str(lens_pos)])

        # Image rotation
        if settings.rotation_degrees and settings.rotation_degrees in [180]:
            cmd.extend(["--rotation", str(settings.rotation_degrees)])

        return cmd

    async def _execute_capture_command(self, cmd: List[str]) -> Dict[str, str]:
        """Execute rpicam-still command."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            timeout_seconds = self._capture_timeout_ms / 1000 + 5  # Add 5s buffer for processing
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)

            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "returncode": process.returncode,
            }

        except asyncio.TimeoutError:
            # Kill the process if it's still running
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass  # Process cleanup failed, but we can continue
            raise CaptureError(f"Capture command timed out after {timeout_seconds}s")

    async def _assess_capture_quality(self, image_path: str) -> float:
        """Assess basic image quality based on file size and metadata."""
        try:
            path = Path(image_path)
            if not path.exists():
                return 0.0

            # Basic quality assessment based on file size
            file_size_mb = path.stat().st_size / (1024 * 1024)

            # Expected size for 16MP JPEG at quality 95: ~8-12MB
            if file_size_mb > 6:
                return 0.9  # Good quality
            elif file_size_mb > 3:
                return 0.7  # Acceptable quality
            elif file_size_mb > 1:
                return 0.5  # Low quality
            else:
                return 0.2  # Very low quality

        except Exception as e:
            logger.warning(f"Quality assessment failed: {e}")
            return 0.5  # Default quality score

    def _detect_sequence_type(self, settings_list: List[CaptureSettings]) -> str:
        """Detect the type of capture sequence."""
        if len(settings_list) <= 1:
            return "single"

        # Check for HDR bracketing (different exposures)
        exposures = [s.exposure_time_us for s in settings_list if s.exposure_time_us is not None]
        if len(set(exposures)) > 1:
            return "hdr_bracket"

        # Check for focus stacking (different focus distances)
        focus_distances = [
            s.focus_distance_mm for s in settings_list if s.focus_distance_mm is not None
        ]
        if len(set(focus_distances)) > 1:
            return "focus_stack"

        return "sequence"

    async def optimize_settings_for_conditions(
        self, base_settings: CaptureSettings, conditions: EnvironmentalConditions
    ) -> CaptureSettings:
        """Optimize capture settings based on environmental conditions."""
        optimized = CaptureSettings(
            exposure_time_us=base_settings.exposure_time_us,
            iso=base_settings.iso,
            exposure_compensation=base_settings.exposure_compensation,
            focus_distance_mm=base_settings.focus_distance_mm,
            autofocus_enabled=base_settings.autofocus_enabled,
            white_balance_k=base_settings.white_balance_k,
            white_balance_mode=base_settings.white_balance_mode,
            quality=base_settings.quality,
            format=base_settings.format,
            hdr_bracket_stops=base_settings.hdr_bracket_stops.copy(),
            processing_hints=base_settings.processing_hints.copy(),
        )

        # Apply mountain-specific optimizations from config
        mountain_presets = self._config.get("mountain_presets", {})

        # Golden hour optimization
        if conditions.is_golden_hour and "golden_hour" in mountain_presets:
            preset = mountain_presets["golden_hour"]
            optimized.white_balance_k = preset.get("white_balance_k", 3200)
            optimized.exposure_compensation += preset.get("exposure_compensation", 0.3)
            if preset.get("hdr_enabled", False):
                optimized.hdr_bracket_stops = [-1, 0, 1]

        # Blue hour optimization
        elif conditions.is_blue_hour and "blue_hour" in mountain_presets:
            preset = mountain_presets["blue_hour"]
            optimized.white_balance_k = preset.get("white_balance_k", 8500)
            optimized.iso = min(preset.get("iso_max", 800), self._specs.max_iso)

        # Low light conditions
        if conditions.ambient_light_lux and conditions.ambient_light_lux < 10:
            optimized.iso = min(400, self._specs.max_iso)
            optimized.exposure_time_us = min(2_000_000, self._specs.max_exposure_us)  # 2s max

        # High dynamic range scenes
        if conditions.scene_brightness and conditions.scene_brightness > 0.8:
            optimized.hdr_bracket_stops = [-2, -1, 0, 1, 2]

        return optimized

    def get_processing_hints(self, settings: CaptureSettings) -> Dict[str, Any]:
        """Generate processing hints based on capture settings."""
        hints = {
            "hardware_capture": True,
            "camera_model": "imx519",
            "use_noise_reduction": (settings.iso or 100) > 400,
            "apply_hdr_processing": len(settings.hdr_bracket_stops) > 1,
            "lens_correction_needed": True,  # IMX519 benefits from lens correction
            "suggested_sharpening": 0.2,
        }

        # Add mountain-specific processing hints
        if settings.processing_hints:
            hints.update(settings.processing_hints)

        return hints
