"""
Smart Exposure Calculator

Calculates optimal camera settings based on time of day and schedule type.
"""

from datetime import datetime, timedelta
from typing import Dict
import logging
from schedule_types import ScheduleType

logger = logging.getLogger(__name__)


class ExposureCalculator:
    """Calculate optimal camera exposure settings"""

    def __init__(self, solar_calculator=None):
        """
        Initialize exposure calculator.

        Args:
            solar_calculator: Optional SolarCalculator for sun-based adjustments
        """
        self.solar_calculator = solar_calculator

    def calculate_settings(
        self, schedule_type: str, current_time: datetime = None, profile: str = "a"
    ) -> Dict[str, any]:
        """
        Calculate camera settings for current conditions and profile.

        Args:
            schedule_type: "sunrise", "daytime", or "sunset"
            current_time: Current time (defaults to now in solar calculator's timezone)
            profile: Profile identifier (a/b/c/d) - determines WB and exposure strategy

        Returns:
            Dictionary with ISO, shutter_speed, exposure_compensation, profile, awb_mode, hdr_mode
        """
        if current_time is None:
            if self.solar_calculator:
                current_time = datetime.now(self.solar_calculator.timezone)
            else:
                current_time = datetime.now()

        # Calculate base settings based on schedule type
        if schedule_type == ScheduleType.SUNRISE:
            base_settings = self._calculate_sunrise_settings(current_time)
        elif schedule_type == ScheduleType.DAYTIME:
            base_settings = self._calculate_daytime_settings()
        elif schedule_type == ScheduleType.SUNSET:
            base_settings = self._calculate_sunset_settings(current_time)
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

        # Apply profile-specific modifications
        return self._apply_profile_settings(base_settings, profile)

    def _calculate_sunrise_settings(self, current_time: datetime) -> Dict[str, any]:
        """
        Calculate settings for sunrise capture.

        Sunrise characteristics:
        - Rapidly changing light (dark → bright)
        - Fast shutter to freeze motion
        - Medium-high ISO for low light at start
        - Positive exposure compensation as sun rises
        """
        if self.solar_calculator:
            sunrise_time = self.solar_calculator.get_sunrise(current_time)
            minutes_from_sunrise = (
                current_time - sunrise_time
            ).total_seconds() / 60

            # Before sunrise: Higher ISO, slightly slower shutter
            if minutes_from_sunrise < -15:
                iso = 800
                shutter = "1/500"
                ev = +1.0
            # Near sunrise: Medium ISO, fast shutter
            elif -15 <= minutes_from_sunrise < 0:
                iso = 400
                shutter = "1/1000"
                ev = +0.7
            # After sunrise: Lower ISO, fast shutter
            else:
                iso = 200
                shutter = "1/1000"
                ev = +0.3
        else:
            # Default sunrise settings (no solar calculator)
            iso = 400
            shutter = "1/1000"
            ev = +0.7

        settings = {
            "iso": iso,
            "shutter_speed": shutter,
            "exposure_compensation": ev,
        }

        logger.debug(f"Sunrise settings at {current_time}: {settings}")
        return settings

    def _calculate_daytime_settings(self) -> Dict[str, any]:
        """
        Calculate settings for daytime capture.

        Daytime characteristics:
        - Bright, consistent light
        - Low ISO for best quality
        - Fast shutter for sharpness
        - Neutral exposure
        """
        settings = {
            "iso": 100,
            "shutter_speed": "1/500",
            "exposure_compensation": 0.0,
        }

        logger.debug(f"Daytime settings: {settings}")
        return settings

    def _calculate_sunset_settings(self, current_time: datetime) -> Dict[str, any]:
        """
        Calculate settings for sunset capture.

        Sunset characteristics:
        - Gradually darkening light
        - Need to increase exposure as sun sets
        - Slightly higher ISO as light fades
        - Longer shutter than sunrise (less motion)
        """
        if self.solar_calculator:
            sunset_time = self.solar_calculator.get_sunset(current_time)
            minutes_from_sunset = (
                current_time - sunset_time
            ).total_seconds() / 60

            # Before sunset: Standard settings
            if minutes_from_sunset < -15:
                iso = 200
                shutter = "1/500"
                ev = 0.0
            # Near sunset: Boost exposure
            elif -15 <= minutes_from_sunset < 0:
                iso = 400
                shutter = "1/250"
                ev = +0.3
            # After sunset: Higher ISO, longer exposure
            else:
                iso = 800
                shutter = "1/125"
                ev = +0.7
        else:
            # Default sunset settings (no solar calculator)
            iso = 400
            shutter = "1/250"
            ev = +0.3

        settings = {
            "iso": iso,
            "shutter_speed": shutter,
            "exposure_compensation": ev,
        }

        logger.debug(f"Sunset settings at {current_time}: {settings}")
        return settings

    def _apply_profile_settings(self, base_settings: Dict[str, any], profile: str) -> Dict[str, any]:
        """
        Apply profile-specific modifications to base settings.

        Profile A: Auto WB (AwbMode=0), no HDR
        Profile B: Daylight WB (AwbMode=1), no HDR
        Profile C: Daylight WB (AwbMode=1), manual ramping, no HDR
        Profile D: Daylight WB (AwbMode=1), HDR Mode 1

        Args:
            base_settings: Base ISO/shutter/EV settings
            profile: Profile identifier (a/b/c/d)

        Returns:
            Complete settings dict with profile, awb_mode, hdr_mode
        """
        settings = base_settings.copy()
        settings["profile"] = profile

        if profile == "a":
            # Profile A: Auto Everything (Baseline)
            settings["awb_mode"] = 0  # Auto white balance
            settings["hdr_mode"] = 0  # No HDR
            logger.debug(f"Profile A (Auto WB): {settings}")

        elif profile == "b":
            # Profile B: Fixed Daylight WB
            settings["awb_mode"] = 1  # Daylight white balance
            settings["hdr_mode"] = 0  # No HDR
            logger.debug(f"Profile B (Daylight WB): {settings}")

        elif profile == "c":
            # Profile C: Manual Ramping (same as B for now)
            settings["awb_mode"] = 1  # Daylight white balance
            settings["hdr_mode"] = 0  # No HDR
            logger.debug(f"Profile C (Manual Ramp): {settings}")

        elif profile == "d":
            # Profile D: HDR Mode
            settings["awb_mode"] = 1  # Daylight white balance
            settings["hdr_mode"] = 1  # Single exposure HDR
            logger.debug(f"Profile D (HDR): {settings}")

        else:
            # Default fallback
            settings["awb_mode"] = 1
            settings["hdr_mode"] = 0
            logger.warning(f"Unknown profile '{profile}', using defaults")

        return settings

    def format_for_pi(self, settings: Dict[str, any]) -> Dict[str, any]:
        """
        Format settings for Pi API request.

        Args:
            settings: Settings from calculate_settings()

        Returns:
            Dictionary ready for Pi capture API
        """
        # Settings already in correct format for Pi
        return settings
