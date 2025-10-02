"""
Smart Exposure Calculator

Calculates optimal camera settings based on camera metering + profile adjustments.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from schedule_types import ScheduleType

# Add parent directory to path for shared module access
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        Apply profile-specific modifications to base settings.

        Profile A: Auto WB (AwbMode=0), no HDR
        Profile B: Daylight WB (AwbMode=1), no HDR
        Profile C: Underexposed Daylight WB, highlight protection
        Profile D: Cloudy WB (AwbMode=2), natural sunset colors
        Profile E: EXPERIMENTAL Adaptive WB ramping (lux + time based)
        Profile F: Daylight WB + 3-shot HDR bracket

        Args:
            base_settings: Base ISO/shutter/EV/lux settings
            profile: Profile identifier (a/b/c/d/e/f)
            current_time: Current time (for Profile E ramping)
            schedule_type: Schedule type (for Profile E context)

        Returns:
            Complete settings dict with profile, awb_mode, hdr_mode, bracket_count
        """
        settings = base_settings.copy()
        settings["profile"] = profile

        # Extract and remove lux from settings (internal use only)
        lux = settings.pop("lux", None)

        if profile == "a":
            # Profile A: Pure Full Auto with Manual Focus at Infinity
            # Fully automatic exposure and white balance with no bias
            # Manual focus set to infinity for landscape sharpness
            settings["iso"] = 0  # ISO=0 signals full auto mode to Pi
            settings["shutter_speed"] = "auto"  # Placeholder (not used in auto mode)
            settings["exposure_compensation"] = 0.0  # Pure auto, no bias
            settings["awb_mode"] = 0  # Auto white balance
            settings["hdr_mode"] = 0  # No HDR
            settings["bracket_count"] = 1  # Single shot
            settings["ae_metering_mode"] = 0  # Center-weighted metering
            settings["lens_position"] = 0.0  # Manual focus at infinity (0.0 = infinity)
            logger.debug(
                f"Profile A (Pure Auto + Infinity Focus): EV{settings['exposure_compensation']:+.1f}"
            )

        elif profile == "b":
            # Profile B: Fixed Daylight WB
            settings["awb_mode"] = 1  # Daylight white balance
            settings["hdr_mode"] = 0  # No HDR
            settings["bracket_count"] = 1  # Single shot
            logger.debug(f"Profile B (Daylight WB): {settings}")

        elif profile == "c":
            # Profile C: EXPERIMENTAL Conservative adaptive curve
            # Cooler baseline, protects highlights, subtle warmth progression
            wb_temp = self._calculate_adaptive_wb_temp(current_time, lux=lux, curve="conservative")
            settings["awb_mode"] = 6  # Custom WB
            settings["wb_temp"] = wb_temp  # Color temperature in Kelvin
            settings["exposure_compensation"] = -0.3  # Slight underexposure for highlights
            settings["hdr_mode"] = 0  # No HDR
            settings["bracket_count"] = 1  # Single shot

        elif profile == "d":
            # Profile D: EXPERIMENTAL Warm/dramatic adaptive curve
            # Embraces golden tones earlier, richer sunset colors
            wb_temp = self._calculate_adaptive_wb_temp(current_time, lux=lux, curve="warm")
            settings["awb_mode"] = 6  # Custom WB
            settings["wb_temp"] = wb_temp  # Color temperature in Kelvin
            settings["hdr_mode"] = 0  # No HDR
            settings["bracket_count"] = 1  # Single shot

        elif profile == "e":
            # Profile E: EXPERIMENTAL Balanced adaptive curve
            # Matches B when bright, natural warmth progression
            wb_temp = self._calculate_adaptive_wb_temp(current_time, lux=lux, curve="balanced")
            settings["awb_mode"] = 6  # Custom WB
            settings["wb_temp"] = wb_temp  # Color temperature in Kelvin
            settings["hdr_mode"] = 0  # No HDR
            settings["bracket_count"] = 1  # Single shot

        elif profile == "f":
            # Profile F: Auto-Exposure with Spot Metering for Mountains
            # Meters lower-center region (where mountains are), ignores bright sky
            settings["iso"] = 0  # ISO=0 signals full auto mode to Pi
            settings["shutter_speed"] = "auto"  # Placeholder (not used in auto mode)
            settings["exposure_compensation"] = +0.7  # Strong positive bias for darker mountains
            settings["awb_mode"] = 1  # Daylight white balance for consistency
            settings["hdr_mode"] = 0  # No HDR
            settings["bracket_count"] = 1  # Single shot
            settings["ae_metering_mode"] = 1  # Spot metering (center of frame)
            logger.debug(
                f"Profile F (Auto + Spot Metering for Mountains): EV{settings['exposure_compensation']:+.1f}"
            )

        elif profile == "g":
            # Profile G: EXPERIMENTAL Adaptive EV + Balanced WB
            # Protects highlights in bright conditions, lifts shadows in low light
            # Uses lux-based EV curve: negative EV when bright, positive when dark
            wb_temp = self._calculate_adaptive_wb_temp(current_time, lux=lux, curve="balanced")

            # Calculate adaptive EV compensation based on lux
            if lux is not None:
                ev_curve = EV_CURVES["adaptive"]
                ev_comp = interpolate_ev_from_lux(lux, ev_curve)
            else:
                ev_comp = 0.0  # Fallback to neutral if no lux data

            settings["awb_mode"] = 6  # Custom WB
            settings["wb_temp"] = wb_temp  # Adaptive color temperature
            settings["exposure_compensation"] = ev_comp  # Adaptive EV
            settings["hdr_mode"] = 0  # No HDR
            settings["bracket_count"] = 1  # Single shot
            logger.info(
                f"🎯 Profile G (Adaptive EV): lux={lux:.0f} → EV{ev_comp:+.1f}, WB={wb_temp}K"
            )

        else:
            # Default fallback
            settings["awb_mode"] = 1
            settings["hdr_mode"] = 0
            settings["bracket_count"] = 1
            logger.warning(f"Unknown profile '{profile}', using defaults")

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
