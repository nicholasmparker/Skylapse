"""Tests for environmental sensing functionality."""

import pytest
import pytest_asyncio
import asyncio
import math

from src.environmental_sensing import EnvironmentalSensor
from src.camera_types import EnvironmentalConditions


class TestEnvironmentalSensor:
    """Test cases for EnvironmentalSensor class."""

    @pytest_asyncio.fixture
    async def sensor(self):
        """Create and initialize environmental sensor."""
        sensor = EnvironmentalSensor()
        await sensor.initialize()
        yield sensor
        await sensor.shutdown()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test sensor initialization and shutdown."""
        sensor = EnvironmentalSensor()
        assert not sensor._is_initialized

        await sensor.initialize()
        assert sensor._is_initialized

        await sensor.shutdown()
        assert not sensor._is_initialized

    @pytest.mark.asyncio
    async def test_get_current_conditions(self, sensor):
        """Test getting current environmental conditions."""
        conditions = await sensor.get_current_conditions()

        assert isinstance(conditions, EnvironmentalConditions)

        # Check that we have some astronomical data
        assert conditions.sun_elevation_deg is not None
        assert conditions.sun_azimuth_deg is not None
        assert isinstance(conditions.is_golden_hour, bool)
        assert isinstance(conditions.is_blue_hour, bool)

        # Check that we have simulated sensor data
        assert conditions.ambient_light_lux is not None
        assert conditions.color_temperature_k is not None
        assert conditions.temperature_c is not None

    @pytest.mark.asyncio
    async def test_astronomical_calculations(self, sensor):
        """Test astronomical data calculations."""
        conditions = await sensor.get_current_conditions()

        # Sun elevation should be reasonable (-90 to 90 degrees)
        assert -90 <= conditions.sun_elevation_deg <= 90

        # Sun azimuth should be 0-360 degrees
        assert 0 <= conditions.sun_azimuth_deg <= 360

        # Golden hour and blue hour should be mutually exclusive
        if conditions.is_golden_hour:
            assert not conditions.is_blue_hour
        if conditions.is_blue_hour:
            assert not conditions.is_golden_hour

    @pytest.mark.asyncio
    async def test_simulated_weather_data(self, sensor):
        """Test simulated weather data stub."""
        conditions = await sensor.get_current_conditions()

        # Should have reasonable weather data
        assert 0 <= conditions.cloud_cover_pct <= 100
        assert conditions.visibility_km > 0
        assert 0 <= conditions.precipitation_prob_pct <= 100
        assert conditions.wind_speed_kph >= 0

    @pytest.mark.asyncio
    async def test_simulated_sensor_data(self, sensor):
        """Test simulated hardware sensor data."""
        conditions = await sensor.get_current_conditions()

        # Should have reasonable sensor data
        assert conditions.ambient_light_lux >= 0
        assert conditions.color_temperature_k > 1000  # Reasonable color temp range
        assert conditions.color_temperature_k < 10000
        assert conditions.temperature_c is not None

    @pytest.mark.asyncio
    async def test_conditions_caching(self, sensor):
        """Test that conditions are cached and updated appropriately."""
        # Get conditions twice quickly
        conditions1 = await sensor.get_current_conditions()
        conditions2 = await sensor.get_current_conditions()

        # Should be the same cached values
        assert conditions1.sun_elevation_deg == conditions2.sun_elevation_deg
        assert conditions1.ambient_light_lux == conditions2.ambient_light_lux

    @pytest.mark.asyncio
    async def test_force_update(self, sensor):
        """Test forced update of conditions."""
        # Get initial conditions
        conditions1 = await sensor.get_current_conditions()

        # Force update
        conditions2 = await sensor.force_update()

        # Should be EnvironmentalConditions objects
        assert isinstance(conditions1, EnvironmentalConditions)
        assert isinstance(conditions2, EnvironmentalConditions)

    @pytest.mark.asyncio
    async def test_get_status(self, sensor):
        """Test sensor status retrieval."""
        status = await sensor.get_status()

        assert isinstance(status, dict)
        assert status['initialized'] is True
        assert 'last_update_time' in status
        assert 'data_sources' in status

        # Check data sources
        data_sources = status['data_sources']
        assert data_sources['astronomical'] == 'active'
        assert data_sources['weather_api'] == 'stub'
        assert data_sources['hardware_sensors'] == 'stub'

        # Should have current conditions
        if 'current_conditions' in status:
            conditions = status['current_conditions']
            assert 'sun_elevation_deg' in conditions
            assert 'is_golden_hour' in conditions
            assert 'ambient_light_lux' in conditions

    @pytest.mark.asyncio
    async def test_uninitialized_behavior(self):
        """Test behavior when sensor is not initialized."""
        sensor = EnvironmentalSensor()

        # Should return empty conditions
        conditions = await sensor.get_current_conditions()
        assert isinstance(conditions, EnvironmentalConditions)

        # Most fields should be None or default values
        assert conditions.sun_elevation_deg is None
        assert conditions.ambient_light_lux is None

    @pytest.mark.asyncio
    async def test_golden_hour_detection(self):
        """Test golden hour detection logic."""
        # This test verifies the logic, though exact values depend on time of day
        sensor = EnvironmentalSensor()
        await sensor.initialize()

        try:
            conditions = await sensor.get_current_conditions()

            # Golden hour is when sun elevation is between -6 and +6 degrees
            if conditions.is_golden_hour:
                assert -6 <= conditions.sun_elevation_deg <= 6

            # Blue hour is when sun elevation is between -12 and -6 degrees
            if conditions.is_blue_hour:
                assert -12 <= conditions.sun_elevation_deg <= -6

        finally:
            await sensor.shutdown()

    @pytest.mark.asyncio
    async def test_time_based_light_simulation(self):
        """Test that simulated light levels change based on time."""
        sensor = EnvironmentalSensor()
        await sensor.initialize()

        try:
            conditions = await sensor.get_current_conditions()

            # Light levels should be positive
            assert conditions.ambient_light_lux > 0

            # Color temperature should be reasonable
            assert 2000 <= conditions.color_temperature_k <= 10000

        finally:
            await sensor.shutdown()


class TestEnvironmentalConditions:
    """Test cases for EnvironmentalConditions data class."""

    def test_environmental_conditions_creation(self):
        """Test creating environmental conditions object."""
        conditions = EnvironmentalConditions(
            cloud_cover_pct=50.0,
            visibility_km=10.0,
            sun_elevation_deg=30.0,
            is_golden_hour=False,
            ambient_light_lux=8000.0,
            temperature_c=15.0
        )

        assert conditions.cloud_cover_pct == 50.0
        assert conditions.visibility_km == 10.0
        assert conditions.sun_elevation_deg == 30.0
        assert conditions.is_golden_hour is False
        assert conditions.ambient_light_lux == 8000.0
        assert conditions.temperature_c == 15.0

    def test_environmental_conditions_defaults(self):
        """Test default values for environmental conditions."""
        conditions = EnvironmentalConditions()

        # All fields should default to None or False
        assert conditions.cloud_cover_pct is None
        assert conditions.visibility_km is None
        assert conditions.sun_elevation_deg is None
        assert conditions.is_golden_hour is False
        assert conditions.is_blue_hour is False
        assert conditions.ambient_light_lux is None
        assert conditions.temperature_c is None