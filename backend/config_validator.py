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
    VALID_WB_CURVES = {"balanced", "conservative", "warm"}
    VALID_EV_CURVES = {"adaptive"}

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
        profiles = config.get("profiles", {})
        schedules = config.get("schedules", {})
        self._validate_profiles(profiles)
        self._validate_schedules(schedules)
        self._validate_schedule_profiles(schedules, profiles)
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

            # Validate smoothing settings
            if "smoothing" in schedule:
                self._validate_smoothing(name, schedule["smoothing"])

            # Validate video debug settings
            if "video_debug" in schedule:
                self._validate_video_debug(name, schedule["video_debug"])

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

    def _validate_smoothing(self, schedule_name: str, smoothing: Dict[str, Any]):
        """Validate smoothing configuration."""
        if not isinstance(smoothing, dict):
            self.errors.append(f"Schedule '{schedule_name}' smoothing must be a dictionary")
            return

        # Validate enabled
        if "enabled" in smoothing and not isinstance(smoothing["enabled"], bool):
            self.errors.append(f"Schedule '{schedule_name}' smoothing.enabled must be boolean")

        # If smoothing is enabled, validate parameters
        if smoothing.get("enabled", False):
            # Validate window_frames
            window_frames = smoothing.get("window_frames")
            if window_frames is not None:
                if not isinstance(window_frames, int) or window_frames < 1:
                    self.errors.append(
                        f"Schedule '{schedule_name}' smoothing.window_frames must be positive integer"
                    )

            # Validate max_change_per_frame
            max_change = smoothing.get("max_change_per_frame")
            if max_change is not None:
                if not isinstance(max_change, (int, float)) or not 0 < max_change <= 1:
                    self.errors.append(
                        f"Schedule '{schedule_name}' smoothing.max_change_per_frame must be between 0 and 1"
                    )

            # Validate weights
            iso_weight = smoothing.get("iso_weight")
            if iso_weight is not None:
                if not isinstance(iso_weight, (int, float)) or not 0 <= iso_weight <= 1:
                    self.errors.append(
                        f"Schedule '{schedule_name}' smoothing.iso_weight must be between 0 and 1"
                    )

            shutter_weight = smoothing.get("shutter_weight")
            if shutter_weight is not None:
                if not isinstance(shutter_weight, (int, float)) or not 0 <= shutter_weight <= 1:
                    self.errors.append(
                        f"Schedule '{schedule_name}' smoothing.shutter_weight must be between 0 and 1"
                    )

    def _validate_video_debug(self, schedule_name: str, video_debug: Dict[str, Any]):
        """Validate video debug configuration."""
        if not isinstance(video_debug, dict):
            self.errors.append(f"Schedule '{schedule_name}' video_debug must be a dictionary")
            return

        # Validate enabled
        if "enabled" in video_debug and not isinstance(video_debug["enabled"], bool):
            self.errors.append(f"Schedule '{schedule_name}' video_debug.enabled must be boolean")

        # Validate font_size
        font_size = video_debug.get("font_size")
        if font_size is not None:
            if not isinstance(font_size, int) or font_size < 8:
                self.errors.append(
                    f"Schedule '{schedule_name}' video_debug.font_size must be integer >= 8"
                )

        # Validate position
        position = video_debug.get("position")
        if position is not None:
            valid_positions = {"bottom-left", "top-left", "bottom-right", "top-right"}
            if position not in valid_positions:
                self.errors.append(
                    f"Schedule '{schedule_name}' video_debug.position must be one of {valid_positions}"
                )

        # Validate background
        if "background" in video_debug and not isinstance(video_debug["background"], bool):
            self.errors.append(f"Schedule '{schedule_name}' video_debug.background must be boolean")

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

    def _validate_profiles(self, profiles: Dict[str, Any]):
        """Validate profiles section."""
        if not profiles:
            self.errors.append("No profiles defined")
            return

        enabled_count = 0
        for profile_id, profile_data in profiles.items():
            # Validate profile ID format (single lowercase letter)
            if not re.match(r'^[a-z]$', profile_id):
                self.errors.append(
                    f"Invalid profile ID: '{profile_id}' (must be single lowercase letter a-z)"
                )

            if not isinstance(profile_data, dict):
                self.errors.append(f"Profile '{profile_id}' must be a dictionary")
                continue

            # Count enabled profiles
            if profile_data.get("enabled", True):
                enabled_count += 1

            # Validate required fields
            if "name" not in profile_data:
                self.errors.append(f"Profile '{profile_id}' missing 'name'")

            if "description" not in profile_data:
                self.warnings.append(f"Profile '{profile_id}' missing 'description'")

            if "settings" not in profile_data:
                self.errors.append(f"Profile '{profile_id}' missing 'settings' section")
                continue

            settings = profile_data["settings"]

            # Validate settings structure
            if "base" not in settings:
                self.errors.append(f"Profile '{profile_id}' missing 'settings.base'")

            if "adaptive_wb" not in settings:
                self.warnings.append(f"Profile '{profile_id}' missing 'settings.adaptive_wb'")
            else:
                wb = settings["adaptive_wb"]
                if wb.get("enabled"):
                    curve = wb.get("curve")
                    if not curve:
                        self.errors.append(
                            f"Profile '{profile_id}' has adaptive_wb enabled but no curve specified"
                        )
                    elif curve not in self.VALID_WB_CURVES:
                        self.errors.append(
                            f"Profile '{profile_id}' has invalid WB curve: '{curve}' "
                            f"(must be one of {self.VALID_WB_CURVES})"
                        )

            if "adaptive_ev" not in settings:
                self.warnings.append(f"Profile '{profile_id}' missing 'settings.adaptive_ev'")
            else:
                ev = settings["adaptive_ev"]
                if ev.get("enabled"):
                    curve = ev.get("curve")
                    if not curve:
                        self.errors.append(
                            f"Profile '{profile_id}' has adaptive_ev enabled but no curve specified"
                        )
                    elif curve not in self.VALID_EV_CURVES:
                        self.errors.append(
                            f"Profile '{profile_id}' has invalid EV curve: '{curve}' "
                            f"(must be one of {self.VALID_EV_CURVES})"
                        )

        if enabled_count == 0:
            self.warnings.append("No profiles are enabled")

    def _validate_schedule_profiles(self, schedules: Dict[str, Any], profiles: Dict[str, Any]):
        """Validate that schedule profiles reference existing profile IDs."""
        for schedule_name, schedule in schedules.items():
            profile_list = schedule.get("profiles", [])

            if not isinstance(profile_list, list):
                self.errors.append(
                    f"Schedule '{schedule_name}' profiles must be a list, got {type(profile_list).__name__}"
                )
                continue

            # Check each profile reference
            for profile_id in profile_list:
                if profile_id not in profiles:
                    self.errors.append(
                        f"Schedule '{schedule_name}' references non-existent profile '{profile_id}'"
                    )
                elif not profiles[profile_id].get("enabled", True):
                    self.warnings.append(
                        f"Schedule '{schedule_name}' references disabled profile '{profile_id}'"
                    )

            # Warn about duplicates
            if len(profile_list) != len(set(profile_list)):
                duplicates = [p for p in profile_list if profile_list.count(p) > 1]
                self.warnings.append(
                    f"Schedule '{schedule_name}' has duplicate profiles: {set(duplicates)}"
                )


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
