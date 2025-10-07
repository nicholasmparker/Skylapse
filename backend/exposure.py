"""
Smart Exposure Calculator

Calculates optimal camera settings based on camera metering + profile adjustments.
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from schedule_types import ScheduleType
from shared.wb_curves import EV_CURVES, WB_CURVES, interpolate_ev_from_lux, interpolate_wb_from_lux

logger = logging.getLogger(__name__)


class ExposureHistory:
    """Manages per-session exposure history for temporal smoothing."""

    def __init__(self):
        """Initialize empty exposure history."""
        # Key: session_id, Value: deque of recent settings
        self._history: Dict[str, deque] = {}

    def add_frame(self, session_id: str, settings: Dict[str, Any], max_window: int = 8):
        """
        Add a frame's settings to the history.

        Args:
            session_id: Unique session identifier
            settings: Capture settings (iso, shutter_speed, etc.)
            max_window: Maximum frames to store
        """
        if session_id not in self._history:
            self._history[session_id] = deque(maxlen=max_window)

        self._history[session_id].append(
            {"iso": settings.get("iso", 100), "timestamp": datetime.now()}
        )

    def get_recent_frames(self, session_id: str, count: int = 8) -> List[Dict[str, Any]]:
        """
        Get recent frames for a session.

        Args:
            session_id: Unique session identifier
            count: Number of recent frames to return

        Returns:
            List of recent frame settings (most recent last)
        """
        if session_id not in self._history:
            return []

        history = list(self._history[session_id])
        return history[-count:] if len(history) > count else history

    def get_last_iso(self, session_id: str) -> Optional[int]:
        """Get the last ISO value for a session."""
        if session_id not in self._history or not self._history[session_id]:
            return None
        return self._history[session_id][-1]["iso"]

    def clear_session(self, session_id: str):
        """Clear history for a specific session."""
        if session_id in self._history:
            del self._history[session_id]


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
        self.exposure_history = ExposureHistory()

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
        self,
        schedule_type: str,
        current_time: datetime = None,
        profile: str = "a",
        session_id: str = None,
        smoothing_config: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Calculate camera settings using camera metering + profile adjustments (async).

        Args:
            schedule_type: "sunrise", "daytime", or "sunset"
            current_time: Current time (defaults to now in solar calculator's timezone)
            profile: Profile identifier (a/b/c/d/e/f/g) - determines WB and exposure strategy
            session_id: Optional session ID for smoothing history tracking
            smoothing_config: Optional smoothing configuration (enables temporal smoothing)

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
        settings = self._apply_profile_settings(base_settings, profile, current_time, schedule_type)

        # Apply temporal smoothing if enabled
        if session_id and smoothing_config:
            settings = self._apply_smoothing(settings, session_id, smoothing_config)

        return settings

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

    def _apply_smoothing(
        self,
        settings: Dict[str, Any],
        session_id: str,
        smoothing_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply temporal smoothing to exposure settings using EMA.

        Args:
            settings: Current frame settings
            session_id: Session identifier for history tracking
            smoothing_config: Smoothing configuration from schedule
                - enabled: bool
                - window_frames: int (number of frames for EMA)
                - max_change_per_frame: float (max fractional change, e.g., 0.12 = 12%)
                - iso_weight: float (0-1, weight for ISO smoothing)
                - shutter_weight: float (0-1, weight for shutter smoothing)

        Returns:
            Smoothed settings dict
        """
        if not smoothing_config.get("enabled", False):
            return settings

        # Get last ISO from history
        last_iso = self.exposure_history.get_last_iso(session_id)
        current_iso = settings.get("iso", 100)

        if last_iso is None:
            # First frame, no smoothing needed
            logger.debug(f"🎬 First frame for session {session_id}, no smoothing")
            self.exposure_history.add_frame(
                session_id, settings, max_window=smoothing_config.get("window_frames", 8)
            )
            return settings

        # Calculate ISO change
        max_change = smoothing_config.get("max_change_per_frame", 0.12)
        iso_weight = smoothing_config.get("iso_weight", 0.7)

        # Apply EMA smoothing to ISO
        iso_diff = current_iso - last_iso
        iso_change_fraction = abs(iso_diff) / last_iso if last_iso > 0 else 0

        if iso_change_fraction > max_change:
            # Limit the change
            max_iso_change = int(last_iso * max_change)
            if iso_diff > 0:
                smoothed_iso = last_iso + max_iso_change
            else:
                smoothed_iso = last_iso - max_iso_change

            # Apply weight
            smoothed_iso = int(last_iso + (smoothed_iso - last_iso) * iso_weight)

            logger.info(
                f"🎨 Smoothing ISO: {last_iso} → {current_iso} (raw), "
                f"limited to {smoothed_iso} (Δ{iso_change_fraction*100:.0f}% → {max_change*100:.0f}%)"
            )

            settings["iso"] = smoothed_iso
        else:
            # Change is within limits, apply gentle smoothing
            smoothed_iso = int(last_iso + (current_iso - last_iso) * iso_weight)
            if smoothed_iso != current_iso:
                logger.debug(
                    f"🎨 Gentle ISO smoothing: {current_iso} → {smoothed_iso} "
                    f"(Δ{iso_change_fraction*100:.0f}%)"
                )
                settings["iso"] = smoothed_iso

        # Add frame to history
        self.exposure_history.add_frame(
            session_id, settings, max_window=smoothing_config.get("window_frames", 8)
        )

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
