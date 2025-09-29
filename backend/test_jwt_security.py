"""
Test cases for JWT secret security validation.

Tests the critical security fix for Issue #5 - JWT Secret Hardcoded.
Ensures JWT secrets are properly loaded from environment variables with validation.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src directory to Python path for importing
sys.path.insert(0, str(Path(__file__).parent / "src"))


class TestJWTSecretSecurity:
    """Test JWT secret loading and validation security measures."""

    def setup_method(self):
        """Clear any existing JWT secret environment variables before each test."""
        env_vars = ["SKYLAPSE_JWT_SECRET", "JWT_SECRET", "REALTIME_JWT_SECRET"]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    def test_jwt_secret_missing_all_env_vars(self):
        """Test that missing JWT secret raises appropriate error."""
        # Clear all JWT-related environment variables
        env_patch = patch.dict(os.environ, {}, clear=True)

        with env_patch:
            # Import should fail when no JWT secret is available
            with pytest.raises(ValueError) as exc_info:
                # Force reload of the module to trigger secret loading
                if "realtime_server" in sys.modules:
                    del sys.modules["realtime_server"]
                import realtime_server  # noqa: F401

            error_message = str(exc_info.value)
            assert "JWT secret not configured" in error_message
            assert "SKYLAPSE_JWT_SECRET" in error_message
            assert "JWT_SECRET" in error_message
            assert "REALTIME_JWT_SECRET" in error_message

    def test_jwt_secret_too_short(self):
        """Test that short JWT secret raises security error."""
        short_secret = "short_secret"  # Only 12 characters

        with patch.dict(os.environ, {"SKYLAPSE_JWT_SECRET": short_secret}):
            with pytest.raises(ValueError) as exc_info:
                # Force reload of the module
                if "realtime_server" in sys.modules:
                    del sys.modules["realtime_server"]
                import realtime_server  # noqa: F401

            error_message = str(exc_info.value)
            assert "must be at least 32 characters long" in error_message
            assert f"Current length: {len(short_secret)}" in error_message

    def test_jwt_secret_minimum_length_valid(self):
        """Test that 32-character JWT secret is accepted."""
        valid_secret = "a" * 32  # Exactly 32 characters

        with patch.dict(os.environ, {"SKYLAPSE_JWT_SECRET": valid_secret}):
            # Force reload of the module
            if "realtime_server" in sys.modules:
                del sys.modules["realtime_server"]

            # Should not raise an exception
            import realtime_server

            assert realtime_server.JWT_SECRET == valid_secret

    def test_jwt_secret_long_valid(self):
        """Test that long JWT secret (>32 chars) is accepted."""
        long_secret = "this_is_a_very_secure_jwt_secret_with_more_than_32_characters"

        with patch.dict(os.environ, {"SKYLAPSE_JWT_SECRET": long_secret}):
            # Force reload of the module
            if "realtime_server" in sys.modules:
                del sys.modules["realtime_server"]

            import realtime_server

            assert realtime_server.JWT_SECRET == long_secret

    def test_jwt_secret_priority_skylapse_jwt_secret(self):
        """Test that SKYLAPSE_JWT_SECRET takes priority over other env vars."""
        primary_secret = "primary_skylapse_jwt_secret_32_chars"
        secondary_secret = "secondary_jwt_secret_32_characters"
        tertiary_secret = "tertiary_realtime_jwt_32_chars_long"

        env_vars = {
            "SKYLAPSE_JWT_SECRET": primary_secret,
            "JWT_SECRET": secondary_secret,
            "REALTIME_JWT_SECRET": tertiary_secret,
        }

        with patch.dict(os.environ, env_vars):
            # Force reload of the module
            if "realtime_server" in sys.modules:
                del sys.modules["realtime_server"]

            import realtime_server

            assert realtime_server.JWT_SECRET == primary_secret

    def test_jwt_secret_fallback_jwt_secret(self):
        """Test that JWT_SECRET is used when SKYLAPSE_JWT_SECRET is missing."""
        fallback_secret = "fallback_jwt_secret_32_characters_"

        with patch.dict(os.environ, {"JWT_SECRET": fallback_secret}):
            # Force reload of the module
            if "realtime_server" in sys.modules:
                del sys.modules["realtime_server"]

            import realtime_server

            assert realtime_server.JWT_SECRET == fallback_secret

    def test_jwt_secret_fallback_realtime_jwt_secret(self):
        """Test that REALTIME_JWT_SECRET is used as final fallback."""
        final_fallback = "realtime_jwt_secret_32_chars_long_"

        with patch.dict(os.environ, {"REALTIME_JWT_SECRET": final_fallback}):
            # Force reload of the module
            if "realtime_server" in sys.modules:
                del sys.modules["realtime_server"]

            import realtime_server

            assert realtime_server.JWT_SECRET == final_fallback

    def test_jwt_operations_with_env_secret(self):
        """Test that JWT encode/decode operations work with environment secret."""
        secure_secret = "test_jwt_secret_32_characters_long_"

        with patch.dict(os.environ, {"SKYLAPSE_JWT_SECRET": secure_secret}):
            # Force reload of the module
            if "realtime_server" in sys.modules:
                del sys.modules["realtime_server"]

            import realtime_server

            # Test JWT token generation
            authenticator = realtime_server.JWTAuthenticator()
            token = authenticator.generate_token("test_user", ["dashboard:read"])

            # Test JWT token verification
            payload = authenticator.verify_token(token)

            assert payload is not None
            assert payload["user_id"] == "test_user"
            assert "dashboard:read" in payload["permissions"]

    def test_no_secret_logging(self):
        """Test that JWT secret value is not logged anywhere."""
        secret_value = "secret_that_should_never_be_logged_32"

        # Capture log output
        import logging

        log_capture = []

        class TestLogHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())

        handler = TestLogHandler()
        logger = logging.getLogger("realtime_server")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            with patch.dict(os.environ, {"SKYLAPSE_JWT_SECRET": secret_value}):
                # Force reload of the module
                if "realtime_server" in sys.modules:
                    del sys.modules["realtime_server"]

                import realtime_server  # noqa: F401

                # Check that no log message contains the secret value
                for message in log_capture:
                    assert secret_value not in message

                # But should log that secret was loaded
                success_messages = [
                    msg for msg in log_capture if "JWT secret loaded successfully" in msg
                ]
                assert len(success_messages) > 0

                # Should log the length but not the value
                length_logged = any(
                    f"({len(secret_value)} characters)" in msg for msg in log_capture
                )
                assert length_logged

        finally:
            logger.removeHandler(handler)


class TestJWTSecurityIntegration:
    """Integration tests for JWT security in the real-time server."""

    def test_server_initialization_with_valid_secret(self):
        """Test that server initializes properly with valid JWT secret."""
        valid_secret = "integration_test_jwt_secret_32_chars"

        with patch.dict(os.environ, {"SKYLAPSE_JWT_SECRET": valid_secret}):
            # Force reload
            if "realtime_server" in sys.modules:
                del sys.modules["realtime_server"]

            import realtime_server

            # Should be able to create server instance
            server = realtime_server.SkylapsRealTimeServer()
            assert server is not None
            assert hasattr(server, "authenticator")

    def test_server_initialization_fails_without_secret(self):
        """Test that server fails to initialize without JWT secret."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                # Force reload should fail
                if "realtime_server" in sys.modules:
                    del sys.modules["realtime_server"]
                import realtime_server  # noqa: F401

            assert "JWT secret not configured" in str(exc_info.value)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
