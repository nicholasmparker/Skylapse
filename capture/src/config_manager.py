"""Configuration management for camera and system settings."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CameraConfigManager:
    """Manages camera-specific configuration files."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager with config directory."""
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config" / "cameras"

        self.config_dir = Path(config_dir)
        self.configs: Dict[str, Dict[str, Any]] = {}
        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """Load all camera configuration files from the config directory."""
        self.configs = {}

        if not self.config_dir.exists():
            logger.warning(f"Camera config directory does not exist: {self.config_dir}")
            return

        for config_file in self.config_dir.glob("*.yaml"):
            try:
                camera_model = config_file.stem
                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)

                self.configs[camera_model] = config
                logger.info(f"Loaded config for camera: {camera_model}")

            except Exception as e:
                logger.error(f"Failed to load config {config_file}: {e}")

    def get_config_for_camera(self, camera_model: str) -> Dict[str, Any]:
        """Get configuration for a specific camera model."""
        config = self.configs.get(camera_model)

        if config is None:
            logger.warning(f"No config found for {camera_model}, using default")
            return self._get_default_config()

        # Merge with default config to ensure all required fields are present
        default_config = self._get_default_config()
        merged_config = self._deep_merge(default_config, config)

        return merged_config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default camera configuration."""
        return {
            "sensor": {
                "bayer_pattern": "RGGB",
                "base_iso": 100,
                "max_iso": 800,
                "iso_invariance_point": 800,
            },
            "optical": {
                "focal_length_mm": 4.28,
                "hyperfocal_distance_mm": 1830,
                "focus_range_mm": [100.0, float("inf")],
            },
            "processing": {
                "demosaic_algorithm": "DCB",
                "noise_reduction_strength": 0.2,
                "color_correction_enabled": True,
            },
            "capture": {
                "default_quality": 95,
                "default_format": "JPEG",
                "enable_raw_capture": False,
                "capture_timeout_ms": 5000,
            },
            "performance": {
                "capture_buffer_size": 4,
                "max_capture_latency_ms": 50,
                "focus_timeout_ms": 2000,
            },
        }

    def _deep_merge(
        self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override_dict taking precedence."""
        result = base_dict.copy()

        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def update_config(self, camera_model: str, updates: Dict[str, Any]) -> None:
        """Update configuration for a camera model and save to file."""
        if camera_model not in self.configs:
            self.configs[camera_model] = self._get_default_config()

        self.configs[camera_model] = self._deep_merge(self.configs[camera_model], updates)
        self._save_config(camera_model)

    def _save_config(self, camera_model: str) -> None:
        """Save camera configuration to file."""
        config_file = self.config_dir / f"{camera_model}.yaml"

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            with open(config_file, "w") as f:
                yaml.safe_dump(self.configs[camera_model], f, indent=2)

            logger.info(f"Saved config for {camera_model}")

        except Exception as e:
            logger.error(f"Failed to save config for {camera_model}: {e}")

    def list_camera_configs(self) -> list[str]:
        """List all available camera configurations."""
        return list(self.configs.keys())

    def reload_configs(self) -> None:
        """Reload all configuration files from disk."""
        self._load_all_configs()


class SystemConfigManager:
    """Manages system-wide configuration settings."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize system configuration manager."""
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "system" / "system.yaml"

        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load system configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"System config file does not exist: {self.config_file}")
                self.config = {}

            # Merge with default system config
            default_config = self._get_default_system_config()
            self.config = self._deep_merge(default_config, self.config)

        except Exception as e:
            logger.error(f"Failed to load system config: {e}")
            self.config = self._get_default_system_config()

    def _get_default_system_config(self) -> Dict[str, Any]:
        """Get default system configuration."""
        import os

        # Check environment for development settings
        skylapse_env = os.getenv("SKYLAPSE_ENV", "production").lower()
        is_development = skylapse_env == "development"

        base_config = {
            "storage": {
                "capture_buffer_path": (
                    "/opt/skylapse/buffer" if not is_development else "/tmp/skylapse/buffer"
                ),
                "buffer_retention_hours": 48,
                "max_buffer_size_gb": 100,
                "cleanup_interval_hours": 6,
            },
            "network": {
                "processing_service_host": "localhost",
                "processing_service_port": 8081,
                "transfer_retry_attempts": 3,
                "transfer_timeout_seconds": 30,
            },
            "capture": {
                "service_port": 8080,
                "max_concurrent_captures": 1,
                "health_check_interval_seconds": 30,
            },
            "monitoring": {
                "metrics_enabled": True,
                "log_level": "DEBUG" if is_development else "INFO",
                "performance_tracking": True,
            },
            "development": {
                "mock_camera_enabled": is_development,
                "debug_logging": is_development,
                "development_mode": is_development,
            },
        }

        return base_config

    def _deep_merge(
        self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base_dict.copy()

        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default=None):
        """Get a configuration value using dot notation (e.g., 'storage.buffer_retention_hours')."""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def update(self, updates: Dict[str, Any]) -> None:
        """Update system configuration and save to file."""
        self.config = self._deep_merge(self.config, updates)
        self._save_config()

    def _save_config(self) -> None:
        """Save system configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w") as f:
                yaml.safe_dump(self.config, f, indent=2)

            logger.info("Saved system configuration")

        except Exception as e:
            logger.error(f"Failed to save system config: {e}")

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
