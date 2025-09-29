"""
Centralized configuration management for Skylapse services.

Provides type-safe, validated configuration for all services with
environment-specific defaults and service discovery.
"""

from .environment import (
    BackendConfig,
    CaptureConfig,
    FrontendConfig,
    ProcessingConfig,
    SharedConfig,
    get_backend_config,
    get_capture_config,
    get_frontend_config,
    get_processing_config,
    get_shared_config,
    validate_service_discovery,
)

__all__ = [
    "CaptureConfig",
    "ProcessingConfig",
    "BackendConfig",
    "FrontendConfig",
    "SharedConfig",
    "get_capture_config",
    "get_processing_config",
    "get_backend_config",
    "get_frontend_config",
    "get_shared_config",
    "validate_service_discovery",
]
