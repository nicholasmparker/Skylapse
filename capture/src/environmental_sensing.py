"""Environmental sensing system for adaptive capture control."""

import logging
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from .camera_types import EnvironmentalConditions

logger = logging.getLogger(__name__)


class EnvironmentalSensor:
    """
    Environmental sensing system that provides context for adaptive capture control.

    This is a foundational implementation for Sprint 1 with stubs for future enhancement.
    Phase 2 will add real weather API integration and hardware sensor support.
    """

    def __init__(self, latitude: float = 40.7589, longitude: float = -111.8883, timezone_offset: float = -7.0):
        """Initialize environmental sensor system.
        
        Args:
            latitude: Location latitude in degrees (default: Park City, UT)
            longitude: Location longitude in degrees (default: Park City, UT) 
            timezone_offset: Timezone offset from UTC in hours (default: -7 for MST)
        """
        self._is_initialized = False
        self._last_update_time: Optional[float] = None
        self._cached_conditions: Optional[EnvironmentalConditions] = None
        self._update_interval_seconds = 300  # Update every 5 minutes
        
        # Location configuration for accurate astronomical calculations
        self._latitude = latitude
        self._longitude = longitude
        self._timezone_offset = timezone_offset
        
        logger.info(f"Environmental sensor configured for location: {latitude:.4f}°N, {longitude:.4f}°W")

    async def initialize(self) -> None:
        """Initialize environmental sensing system."""
        logger.info("Initializing environmental sensor")

        # For Sprint 1, we'll use basic astronomical calculations
        # Future phases will add weather API integration
        await self._update_astronomical_data()

        self._is_initialized = True
        logger.info("Environmental sensor initialized")

    async def shutdown(self) -> None:
        """Shutdown environmental sensor."""
        logger.info("Shutting down environmental sensor")
        self._is_initialized = False

    async def get_current_conditions(self) -> EnvironmentalConditions:
        """Get current environmental conditions."""
        if not self._is_initialized:
            return EnvironmentalConditions()

        current_time = time.time()

        # Update cached conditions if stale
        if (
            self._last_update_time is None
            or current_time - self._last_update_time > self._update_interval_seconds
        ):
            await self._update_conditions()

        return self._cached_conditions or EnvironmentalConditions()

    async def _update_conditions(self) -> None:
        """Update all environmental conditions."""
        current_time = time.time()

        # Get astronomical data
        astronomical_data = await self._update_astronomical_data()

        # Stub for weather data (Phase 2 implementation)
        weather_data = await self._get_weather_data_stub()

        # Stub for sensor data (Phase 2 implementation)
        sensor_data = await self._get_sensor_data_stub()

        # Combine all data sources
        self._cached_conditions = EnvironmentalConditions(
            # Weather data (stubs for now)
            cloud_cover_pct=weather_data.get("cloud_cover_pct"),
            visibility_km=weather_data.get("visibility_km"),
            precipitation_prob_pct=weather_data.get("precipitation_prob_pct"),
            wind_speed_kph=weather_data.get("wind_speed_kph"),
            # Astronomical data (real calculations)
            sun_elevation_deg=astronomical_data["sun_elevation_deg"],
            sun_azimuth_deg=astronomical_data["sun_azimuth_deg"],
            is_golden_hour=astronomical_data["is_golden_hour"],
            is_blue_hour=astronomical_data["is_blue_hour"],
            # Sensor data (stubs for now)
            ambient_light_lux=sensor_data.get("ambient_light_lux"),
            color_temperature_k=sensor_data.get("color_temperature_k"),
            temperature_c=sensor_data.get("temperature_c"),
            # Scene analysis (future implementation)
            scene_brightness=None,
            focus_quality_score=None,
        )

        self._last_update_time = current_time
        logger.debug("Updated environmental conditions")

    async def _update_astronomical_data(self) -> Dict[str, Any]:
        """Calculate accurate astronomical data for mountain photography."""
        now = datetime.now()
        
        # Calculate sun position using configured location
        sun_elevation, sun_azimuth = self._calculate_sun_position(now)
        
        # Calculate sunrise/sunset times for today
        sunrise_time, sunset_time = self._calculate_sunrise_sunset(now.date())
        
        # Determine lighting conditions with mountain photography specifics
        is_golden_hour = self._is_golden_hour(sun_elevation, sunrise_time, sunset_time, now)
        is_blue_hour = self._is_blue_hour(sun_elevation)
        
        # Calculate next golden hour window for scheduling
        next_golden_start, next_golden_end = self._calculate_next_golden_hour(now)
        
        return {
            "sun_elevation_deg": sun_elevation,
            "sun_azimuth_deg": sun_azimuth,
            "is_golden_hour": is_golden_hour,
            "is_blue_hour": is_blue_hour,
            "sunrise_time": sunrise_time.isoformat() if sunrise_time else None,
            "sunset_time": sunset_time.isoformat() if sunset_time else None,
            "next_golden_start": next_golden_start.isoformat() if next_golden_start else None,
            "next_golden_end": next_golden_end.isoformat() if next_golden_end else None,
        }
    
    def _calculate_sun_position(self, dt: datetime) -> Tuple[float, float]:
        """Calculate accurate sun elevation and azimuth using astronomical algorithms."""
        # Use configured location instead of hardcoded values
        day_of_year = dt.timetuple().tm_yday
        
        # Solar declination (more accurate)
        declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
        
        # Local solar time accounting for longitude
        decimal_hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        local_solar_time = decimal_hour - (self._longitude / 15.0) + self._timezone_offset
        hour_angle = (local_solar_time - 12) * 15  # Degrees from solar noon
        
        # Calculate elevation using configured latitude
        lat_rad = math.radians(self._latitude)
        dec_rad = math.radians(declination)
        hour_rad = math.radians(hour_angle)
        
        sin_elevation = (math.sin(lat_rad) * math.sin(dec_rad) + 
                        math.cos(lat_rad) * math.cos(dec_rad) * math.cos(hour_rad))
        elevation = math.degrees(math.asin(max(-1, min(1, sin_elevation))))
        
        # Calculate azimuth
        cos_azimuth = ((math.sin(dec_rad) - math.sin(lat_rad) * math.sin(math.radians(elevation))) /
                      (math.cos(lat_rad) * math.cos(math.radians(elevation))))
        cos_azimuth = max(-1, min(1, cos_azimuth))
        
        azimuth = math.degrees(math.acos(cos_azimuth))
        if math.sin(hour_rad) > 0:
            azimuth = 360 - azimuth
            
        return elevation, azimuth
    
    def _calculate_sunrise_sunset(self, date) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Calculate sunrise and sunset times for given date using configured location."""
        day_of_year = date.timetuple().tm_yday
        
        # Solar declination
        declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
        
        # Hour angle for sunrise/sunset (sun at horizon)
        lat_rad = math.radians(self._latitude)
        dec_rad = math.radians(declination)
        
        try:
            cos_hour_angle = -math.tan(lat_rad) * math.tan(dec_rad)
            if abs(cos_hour_angle) > 1:
                # Polar day or polar night
                return None, None
                
            hour_angle = math.degrees(math.acos(cos_hour_angle))
            
            # Calculate times in local solar time
            solar_noon = 12 - (self._longitude / 15.0)
            sunrise_lst = solar_noon - (hour_angle / 15.0)
            sunset_lst = solar_noon + (hour_angle / 15.0)
            
            # Convert to local time
            sunrise_local = sunrise_lst + self._timezone_offset
            sunset_local = sunset_lst + self._timezone_offset
            
            # Create datetime objects
            sunrise_dt = None
            sunset_dt = None
            
            if 0 <= sunrise_local <= 24:
                sunrise_dt = datetime.combine(date, datetime.min.time()) + \
                           timedelta(hours=sunrise_local)
                           
            if 0 <= sunset_local <= 24:
                sunset_dt = datetime.combine(date, datetime.min.time()) + \
                          timedelta(hours=sunset_local)
                          
            return sunrise_dt, sunset_dt
            
        except (ValueError, OverflowError):
            return None, None
    
    def _is_golden_hour(self, sun_elevation: float, sunrise_time: Optional[datetime], 
                       sunset_time: Optional[datetime], current_time: datetime) -> bool:
        """Determine if current time is during golden hour for mountain photography."""
        # Golden hour: sun elevation between -6° and 6° (civil twilight to low sun)
        elevation_golden = -6 <= sun_elevation <= 6
        
        # Enhanced golden hour detection within 1 hour of sunrise/sunset
        if sunrise_time and sunset_time:
            sunrise_window = abs((current_time - sunrise_time).total_seconds()) <= 3600
            sunset_window = abs((current_time - sunset_time).total_seconds()) <= 3600
            time_based_golden = sunrise_window or sunset_window
            
            return elevation_golden and time_based_golden
        
        return elevation_golden
    
    def _is_blue_hour(self, sun_elevation: float) -> bool:
        """Determine if current time is during blue hour."""
        return -12 <= sun_elevation <= -6
    
    def _calculate_next_golden_hour(self, current_time: datetime) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Calculate the next golden hour window for adaptive scheduling."""
        today = current_time.date()
        tomorrow = today + timedelta(days=1)
        
        # Get today's sunrise/sunset
        today_sunrise, today_sunset = self._calculate_sunrise_sunset(today)
        
        # Check morning golden hour (30 min before to 30 min after sunrise)
        if today_sunrise:
            morning_start = today_sunrise - timedelta(minutes=30)
            morning_end = today_sunrise + timedelta(minutes=30)
            
            if current_time < morning_end:
                return morning_start, morning_end
        
        # Check evening golden hour (30 min before to 30 min after sunset)
        if today_sunset:
            evening_start = today_sunset - timedelta(minutes=30)
            evening_end = today_sunset + timedelta(minutes=30)
            
            if current_time < evening_start:
                return evening_start, evening_end
        
        # Return tomorrow's morning golden hour
        tomorrow_sunrise, _ = self._calculate_sunrise_sunset(tomorrow)
        if tomorrow_sunrise:
            morning_start = tomorrow_sunrise - timedelta(minutes=30)
            morning_end = tomorrow_sunrise + timedelta(minutes=30)
            return morning_start, morning_end
            
        return None, None

    async def _get_weather_data_stub(self) -> Dict[str, Any]:
        """
        Stub for weather data retrieval.
        Phase 2 will implement real weather API integration.
        """
        # Return simulated/default weather data for now
        return {
            "cloud_cover_pct": 30.0,  # Partly cloudy
            "visibility_km": 15.0,  # Good visibility
            "precipitation_prob_pct": 20.0,  # Low chance of rain
            "wind_speed_kph": 10.0,  # Light breeze
        }

    async def _get_sensor_data_stub(self) -> Dict[str, Any]:
        """
        Stub for hardware sensor data.
        Phase 2 will implement real sensor integration.
        """
        # Simulate sensor readings based on time of day
        now = datetime.now()
        hour = now.hour

        # Simulate light levels based on time
        if 6 <= hour <= 18:  # Daytime
            ambient_light_lux = 10000 + (5000 * math.sin(math.radians((hour - 6) * 15)))
        elif 18 < hour <= 20 or 5 <= hour < 6:  # Twilight
            ambient_light_lux = 100
        else:  # Night
            ambient_light_lux = 1

        # Simulate color temperature
        if 6 <= hour <= 10:  # Morning
            color_temperature_k = 3500
        elif 10 < hour <= 16:  # Midday
            color_temperature_k = 5500
        elif 16 < hour <= 20:  # Evening
            color_temperature_k = 2800
        else:  # Night
            color_temperature_k = 2200

        # Simulate temperature (very basic)
        base_temp = 15.0  # Base mountain temperature
        daily_variation = 5 * math.sin(math.radians((hour - 6) * 15))
        temperature_c = base_temp + daily_variation

        return {
            "ambient_light_lux": ambient_light_lux,
            "color_temperature_k": color_temperature_k,
            "temperature_c": temperature_c,
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get environmental sensor system status."""
        if not self._is_initialized:
            return {"initialized": False}

        status = {
            "initialized": True,
            "last_update_time": self._last_update_time,
            "update_interval_seconds": self._update_interval_seconds,
            "data_sources": {
                "astronomical": "active",
                "weather_api": "stub",  # Will be 'active' in Phase 2
                "hardware_sensors": "stub",  # Will be 'active' in Phase 2
            },
        }

        # Include current conditions if available
        if self._cached_conditions:
            status["current_conditions"] = {
                "sun_elevation_deg": self._cached_conditions.sun_elevation_deg,
                "is_golden_hour": self._cached_conditions.is_golden_hour,
                "is_blue_hour": self._cached_conditions.is_blue_hour,
                "ambient_light_lux": self._cached_conditions.ambient_light_lux,
                "temperature_c": self._cached_conditions.temperature_c,
            }

        return status

    async def force_update(self) -> EnvironmentalConditions:
        """Force an immediate update of environmental conditions."""
        await self._update_conditions()
        return self._cached_conditions or EnvironmentalConditions()

    # Future methods for Phase 2 implementation

    async def _setup_weather_api(self, api_key: str) -> None:
        """Setup weather API integration (Phase 2)."""
        # TODO: Implement OpenWeatherMap or similar API integration
        pass

    async def _setup_hardware_sensors(self) -> None:
        """Setup hardware sensor integration (Phase 2)."""
        # TODO: Implement I2C sensor integration for:
        # - Light sensor (TSL2561 or similar)
        # - Temperature/humidity sensor (SHT30 or similar)
        # - Atmospheric pressure sensor (BMP280 or similar)
        pass

    async def _update_weather_from_api(self) -> Dict[str, Any]:
        """Update weather data from external API (Phase 2)."""
        # TODO: Implement real weather API calls
        return {}

    async def _read_hardware_sensors(self) -> Dict[str, Any]:
        """Read data from hardware sensors (Phase 2)."""
        # TODO: Implement I2C sensor reading
        return {}

    def _is_data_stale(self, max_age_seconds: int = 900) -> bool:
        """Check if cached data is stale (older than max_age_seconds)."""
        if self._last_update_time is None:
            return True

        return time.time() - self._last_update_time > max_age_seconds
