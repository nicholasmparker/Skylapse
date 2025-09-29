"""
Shared Error Handling Middleware for Skylapse Services
Professional Mountain Timelapse Camera System

Provides consistent error handling, logging, and response formatting
across capture, processing, and backend services.
"""

import json
import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

try:
    from aiohttp import web
    from aiohttp.web import Request, Response

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    # Fallback types for when aiohttp is not available
    Response = Any
    Request = Any
    web = None

logger = logging.getLogger(__name__)


class SkylapsError(Exception):
    """Base exception class for Skylapse application errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class ValidationError(SkylapsError):
    """Error for input validation failures."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field, **(details or {})},
        )


class AuthenticationError(SkylapsError):
    """Error for authentication failures."""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict] = None):
        super().__init__(
            message=message, error_code="AUTHENTICATION_ERROR", status_code=401, details=details
        )


class AuthorizationError(SkylapsError):
    """Error for authorization failures."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict] = None):
        super().__init__(
            message=message, error_code="AUTHORIZATION_ERROR", status_code=403, details=details
        )


class NotFoundError(SkylapsError):
    """Error for resource not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        super().__init__(
            message=message,
            error_code="NOT_FOUND_ERROR",
            status_code=404,
            details={"resource_type": resource_type, **(details or {})},
        )


class CameraError(SkylapsError):
    """Error for camera-related operations."""

    def __init__(
        self, message: str, operation: Optional[str] = None, details: Optional[Dict] = None
    ):
        super().__init__(
            message=message,
            error_code="CAMERA_ERROR",
            status_code=503,
            details={"operation": operation, **(details or {})},
        )


class ProcessingError(SkylapsError):
    """Error for image processing operations."""

    def __init__(self, message: str, stage: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            status_code=503,
            details={"stage": stage, **(details or {})},
        )


def create_error_response(
    error: Union[SkylapsError, Exception], service_name: str = "skylapse"
) -> Dict[str, Any]:
    """Create standardized error response dictionary."""

    if isinstance(error, SkylapsError):
        return {
            "error": {
                "code": error.error_code,
                "message": error.message,
                "details": error.details,
                "timestamp": error.timestamp,
                "service": service_name,
            },
            "status": error.status_code,
        }
    else:
        # Handle HTTP exceptions with proper status codes
        status_code = 500  # Default to 500 for unknown errors
        error_code = "INTERNAL_ERROR"

        # Map common HTTP exceptions to proper status codes
        if hasattr(error, "status") or hasattr(error, "status_code"):
            # aiohttp HTTPException has status attribute
            status_code = getattr(error, "status", getattr(error, "status_code", 500))
            if status_code == 404:
                error_code = "NOT_FOUND"
            elif status_code == 403:
                error_code = "FORBIDDEN"
            elif status_code == 401:
                error_code = "UNAUTHORIZED"
            elif status_code == 400:
                error_code = "BAD_REQUEST"

        return {
            "error": {
                "code": error_code,
                "message": str(error) if str(error) else "An unexpected error occurred",
                "details": {"exception_type": type(error).__name__},
                "timestamp": datetime.now().isoformat(),
                "service": service_name,
            },
            "status": status_code,
        }


def log_error(
    error: Union[SkylapsError, Exception],
    request_info: Optional[Dict] = None,
    service_name: str = "skylapse",
) -> None:
    """Log error with consistent formatting and context."""

    error_context = {
        "service": service_name,
        "timestamp": datetime.now().isoformat(),
    }

    if request_info:
        error_context.update(request_info)

    if isinstance(error, SkylapsError):
        error_context.update(
            {
                "error_code": error.error_code,
                "status_code": error.status_code,
                "details": error.details,
            }
        )

        if error.status_code >= 500:
            logger.error(
                f"[{service_name}] {error.error_code}: {error.message}", extra=error_context
            )
        else:
            logger.warning(
                f"[{service_name}] {error.error_code}: {error.message}", extra=error_context
            )
    else:
        # Log full traceback for unexpected errors
        error_context["traceback"] = traceback.format_exc()
        logger.error(f"[{service_name}] INTERNAL_ERROR: {str(error)}", extra=error_context)


# Aiohttp middleware (only available if aiohttp is installed)
if AIOHTTP_AVAILABLE:

    def create_aiohttp_error_middleware(service_name: str = "skylapse"):
        """Create aiohttp error handling middleware."""

        @web.middleware
        async def error_middleware(request: Request, handler: Callable) -> Response:
            """Aiohttp error handling middleware."""
            try:
                return await handler(request)
            except web.HTTPException as http_ex:
                # Handle HTTP exceptions with standardized error format
                # while preserving original status codes

                # Extract request info for logging
                request_info = {
                    "method": request.method,
                    "path": request.path,
                    "remote": str(request.remote),
                    "user_agent": request.headers.get("User-Agent", "Unknown"),
                }

                # Create standardized error response for HTTP exceptions
                error_response = create_error_response(http_ex, service_name)

                # Log HTTP exceptions (but only warning level for client errors)
                if http_ex.status >= 500:
                    log_error(http_ex, request_info, service_name)
                else:
                    logger.warning(
                        f"[{service_name}] HTTP {http_ex.status}: {request.method} {request.path} - {str(http_ex)}"
                    )

                # Return standardized JSON error response instead of default HTML/empty JSON
                return web.json_response(error_response, status=error_response["status"])
            except Exception as e:
                # Extract request info for logging
                request_info = {
                    "method": request.method,
                    "path": request.path,
                    "remote": str(request.remote),
                    "user_agent": request.headers.get("User-Agent", "Unknown"),
                }

                # Log the error
                log_error(e, request_info, service_name)

                # Create error response
                error_response = create_error_response(e, service_name)

                # Return JSON response
                return web.json_response(error_response, status=error_response["status"])

        return error_middleware

    def create_json_validation_middleware(service_name: str = "skylapse"):
        """Create JSON validation middleware to catch malformed JSON and return 400 errors."""

        @web.middleware
        async def json_validation_middleware(request: Request, handler: Callable) -> Response:
            """JSON validation middleware for aiohttp."""

            # Only validate JSON for requests with JSON content type
            content_type = request.headers.get("Content-Type", "")
            if "application/json" in content_type and request.can_read_body:
                try:
                    # Try to read and parse JSON to validate it
                    body = await request.read()
                    if body:  # Only validate if there's actually a body
                        json.loads(body.decode("utf-8"))

                        # Create a new request with the body we just read
                        # This is needed because aiohttp can only read the body once
                        class RequestWithBody:
                            def __init__(self, original_request, body_bytes):
                                self._original = original_request
                                self._body = body_bytes
                                self._json_cache = None

                            def __getattr__(self, name):
                                return getattr(self._original, name)

                            async def json(self):
                                if self._json_cache is None:
                                    self._json_cache = json.loads(self._body.decode("utf-8"))
                                return self._json_cache

                            async def read(self):
                                return self._body

                            async def text(self):
                                return self._body.decode("utf-8")

                            def can_read_body(self):
                                return True

                        # Replace request with our wrapper
                        request = RequestWithBody(request, body)

                except json.JSONDecodeError as e:
                    # Return standardized 400 error for malformed JSON
                    error_response = {
                        "error": {
                            "code": "INVALID_JSON",
                            "message": f"Invalid JSON in request body: {str(e)}",
                            "details": {
                                "json_error": str(e),
                                "line": getattr(e, "lineno", None),
                                "column": getattr(e, "colno", None),
                            },
                            "timestamp": datetime.now().isoformat(),
                            "service": service_name,
                        }
                    }

                    logger.warning(
                        f"[{service_name}] Invalid JSON in request: {request.method} {request.path} - {str(e)}"
                    )

                    return web.json_response(error_response, status=400)
                except UnicodeDecodeError as e:
                    # Handle encoding errors
                    error_response = {
                        "error": {
                            "code": "INVALID_ENCODING",
                            "message": f"Invalid encoding in request body: {str(e)}",
                            "details": {"encoding_error": str(e)},
                            "timestamp": datetime.now().isoformat(),
                            "service": service_name,
                        }
                    }

                    logger.warning(
                        f"[{service_name}] Invalid encoding in request: {request.method} {request.path} - {str(e)}"
                    )

                    return web.json_response(error_response, status=400)
                except Exception as e:
                    # Log unexpected errors but don't fail the request
                    logger.error(f"[{service_name}] Unexpected error in JSON validation: {str(e)}")

            # Continue to next middleware/handler
            return await handler(request)

        return json_validation_middleware

    def json_response(data: Any, status: int = 200, **kwargs) -> Response:
        """Create JSON response with consistent formatting."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available")

        return web.json_response(data, status=status, **kwargs)

else:

    def create_aiohttp_error_middleware(service_name: str = "skylapse"):
        """Fallback when aiohttp is not available."""

        def middleware(request, handler):
            raise RuntimeError("aiohttp not available - cannot create middleware")

        return middleware

    def create_json_validation_middleware(service_name: str = "skylapse"):
        """Fallback when aiohttp is not available."""

        def middleware(request, handler):
            raise RuntimeError("aiohttp not available - cannot create JSON validation middleware")

        return middleware


# Decorator for function-level error handling
def handle_errors(service_name: str = "skylapse", log_errors: bool = True):
    """Decorator for consistent error handling in functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    log_error(e, {"function": func.__name__}, service_name)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    log_error(e, {"function": func.__name__}, service_name)
                raise

        # Return appropriate wrapper based on function type
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Utility functions for consistent error creation
def validation_error(message: str, field: Optional[str] = None, **details) -> ValidationError:
    """Create a validation error with consistent formatting."""
    return ValidationError(message, field, details)


def camera_error(message: str, operation: Optional[str] = None, **details) -> CameraError:
    """Create a camera error with consistent formatting."""
    return CameraError(message, operation, details)


def processing_error(message: str, stage: Optional[str] = None, **details) -> ProcessingError:
    """Create a processing error with consistent formatting."""
    return ProcessingError(message, stage, details)


def not_found_error(message: str, resource_type: Optional[str] = None, **details) -> NotFoundError:
    """Create a not found error with consistent formatting."""
    return NotFoundError(message, resource_type, details)


# Configuration for different environments
class ErrorHandlerConfig:
    """Configuration for error handling behavior."""

    def __init__(
        self,
        include_traceback: bool = False,
        log_level: str = "INFO",
        include_request_id: bool = True,
        sanitize_headers: bool = True,
    ):
        self.include_traceback = include_traceback
        self.log_level = log_level
        self.include_request_id = include_request_id
        self.sanitize_headers = sanitize_headers


# Default configurations
DEVELOPMENT_CONFIG = ErrorHandlerConfig(include_traceback=True, log_level="DEBUG")
PRODUCTION_CONFIG = ErrorHandlerConfig(include_traceback=False, log_level="WARNING")
