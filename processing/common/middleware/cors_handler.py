"""
Shared CORS Handling Middleware for Skylapse Services
Professional Mountain Timelapse Camera System

Provides consistent CORS configuration across all services.
"""

import logging
from typing import List, Optional, Union

try:
    from aiohttp import web
    from aiohttp.web import Request, Response

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    Response = None
    Request = None
    web = None

logger = logging.getLogger(__name__)


class CORSConfig:
    """Configuration for CORS middleware."""

    def __init__(
        self,
        allowed_origins: Union[str, List[str]] = "*",
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        exposed_headers: List[str] = None,
        allow_credentials: bool = False,
        max_age: int = 86400,  # 24 hours
    ):
        self.allowed_origins = (
            allowed_origins if isinstance(allowed_origins, list) else [allowed_origins]
        )
        self.allowed_methods = allowed_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
            "PATCH",
            "HEAD",
        ]
        self.allowed_headers = allowed_headers or [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "Origin",
            "Cache-Control",
            "X-File-Name",
        ]
        self.exposed_headers = exposed_headers or []
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed."""
        if not origin:
            return True

        if "*" in self.allowed_origins:
            return True

        return origin in self.allowed_origins

    def get_allowed_origin(self, request_origin: Optional[str]) -> str:
        """Get the appropriate allowed origin header value."""
        if "*" in self.allowed_origins and not self.allow_credentials:
            return "*"

        if self.is_origin_allowed(request_origin):
            return request_origin or "*"

        return ""


# Default CORS configurations for different environments
DEVELOPMENT_CORS_CONFIG = CORSConfig(allowed_origins="*", allow_credentials=False)

PRODUCTION_CORS_CONFIG = CORSConfig(
    allowed_origins=["http://localhost:3000", "https://skylapse.local", "https://skylapse.app"],
    allow_credentials=True,
)

# Standardized CORS configurations for all services
CAPTURE_SERVICE_CORS_CONFIG = CORSConfig(
    allowed_origins="*",  # Allow all origins for camera access
    allowed_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
        "PATCH",
        "HEAD",
    ],  # Standardized methods
    allow_credentials=False,
)

PROCESSING_SERVICE_CORS_CONFIG = CORSConfig(
    allowed_origins="*",  # Allow all origins for processing service
    allowed_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
        "PATCH",
        "HEAD",
    ],  # Standardized methods
    allow_credentials=False,
)

BACKEND_SERVICE_CORS_CONFIG = CORSConfig(
    allowed_origins="*",  # Allow all origins for backend service
    allowed_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
        "PATCH",
        "HEAD",
    ],  # Standardized methods
    allow_credentials=False,
)

if AIOHTTP_AVAILABLE:

    def create_cors_middleware(config: CORSConfig = None, service_name: str = "skylapse"):
        """Create aiohttp CORS middleware."""

        if config is None:
            config = DEVELOPMENT_CORS_CONFIG

        @web.middleware
        async def cors_middleware(request: Request, handler) -> Response:
            """CORS middleware for aiohttp."""

            origin = request.headers.get("Origin")

            # Handle preflight OPTIONS requests
            if request.method == "OPTIONS":
                # Check if origin is allowed
                if not config.is_origin_allowed(origin):
                    return web.Response(status=403, text="Origin not allowed")

                response = web.Response(status=200)
            else:
                try:
                    response = await handler(request)
                except web.HTTPException as http_ex:
                    # HTTPException instances should be re-raised to preserve status codes
                    raise
                except Exception as e:
                    logger.error(f"CORS middleware error in {service_name}: {e}")
                    # Still apply CORS headers to error responses
                    response = web.Response(status=500, text=str(e))

            # Add CORS headers
            allowed_origin = config.get_allowed_origin(origin)
            if allowed_origin:
                response.headers["Access-Control-Allow-Origin"] = allowed_origin

            response.headers["Access-Control-Allow-Methods"] = ", ".join(config.allowed_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(config.allowed_headers)

            if config.exposed_headers:
                response.headers["Access-Control-Expose-Headers"] = ", ".join(
                    config.exposed_headers
                )

            if config.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

            response.headers["Access-Control-Max-Age"] = str(config.max_age)

            # Add comprehensive security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            )

            # Add cache control for API responses
            if request.path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

            return response

        return cors_middleware

    def add_cors_headers(
        response: Response, config: CORSConfig = None, origin: Optional[str] = None
    ) -> Response:
        """Add CORS headers to an existing response."""

        if config is None:
            config = DEVELOPMENT_CORS_CONFIG

        allowed_origin = config.get_allowed_origin(origin)
        if allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin

        response.headers["Access-Control-Allow-Methods"] = ", ".join(config.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(config.allowed_headers)

        if config.exposed_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(config.exposed_headers)

        if config.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers["Access-Control-Max-Age"] = str(config.max_age)

        return response

else:

    def create_cors_middleware(config: CORSConfig = None, service_name: str = "skylapse"):
        """Fallback when aiohttp is not available."""

        def middleware(request, handler):
            raise RuntimeError("aiohttp not available - cannot create CORS middleware")

        return middleware

    def add_cors_headers(response, config: CORSConfig = None, origin: Optional[str] = None):
        """Fallback when aiohttp is not available."""
        raise RuntimeError("aiohttp not available - cannot add CORS headers")


# Utility function to get environment-appropriate CORS config
def get_cors_config(environment: str = "development", service_type: str = "api") -> CORSConfig:
    """Get appropriate CORS configuration based on environment and service type."""

    # Service-specific configurations (standardized)
    if service_type == "capture":
        return CAPTURE_SERVICE_CORS_CONFIG
    elif service_type == "processing":
        return PROCESSING_SERVICE_CORS_CONFIG
    elif service_type == "backend":
        return BACKEND_SERVICE_CORS_CONFIG

    # Environment-based fallback
    if environment.lower() in ["production", "prod"]:
        return PRODUCTION_CORS_CONFIG
    else:
        return DEVELOPMENT_CORS_CONFIG


# Validation functions
def validate_cors_config(config: CORSConfig) -> None:
    """Validate CORS configuration."""

    if not config.allowed_methods:
        raise ValueError("At least one HTTP method must be allowed")

    if not config.allowed_headers:
        raise ValueError("At least one header must be allowed")

    if config.allow_credentials and "*" in config.allowed_origins:
        logger.warning("Using credentials with wildcard origins is not recommended for security")

    if config.max_age < 0:
        raise ValueError("max_age must be non-negative")


# Logging helpers
def log_cors_request(request_info: dict, config: CORSConfig, service_name: str) -> None:
    """Log CORS request information for debugging."""

    logger.debug(f"[{service_name}] CORS request: {request_info}")
    logger.debug(
        f"[{service_name}] CORS config: origins={config.allowed_origins}, credentials={config.allow_credentials}"
    )
