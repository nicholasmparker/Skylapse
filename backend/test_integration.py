"""
Minimal Integration Tests for Skylapse Backend

Quick smoke tests to verify core functionality.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from exposure import ExposureCalculator
from schedule_types import ScheduleType
from solar import SolarCalculator


class TestConfig:
    """Test configuration management"""

    def test_config_loads_default(self, tmp_path):
        """Test config creates default when file doesn't exist"""
        config_file = tmp_path / "test_config.json"
        config = Config(str(config_file))

        assert config.config is not None
        assert "location" in config.config
        assert "schedules" in config.config
        assert "pi" in config.config

    def test_config_atomic_save(self, tmp_path):
        """Test atomic save creates file successfully"""
        config_file = tmp_path / "test_config.json"
        config = Config(str(config_file))

        # Modify and save
        config.set("location.name", "Test Location")

        # Verify file exists and contains correct data
        assert config_file.exists()
        assert config.get("location.name") == "Test Location"

    def test_config_dot_notation(self, tmp_path):
        """Test dot notation get/set"""
        config_file = tmp_path / "test_config.json"
        config = Config(str(config_file))

        # Test get
        assert config.get("pi.host") is not None

        # Test set
        config.set("pi.timeout_seconds", 15)
        assert config.get("pi.timeout_seconds") == 15


class TestSolarCalculator:
    """Test solar calculations"""

    def test_solar_calculator_initializes(self):
        """Test solar calculator creates without error"""
        calc = SolarCalculator(
            latitude=39.7392, longitude=-104.9903, timezone="America/Denver"  # Denver
        )
        assert calc is not None

    def test_get_sun_times(self):
        """Test getting sunrise/sunset times"""
        calc = SolarCalculator(latitude=39.7392, longitude=-104.9903, timezone="America/Denver")

        sun_times = calc.get_sun_times()
        assert "sunrise" in sun_times
        assert "sunset" in sun_times
        assert isinstance(sun_times["sunrise"], datetime)
        assert isinstance(sun_times["sunset"], datetime)

    def test_is_daytime(self):
        """Test daytime detection"""
        calc = SolarCalculator(latitude=39.7392, longitude=-104.9903, timezone="America/Denver")

        # Just verify it doesn't crash
        result = calc.is_daytime()
        assert isinstance(result, bool)


class TestExposureCalculator:
    """Test exposure calculations"""

    def test_exposure_calculator_initializes(self):
        """Test exposure calculator creates without error"""
        calc = ExposureCalculator()
        assert calc is not None

    def test_calculate_daytime_settings(self):
        """Test daytime settings calculation"""
        calc = ExposureCalculator()

        settings = calc.calculate_settings(ScheduleType.DAYTIME, profile="a")

        assert settings is not None
        assert "iso" in settings
        assert "shutter_speed" in settings
        assert "exposure_compensation" in settings
        assert "profile" in settings
        assert settings["profile"] == "a"

    def test_all_profiles(self):
        """Test all 6 profiles work"""
        calc = ExposureCalculator()
        profiles = ["a", "b", "c", "d", "e", "f"]

        for profile in profiles:
            settings = calc.calculate_settings(ScheduleType.DAYTIME, profile=profile)
            assert settings["profile"] == profile
            assert "awb_mode" in settings
            assert "hdr_mode" in settings
            assert "bracket_count" in settings

    def test_profile_f_bracket_settings(self):
        """Test Profile F has correct bracket configuration"""
        calc = ExposureCalculator()

        settings = calc.calculate_settings(ScheduleType.DAYTIME, profile="f")

        assert settings["bracket_count"] == 3
        assert "bracket_ev" in settings
        assert len(settings["bracket_ev"]) == 3
        assert settings["bracket_ev"] == [-1.0, 0.0, 1.0]


class TestScheduleTypes:
    """Test schedule type utilities"""

    def test_solar_schedule_detection(self):
        """Test is_solar correctly identifies solar schedules"""
        assert ScheduleType.is_solar(ScheduleType.SUNRISE) is True
        assert ScheduleType.is_solar(ScheduleType.SUNSET) is True
        assert ScheduleType.is_solar(ScheduleType.DAYTIME) is False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
