"""
Smart Exposure Calculator

Calculates optimal camera settings based on time of day and schedule type.
"""

from datetime import datetime, timedelta
from typing import Dict
import logging

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
        self, schedule_type: str, current_time: datetime = None
    ) -> Dict[str, any]:
        """
        Calculate camera settings for current conditions.

        Args:
            schedule_type: "sunrise", "daytime", or "sunset"
            current_time: Current time (defaults to now)

        Returns:
            Dictionary with ISO, shutter_speed, and exposure_compensation
        """
        if current_time is None:
            current_time = datetime.now()

        if schedule_type == "sunrise":
            return self._calculate_sunrise_settings(current_time)
        elif schedule_type == "daytime":
            return self._calculate_daytime_settings()
        elif schedule_type == "sunset":
            return self._calculate_sunset_settings(current_time)
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

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

    def format_for_pi(self, settings: Dict[str, any]) -> Dict[str, any]:
        """
        Format settings for Pi API request.

        Args:
            settings: Settings from calculate_settings()

        Returns:
            Dictionary ready to send to Pi /capture endpoint
        """
        return {
            "iso": settings["iso"],
            "shutter_speed": settings["shutter_speed"],
            "exposure_compensation": settings["exposure_compensation"],
        }


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    calc = ExposureCalculator()

    print("\n=== Exposure Calculator Test ===")

    # Test each schedule type
    for schedule_type in ["sunrise", "daytime", "sunset"]:
        print(f"\n{schedule_type.upper()} Settings:")
        settings = calc.calculate_settings(schedule_type)
        for key, value in settings.items():
            print(f"  {key}: {value}")

    # Test with solar calculator
    print("\n=== With Solar Calculator ===")
    from solar import SolarCalculator

    solar_calc = SolarCalculator(40.7128, -74.0060, "America/New_York")
    calc_with_solar = ExposureCalculator(solar_calc)

    # Simulate different times relative to sunrise
    sunrise_time = solar_calc.get_sunrise()

    print(f"\nSunrise time: {sunrise_time.strftime('%I:%M %p')}")

    test_times = [
        ("30 min before", sunrise_time - timedelta(minutes=30)),
        ("15 min before", sunrise_time - timedelta(minutes=15)),
        ("At sunrise", sunrise_time),
        ("15 min after", sunrise_time + timedelta(minutes=15)),
    ]

    for label, test_time in test_times:
        print(f"\n{label}:")
        settings = calc_with_solar.calculate_settings("sunrise", test_time)
        print(f"  ISO: {settings['iso']}")
        print(f"  Shutter: {settings['shutter_speed']}")
        print(f"  EV: {settings['exposure_compensation']:+.1f}")
