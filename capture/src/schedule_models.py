"""Data models and validation for schedule management."""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ScheduleStatus(Enum):
    """Schedule status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class CaptureSettings:
    """Capture settings for scheduled captures."""

    preset: Optional[str] = None
    manual: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        if self.preset:
            result["preset"] = self.preset
        if self.manual:
            result["manual"] = self.manual
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaptureSettings":
        """Create from dictionary representation."""
        return cls(preset=data.get("preset"), manual=data.get("manual"))


@dataclass
class ScheduleConditions:
    """Environmental conditions for schedule execution."""

    weather_dependent: bool = False
    min_light_level: float = 0.0
    max_wind_speed: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "weatherDependent": self.weather_dependent,
            "minLightLevel": self.min_light_level,
            "maxWindSpeed": self.max_wind_speed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleConditions":
        """Create from dictionary representation."""
        return cls(
            weather_dependent=data.get("weatherDependent", False),
            min_light_level=data.get("minLightLevel", 0.0),
            max_wind_speed=data.get("maxWindSpeed", 100.0),
        )


@dataclass
class ScheduleRule:
    """Complete schedule rule definition matching frontend expectations."""

    id: str
    name: str
    description: str
    enabled: bool
    start_time: str  # ISO time format (HH:MM)
    end_time: str  # ISO time format (HH:MM)
    interval_minutes: int
    days_of_week: List[int]  # 0=Sunday, 1=Monday, etc.
    capture_settings: CaptureSettings
    conditions: Optional[ScheduleConditions] = None
    next_execution: Optional[str] = None  # ISO datetime
    last_execution: Optional[str] = None  # ISO datetime
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    execution_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "intervalMinutes": self.interval_minutes,
            "daysOfWeek": self.days_of_week,
            "captureSettings": self.capture_settings.to_dict(),
            "conditions": self.conditions.to_dict() if self.conditions else None,
            "nextExecution": self.next_execution,
            "lastExecution": self.last_execution,
            "status": self.status.value,
            "executionCount": self.execution_count,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleRule":
        """Create from dictionary representation."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            start_time=data["startTime"],
            end_time=data["endTime"],
            interval_minutes=data["intervalMinutes"],
            days_of_week=data.get("daysOfWeek", [0, 1, 2, 3, 4, 5, 6]),
            capture_settings=CaptureSettings.from_dict(data.get("captureSettings", {})),
            conditions=(
                ScheduleConditions.from_dict(data["conditions"]) if data.get("conditions") else None
            ),
            next_execution=data.get("nextExecution"),
            last_execution=data.get("lastExecution"),
            status=ScheduleStatus(data.get("status", "active")),
            execution_count=data.get("executionCount", 0),
            created_at=data.get("createdAt", datetime.now().isoformat()),
        )

    def calculate_next_execution(
        self, current_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Calculate the next execution time for this schedule."""
        if not self.enabled or self.status != ScheduleStatus.ACTIVE:
            return None

        if current_time is None:
            current_time = datetime.now()

        # Parse start and end times
        try:
            start_hour, start_minute = map(int, self.start_time.split(":"))
            end_hour, end_minute = map(int, self.end_time.split(":"))
        except ValueError:
            logger.error(
                f"Invalid time format in schedule {self.id}: {self.start_time}, {self.end_time}"
            )
            return None

        # Find next valid day
        for days_ahead in range(8):  # Check up to a week ahead
            check_date = current_time + timedelta(days=days_ahead)
            weekday = check_date.weekday()
            # Convert Python weekday (0=Monday) to our format (0=Sunday)
            our_weekday = (weekday + 1) % 7

            if our_weekday not in self.days_of_week:
                continue

            # Calculate next execution on this day
            if days_ahead == 0:
                # Today - check if we're still within the time window
                start_today = current_time.replace(
                    hour=start_hour, minute=start_minute, second=0, microsecond=0
                )
                end_today = current_time.replace(
                    hour=end_hour, minute=end_minute, second=0, microsecond=0
                )

                # Handle overnight schedules (end_time < start_time)
                if end_today < start_today:
                    end_today += timedelta(days=1)

                if current_time < start_today:
                    # Before start time today
                    return start_today
                elif current_time <= end_today:
                    # Within execution window - calculate next interval
                    if self.last_execution:
                        try:
                            last_exec = datetime.fromisoformat(
                                self.last_execution.replace("Z", "+00:00")
                            )
                            next_exec = last_exec + timedelta(minutes=self.interval_minutes)
                            if next_exec <= end_today and next_exec > current_time:
                                return next_exec
                        except ValueError:
                            pass

                    # Default to next interval from now
                    next_exec = current_time + timedelta(minutes=self.interval_minutes)
                    if next_exec <= end_today:
                        return next_exec
            else:
                # Future day
                next_start = check_date.replace(
                    hour=start_hour, minute=start_minute, second=0, microsecond=0
                )
                return next_start

        return None

    def update_execution_status(
        self, success: bool = True, execution_time: Optional[datetime] = None
    ) -> None:
        """Update execution status and calculate next execution."""
        if execution_time is None:
            execution_time = datetime.now()

        self.last_execution = execution_time.isoformat()
        self.execution_count += 1

        if success:
            self.status = ScheduleStatus.ACTIVE
        else:
            # Don't automatically set to error - let the caller decide
            pass

        # Calculate next execution
        next_exec = self.calculate_next_execution(execution_time)
        self.next_execution = next_exec.isoformat() if next_exec else None


class ScheduleValidationError(Exception):
    """Exception raised for schedule validation errors."""

    pass


def validate_schedule_data(data: Dict[str, Any]) -> None:
    """Validate schedule data before creating ScheduleRule."""
    required_fields = ["name", "startTime", "endTime", "intervalMinutes"]

    for field in required_fields:
        if field not in data or data[field] is None:
            raise ScheduleValidationError(f"Missing required field: {field}")

    # Validate name
    if not isinstance(data["name"], str) or len(data["name"].strip()) == 0:
        raise ScheduleValidationError("Schedule name must be a non-empty string")

    # Validate time format
    try:
        start_parts = data["startTime"].split(":")
        end_parts = data["endTime"].split(":")

        if len(start_parts) != 2 or len(end_parts) != 2:
            raise ScheduleValidationError("Time format must be HH:MM")

        start_hour, start_minute = int(start_parts[0]), int(start_parts[1])
        end_hour, end_minute = int(end_parts[0]), int(end_parts[1])

        if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59):
            raise ScheduleValidationError("Invalid start time")
        if not (0 <= end_hour <= 23 and 0 <= end_minute <= 59):
            raise ScheduleValidationError("Invalid end time")

    except (ValueError, AttributeError):
        raise ScheduleValidationError("Invalid time format - use HH:MM")

    # Validate interval
    if not isinstance(data["intervalMinutes"], int) or data["intervalMinutes"] < 1:
        raise ScheduleValidationError("Interval must be a positive integer (minutes)")

    # Validate days of week
    if "daysOfWeek" in data:
        days = data["daysOfWeek"]
        if not isinstance(days, list) or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
            raise ScheduleValidationError("daysOfWeek must be a list of integers 0-6 (0=Sunday)")

    # Validate capture settings
    capture_settings = data.get("captureSettings", {})
    if not isinstance(capture_settings, dict):
        raise ScheduleValidationError("captureSettings must be an object")

    preset = capture_settings.get("preset")
    manual = capture_settings.get("manual")

    if preset and manual:
        raise ScheduleValidationError("Cannot specify both preset and manual capture settings")

    if manual:
        if not isinstance(manual, dict):
            raise ScheduleValidationError("manual capture settings must be an object")

        # Validate manual settings
        required_manual = ["iso", "exposureTime", "hdrBracketing", "quality"]
        for field in required_manual:
            if field not in manual:
                raise ScheduleValidationError(f"Missing required manual setting: {field}")

    # Validate conditions if present
    conditions = data.get("conditions")
    if conditions:
        if not isinstance(conditions, dict):
            raise ScheduleValidationError("conditions must be an object")

        weather_dependent = conditions.get("weatherDependent")
        if weather_dependent is not None and not isinstance(weather_dependent, bool):
            raise ScheduleValidationError("weatherDependent must be a boolean")

        min_light = conditions.get("minLightLevel")
        if min_light is not None and (not isinstance(min_light, (int, float)) or min_light < 0):
            raise ScheduleValidationError("minLightLevel must be a non-negative number")

        max_wind = conditions.get("maxWindSpeed")
        if max_wind is not None and (not isinstance(max_wind, (int, float)) or max_wind < 0):
            raise ScheduleValidationError("maxWindSpeed must be a non-negative number")
