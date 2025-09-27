"""Tests for configuration management."""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.config_manager import CameraConfigManager, SystemConfigManager


class TestCameraConfigManager:
    """Test cases for CameraConfigManager."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with sample files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "cameras"
            config_dir.mkdir(parents=True)

            # Create sample camera config
            sample_config = {
                "sensor": {"model": "Test Camera", "base_iso": 100, "max_iso": 800},
                "optical": {"focal_length_mm": 4.28},
                "capabilities": ["AUTOFOCUS", "HDR_BRACKETING"],
            }

            with open(config_dir / "test_camera.yaml", "w") as f:
                yaml.dump(sample_config, f)

            yield str(config_dir.parent)

    def test_config_loading(self, temp_config_dir):
        """Test configuration loading from files."""
        manager = CameraConfigManager(temp_config_dir + "/cameras")

        # Should have loaded the test camera config
        assert "test_camera" in manager.configs
        config = manager.configs["test_camera"]
        assert config["sensor"]["model"] == "Test Camera"

    def test_get_config_for_camera(self, temp_config_dir):
        """Test getting configuration for specific camera."""
        manager = CameraConfigManager(temp_config_dir + "/cameras")

        # Get existing config
        config = manager.get_config_for_camera("test_camera")
        assert config["sensor"]["model"] == "Test Camera"

        # Get non-existent config (should return default)
        default_config = manager.get_config_for_camera("nonexistent_camera")
        assert "sensor" in default_config
        assert "optical" in default_config

    def test_config_merging(self, temp_config_dir):
        """Test that configs are properly merged with defaults."""
        manager = CameraConfigManager(temp_config_dir + "/cameras")

        config = manager.get_config_for_camera("test_camera")

        # Should have fields from both sample config and defaults
        assert config["sensor"]["model"] == "Test Camera"  # From sample
        assert "processing" in config  # From defaults
        assert "performance" in config  # From defaults

    def test_update_config(self, temp_config_dir):
        """Test updating and saving configuration."""
        manager = CameraConfigManager(temp_config_dir + "/cameras")

        updates = {
            "sensor": {"max_iso": 1600},  # Update existing
            "custom_setting": "test_value",  # Add new
        }

        manager.update_config("test_camera", updates)

        # Verify updates were applied
        config = manager.get_config_for_camera("test_camera")
        assert config["sensor"]["max_iso"] == 1600
        assert config["custom_setting"] == "test_value"

        # Original values should be preserved
        assert config["sensor"]["model"] == "Test Camera"


class TestSystemConfigManager:
    """Test cases for SystemConfigManager."""

    @pytest.fixture
    def temp_system_config(self):
        """Create temporary system config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "system.yaml"

            sample_config = {
                "storage": {"capture_buffer_path": "/custom/path", "max_buffer_size_gb": 200},
                "network": {"processing_service_host": "custom-host"},
            }

            with open(config_file, "w") as f:
                yaml.dump(sample_config, f)

            yield str(config_file)

    def test_system_config_loading(self, temp_system_config):
        """Test system configuration loading."""
        manager = SystemConfigManager(temp_system_config)

        # Should have custom values
        assert manager.get("storage.capture_buffer_path") == "/custom/path"
        assert manager.get("storage.max_buffer_size_gb") == 200
        assert manager.get("network.processing_service_host") == "custom-host"

        # Should have default values for unspecified settings
        assert manager.get("network.processing_service_port") == 8081

    def test_dot_notation_access(self, temp_system_config):
        """Test accessing config values with dot notation."""
        manager = SystemConfigManager(temp_system_config)

        # Existing values
        assert manager.get("storage.capture_buffer_path") == "/custom/path"
        assert manager.get("network.processing_service_host") == "custom-host"

        # Non-existent values with defaults
        assert manager.get("nonexistent.key") is None
        assert manager.get("nonexistent.key", "default") == "default"

    def test_config_update(self, temp_system_config):
        """Test updating system configuration."""
        manager = SystemConfigManager(temp_system_config)

        updates = {
            "storage": {"max_buffer_size_gb": 500},  # Update existing
            "new_section": {"new_setting": "new_value"},  # Add new
        }

        manager.update(updates)

        # Verify updates
        assert manager.get("storage.max_buffer_size_gb") == 500
        assert manager.get("new_section.new_setting") == "new_value"

        # Original values should be preserved
        assert manager.get("storage.capture_buffer_path") == "/custom/path"

    def test_config_reload(self, temp_system_config):
        """Test configuration reloading."""
        manager = SystemConfigManager(temp_system_config)

        original_value = manager.get("storage.max_buffer_size_gb")

        # Modify file externally
        with open(temp_system_config, "r") as f:
            config_data = yaml.safe_load(f)

        config_data["storage"]["max_buffer_size_gb"] = 999

        with open(temp_system_config, "w") as f:
            yaml.dump(config_data, f)

        # Reload and verify change
        manager.reload()
        assert manager.get("storage.max_buffer_size_gb") == 999

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        import os

        # Should not raise exception and use defaults
        manager = SystemConfigManager("/nonexistent/config.yaml")

        # Should have default values (accounting for development environment)
        skylapse_env = os.getenv("SKYLAPSE_ENV", "production").lower()
        expected_buffer_path = (
            "/tmp/skylapse/buffer" if skylapse_env == "development" else "/opt/skylapse/buffer"
        )

        assert manager.get("storage.capture_buffer_path") == expected_buffer_path
        assert manager.get("network.processing_service_port") == 8081
