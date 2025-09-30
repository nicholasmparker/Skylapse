"""
Configuration Management

Simple JSON-based configuration for Skylapse.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Config:
    """Manage application configuration"""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file (relative to backend directory)
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_or_create_default()

    def _load_or_create_default(self) -> Dict[str, Any]:
        """Load config from file or create default if not exists"""
        if self.config_path.exists():
            logger.info(f"Loading config from {self.config_path}")
            with open(self.config_path, "r") as f:
                return json.load(f)
        else:
            logger.warning(
                f"Config file not found at {self.config_path}, creating default"
            )
            default_config = self._get_default_config()
            self.save(default_config)
            return default_config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "location": {
                "latitude": 40.7128,  # New York City (example)
                "longitude": -74.0060,
                "timezone": "America/New_York",
                "name": "New York",
            },
            "schedules": {
                "sunrise": {
                    "enabled": True,
                    "offset_minutes": -30,  # Start 30min before sunrise
                    "duration_minutes": 60,  # Capture for 1 hour
                    "interval_seconds": 30,  # Every 30 seconds
                    "stack_images": True,
                    "stack_count": 5,
                },
                "daytime": {
                    "enabled": True,
                    "start_time": "09:00",
                    "end_time": "15:00",
                    "interval_seconds": 300,  # Every 5 minutes
                    "stack_images": False,
                },
                "sunset": {
                    "enabled": True,
                    "offset_minutes": -30,  # Start 30min before sunset
                    "duration_minutes": 60,
                    "interval_seconds": 30,
                    "stack_images": True,
                    "stack_count": 5,
                },
            },
            "pi": {
                "host": os.getenv("PI_HOST", "helios.local"),
                "port": int(os.getenv("PI_PORT", "8080")),
                "timeout_seconds": 10,
            },
            "storage": {
                "images_dir": "data/images",
                "videos_dir": "data/videos",
                "max_days_to_keep": 7,  # Delete images older than 7 days
            },
            "processing": {
                "video_fps": 24,
                "video_codec": "libx264",
                "video_quality": "23",  # Lower = better quality
            },
        }

    def save(self, config: Dict[str, Any] = None):
        """
        Save configuration to file.

        Args:
            config: Config dict to save (defaults to current config)
        """
        if config is not None:
            self.config = config

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

        logger.info(f"Configuration saved to {self.config_path}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Configuration key (e.g., "location.latitude")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set a configuration value using dot notation.

        Args:
            key: Configuration key (e.g., "location.latitude")
            value: Value to set
        """
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        self.save()
        logger.info(f"Configuration updated: {key} = {value}")

    def get_location(self) -> Dict[str, Any]:
        """Get location configuration"""
        return self.config["location"]

    def get_schedule(self, schedule_type: str) -> Dict[str, Any]:
        """Get schedule configuration for a specific type"""
        return self.config["schedules"].get(schedule_type, {})

    def get_pi_config(self) -> Dict[str, Any]:
        """Get Raspberry Pi configuration"""
        return self.config["pi"]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = Config("test_config.json")

    print("\n=== Configuration Test ===")
    print(f"\nLocation: {config.get_location()}")
    print(f"\nSunrise schedule: {config.get_schedule('sunrise')}")
    print(f"\nPi host: {config.get('pi.host')}")

    # Test setting a value
    config.set("location.name", "San Francisco")
    print(f"\nUpdated location name: {config.get('location.name')}")

    # Clean up test file
    import os

    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
        print("\nTest config file cleaned up")
