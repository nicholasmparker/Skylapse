"""
Solar Time Calculations

Uses astral library to calculate sunrise and sunset times for scheduling.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from zoneinfo import ZoneInfo
from astral import LocationInfo
from astral.sun import sun
import logging

logger = logging.getLogger(__name__)


class SolarCalculator:
    """Calculate sunrise and sunset times for a given location"""

    def __init__(self, latitude: float, longitude: float, timezone: str = "UTC"):
        """
        Initialize solar calculator with location.

        Args:
            latitude: Latitude in degrees (-90 to 90)
            longitude: Longitude in degrees (-180 to 180)
            timezone: IANA timezone name (e.g., "America/New_York")
        """
        self.location = LocationInfo(
            name="Skylapse",
            region="",
            timezone=timezone,
            latitude=latitude,
            longitude=longitude,
        )
        self.timezone = ZoneInfo(timezone)
        self._cache: Dict[str, Dict[str, datetime]] = {}
        logger.info(
            f"Solar calculator initialized for lat={latitude}, lon={longitude}, tz={timezone}"
        )

    def get_sun_times(self, date: Optional[datetime] = None) -> Dict[str, datetime]:
        """
        Get sunrise and sunset times for a given date.

        Args:
            date: Date to calculate for (defaults to today in local timezone)

        Returns:
            Dictionary with 'sunrise' and 'sunset' datetime objects (timezone-aware)
        """
        if date is None:
            date = datetime.now(self.timezone)
        elif date.tzinfo is None:
            # Make timezone-aware if naive
            date = date.replace(tzinfo=self.timezone)

        # Cache by date string (one entry per day)
        date_key = date.strftime("%Y-%m-%d")

        if date_key not in self._cache:
            sun_times = sun(self.location.observer, date=date.date())

            self._cache[date_key] = {
                "sunrise": sun_times["sunrise"],
                "sunset": sun_times["sunset"],
                "dawn": sun_times["dawn"],
                "dusk": sun_times["dusk"],
            }

            logger.info(
                f"Calculated sun times for {date_key}: "
                f"sunrise={sun_times['sunrise'].strftime('%H:%M')}, "
                f"sunset={sun_times['sunset'].strftime('%H:%M')}"
            )

        return self._cache[date_key]

    def get_sunrise(self, date: Optional[datetime] = None) -> datetime:
        """Get sunrise time for date"""
        return self.get_sun_times(date)["sunrise"]

    def get_sunset(self, date: Optional[datetime] = None) -> datetime:
        """Get sunset time for date"""
        return self.get_sun_times(date)["sunset"]

    def is_daytime(self, time: Optional[datetime] = None) -> bool:
        """
        Check if given time is during daytime (between sunrise and sunset).

        Args:
            time: Time to check (defaults to now in local timezone)

        Returns:
            True if during daytime, False otherwise
        """
        if time is None:
            time = datetime.now(self.timezone)
        elif time.tzinfo is None:
            time = time.replace(tzinfo=self.timezone)

        sun_times = self.get_sun_times(time)
        return sun_times["sunrise"] <= time <= sun_times["sunset"]

    def get_schedule_window(
        self, schedule_type: str, date: Optional[datetime] = None
    ) -> Dict[str, datetime]:
        """
        Get the capture window for a schedule type.

        Args:
            schedule_type: "sunrise" or "sunset"
            date: Date to calculate for (defaults to today)

        Returns:
            Dictionary with 'start' and 'end' datetime objects
        """
        sun_times = self.get_sun_times(date)

        if schedule_type == "sunrise":
            # Start 30min before sunrise, run for 60min
            start = sun_times["sunrise"] - timedelta(minutes=30)
            end = sun_times["sunrise"] + timedelta(minutes=30)
        elif schedule_type == "sunset":
            # Start 30min before sunset, run for 60min
            start = sun_times["sunset"] - timedelta(minutes=30)
            end = sun_times["sunset"] + timedelta(minutes=30)
        else:
            raise ValueError(f"Unknown solar schedule type: {schedule_type}")

        return {"start": start, "end": end}

    def clear_cache(self):
        """Clear the date cache (call daily to prevent memory leak)"""
        self._cache.clear()
        logger.debug("Solar time cache cleared")


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: New York City
    calc = SolarCalculator(
        latitude=40.7128, longitude=-74.0060, timezone="America/New_York"
    )

    print("\n=== Solar Calculator Test ===")
    print(f"Location: {calc.location.latitude}, {calc.location.longitude}")
    print(f"Timezone: {calc.location.timezone}")

    sun_times = calc.get_sun_times()
    print(f"\nToday's sun times:")
    print(f"  Sunrise: {sun_times['sunrise'].strftime('%I:%M %p')}")
    print(f"  Sunset:  {sun_times['sunset'].strftime('%I:%M %p')}")

    sunrise_window = calc.get_schedule_window("sunrise")
    print(f"\nSunrise capture window:")
    print(f"  Start: {sunrise_window['start'].strftime('%I:%M %p')}")
    print(f"  End:   {sunrise_window['end'].strftime('%I:%M %p')}")

    sunset_window = calc.get_schedule_window("sunset")
    print(f"\nSunset capture window:")
    print(f"  Start: {sunset_window['start'].strftime('%I:%M %p')}")
    print(f"  End:   {sunset_window['end'].strftime('%I:%M %p')}")

    print(f"\nIs it daytime now? {calc.is_daytime()}")
