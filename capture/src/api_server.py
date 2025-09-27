"""REST API server for capture service control and monitoring."""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict

try:
    from aiohttp import web, web_request
    from aiohttp.web import Response
except ImportError:
    # Fallback for systems without aiohttp
    web = None
    web_request = None
    Response = None

from .camera_types import CaptureSettings, SkylapsJSONEncoder, to_dict

logger = logging.getLogger(__name__)


def json_response(data: Any, status: int = 200, **kwargs) -> web.Response:
    """Create JSON response using Skylapse JSON encoder."""
    if web is None:
        raise RuntimeError("aiohttp not available")

    # Convert data to JSON-serializable format
    serializable_data = to_dict(data)

    # Create JSON response
    return web.json_response(
        serializable_data,
        status=status,
        dumps=lambda obj: json.dumps(obj, cls=SkylapsJSONEncoder),
        **kwargs,
    )


class CaptureAPIServer:
    """REST API server for capture service control and monitoring."""

    def __init__(self, port: int = 8080, controller=None):
        """Initialize API server."""
        self.port = port
        self.controller = controller  # CaptureService instance
        self.app = None
        self.runner = None
        self.site = None
        self._is_running = False

        if web is None:
            logger.warning("aiohttp not available, API server will be disabled")

    async def start(self) -> None:
        """Start the API server."""
        if web is None:
            logger.warning("API server disabled - aiohttp not available")
            return

        logger.info(f"Starting API server on port {self.port}")

        try:
            # Create web application
            self.app = web.Application()

            # Add routes
            self._setup_routes()

            # Add middleware
            self.app.middlewares.append(self._error_middleware)
            self.app.middlewares.append(self._logging_middleware)

            # Start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()

            self._is_running = True
            logger.info(f"API server started on http://0.0.0.0:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the API server."""
        if not self._is_running or web is None:
            return

        logger.info("Shutting down API server")

        try:
            if self.site:
                await self.site.stop()

            if self.runner:
                await self.runner.cleanup()

            self._is_running = False
            logger.info("API server shutdown complete")

        except Exception as e:
            logger.error(f"Error during API server shutdown: {e}")

    def _setup_routes(self) -> None:
        """Setup API routes."""
        if web is None:
            return

        # Health check
        self.app.router.add_get("/health", self._health_check)

        # Status and information
        self.app.router.add_get("/status", self._get_status)
        self.app.router.add_get("/camera/status", self._get_camera_status)

        # Capture operations
        self.app.router.add_post("/capture/manual", self._manual_capture)
        self.app.router.add_post("/capture/test", self._test_capture)
        self.app.router.add_get("/capture/preview", self._get_preview)

        # Configuration
        self.app.router.add_get("/config", self._get_config)
        self.app.router.add_post("/config", self._update_config)

        # Storage and history
        self.app.router.add_get("/captures/recent", self._get_recent_captures)
        self.app.router.add_get("/storage/status", self._get_storage_status)

        # Metrics and statistics
        self.app.router.add_get("/metrics", self._get_metrics)
        self.app.router.add_get("/statistics", self._get_statistics)

    @web.middleware
    async def _error_middleware(self, request, handler):
        """Error handling middleware."""
        try:
            return await handler(request)
        except Exception as e:
            logger.error(f"API error: {e}\n{traceback.format_exc()}")
            return json_response(
                {
                    "error": str(e),
                    "type": type(e).__name__,
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    @web.middleware
    async def _logging_middleware(self, request, handler):
        """Request logging middleware."""
        start_time = asyncio.get_event_loop().time()
        response = await handler(request)
        process_time = asyncio.get_event_loop().time() - start_time

        logger.info(f"{request.method} {request.path} - {response.status} - {process_time:.3f}s")
        return response

    async def _health_check(self, request) -> web.Response:
        """Health check endpoint."""
        if not self.controller:
            return json_response({"status": "unhealthy", "reason": "no_controller"}, status=503)

        try:
            camera_initialized = self.controller._camera_controller.is_initialized
            storage_initialized = self.controller._storage_manager._is_initialized

            if camera_initialized and storage_initialized:
                return json_response(
                    {
                        "status": "healthy",
                        "timestamp": datetime.now().isoformat(),
                        "version": "1.0.0-sprint1",
                    }
                )
            else:
                return json_response(
                    {
                        "status": "unhealthy",
                        "reason": "components_not_initialized",
                        "camera_initialized": camera_initialized,
                        "storage_initialized": storage_initialized,
                    },
                    status=503,
                )

        except Exception as e:
            return json_response({"status": "unhealthy", "reason": str(e)}, status=503)

    async def _get_status(self, request) -> web.Response:
        """Get comprehensive service status."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            status = await self.controller.get_service_status()
            return json_response(status)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_camera_status(self, request) -> web.Response:
        """Get detailed camera status."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            camera_status = await self.controller._camera_controller.get_camera_status()
            return json_response(camera_status)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _manual_capture(self, request) -> web.Response:
        """Perform a manual capture."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            # Parse request body for capture settings
            settings = None
            if request.content_type == "application/json":
                data = await request.json()
                settings = self._parse_capture_settings(data.get("settings", {}))

            result = await self.controller.manual_capture(settings)
            return json_response(result)

        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _test_capture(self, request) -> web.Response:
        """Perform a test capture."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            result = await self.controller._camera_controller.test_capture()
            return json_response(result)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_preview(self, request) -> web.Response:
        """Get live preview frame."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            preview_data = await self.controller.get_live_preview()
            if preview_data:
                return web.Response(body=preview_data, content_type="image/jpeg")
            else:
                return json_response({"error": "No preview available"}, status=404)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_config(self, request) -> web.Response:
        """Get current configuration."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            # Return sanitized configuration (no sensitive data)
            config = {
                "storage": {
                    "buffer_path": str(self.controller._storage_manager.buffer_path),
                    "max_size_gb": self.controller._storage_manager.max_size_gb,
                    "retention_hours": self.controller._storage_manager.retention_hours,
                },
                "api": {"port": self.port, "running": self._is_running},
            }
            return json_response(config)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _update_config(self, request) -> web.Response:
        """Update service configuration."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            data = await request.json()
            success = await self.controller.update_configuration(data)

            if success:
                return json_response({"status": "configuration_updated"})
            else:
                return json_response({"error": "Failed to update configuration"}, status=500)

        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_recent_captures(self, request) -> web.Response:
        """Get recent capture history."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            limit = int(request.query.get("limit", 10))
            recent_captures = await self.controller.get_recent_captures(limit)
            return json_response({"captures": recent_captures})
        except ValueError:
            return json_response({"error": "Invalid limit parameter"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_storage_status(self, request) -> web.Response:
        """Get storage system status."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            storage_status = await self.controller._storage_manager.get_status()
            return json_response(storage_status)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_metrics(self, request) -> web.Response:
        """Get service metrics in Prometheus format."""
        if not self.controller:
            return web.Response(
                text="# Service not available\n", content_type="text/plain", status=503
            )

        try:
            metrics = []

            # Service uptime
            uptime = asyncio.get_event_loop().time() - self.controller._service_start_time
            metrics.append(f"skylapse_service_uptime_seconds {uptime:.2f}")

            # Camera metrics
            camera_status = await self.controller._camera_controller.get_camera_status()
            metrics.append(
                f"skylapse_camera_initialized {1 if camera_status['initialized'] else 0}"
            )

            if "performance" in camera_status:
                perf = camera_status["performance"]
                metrics.append(f"skylapse_captures_total {perf['total_captures']}")
                metrics.append(f"skylapse_captures_successful {perf['successful_captures']}")
                metrics.append(f"skylapse_captures_failed {perf['failed_captures']}")
                metrics.append(
                    f"skylapse_capture_time_ms_avg {perf['average_capture_time_ms']:.2f}"
                )

            # Storage metrics
            storage_status = await self.controller._storage_manager.get_status()
            if "space_info" in storage_status:
                space = storage_status["space_info"]
                metrics.append(f"skylapse_storage_total_gb {space['total_gb']:.2f}")
                metrics.append(f"skylapse_storage_free_gb {space['free_gb']:.2f}")
                metrics.append(f"skylapse_storage_buffer_gb {space['buffer_size_gb']:.2f}")

            if "file_counts" in storage_status:
                counts = storage_status["file_counts"]
                metrics.append(f"skylapse_stored_images {counts['images']}")
                metrics.append(f"skylapse_transfer_queue_items {counts['transfer_queue']}")

            metrics_text = "\n".join(metrics) + "\n"
            return web.Response(text=metrics_text, content_type="text/plain")

        except Exception as e:
            return web.Response(
                text=f"# Error generating metrics: {e}\n", content_type="text/plain", status=500
            )

    async def _get_statistics(self, request) -> web.Response:
        """Get detailed service statistics."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            hours = int(request.query.get("hours", 24))
            scheduler_stats = self.controller._scheduler.get_capture_statistics(hours)

            return json_response(
                {"scheduler": scheduler_stats, "timestamp": datetime.now().isoformat()}
            )

        except ValueError:
            return json_response({"error": "Invalid hours parameter"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    def _parse_capture_settings(self, data: Dict[str, Any]) -> CaptureSettings:
        """Parse capture settings from request data."""
        return CaptureSettings(
            exposure_time_us=data.get("exposure_time_us"),
            iso=data.get("iso"),
            exposure_compensation=data.get("exposure_compensation", 0.0),
            focus_distance_mm=data.get("focus_distance_mm"),
            autofocus_enabled=data.get("autofocus_enabled", True),
            white_balance_k=data.get("white_balance_k"),
            white_balance_mode=data.get("white_balance_mode", "auto"),
            quality=data.get("quality", 95),
            format=data.get("format", "JPEG"),
            hdr_bracket_stops=data.get("hdr_bracket_stops", []),
            processing_hints=data.get("processing_hints", {}),
        )
