"""
Profile Executor - Local Profile Execution on Pi

Handles storage and execution of deployed profiles from Backend.
Profiles contain pre-compiled settings and lux lookup tables for autonomous operation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProfileExecutor:
    """Manages deployed profiles and calculates settings locally"""

    def __init__(self, profile_path: str = "/home/pi/.skylapse/current_profile.json"):
        self.profile_path = Path(profile_path)
        self.profile = self._load_profile()

    def _load_profile(self) -> Optional[Dict[str, Any]]:
        """Load deployed profile from disk"""
        if not self.profile_path.exists():
            logger.info("No deployed profile found")
            return None

        try:
            with open(self.profile_path) as f:
                profile = json.load(f)
                logger.info(f"✓ Loaded deployed profile: {profile.get('profile_id', 'unknown')}")
                return profile
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            return None

    def deploy_profile(self, profile_data: Dict[str, Any]) -> bool:
        """
        Deploy a new profile (save to disk and activate).

        Args:
            profile_data: Profile snapshot from Backend

        Returns:
            True if deployment successful
        """
        try:
            # Ensure directory exists
            self.profile_path.parent.mkdir(parents=True, exist_ok=True)

            # Save profile to disk
            with open(self.profile_path, "w") as f:
                json.dump(profile_data, f, indent=2)

            # Load into memory
            self.profile = profile_data

            logger.info(
                f"✓ Profile deployed: {profile_data['profile_id']} "
                f"v{profile_data.get('version', '1.0.0')}"
            )
            return True

        except Exception as e:
            logger.error(f"Profile deployment failed: {e}")
            return False

    def clear_profile(self) -> bool:
        """Clear deployed profile (revert to live orchestration mode)"""
        try:
            if self.profile_path.exists():
                self.profile_path.unlink()
            self.profile = None
            logger.info("✓ Profile cleared - reverted to live orchestration mode")
            return True
        except Exception as e:
            logger.error(f"Failed to clear profile: {e}")
            return False

    def has_profile(self) -> bool:
        """Check if a profile is currently deployed"""
        return self.profile is not None

    def get_profile_info(self) -> Optional[Dict[str, Any]]:
        """Get current profile metadata"""
        if not self.profile:
            return None

        return {
            "profile_id": self.profile.get("profile_id"),
            "version": self.profile.get("version", "1.0.0"),
            "deployed_at": self.profile.get("deployed_at"),
            "schedules": self.profile.get("schedules", []),
        }

    def calculate_settings(
        self, schedule_type: str, lux: float, override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate capture settings using deployed profile.

        This is the LOCAL version of Backend's exposure.calculate_settings()
        but uses pre-compiled profile data.

        Args:
            schedule_type: Schedule name (sunrise/daytime/sunset)
            lux: Current light level from camera metering
            override: Optional override settings (for testing)

        Returns:
            Complete capture settings dict
        """
        if not self.profile:
            raise ValueError("No profile deployed - use live orchestration mode")

        # Start with base settings from profile
        settings = self.profile["settings"]["base"].copy()

        # Apply adaptive WB if enabled
        if self.profile["settings"].get("adaptive_wb", {}).get("enabled"):
            wb_temp = self._interpolate_wb_from_lux(
                lux, self.profile["settings"]["adaptive_wb"]["lux_table"]
            )
            settings["awb_mode"] = 6  # Custom WB
            settings["wb_temp"] = wb_temp

        # Apply schedule-specific overrides
        schedule_overrides = (
            self.profile["settings"].get("schedule_overrides", {}).get(schedule_type, {})
        )
        settings.update(schedule_overrides)

        # Apply test overrides if provided
        if override:
            settings.update(override)
            logger.info(f"🧪 Override applied: {override}")

        logger.info(
            f"🎯 Profile execution: {self.profile['profile_id']} "
            f"for {schedule_type}, lux={lux:.0f}, "
            f"EV{settings.get('exposure_compensation', 0):+.1f}"
        )

        return settings

    def _interpolate_wb_from_lux(self, lux: float, lux_table: List[Tuple[float, int]]) -> int:
        """
        Linear interpolation of WB temp from lux value.

        This is the same logic as backend/exposure.py but uses
        pre-compiled lux_table from deployed profile.

        Args:
            lux: Current light level
            lux_table: List of [lux, wb_temp] control points

        Returns:
            Interpolated white balance temperature in Kelvin
        """
        if not lux_table:
            return 5500  # Default daylight

        # Handle edge cases
        if lux >= lux_table[0][0]:
            return lux_table[0][1]

        if lux <= lux_table[-1][0]:
            return lux_table[-1][1]

        # Find bracketing points and interpolate
        for i in range(len(lux_table) - 1):
            lux_high, temp_high = lux_table[i]
            lux_low, temp_low = lux_table[i + 1]

            if lux_low <= lux <= lux_high:
                # Linear interpolation
                progress = (lux_high - lux) / (lux_high - lux_low)
                wb_temp = int(temp_high - (progress * (temp_high - temp_low)))
                logger.debug(
                    f"WB interpolation: lux={lux:.0f} → {wb_temp}K "
                    f"(between {lux_high}→{temp_high}K and {lux_low}→{temp_low}K)"
                )
                return wb_temp

        # Fallback
        return 5500
