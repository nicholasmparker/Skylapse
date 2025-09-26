"""Configuration management for the processing service."""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProcessingConfigManager:
    """Manages configuration for the processing service."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize processing configuration manager."""
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "processing.yaml"

        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file does not exist: {self.config_file}")
                self.config = {}

            # Merge with default configuration
            default_config = self._get_default_config()
            self.config = self._deep_merge(default_config, self.config)

        except Exception as e:
            logger.error(f"Failed to load processing config: {e}")
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default processing service configuration."""
        return {
            'api': {
                'port': 8081,
                'cors_enabled': True,
                'max_request_size_mb': 100
            },
            'processing': {
                'max_concurrent_jobs': 4,
                'job_timeout_seconds': 3600,
                'temp_dir': '/tmp/skylapse_processing',
                'output_dir': '/opt/skylapse/output'
            },
            'image': {
                'max_resolution': [4656, 3496],
                'supported_formats': ['JPEG', 'PNG', 'TIFF'],
                'quality_levels': {
                    'high': 95,
                    'medium': 85,
                    'low': 75
                }
            },
            'video': {
                'output_formats': ['1080p', '4k'],
                'framerate': 24.0,
                'encoding': {
                    'codec': 'h264',
                    'quality': 'high',
                    'gpu_acceleration': False
                }
            },
            'storage': {
                'cleanup_interval_hours': 24,
                'temp_retention_hours': 6,
                'output_retention_days': 30
            },
            'transfer': {
                'incoming_dir': '/tmp/skylapse_transfers/incoming',
                'processing_dir': '/tmp/skylapse_transfers/processing',
                'completed_dir': '/tmp/skylapse_transfers/completed'
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }

    def _deep_merge(self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base_dict.copy()

        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default=None):
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration and save to file."""
        self.config = self._deep_merge(self.config, updates)
        self._save_config()

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w') as f:
                yaml.safe_dump(self.config, f, indent=2)

            logger.info("Processing configuration saved")

        except Exception as e:
            logger.error(f"Failed to save processing config: {e}")

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()