"""Capture scheduling system for timelapse operations."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .camera_types import CaptureResult, CaptureSettings, EnvironmentalConditions

logger = logging.getLogger(__name__)


@dataclass
class ScheduleRule:
    """Capture schedule rule definition."""

    name: str
    active: bool
    interval_seconds: int
    start_hour: Optional[int] = None  # 0-23, None for all day
    end_hour: Optional[int] = None  # 0-23, None for all day
    min_light_level: Optional[float] = None  # Minimum lux
    max_light_level: Optional[float] = None  # Maximum lux
    conditions: Dict[str, Any] = None  # Additional conditions


class CaptureScheduler:
    """Intelligent scheduling system for timelapse captures."""

    def __init__(self):
        """Initialize capture scheduler."""
        self._is_initialized = False
        self._schedule_rules: List[ScheduleRule] = []
        self._last_capture_time: Optional[float] = None
        self._capture_history: List[Dict[str, Any]] = []
        self._failure_count = 0
        self._consecutive_failures = 0

        # Enhanced adaptive schedule rules for Sprint 2
        self._default_rules = [
            ScheduleRule(
                name="golden_hour_intensive",
                active=True,
                interval_seconds=2,  # Every 2 seconds during golden hour (SCHED-002)
                conditions={"golden_hour": True},
            ),
            ScheduleRule(
                name="golden_hour_moderate",
                active=True,
                interval_seconds=5,  # Every 5 seconds near golden hour
                conditions={"near_golden_hour": True},
            ),
            ScheduleRule(
                name="blue_hour_intensive",
                active=True,
                interval_seconds=10,  # Every 10 seconds during blue hour
                conditions={"blue_hour": True},
            ),
            ScheduleRule(
                name="sunrise_sunset_burst",
                active=True,
                interval_seconds=1,  # Every second during sunrise/sunset
                conditions={"sunrise_sunset_window": True},
            ),
            ScheduleRule(
                name="daylight_stable",
                active=True,
                interval_seconds=300,  # Every 5 minutes during stable daylight
                start_hour=10,
                end_hour=15,
                min_light_level=5000,  # Bright stable daylight
            ),
            ScheduleRule(
                name="changing_light",
                active=True,
                interval_seconds=30,  # Every 30 seconds when light is changing
                conditions={"light_changing": True},
            ),
            ScheduleRule(
                name="low_light_reduced",
                active=True,
                interval_seconds=600,  # Every 10 minutes in low light
                max_light_level=100,
            ),
            ScheduleRule(
                name="default_fallback",
                active=True,
                interval_seconds=300,  # Default 5 minute interval
            ),
        ]

    async def initialize(self) -> None:
        """Initialize scheduler with default rules."""
        logger.info("Initializing capture scheduler")

        # Load default schedule rules
        self._schedule_rules = self._default_rules.copy()

        # Initialize capture history
        self._capture_history = []
        self._last_capture_time = None

        self._is_initialized = True
        logger.info("Capture scheduler initialized")

    async def shutdown(self) -> None:
        """Shutdown scheduler."""
        logger.info("Shutting down capture scheduler")
        self._is_initialized = False

    async def should_capture(self, conditions: Optional[EnvironmentalConditions] = None) -> bool:
        """
        Determine if a capture should be performed now based on schedule rules.
        """
        if not self._is_initialized:
            return False

        current_time = time.time()

        # Don't capture too frequently (minimum 10 second gap)
        if self._last_capture_time and current_time - self._last_capture_time < 10:
            return False

        # Back off on repeated failures
        if self._consecutive_failures >= 3:
            backoff_seconds = min(300, 30 * (2 ** (self._consecutive_failures - 2)))
            if self._last_capture_time and current_time - self._last_capture_time < backoff_seconds:
                return False

        # Find matching rule
        matching_rule = self._find_matching_rule(conditions)
        if not matching_rule:
            return False

        # Check if enough time has passed according to rule interval
        if (
            self._last_capture_time
            and current_time - self._last_capture_time < matching_rule.interval_seconds
        ):
            return False

        logger.debug(f"Capture scheduled by rule: {matching_rule.name}")
        return True

    def _find_matching_rule(
        self, conditions: Optional[EnvironmentalConditions] = None
    ) -> Optional[ScheduleRule]:
        """Find the first matching schedule rule for current conditions."""
        current_hour = datetime.now().hour

        for rule in self._schedule_rules:
            if not rule.active:
                continue

            # Check time constraints
            if rule.start_hour is not None and current_hour < rule.start_hour:
                continue
            if rule.end_hour is not None and current_hour >= rule.end_hour:
                continue

            # Check light level constraints
            if conditions and conditions.ambient_light_lux is not None:
                if (
                    rule.min_light_level is not None
                    and conditions.ambient_light_lux < rule.min_light_level
                ):
                    continue
                if (
                    rule.max_light_level is not None
                    and conditions.ambient_light_lux > rule.max_light_level
                ):
                    continue

            # Check special conditions with enhanced adaptive logic
        if rule.conditions:
            if conditions is None:
                # Can't match condition-specific rules without conditions
                continue

            match = True
            for condition, required_value in rule.conditions.items():
                if condition == "golden_hour":
                    if getattr(conditions, "is_golden_hour", False) != required_value:
                        match = False
                        break
                elif condition == "blue_hour":
                    if getattr(conditions, "is_blue_hour", False) != required_value:
                        match = False
                        break
                elif condition == "near_golden_hour":
                    # Check if we're within 30 minutes of golden hour
                    near_golden = self._is_near_golden_hour(conditions)
                    if near_golden != required_value:
                        match = False
                        break
                elif condition == "sunrise_sunset_window":
                    # Check if we're within 15 minutes of sunrise/sunset
                    sunrise_sunset_window = self._is_sunrise_sunset_window(conditions)
                    if sunrise_sunset_window != required_value:
                        match = False
                        break
                elif condition == "light_changing":
                    # Check if light conditions are rapidly changing
                    light_changing = self._is_light_changing(conditions)
                    if light_changing != required_value:
                        match = False
                        break

            if not match:
                continue

            # Rule matches
            return rule

        return None

    def get_current_capture_settings(self) -> CaptureSettings:
        """Get appropriate capture settings for current conditions."""
        # This is a basic implementation for Sprint 1
        # In Phase 2, this will be enhanced with adaptive intelligence

        base_settings = CaptureSettings(quality=95, format="JPEG", iso=100, autofocus_enabled=True)

        # Add processing hints based on current rule
        matching_rule = self._find_matching_rule()
        if matching_rule:
            base_settings.processing_hints["schedule_rule"] = matching_rule.name

            # Adjust settings based on rule
            if matching_rule.name == "golden_hour_intensive":
                base_settings.hdr_bracket_stops = [-1, 0, 1]  # 3-stop HDR
                base_settings.processing_hints["enhance_warmth"] = True

            elif matching_rule.name == "blue_hour_intensive":
                base_settings.iso = 400  # Higher ISO for low light
                base_settings.processing_hints["enhance_blues"] = True

            elif matching_rule.name == "low_light_reduced":
                base_settings.iso = 800  # High ISO for very low light
                base_settings.processing_hints["noise_reduction"] = True

        return base_settings

    async def record_capture_result(
        self, result: CaptureResult, conditions: Optional[EnvironmentalConditions] = None
    ) -> None:
        """Record the result of a capture operation."""
        current_time = time.time()
        self._last_capture_time = current_time

        # Reset consecutive failure count on success
        self._consecutive_failures = 0

        # Add to capture history
        history_entry = {
            "timestamp": current_time,
            "success": True,
            "capture_time_ms": result.capture_time_ms,
            "image_count": len(result.file_paths),
            "quality_score": result.quality_score,
            "conditions": {
                "is_golden_hour": conditions.is_golden_hour if conditions else False,
                "is_blue_hour": conditions.is_blue_hour if conditions else False,
                "ambient_light_lux": conditions.ambient_light_lux if conditions else None,
                "sun_elevation_deg": conditions.sun_elevation_deg if conditions else None,
            },
        }

        self._capture_history.append(history_entry)

        # Keep only recent history (last 1000 entries)
        if len(self._capture_history) > 1000:
            self._capture_history = self._capture_history[-1000:]

        logger.info(
            f"Recorded successful capture: {result.capture_time_ms:.1f}ms, "
            f"quality: {result.quality_score:.2f}"
        )

    async def record_capture_failure(self, error_message: str) -> None:
        """Record a capture failure."""
        current_time = time.time()
        self._failure_count += 1
        self._consecutive_failures += 1

        # Add failure to history
        history_entry = {
            "timestamp": current_time,
            "success": False,
            "error": error_message,
            "consecutive_failures": self._consecutive_failures,
        }

        self._capture_history.append(history_entry)

        # Keep only recent history
        if len(self._capture_history) > 1000:
            self._capture_history = self._capture_history[-1000:]

        logger.warning(f"Recorded capture failure #{self._consecutive_failures}: {error_message}")

    async def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics."""
        if not self._is_initialized:
            return {"initialized": False}

        current_time = time.time()

        # Calculate statistics from recent history
        recent_history = [
            entry
            for entry in self._capture_history
            if current_time - entry["timestamp"] < 3600  # Last hour
        ]

        successful_captures = [entry for entry in recent_history if entry["success"]]
        failed_captures = [entry for entry in recent_history if not entry["success"]]

        avg_capture_time = 0.0
        if successful_captures:
            avg_capture_time = sum(
                entry.get("capture_time_ms", 0) for entry in successful_captures
            ) / len(successful_captures)

        return {
            "initialized": True,
            "active_rules": len([rule for rule in self._schedule_rules if rule.active]),
            "last_capture_time": self._last_capture_time,
            "consecutive_failures": self._consecutive_failures,
            "statistics": {
                "total_captures_hour": len(recent_history),
                "successful_captures_hour": len(successful_captures),
                "failed_captures_hour": len(failed_captures),
                "success_rate_pct": (
                    (len(successful_captures) / len(recent_history) * 100) if recent_history else 0
                ),
                "average_capture_time_ms": avg_capture_time,
            },
            "next_capture_estimate": self._estimate_next_capture_time(),
        }

    def _estimate_next_capture_time(self) -> Optional[float]:
        """Estimate when the next capture will occur."""
        if not self._last_capture_time:
            return time.time()  # Immediate if no previous capture

        # Find the rule with shortest interval that would apply
        matching_rule = self._find_matching_rule()
        if not matching_rule:
            return None

        next_capture_time = self._last_capture_time + matching_rule.interval_seconds

        # Account for failure backoff
        if self._consecutive_failures >= 3:
            backoff_seconds = min(300, 30 * (2 ** (self._consecutive_failures - 2)))
            next_capture_time = max(next_capture_time, self._last_capture_time + backoff_seconds)

        return max(next_capture_time, time.time())

    async def update_schedule_rules(self, new_rules: List[Dict[str, Any]]) -> bool:
        """Update schedule rules at runtime."""
        try:
            updated_rules = []
            for rule_data in new_rules:
                rule = ScheduleRule(
                    name=rule_data["name"],
                    active=rule_data.get("active", True),
                    interval_seconds=rule_data["interval_seconds"],
                    start_hour=rule_data.get("start_hour"),
                    end_hour=rule_data.get("end_hour"),
                    min_light_level=rule_data.get("min_light_level"),
                    max_light_level=rule_data.get("max_light_level"),
                    conditions=rule_data.get("conditions", {}),
                )
                updated_rules.append(rule)

            self._schedule_rules = updated_rules
            logger.info(f"Updated {len(updated_rules)} schedule rules")
            return True

        except Exception as e:
            logger.error(f"Failed to update schedule rules: {e}")
            return False

    async def should_capture_now(self, conditions: EnvironmentalConditions = None) -> bool:
        """Determine if a capture should be performed now based on schedule rules."""
        return await self.should_capture(conditions)

    async def get_next_capture_time(self, conditions: EnvironmentalConditions = None) -> float:
        """Get the next scheduled capture time based on current conditions."""
        if not self._is_initialized:
            raise RuntimeError("Scheduler not initialized")

        # Find matching rule for these conditions
        matching_rule = self._find_matching_rule(conditions)
        if not matching_rule:
            # Use default fallback rule
            matching_rule = next(
                (rule for rule in self._schedule_rules if rule.name == "default_fallback"),
                self._default_rules[-1],  # Last default rule as ultimate fallback
            )

        # Calculate next time based on last capture + interval
        if self._last_capture_time:
            next_time = self._last_capture_time + matching_rule.interval_seconds
        else:
            next_time = (
                time.time() + matching_rule.interval_seconds
            )  # Schedule based on interval from now

        # Account for failure backoff
        if self._consecutive_failures >= 3:
            backoff_seconds = min(300, 30 * (2 ** (self._consecutive_failures - 2)))
            if self._last_capture_time:
                backoff_time = self._last_capture_time + backoff_seconds
                next_time = max(next_time, backoff_time)

        return max(next_time, time.time())

    async def add_schedule_rule(self, rule: ScheduleRule) -> None:
        """Add a new schedule rule."""
        if not self._is_initialized:
            raise RuntimeError("Scheduler not initialized")

        # Remove any existing rule with the same name
        self._schedule_rules = [r for r in self._schedule_rules if r.name != rule.name]

        # Add the new rule
        self._schedule_rules.append(rule)
        logger.info(f"Added schedule rule: {rule.name}")

    async def remove_schedule_rule(self, rule_name: str) -> bool:
        """Remove a schedule rule by name."""
        if not self._is_initialized:
            raise RuntimeError("Scheduler not initialized")

        initial_count = len(self._schedule_rules)
        self._schedule_rules = [r for r in self._schedule_rules if r.name != rule_name]

        removed = len(self._schedule_rules) < initial_count
        if removed:
            logger.info(f"Removed schedule rule: {rule_name}")
        return removed

    async def record_capture_attempt(
        self,
        result: Optional[CaptureResult] = None,
        success: bool = True,
        timestamp: datetime = None,
    ) -> None:
        """Record the result of a capture attempt."""
        if not self._is_initialized:
            return

        if timestamp is None:
            timestamp = datetime.now()

        timestamp_float = timestamp.timestamp()
        self._last_capture_time = timestamp_float

        if success and result:
            # Success case
            self._consecutive_failures = 0

            history_entry = {
                "timestamp": timestamp_float,
                "success": True,
                "capture_time_ms": result.capture_time_ms,
                "image_count": len(result.file_paths),
                "quality_score": result.quality_score,
            }
        else:
            # Failure case
            self._failure_count += 1
            self._consecutive_failures += 1

            history_entry = {
                "timestamp": timestamp_float,
                "success": False,
                "consecutive_failures": self._consecutive_failures,
            }

            if result and hasattr(result, "error_message"):
                history_entry["error"] = result.error_message

        self._capture_history.append(history_entry)

        # Keep only recent history (last 1000 entries)
        if len(self._capture_history) > 1000:
            self._capture_history = self._capture_history[-1000:]

    async def get_schedule_rules(self) -> List[ScheduleRule]:
        """Get the current list of schedule rules."""
        if not self._is_initialized:
            return []
        return self._schedule_rules.copy()

    def get_capture_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get detailed capture statistics for the specified time period."""
        current_time = time.time()
        cutoff_time = current_time - (hours * 3600)

        period_history = [
            entry for entry in self._capture_history if entry["timestamp"] >= cutoff_time
        ]

        if not period_history:
            return {
                "period_hours": hours,
                "total_captures": 0,
                "success_rate": 0.0,
                "avg_interval_seconds": 0,
                "quality_stats": {},
            }

        successful = [entry for entry in period_history if entry["success"]]
        failed = [entry for entry in period_history if not entry["success"]]

        # Calculate average interval between captures
        timestamps = sorted([entry["timestamp"] for entry in successful])
        intervals = []
        for i in range(1, len(timestamps)):
            intervals.append(timestamps[i] - timestamps[i - 1])

        avg_interval = sum(intervals) / len(intervals) if intervals else 0

        # Quality statistics
        quality_scores = [
            entry["quality_score"] for entry in successful if entry.get("quality_score") is not None
        ]

        quality_stats = {}
        if quality_scores:
            quality_stats = {
                "average": sum(quality_scores) / len(quality_scores),
                "minimum": min(quality_scores),
                "maximum": max(quality_scores),
                "count": len(quality_scores),
            }

        return {
            "period_hours": hours,
            "total_captures": len(period_history),
            "successful_captures": len(successful),
            "failed_captures": len(failed),
            "success_rate": len(successful) / len(period_history) * 100,
            "avg_interval_seconds": avg_interval,
            "quality_stats": quality_stats,
        }

    def get_capture_history(self) -> List[Dict]:
        """Get the complete capture history."""
        return self._capture_history.copy()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics about scheduler performance."""
        if not self._is_initialized:
            return {"initialized": False}

        current_time = time.time()

        # Calculate statistics from recent history
        recent_history = [
            entry
            for entry in self._capture_history
            if current_time - entry["timestamp"] < 3600  # Last hour
        ]

        daily_history = [
            entry
            for entry in self._capture_history
            if current_time - entry["timestamp"] < 86400  # Last 24 hours
        ]

        successful_recent = [entry for entry in recent_history if entry["success"]]
        failed_recent = [entry for entry in recent_history if not entry["success"]]

        successful_daily = [entry for entry in daily_history if entry["success"]]
        failed_daily = [entry for entry in daily_history if not entry["success"]]

        avg_capture_time = 0.0
        if successful_recent:
            capture_times = [entry.get("capture_time_ms", 0) for entry in successful_recent]
            avg_capture_time = sum(capture_times) / len(capture_times)

        # Calculate average interval between captures
        timestamps = sorted([entry["timestamp"] for entry in successful_recent])
        intervals = []
        for i in range(1, len(timestamps)):
            intervals.append(timestamps[i] - timestamps[i - 1])
        avg_interval = sum(intervals) / len(intervals) if intervals else 0

        return {
            "initialized": True,
            "active_rules": len([rule for rule in self._schedule_rules if rule.active]),
            "total_rules": len(self._schedule_rules),
            "last_capture_time": self._last_capture_time,
            "consecutive_failures": self._consecutive_failures,
            "total_failure_count": self._failure_count,
            "total_captures": len(recent_history),
            "successful_captures": len(successful_recent),
            "failed_captures": len(failed_recent),
            "average_interval": avg_interval,
            "success_rate_pct": (
                (len(successful_recent) / len(recent_history) * 100) if recent_history else 100
            ),
            "average_capture_time_ms": avg_capture_time,
            "hourly_stats": {
                "total_captures": len(recent_history),
                "successful_captures": len(successful_recent),
                "failed_captures": len(failed_recent),
                "success_rate_pct": (
                    (len(successful_recent) / len(recent_history) * 100) if recent_history else 100
                ),
                "average_capture_time_ms": avg_capture_time,
            },
            "daily_stats": {
                "total_captures": len(daily_history),
                "successful_captures": len(successful_daily),
                "failed_captures": len(failed_daily),
                "success_rate_pct": (
                    (len(successful_daily) / len(daily_history) * 100) if daily_history else 100
                ),
            },
            "next_capture_estimate": self._estimate_next_capture_time(),
        }

    async def set_rule_active(self, rule_name: str, active: bool) -> None:
        """Set the active status of a schedule rule."""
        if not self._is_initialized:
            raise RuntimeError("Scheduler not initialized")

        for rule in self._schedule_rules:
            if rule.name == rule_name:
                rule.active = active
                logger.info(f"Set rule '{rule_name}' active status to {active}")
                return

        raise ValueError(f"Schedule rule '{rule_name}' not found")

    def _matches_rule_conditions(
        self, rule: ScheduleRule, conditions: EnvironmentalConditions
    ) -> bool:
        """Check if environmental conditions match a rule's requirements."""
        if not rule.active:
            return False

        # Check time constraints
        current_hour = datetime.now().hour
        if rule.start_hour is not None and current_hour < rule.start_hour:
            return False
        if rule.end_hour is not None and current_hour >= rule.end_hour:
            return False

        # Check light level constraints
        if conditions and conditions.ambient_light_lux is not None:
            if (
                rule.min_light_level is not None
                and conditions.ambient_light_lux < rule.min_light_level
            ):
                return False
            if (
                rule.max_light_level is not None
                and conditions.ambient_light_lux > rule.max_light_level
            ):
                return False

        # Check special conditions
        if rule.conditions:
            if conditions is None:
                # Can't match condition-specific rules without conditions
                return False

            for condition, required_value in rule.conditions.items():
                if (
                    condition == "golden_hour"
                    and getattr(conditions, "is_golden_hour", False) != required_value
                ):
                    return False
                elif (
                    condition == "blue_hour"
                    and getattr(conditions, "is_blue_hour", False) != required_value
                ):
                    return False

        return True

    def _get_matching_rules(self, conditions: EnvironmentalConditions) -> List[ScheduleRule]:
        """Get all rules that match the current environmental conditions."""
        matching_rules = []

        for rule in self._schedule_rules:
            if self._matches_rule_conditions(rule, conditions):
                matching_rules.append(rule)

        return matching_rules

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        return False
    
    def _is_near_golden_hour(self, conditions: EnvironmentalConditions) -> bool:
        """Check if we're within 30 minutes of golden hour (SCHED-002)."""
        if not conditions:
            return False
            
        # Check sun elevation - near golden hour if between 6° and 15° elevation
        if conditions.sun_elevation_deg is not None:
            return 6 <= conditions.sun_elevation_deg <= 15
            
        return False
    
    def _is_sunrise_sunset_window(self, conditions: EnvironmentalConditions) -> bool:
        """Check if we're within 15 minutes of sunrise/sunset (SCHED-002)."""
        if not conditions:
            return False
            
        # Check sun elevation - sunrise/sunset window if between -2° and 2° elevation
        if conditions.sun_elevation_deg is not None:
            return -2 <= conditions.sun_elevation_deg <= 2
            
        return False
    
    def _is_light_changing(self, conditions: EnvironmentalConditions) -> bool:
        """Check if light conditions are rapidly changing (SCHED-002)."""
        if not conditions or len(self._capture_history) < 3:
            return False
            
        # Look at recent light level changes in capture history
        recent_captures = [
            entry for entry in self._capture_history[-10:]
            if entry.get("success") and "conditions" in entry
        ]
        
        if len(recent_captures) < 3:
            return False
            
        # Check if light levels have changed significantly
        light_levels = [
            entry["conditions"].get("ambient_light_lux", 0) 
            for entry in recent_captures
            if entry["conditions"].get("ambient_light_lux") is not None
        ]
        
        if len(light_levels) < 3:
            return False
            
        # Calculate variance in recent light levels
        avg_light = sum(light_levels) / len(light_levels)
        variance = sum((x - avg_light) ** 2 for x in light_levels) / len(light_levels)
        
        # Consider light "changing" if variance is high (>20% of average)
        return variance > (avg_light * 0.2) ** 2
