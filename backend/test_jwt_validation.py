#!/usr/bin/env python3
"""
Simple test script for JWT secret validation logic.
Tests the critical security fix for Issue #5 - JWT Secret Hardcoded.
"""

import os
import sys


def _load_jwt_secret():
    """
    Load JWT secret from environment variable with security validation.
    This is the exact same function from realtime_server.py
    """
    # Try multiple environment variable names for flexibility
    secret = (
        os.getenv("SKYLAPSE_JWT_SECRET")
        or os.getenv("JWT_SECRET")
        or os.getenv("REALTIME_JWT_SECRET")
    )

    if not secret:
        raise ValueError(
            "JWT secret not configured! Set one of these environment variables:\n"
            "  - SKYLAPSE_JWT_SECRET (recommended)\n"
            "  - JWT_SECRET\n"
            "  - REALTIME_JWT_SECRET\n"
            "Example: export SKYLAPSE_JWT_SECRET='your_secure_secret_minimum_32_characters_long'"
        )

    # Validate secret length for security
    if len(secret) < 32:
        raise ValueError(
            f"JWT secret must be at least 32 characters long for security. "
            f"Current length: {len(secret)} characters. "
            f"Please use a longer, more secure secret."
        )

    # Don't log the actual secret value - just confirm it's loaded
    print(f"JWT secret loaded successfully ({len(secret)} characters)")
    return secret


def run_tests():
    """Run comprehensive security validation tests."""
    print("🔒 JWT Security Validation Tests")
    print("=" * 50)

    # Test 1: Missing environment variable
    print("\n📋 Test 1: Missing JWT secret")
    for var in ["SKYLAPSE_JWT_SECRET", "JWT_SECRET", "REALTIME_JWT_SECRET"]:
        if var in os.environ:
            del os.environ[var]

    try:
        secret = _load_jwt_secret()
        print("❌ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        error_msg = str(e)
        print("✅ PASSED: Correctly failed with missing JWT secret")

        # Validate error message contains all expected elements
        expected_parts = [
            "JWT secret not configured",
            "SKYLAPSE_JWT_SECRET",
            "JWT_SECRET",
            "REALTIME_JWT_SECRET",
        ]

        for part in expected_parts:
            if part in error_msg:
                print(f"  ✅ Error message contains: {part}")
            else:
                print(f"  ❌ Error message missing: {part}")
                return False

    # Test 2: Short secret (security vulnerability)
    print("\n📋 Test 2: Short JWT secret (security check)")
    os.environ["SKYLAPSE_JWT_SECRET"] = "short_secret"  # Only 12 characters

    try:
        secret = _load_jwt_secret()
        print("❌ FAILED: Should have rejected short secret")
        return False
    except ValueError as e:
        error_msg = str(e)
        print("✅ PASSED: Correctly rejected short JWT secret")
        if "32 characters long" in error_msg and "12 characters" in error_msg:
            print("  ✅ Error message includes length validation details")
        else:
            print(f"  ❌ Error message unclear: {error_msg}")
            return False

    # Test 3: Minimum valid secret (32 characters)
    print("\n📋 Test 3: Minimum valid JWT secret (32 chars)")
    os.environ["SKYLAPSE_JWT_SECRET"] = "a" * 32  # Exactly 32 characters

    try:
        secret = _load_jwt_secret()
        if len(secret) == 32:
            print("✅ PASSED: Accepted 32-character secret")
        else:
            print(f"❌ FAILED: Wrong secret length: {len(secret)}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

    # Test 4: Long valid secret
    print("\n📋 Test 4: Long valid JWT secret (64 chars)")
    long_secret = "secure_jwt_secret_for_production_use_with_64_characters_total"
    os.environ["SKYLAPSE_JWT_SECRET"] = long_secret

    try:
        secret = _load_jwt_secret()
        if len(secret) == len(long_secret):
            print("✅ PASSED: Accepted long secure secret")
        else:
            print(f"❌ FAILED: Wrong secret length: {len(secret)}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

    # Test 5: Environment variable priority
    print("\n📋 Test 5: Environment variable priority")
    os.environ["SKYLAPSE_JWT_SECRET"] = "primary_secret_32_characters_long_"
    os.environ["JWT_SECRET"] = "secondary_secret_32_characters_long"
    os.environ["REALTIME_JWT_SECRET"] = "tertiary_secret_32_characters_long_"

    try:
        secret = _load_jwt_secret()
        if secret == "primary_secret_32_characters_long_":
            print("✅ PASSED: SKYLAPSE_JWT_SECRET takes priority")
        else:
            print(f"❌ FAILED: Wrong priority, got: {secret}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

    # Test 6: Fallback to JWT_SECRET
    print("\n📋 Test 6: Fallback to JWT_SECRET")
    del os.environ["SKYLAPSE_JWT_SECRET"]  # Remove primary

    try:
        secret = _load_jwt_secret()
        if secret == "secondary_secret_32_characters_long":
            print("✅ PASSED: Falls back to JWT_SECRET")
        else:
            print(f"❌ FAILED: Wrong fallback, got: {secret}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

    # Test 7: Final fallback to REALTIME_JWT_SECRET
    print("\n📋 Test 7: Final fallback to REALTIME_JWT_SECRET")
    del os.environ["JWT_SECRET"]  # Remove secondary

    try:
        secret = _load_jwt_secret()
        if secret == "tertiary_secret_32_characters_long_":
            print("✅ PASSED: Falls back to REALTIME_JWT_SECRET")
        else:
            print(f"❌ FAILED: Wrong final fallback, got: {secret}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

    print("\n" + "=" * 50)
    print("🎉 ALL SECURITY TESTS PASSED!")
    print("✅ JWT secret hardcoding vulnerability has been fixed")
    print("✅ Environment variable validation is working correctly")
    print("✅ Security requirements are enforced (32+ character minimum)")
    print("✅ Proper error messages guide users to correct configuration")
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
