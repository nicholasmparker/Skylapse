"""
Schedule Type Definitions

Central definition of all schedule types to eliminate magic strings.
"""

from enum import Enum


class ScheduleType(str, Enum):
    """
    Valid schedule types for timelapse capture.

    Using str Enum so values can be serialized to JSON and compared with strings.
    """

    SUNRISE = "sunrise"
    DAYTIME = "daytime"
    SUNSET = "sunset"

    @classmethod
    def solar_schedules(cls) -> list["ScheduleType"]:
        """Return schedules that depend on solar calculations."""
        return [cls.SUNRISE, cls.SUNSET]

    @classmethod
    def is_solar(cls, schedule_name: str) -> bool:
        """Check if schedule type is solar-based."""
        return schedule_name in [s.value for s in cls.solar_schedules()]

    @classmethod
    def all_values(cls) -> list[str]:
        """Return all schedule type values as strings."""
        return [s.value for s in cls]
