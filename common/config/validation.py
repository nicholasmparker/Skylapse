"""
Configuration validation utilities for Skylapse services.

Provides validation functions to ensure configuration consistency
and service health across all components.
"""

import logging
import os
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .environment import (
    get_backend_config,
    get_capture_config,
    get_frontend_config,
    get_processing_config,
    get_shared_config,
    is_development,
    is_production,
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration validation error."""

    pass


def validate_required_environment_variables() -> List[str]:
    """
    Validate that all required environment variables are set.
    Returns list of missing variables.
    """
    missing = []

    # Required in production
    if is_production():
        required_vars = [
            "SKYLAPSE_JWT_SECRET",
            "POSTGRES_PASSWORD",
            "LOCATION_LAT",
            "LOCATION_LON",
            "TIMEZONE",
        ]

        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

    # Required in development
    elif is_development():
        # JWT secret is auto-generated if missing
        # Other vars have defaults
        pass

    return missing


def validate_directory_permissions() -> Dict[str, bool]:
    """
    Validate that all required directories exist and are writable.
    Returns dict of directory -> accessible status.
    """
    results = {}

    try:
        shared_config = get_shared_config()
        capture_config = get_capture_config()
        processing_config = get_processing_config()
        backend_config = get_backend_config()

        # Test directories
        directories_to_check = [
            ("shared_data", shared_config.data_path),
            ("capture_buffer", capture_config.buffer_path),
            ("capture_storage", capture_config.storage.data_path),
            ("processing_temp", processing_config.temp_dir),
            ("processing_output", processing_config.output_dir),
            ("backend_storage", backend_config.storage.data_path),
        ]

        for name, path in directories_to_check:
            try:
                path_obj = Path(path)

                # Create directory if it doesn't exist
                path_obj.mkdir(parents=True, exist_ok=True)

                # Test write access
                test_file = path_obj / ".skylapse_write_test"
                test_file.write_text("test")
                test_file.unlink()

                results[name] = True
                logger.debug(f"Directory {name} ({path}) is accessible")

            except Exception as e:
                results[name] = False
                logger.error(f"Directory {name} ({path}) is not accessible: {e}")

    except Exception as e:
        logger.error(f"Failed to validate directories: {e}")
        results["validation_failed"] = True

    return results


def validate_port_availability() -> Dict[str, bool]:
    """
    Check if required ports are available for binding.
    Returns dict of service -> port_available status.
    """
    results = {}

    try:
        capture_config = get_capture_config()
        processing_config = get_processing_config()
        backend_config = get_backend_config()

        ports_to_check = [
            ("capture", capture_config.port),
            ("processing", processing_config.port),
            ("backend", backend_config.port),
        ]

        for service, port in ports_to_check:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(("localhost", port))

                    if result == 0:
                        # Port is in use
                        results[service] = False
                        logger.warning(f"Port {port} for {service} is already in use")
                    else:
                        # Port is available
                        results[service] = True
                        logger.debug(f"Port {port} for {service} is available")

            except Exception as e:
                # Assume available on error
                results[service] = True
                logger.debug(f"Could not check port {port} for {service}: {e}")

    except Exception as e:
        logger.error(f"Failed to validate ports: {e}")
        results["validation_failed"] = True

    return results


def validate_service_configuration_consistency() -> List[str]:
    """
    Validate that service configurations are consistent with each other.
    Returns list of consistency issues.
    """
    issues = []

    try:
        capture_config = get_capture_config()
        processing_config = get_processing_config()
        backend_config = get_backend_config()
        frontend_config = get_frontend_config()

        # Check service discovery consistency

        # Capture -> Processing
        if (capture_config.processing_host, capture_config.processing_port) != (
            processing_config.host,
            processing_config.port,
        ):
            issues.append(
                f"Capture service configured to connect to processing at "
                f"{capture_config.processing_host}:{capture_config.processing_port}, "
                f"but processing service runs at {processing_config.host}:{processing_config.port}"
            )

        # Processing -> Backend
        if (processing_config.backend_host, processing_config.backend_port) != (
            backend_config.host,
            backend_config.port,
        ):
            issues.append(
                f"Processing service configured to connect to backend at "
                f"{processing_config.backend_host}:{processing_config.backend_port}, "
                f"but backend service runs at {backend_config.host}:{backend_config.port}"
            )

        # Frontend -> Services
        expected_api_url = f"http://{processing_config.host}:{processing_config.port}"
        expected_ws_url = f"ws://{backend_config.host}:{backend_config.port}"

        # For development, these should match Docker port mappings
        if is_development():
            expected_api_url = "http://localhost:8081"
            expected_ws_url = "ws://localhost:8082"

        if frontend_config.api_url != expected_api_url:
            issues.append(
                f"Frontend API URL ({frontend_config.api_url}) doesn't match "
                f"processing service configuration ({expected_api_url})"
            )

        if frontend_config.ws_url != expected_ws_url:
            issues.append(
                f"Frontend WebSocket URL ({frontend_config.ws_url}) doesn't match "
                f"backend service configuration ({expected_ws_url})"
            )

    except Exception as e:
        issues.append(f"Failed to validate service configuration: {e}")

    return issues


def validate_security_configuration() -> List[str]:
    """
    Validate security-related configuration.
    Returns list of security issues.
    """
    issues = []

    try:
        backend_config = get_backend_config()

        # JWT secret validation
        if backend_config.security:
            jwt_secret = backend_config.security.jwt_secret

            if len(jwt_secret) < 32:
                issues.append(f"JWT secret is too short ({len(jwt_secret)} chars, minimum 32)")

            if is_production() and "development" in jwt_secret.lower():
                issues.append("Production environment is using development JWT secret")

            if jwt_secret == "your_development_secret_minimum_32_characters_long":
                issues.append("Using default development JWT secret - change for security")

        # CORS configuration
        if is_production() and backend_config.security.cors_origins == ["*"]:
            issues.append("Production environment allows all CORS origins - security risk")

    except Exception as e:
        issues.append(f"Failed to validate security configuration: {e}")

    return issues


def run_full_configuration_validation() -> Dict[str, any]:
    """
    Run complete configuration validation suite.
    Returns comprehensive validation results.
    """
    logger.info("Running full configuration validation...")

    results = {
        "environment": {
            "current": os.getenv("SKYLAPSE_ENV", "development"),
            "is_development": is_development(),
            "is_production": is_production(),
        },
        "missing_variables": validate_required_environment_variables(),
        "directory_permissions": validate_directory_permissions(),
        "port_availability": validate_port_availability(),
        "consistency_issues": validate_service_configuration_consistency(),
        "security_issues": validate_security_configuration(),
    }

    # Overall health score
    total_checks = 0
    passed_checks = 0

    # Environment variables
    total_checks += 1
    if not results["missing_variables"]:
        passed_checks += 1

    # Directory permissions
    for status in results["directory_permissions"].values():
        total_checks += 1
        if status:
            passed_checks += 1

    # Port availability
    for status in results["port_availability"].values():
        total_checks += 1
        if status:
            passed_checks += 1

    # Consistency
    total_checks += 1
    if not results["consistency_issues"]:
        passed_checks += 1

    # Security
    total_checks += 1
    if not results["security_issues"]:
        passed_checks += 1

    results["health_score"] = {
        "passed": passed_checks,
        "total": total_checks,
        "percentage": round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 0,
    }

    # Summary
    if results["health_score"]["percentage"] >= 90:
        results["status"] = "HEALTHY"
    elif results["health_score"]["percentage"] >= 70:
        results["status"] = "WARNING"
    else:
        results["status"] = "CRITICAL"

    logger.info(
        f"Configuration validation complete: {results['status']} "
        f"({results['health_score']['percentage']}% passed)"
    )

    return results


def print_configuration_summary():
    """Print a human-readable configuration summary."""
    try:
        shared = get_shared_config()
        capture = get_capture_config()
        processing = get_processing_config()
        backend = get_backend_config()
        frontend = get_frontend_config()

        print("\n" + "=" * 60)
        print("SKYLAPSE CONFIGURATION SUMMARY")
        print("=" * 60)

        print(f"\nEnvironment: {shared.environment.upper()}")
        print(f"Version: {shared.version}")
        print(
            f"Location: {shared.location.latitude}, {shared.location.longitude} ({shared.location.timezone})"
        )

        print("\nService Endpoints:")
        print(f"  Capture Service:    {capture.host}:{capture.port}")
        print(f"  Processing Service: {processing.host}:{processing.port}")
        print(f"  Backend Service:    {backend.host}:{backend.port}")

        print("\nFrontend URLs:")
        print(f"  API URL:     {frontend.api_url}")
        print(f"  WebSocket:   {frontend.ws_url}")
        print(f"  Capture URL: {frontend.capture_url}")

        print("\nStorage Paths:")
        print(f"  Shared Data:     {shared.data_path}")
        print(f"  Capture Buffer:  {capture.buffer_path}")
        print(f"  Processing Temp: {processing.temp_dir}")
        print(f"  Processing Out:  {processing.output_dir}")

        print("\nSecurity:")
        print(f"  JWT Secret: {'✓ Configured' if backend.security.jwt_secret else '✗ Missing'}")
        print(f"  CORS Origins: {len(backend.security.cors_origins)} configured")

        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Failed to print configuration summary: {e}")
