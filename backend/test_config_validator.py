"""
Comprehensive test suite for config_validator.py

Tests all validation logic with edge cases and error conditions.
Target: 75%+ code coverage
"""

import json
import tempfile
from pathlib import Path

import pytest
from config_validator import ConfigValidationError, ConfigValidator


class TestConfigValidator:
    """Test suite for ConfigValidator class."""

    @pytest.fixture
    def valid_config(self):
        """Fixture providing a valid configuration."""
        return {
            "location": {"latitude": 39.7392, "longitude": -104.9903, "timezone": "America/Denver"},
            "schedules": {
                "sunrise": {
                    "enabled": True,
                    "type": "solar_relative",
                    "anchor": "sunrise",
                    "offset_minutes": -30,
                    "duration_minutes": 120,
                    "interval_seconds": 60,
                },
                "daytime": {
                    "enabled": True,
                    "type": "time_of_day",
                    "start_time": "09:00",
                    "end_time": "15:00",
                    "interval_seconds": 300,
                },
            },
            "pi": {"host": "192.168.0.124", "port": 8080, "timeout_seconds": 30},
            "storage": {
                "images_dir": "/data/images",
                "videos_dir": "/data/videos",
                "max_days_to_keep": 7,
            },
            "processing": {"video_fps": 30, "video_codec": "libx264", "video_quality": "23"},
        }

    @pytest.fixture
    def temp_config_file(self, valid_config):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_config, f)
            return f.name

    def test_valid_config_passes(self, temp_config_file):
        """Test Case 1: Valid configuration passes validation."""
        validator = ConfigValidator(temp_config_file)
        config = validator.validate()

        assert config is not None
        assert validator.errors == []
        Path(temp_config_file).unlink()

    def test_missing_config_file(self):
        """Test Case 2: Missing config file raises error."""
        validator = ConfigValidator("nonexistent.json")

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "not found" in str(exc.value)

    def test_invalid_json(self):
        """Test Case 3: Invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json content")
            temp_path = f.name

        validator = ConfigValidator(temp_path)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "Invalid JSON" in str(exc.value)
        Path(temp_path).unlink()

    def test_missing_location_section(self, valid_config, temp_config_file):
        """Test Case 4: Missing location section."""
        config = valid_config.copy()
        del config["location"]

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "Missing 'location' section" in str(exc.value)
        Path(temp_config_file).unlink()

    def test_invalid_latitude(self, valid_config, temp_config_file):
        """Test Case 5: Invalid latitude values."""
        test_cases = [
            (-91, "must be -90 to 90"),
            (91, "must be -90 to 90"),
            ("not a number", "must be -90 to 90"),
        ]

        for lat_value, expected_error in test_cases:
            config = valid_config.copy()
            config["location"]["latitude"] = lat_value

            with open(temp_config_file, "w") as f:
                json.dump(config, f)

            validator = ConfigValidator(temp_config_file)

            with pytest.raises(ConfigValidationError) as exc:
                validator.validate()

            assert expected_error in str(exc.value)

        Path(temp_config_file).unlink()

    def test_invalid_longitude(self, valid_config, temp_config_file):
        """Test Case 6: Invalid longitude values."""
        test_cases = [
            (-181, "must be -180 to 180"),
            (181, "must be -180 to 180"),
        ]

        for lon_value, expected_error in test_cases:
            config = valid_config.copy()
            config["location"]["longitude"] = lon_value

            with open(temp_config_file, "w") as f:
                json.dump(config, f)

            validator = ConfigValidator(temp_config_file)

            with pytest.raises(ConfigValidationError) as exc:
                validator.validate()

            assert expected_error in str(exc.value)

        Path(temp_config_file).unlink()

    def test_invalid_timezone(self, valid_config, temp_config_file):
        """Test Case 7: Invalid timezone values."""
        test_cases = [
            ("America/FakeCity", "not in IANA database"),
            ("UTC+5", "not in IANA database"),
            (123, "must be string"),
        ]

        for tz_value, expected_error in test_cases:
            config = valid_config.copy()
            config["location"]["timezone"] = tz_value

            with open(temp_config_file, "w") as f:
                json.dump(config, f)

            validator = ConfigValidator(temp_config_file)

            with pytest.raises(ConfigValidationError) as exc:
                validator.validate()

            assert expected_error in str(exc.value)

        Path(temp_config_file).unlink()

    def test_valid_timezones(self, valid_config, temp_config_file):
        """Test Case 8: Valid timezone values."""
        valid_timezones = [
            "America/Denver",
            "UTC",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]

        for tz in valid_timezones:
            config = valid_config.copy()
            config["location"]["timezone"] = tz

            with open(temp_config_file, "w") as f:
                json.dump(config, f)

            validator = ConfigValidator(temp_config_file)
            result = validator.validate()

            assert result is not None
            assert validator.errors == []

        Path(temp_config_file).unlink()

    def test_invalid_schedule_type(self, valid_config, temp_config_file):
        """Test Case 9: Invalid schedule type."""
        config = valid_config.copy()
        config["schedules"]["test"] = {"enabled": True, "type": "invalid_type"}

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "invalid type" in str(exc.value)
        Path(temp_config_file).unlink()

    def test_solar_schedule_validation(self, valid_config, temp_config_file):
        """Test Case 10: Solar schedule validation."""
        # Test missing anchor
        config = valid_config.copy()
        config["schedules"]["test"] = {
            "enabled": True,
            "type": "solar_relative",
            "duration_minutes": 120,
        }

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "missing 'anchor'" in str(exc.value)

        # Test invalid anchor
        config["schedules"]["test"]["anchor"] = "invalid_anchor"

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "invalid anchor" in str(exc.value)

        # Test missing duration
        config["schedules"]["test"]["anchor"] = "sunrise"
        del config["schedules"]["test"]["duration_minutes"]

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "missing 'duration_minutes'" in str(exc.value)

        Path(temp_config_file).unlink()

    def test_time_schedule_validation(self, valid_config, temp_config_file):
        """Test Case 11: Time schedule validation (format and semantic)."""
        # Test invalid time format
        config = valid_config.copy()
        config["schedules"]["test"] = {
            "enabled": True,
            "type": "time_of_day",
            "start_time": "9:00",  # Missing leading zero
            "end_time": "17:00",
        }

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "invalid format" in str(exc.value)

        # Test start_time >= end_time (semantic validation)
        config["schedules"]["test"]["start_time"] = "17:00"
        config["schedules"]["test"]["end_time"] = "09:00"

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be before" in str(exc.value)

        Path(temp_config_file).unlink()

    def test_interval_validation(self, valid_config, temp_config_file):
        """Test Case 12: Interval validation."""
        # Test negative interval
        config = valid_config.copy()
        config["schedules"]["sunrise"]["interval_seconds"] = -10

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be positive" in str(exc.value)

        # Test zero interval
        config["schedules"]["sunrise"]["interval_seconds"] = 0

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be positive" in str(exc.value)

        Path(temp_config_file).unlink()

    def test_stacking_validation(self, valid_config, temp_config_file):
        """Test Case 13: Image stacking validation."""
        config = valid_config.copy()
        config["schedules"]["sunrise"]["stack_images"] = True
        config["schedules"]["sunrise"]["stack_count"] = 1  # Too few

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be >= 2" in str(exc.value)
        Path(temp_config_file).unlink()

    def test_pi_validation(self, valid_config, temp_config_file):
        """Test Case 14: Pi configuration validation."""
        # Test invalid port
        config = valid_config.copy()
        config["pi"]["port"] = 70000  # Out of range

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be between 1-65535" in str(exc.value)

        # Test missing host
        del config["pi"]["host"]
        config["pi"]["port"] = 8080  # Fix port

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "Missing pi.host" in str(exc.value)

        Path(temp_config_file).unlink()

    def test_storage_validation(self, valid_config, temp_config_file):
        """Test Case 15: Storage configuration validation."""
        config = valid_config.copy()
        config["storage"]["max_days_to_keep"] = 0

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be >= 1" in str(exc.value)
        Path(temp_config_file).unlink()

    def test_processing_validation(self, valid_config, temp_config_file):
        """Test Case 16: Processing configuration validation."""
        # Test invalid FPS
        config = valid_config.copy()
        config["processing"]["video_fps"] = 150  # Too high

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be 1-120" in str(exc.value)

        # Test invalid quality
        config["processing"]["video_fps"] = 30  # Fix FPS
        config["processing"]["video_quality"] = "100"  # Out of range

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)

        with pytest.raises(ConfigValidationError) as exc:
            validator.validate()

        assert "must be 0-51" in str(exc.value)

        Path(temp_config_file).unlink()

    def test_warnings_do_not_block_validation(self, valid_config, temp_config_file):
        """Test that warnings are logged but don't block validation."""
        config = valid_config.copy()
        config["schedules"]["sunrise"]["interval_seconds"] = 0.3  # Very short, triggers warning

        with open(temp_config_file, "w") as f:
            json.dump(config, f)

        validator = ConfigValidator(temp_config_file)
        result = validator.validate()

        # Should succeed despite warning
        assert result is not None
        assert len(validator.warnings) > 0
        assert "very short interval" in validator.warnings[0]

        Path(temp_config_file).unlink()

    def test_all_valid_solar_anchors(self, valid_config, temp_config_file):
        """Test all valid solar anchor values."""
        valid_anchors = ["sunrise", "sunset", "civil_dawn", "civil_dusk", "noon"]

        for anchor in valid_anchors:
            config = valid_config.copy()
            config["schedules"]["test"] = {
                "enabled": True,
                "type": "solar_relative",
                "anchor": anchor,
                "duration_minutes": 60,
            }

            with open(temp_config_file, "w") as f:
                json.dump(config, f)

            validator = ConfigValidator(temp_config_file)
            result = validator.validate()

            assert result is not None
            assert validator.errors == []

        Path(temp_config_file).unlink()

    def test_edge_case_coordinates(self, valid_config, temp_config_file):
        """Test edge case coordinate values."""
        edge_cases = [
            (90, 180),  # Maximum valid
            (-90, -180),  # Minimum valid
            (0, 0),  # Null Island
        ]

        for lat, lon in edge_cases:
            config = valid_config.copy()
            config["location"]["latitude"] = lat
            config["location"]["longitude"] = lon

            with open(temp_config_file, "w") as f:
                json.dump(config, f)

            validator = ConfigValidator(temp_config_file)
            result = validator.validate()

            assert result is not None
            assert validator.errors == []

        Path(temp_config_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
