"""
Smart Exposure Calculator

Calculates optimal camera settings based on camera metering + profile adjustments.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from schedule_types import ScheduleType
from shared.wb_curves import EV_CURVES, WB_CURVES, interpolate_ev_from_lux, interpolate_wb_from_lux

logger = logging.getLogger(__name__)


class ExposureCalculator:
    """Calculate optimal camera exposure settings"""

    def __init__(self, solar_calculator=None, pi_host: str = None, pi_port: int = 8080):
        """
        Initialize exposure calculator.

        Args:
            solar_calculator: Optional SolarCalculator for sun-based adjustments
            pi_host: Pi hostname/IP for metering endpoint
            pi_port: Pi service port
        """
        self.solar_calculator = solar_calculator
        self.pi_host = pi_host
        self.pi_port = pi_port
        self.meter_url = f"http://{pi_host}:{pi_port}/meter" if pi_host else None

    async def get_metered_exposure(self) -> Optional[Dict[str, Any]]:
        """
        Get camera-metered exposure settings from Pi (async).

        Returns:
            Dict with suggested_iso, suggested_shutter, lux, or None if metering fails
        """
        if not self.meter_url:
            logger.warning("No Pi host configured for metering")
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.meter_url)
                response.raise_for_status()
                meter_data = response.json()

                logger.info(
                    f"📊 Metered: ISO {meter_data['suggested_iso']}, "
                    f"Shutter {meter_data['suggested_shutter']}, Lux {meter_data['lux']:.1f}"
                )

                return meter_data

        except Exception as e:
            logger.error(f"Metering failed: {e}")
            return None

    async def calculate_settings(
        self, schedule_type: str, current_time: datetime = None, profile: str = "a"
    ) -> Dict[str, Any]:
        """
        Calculate camera settings using camera metering + profile adjustments (async).

        Args:
            schedule_type: "sunrise", "daytime", or "sunset"
            current_time: Current time (defaults to now in solar calculator's timezone)
            profile: Profile identifier (a/b/c/d/e/f) - determines WB and exposure strategy

        Returns:
            Dictionary with ISO, shutter_speed, exposure_compensation, profile, awb_mode, hdr_mode
        """
        if current_time is None:
            if self.solar_calculator:
                current_time = datetime.now(self.solar_calculator.timezone)
            else:
                current_time = datetime.now()

        # Try to get camera-metered exposure first
        meter_data = await self.get_metered_exposure()

        if meter_data:
            # Use camera's metered values as base
            base_settings = {
                "iso": meter_data["suggested_iso"],
                "shutter_speed": meter_data["suggested_shutter"],
                "exposure_compensation": 0.0,  # Start neutral, profiles adjust
                "lux": meter_data.get("lux"),  # Pass lux for adaptive WB
            }
            logger.debug(f"Using metered base: {base_settings}")
        else:
            # Fallback to time-based calculation
            logger.warning("Metering unavailable, using time-based fallback")
            if schedule_type == ScheduleType.SUNRISE:
                base_settings = self._calculate_sunrise_settings(current_time)
            elif schedule_type == ScheduleType.DAYTIME:
                base_settings = self._calculate_daytime_settings()
            elif schedule_type == ScheduleType.SUNSET:
                base_settings = self._calculate_sunset_settings(current_time)
            else:
                raise ValueError(f"Unknown schedule type: {schedule_type}")
            base_settings["lux"] = None  # No lux data in fallback mode

        # Apply profile-specific modifications (pass current_time and schedule_type for context)
        return self._apply_profile_settings(base_settings, profile, current_time, schedule_type)

    def _calculate_sunrise_settings(self, current_time: datetime) -> Dict[str, Any]:
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
            minutes_from_sunrise = (current_time - sunrise_time).total_seconds() / 60

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

    def _calculate_daytime_settings(self) -> Dict[str, Any]:
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

    def _calculate_sunset_settings(self, current_time: datetime) -> Dict[str, Any]:
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
            minutes_from_sunset = (current_time - sunset_time).total_seconds() / 60

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

    def _calculate_adaptive_wb_temp(
        self, current_time: datetime, lux: Optional[float] = None, curve: str = "balanced"
    ) -> int:
        """
        Calculate adaptive WB temperature using lux-based curves.

        EXPERIMENTAL: Pure lux-based WB with different curve strategies

        Args:
            current_time: Current time
            lux: Optional light level from metering
            curve: Curve strategy - "balanced", "conservative", "warm"

        Returns:
            Color temperature in Kelvin (3500-6000)
        """
        if not self.solar_calculator:
            return 5500  # Default to daylight

        if lux is None:
            # No lux data: fallback to daylight
            return 5500

        # Get control points from shared curve definitions
        control_points = WB_CURVES.get(curve, WB_CURVES["balanced"])

        # Use shared interpolation function
        wb_temp = interpolate_wb_from_lux(lux, control_points)

        # Determine phase for logging
        if lux >= 6000:
            reason = "bright"
        elif lux >= 3000:
            reason = "softening"
        elif lux >= 1500:
            reason = "golden"
        elif lux >= 700:
            reason = "dusk"
        elif lux >= 300:
            reason = "twilight"
        else:
            reason = "dark"

        # Calculate time info for logging only
        if self.solar_calculator:
            sunset_time = self.solar_calculator.get_sunset(current_time)
            minutes_from_sunset = (current_time - sunset_time).total_seconds() / 60
        else:
            minutes_from_sunset = 0

        logger.info(
            f"🎨 Adaptive WB: lux={lux:.0f} → {wb_temp}K ({reason}) "
            f"[{minutes_from_sunset:+.0f}min from sunset]"
        )

        return wb_temp

    def _apply_profile_settings(
        self,
        base_settings: Dict[str, Any],
        profile: str,
        current_time: datetime = None,
        schedule_type: str = None,
    ) -> Dict[str, Any]:
        """
        Apply profile-specific modifications using config data.

        Profiles are now data-driven from config.json, allowing changes
        without code rebuilds.

        Args:
            base_settings: Base ISO/shutter/EV/lux settings
            profile: Profile identifier (a/b/c/d/e/f/g)
            current_time: Current time (for adaptive WB ramping)
            schedule_type: Schedule type (for context)

        Returns:
            Complete settings dict with profile-specific modifications
        """
        from config import Config  # Import here to avoid circular dependency

        config = Config()
        profile_data = config.get_profile(profile)

        if not profile_data:
            logger.warning(f"Profile '{profile}' not found in config, using defaults")
            settings = base_settings.copy()
            settings["profile"] = profile
            settings["awb_mode"] = 1
            settings["hdr_mode"] = 0
            settings["bracket_count"] = 1
            return settings

        settings = base_settings.copy()
        settings["profile"] = profile

        # Extract and remove lux from settings (internal use only)
        lux = settings.pop("lux", None)

        # Apply base settings from profile config
        profile_base = profile_data.get("settings", {}).get("base", {})
        settings.update(profile_base)

        # Apply adaptive WB if enabled
        adaptive_wb = profile_data.get("settings", {}).get("adaptive_wb", {})
        if adaptive_wb.get("enabled", False):
            curve = adaptive_wb.get("curve", "balanced")
            wb_temp = self._calculate_adaptive_wb_temp(current_time, lux=lux, curve=curve)
            settings["awb_mode"] = 6  # Custom WB
            settings["wb_temp"] = wb_temp

        # Apply adaptive EV if enabled
        adaptive_ev = profile_data.get("settings", {}).get("adaptive_ev", {})
        if adaptive_ev.get("enabled", False) and lux is not None:
            curve = adaptive_ev.get("curve", "adaptive")
            ev_curve = EV_CURVES.get(curve, EV_CURVES["adaptive"])
            ev_comp = interpolate_ev_from_lux(lux, ev_curve)
            settings["exposure_compensation"] = ev_comp

        # Log profile application
        profile_name = profile_data.get("name", f"Profile {profile.upper()}")
        if adaptive_wb.get("enabled") or adaptive_ev.get("enabled"):
            details = []
            if lux is not None:
                details.append(f"lux={lux:.0f}")
            if adaptive_ev.get("enabled") and "exposure_compensation" in settings:
                details.append(f"EV{settings['exposure_compensation']:+.1f}")
            if adaptive_wb.get("enabled") and "wb_temp" in settings:
                details.append(f"WB={settings['wb_temp']}K")
            logger.info(f"📸 Profile {profile.upper()} ({profile_name}): {', '.join(details)}")
        else:
            logger.debug(f"Profile {profile.upper()}: {profile_name}")

        return settings

    def format_for_pi(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format settings for Pi API request.

        Args:
            settings: Settings from calculate_settings()

        Returns:
            Dictionary ready for Pi capture API
        """
        # Settings already in correct format for Pi
        return settings
