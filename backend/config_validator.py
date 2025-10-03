"""
Configuration validation for Skylapse system.

Validates config.json on startup to catch errors early.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class ConfigValidator:
    """Validates Skylapse configuration."""

    VALID_SCHEDULE_TYPES = {"solar_relative", "time_of_day"}
    VALID_SOLAR_ANCHORS = {"sunrise", "sunset", "civil_dawn", "civil_dusk", "noon"}
    VALID_VIDEO_CODECS = {"libx264", "libx265", "h264_nvenc"}

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> Dict[str, Any]:
        """
        Validate configuration file.

        Returns:
            Parsed configuration dict if valid

        Raises:
            ConfigValidationError: If validation fails
        """
        self.errors = []
        self.warnings = []

        # Load config
        try:
            with open(self.config_path) as f:
                config = json.load(f)
        except FileNotFoundError:
            raise ConfigValidationError(f"Config file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in config file: {e}")

        # Validate sections
        self._validate_location(config.get("location", {}))
        self._validate_schedules(config.get("schedules", {}))
        self._validate_pi(config.get("pi", {}))
        self._validate_storage(config.get("storage", {}))
        self._validate_processing(config.get("processing", {}))

        # Check for errors
        if self.errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in self.errors
            )
            raise ConfigValidationError(error_msg)

        # Log warnings
        if self.warnings:
            logger.warning("Configuration warnings:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        logger.info(f"✓ Configuration validated successfully ({self.config_path})")
        return config

    def _validate_location(self, location: Dict[str, Any]):
        """Validate location section."""
        if not location:
            self.errors.append("Missing 'location' section")
            return

        # Required fields
        required = ["latitude", "longitude", "timezone"]
        for field in required:
            if field not in location:
                self.errors.append(f"Missing location.{field}")

        # Validate latitude
        if "latitude" in location:
            lat = location["latitude"]
            if not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
                self.errors.append(f"Invalid latitude: {lat} (must be -90 to 90)")

        # Validate longitude
        if "longitude" in location:
            lon = location["longitude"]
            if not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
                self.errors.append(f"Invalid longitude: {lon} (must be -180 to 180)")

        # Validate timezone
        if "timezone" in location:
            tz = location["timezone"]
            if not isinstance(tz, str):
                self.errors.append(f"Invalid timezone: {tz} (must be string)")

    def _validate_schedules(self, schedules: Dict[str, Any]):
        """Validate schedules section."""
        if not schedules:
            self.warnings.append("No schedules defined")
            return

        enabled_count = 0
        for name, schedule in schedules.items():
            if not isinstance(schedule, dict):
                self.errors.append(f"Schedule '{name}' must be a dictionary")
                continue

            if schedule.get("enabled"):
                enabled_count += 1

            # Validate schedule type
            sched_type = schedule.get("type")
            if not sched_type:
                self.errors.append(f"Schedule '{name}' missing 'type'")
            elif sched_type not in self.VALID_SCHEDULE_TYPES:
                self.errors.append(
                    f"Schedule '{name}' has invalid type: {sched_type} "
                    f"(must be one of {self.VALID_SCHEDULE_TYPES})"
                )

            # Type-specific validation
            if sched_type == "solar_relative":
                self._validate_solar_schedule(name, schedule)
            elif sched_type == "time_of_day":
                self._validate_time_schedule(name, schedule)

            # Validate interval
            interval = schedule.get("interval_seconds")
            if interval is not None:
                if not isinstance(interval, (int, float)) or interval <= 0:
                    self.errors.append(
                        f"Schedule '{name}' interval_seconds must be positive number"
                    )
                elif interval < 0.5:
                    self.warnings.append(f"Schedule '{name}' has very short interval ({interval}s)")

            # Validate stacking
            if schedule.get("stack_images"):
                stack_count = schedule.get("stack_count", 0)
                if not isinstance(stack_count, int) or stack_count < 2:
                    self.errors.append(
                        f"Schedule '{name}' stack_count must be >= 2 when stack_images=true"
                    )

        if enabled_count == 0:
            self.warnings.append("No schedules are enabled")

    def _validate_solar_schedule(self, name: str, schedule: Dict[str, Any]):
        """Validate solar_relative schedule."""
        anchor = schedule.get("anchor")
        if not anchor:
            self.errors.append(f"Solar schedule '{name}' missing 'anchor'")
        elif anchor not in self.VALID_SOLAR_ANCHORS:
            self.errors.append(
                f"Solar schedule '{name}' has invalid anchor: {anchor} "
                f"(must be one of {self.VALID_SOLAR_ANCHORS})"
            )

        # Validate offset
        offset = schedule.get("offset_minutes")
        if offset is not None and not isinstance(offset, (int, float)):
            self.errors.append(f"Solar schedule '{name}' offset_minutes must be a number")

        # Validate duration
        duration = schedule.get("duration_minutes")
        if not duration:
            self.errors.append(f"Solar schedule '{name}' missing 'duration_minutes'")
        elif not isinstance(duration, (int, float)) or duration <= 0:
            self.errors.append(f"Solar schedule '{name}' duration_minutes must be positive")

    def _validate_time_schedule(self, name: str, schedule: Dict[str, Any]):
        """Validate time_of_day schedule."""
        start_time = schedule.get("start_time")
        end_time = schedule.get("end_time")

        if not start_time:
            self.errors.append(f"Time schedule '{name}' missing 'start_time'")
        elif not self._is_valid_time_format(start_time):
            self.errors.append(f"Time schedule '{name}' start_time invalid format (use HH:MM)")

        if not end_time:
            self.errors.append(f"Time schedule '{name}' missing 'end_time'")
        elif not self._is_valid_time_format(end_time):
            self.errors.append(f"Time schedule '{name}' end_time invalid format (use HH:MM)")

    def _is_valid_time_format(self, time_str: str) -> bool:
        """Check if time string is valid HH:MM format."""
        if not isinstance(time_str, str):
            return False
        pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
        return bool(re.match(pattern, time_str))

    def _validate_pi(self, pi_config: Dict[str, Any]):
        """Validate Pi section."""
        if not pi_config:
            self.warnings.append("Missing 'pi' section")
            return

        # Validate host
        if "host" not in pi_config:
            self.errors.append("Missing pi.host")
        elif not isinstance(pi_config["host"], str):
            self.errors.append("pi.host must be a string")

        # Validate port
        if "port" in pi_config:
            port = pi_config["port"]
            if not isinstance(port, int) or not 1 <= port <= 65535:
                self.errors.append(f"pi.port must be between 1-65535, got {port}")

        # Validate timeout
        if "timeout_seconds" in pi_config:
            timeout = pi_config["timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                self.errors.append("pi.timeout_seconds must be positive number")

    def _validate_storage(self, storage: Dict[str, Any]):
        """Validate storage section."""
        if not storage:
            self.warnings.append("Missing 'storage' section")
            return

        # Validate directories
        for dir_key in ["images_dir", "videos_dir"]:
            if dir_key in storage:
                dir_path = storage[dir_key]
                if not isinstance(dir_path, str):
                    self.errors.append(f"storage.{dir_key} must be a string")

        # Validate retention
        if "max_days_to_keep" in storage:
            days = storage["max_days_to_keep"]
            if not isinstance(days, (int, float)) or days < 1:
                self.errors.append("storage.max_days_to_keep must be >= 1")
            elif days < 3:
                self.warnings.append(f"storage.max_days_to_keep is very short ({days} days)")

    def _validate_processing(self, processing: Dict[str, Any]):
        """Validate processing section."""
        if not processing:
            self.warnings.append("Missing 'processing' section")
            return

        # Validate FPS
        if "video_fps" in processing:
            fps = processing["video_fps"]
            if not isinstance(fps, (int, float)) or fps <= 0 or fps > 120:
                self.errors.append(f"processing.video_fps must be 1-120, got {fps}")

        # Validate codec
        if "video_codec" in processing:
            codec = processing["video_codec"]
            if codec not in self.VALID_VIDEO_CODECS:
                self.warnings.append(
                    f"Unusual video codec: {codec} " f"(expected one of {self.VALID_VIDEO_CODECS})"
                )

        # Validate quality (CRF value)
        if "video_quality" in processing:
            quality = processing["video_quality"]
            try:
                quality_int = int(quality)
                if not 0 <= quality_int <= 51:
                    self.errors.append(f"processing.video_quality must be 0-51, got {quality}")
            except (ValueError, TypeError):
                self.errors.append(f"processing.video_quality must be numeric, got {quality}")


def validate_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Validate configuration file on startup.

    Args:
        config_path: Path to config.json

    Returns:
        Validated configuration dictionary

    Raises:
        ConfigValidationError: If validation fails
    """
    validator = ConfigValidator(config_path)
    return validator.validate()
