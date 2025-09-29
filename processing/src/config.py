"""
Simple configuration module for processing service.
Temporary fix for missing config imports.
"""

import os
from typing import Any, Dict


def get_processing_config() -> Dict[str, Any]:
    """Get processing service configuration."""
    return {
        "service": {
            "name": "processing",
            "port": int(os.getenv("PROCESSING_PORT", 8081)),
            "host": os.getenv("PROCESSING_HOST", "0.0.0.0"),
            "debug": os.getenv("SKYLAPSE_ENV", "production") == "development",
        },
        "processing": {
            "max_workers": int(os.getenv("PROCESSING_MAX_WORKERS", 4)),
            "timeout": int(os.getenv("PROCESSING_TIMEOUT", 300)),
            "temp_dir": os.getenv("PROCESSING_TEMP_DIR", "/tmp/skylapse_processing"),
        },
        "storage": {
            "input_dir": os.getenv("STORAGE_INPUT_DIR", "/tmp/skylapse_transfers/incoming"),
            "output_dir": os.getenv("STORAGE_OUTPUT_DIR", "/opt/skylapse/output"),
            "temp_dir": os.getenv("STORAGE_TEMP_DIR", "/tmp/skylapse_processing"),
        },
    }


def get_shared_config() -> Dict[str, Any]:
    """Get shared configuration."""
    return {
        "environment": os.getenv("SKYLAPSE_ENV", "production"),
        "log_level": os.getenv("SKYLAPSE_LOG_LEVEL", "INFO"),
        "services": {
            "capture": {
                "host": os.getenv("CAPTURE_HOST", "helios.local"),
                "port": int(os.getenv("CAPTURE_PORT", 8080)),
            },
            "processing": {
                "host": os.getenv("PROCESSING_HOST", "localhost"),
                "port": int(os.getenv("PROCESSING_PORT", 8081)),
            },
            "backend": {
                "host": os.getenv("BACKEND_HOST", "localhost"),
                "port": int(os.getenv("BACKEND_PORT", 8082)),
            },
        },
    }
