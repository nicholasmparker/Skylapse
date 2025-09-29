"""REST API server for processing service control and monitoring."""

import asyncio
import json
import logging
import traceback
from datetime import datetime, timedelta

try:
    import socketio
    from aiohttp import web
    from aiohttp.web import StreamResponse, json_response

    logger = logging.getLogger(__name__)
except ImportError:
    web = None
    json_response = None
    socketio = None
    StreamResponse = None

# Import camera service
try:
    from .camera_service import camera_service
except ImportError:
    camera_service = None
    logger.warning("Camera service not available")

logger = logging.getLogger(__name__)


class ProcessingAPIServer:
    """REST API server for processing service control and monitoring."""

    def __init__(self, port: int = 8081, controller=None):
        """Initialize processing API server."""
        self.port = port
        self.controller = controller  # ProcessingService instance
        self.app = None
        self.runner = None
        self.site = None
        self.sio = None
        self._is_running = False

        if web is None:
            logger.warning("aiohttp not available, API server will be disabled")
        if socketio is None:
            logger.warning("socketio not available, WebSocket features will be disabled")

    async def start(self) -> None:
        """Start the API server."""
        if web is None:
            logger.warning("Processing API server disabled - aiohttp not available")
            return

        logger.info(f"Starting processing API server on port {self.port}")

        try:
            # Initialize Socket.IO server
            if socketio:
                self.sio = socketio.AsyncServer(
                    async_mode="aiohttp",
                    cors_allowed_origins="*",
                    logger=False,
                    engineio_logger=False,
                )
                self._setup_socketio_handlers()

            self.app = web.Application()
            self._setup_routes()

            # Attach Socket.IO to app
            if self.sio:
                self.sio.attach(self.app)

            # Add middleware - CORS must be first to ensure headers are always added
            self.app.middlewares.append(self._cors_middleware)
            self.app.middlewares.append(self._logging_middleware)

            # Start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()

            # Initialize camera service
            if camera_service:
                await camera_service.initialize()
                logger.info("Camera service initialized")

            self._is_running = True
            logger.info(f"Processing API server started on http://0.0.0.0:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start processing API server: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the API server."""
        if not self._is_running or web is None:
            return

        logger.info("Shutting down processing API server")

        try:
            if self.site:
                await self.site.stop()

            if self.runner:
                await self.runner.cleanup()

            self._is_running = False
            logger.info("Processing API server shutdown complete")

        except Exception as e:
            logger.error(f"Error during processing API server shutdown: {e}")

    @web.middleware
    async def _cors_middleware(self, request, handler):
        """CORS middleware for cross-origin requests."""
        # Handle preflight OPTIONS requests immediately
        if request.method == "OPTIONS":
            logger.debug(f"CORS: Handling preflight OPTIONS request for {request.path}")
            response = web.Response()
        else:
            try:
                # Process the request
                response = await handler(request)
            except Exception as e:
                logger.error(f"Processing API error: {e}\n{traceback.format_exc()}")
                # Create error response with proper status
                if hasattr(e, "status_code"):
                    status = e.status_code
                elif "not found" in str(e).lower():
                    status = 404
                elif "method not allowed" in str(e).lower():
                    status = 405
                else:
                    status = 500

                response = json_response(
                    {
                        "error": str(e),
                        "type": type(e).__name__,
                        "timestamp": datetime.now().isoformat(),
                    },
                    status=status,
                )

        # Add CORS headers to ALL responses (success, error, and preflight)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With"
        )
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Allow-Credentials"] = "false"

        logger.debug(
            f"CORS: Added headers to {request.method} {request.path} response (status: {response.status})"
        )
        return response

    def _setup_routes(self) -> None:
        """Setup API routes."""
        if web is None:
            return

        # Health check
        self.app.router.add_get("/health", self._health_check)

        # Status and information
        self.app.router.add_get("/status", self._get_status)

        # Job management
        self.app.router.add_post("/jobs", self._create_job)
        self.app.router.add_get("/jobs/{job_id}", self._get_job_status)
        self.app.router.add_get("/jobs", self._list_recent_jobs)
        self.app.router.add_delete("/jobs/{job_id}", self._cancel_job)

        # Processing operations
        self.app.router.add_post("/process/images", self._process_images)
        self.app.router.add_post("/process/timelapse", self._create_timelapse)

        # Results and outputs
        self.app.router.add_get("/timelapses", self._get_recent_timelapses)
        self.app.router.add_get("/statistics", self._get_statistics)

        # Transfer management (for testing)
        self.app.router.add_post("/transfers/simulate", self._simulate_transfer)
        self.app.router.add_get("/transfers/pending", self._get_pending_transfers)

        # Dashboard API endpoints (new for Sprint 1)
        self.app.router.add_get("/api/v1/gallery/recent", self._get_recent_gallery)
        self.app.router.add_get("/api/v1/environmental/current", self._get_environmental_data)

        # Frontend-expected API endpoints (Sprint 3 - API contract fix)
        self.app.router.add_get("/api/gallery/sequences", self._get_gallery_sequences)
        self.app.router.add_get("/api/gallery/sequences/{id}", self._get_sequence_details)
        self.app.router.add_delete("/api/gallery/sequences/{id}", self._delete_sequence)
        self.app.router.add_post("/api/gallery/generate", self._generate_timelapse)
        self.app.router.add_get("/api/gallery/jobs", self._get_generation_jobs)
        self.app.router.add_get("/api/analytics", self._get_analytics_data)

        # Camera API - Live preview and control
        if camera_service:
            self.app.router.add_get("/api/camera/stream", self._camera_stream)
            self.app.router.add_get("/api/camera/status", self._get_camera_status)
            self.app.router.add_get("/api/camera/settings", self._get_camera_settings)
            self.app.router.add_put("/api/camera/settings", self._update_camera_settings)
            self.app.router.add_post("/api/camera/capture", self._manual_capture)
            self.app.router.add_post("/api/camera/start-stream", self._start_camera_stream)
            self.app.router.add_post("/api/camera/stop-stream", self._stop_camera_stream)

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
            status = await self.controller.get_service_status()
            if status["service"]["running"]:
                return json_response(
                    {
                        "status": "healthy",
                        "timestamp": datetime.now().isoformat(),
                        "version": "1.0.0-sprint1",
                    }
                )
            else:
                return json_response(
                    {"status": "unhealthy", "reason": "service_not_running"}, status=503
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

    async def _create_job(self, request) -> web.Response:
        """Create a new processing job."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            job_data = await request.json()
            job_id = await self.controller.add_processing_job(job_data)

            return json_response({"job_id": job_id, "status": "created"})

        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_job_status(self, request) -> web.Response:
        """Get status of a specific job."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            job_id = request.match_info["job_id"]
            status = await self.controller.get_job_status(job_id)
            return json_response(status)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _list_recent_jobs(self, request) -> web.Response:
        """List recent jobs."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            limit = int(request.query.get("limit", 10))
            jobs = await self.controller._job_queue.get_recent_jobs(limit)
            return json_response({"jobs": jobs})
        except ValueError:
            return json_response({"error": "Invalid limit parameter"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _cancel_job(self, request) -> web.Response:
        """Cancel a job."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            job_id = request.match_info["job_id"]
            success = await self.controller._job_queue.cancel_job(job_id)

            if success:
                return json_response({"status": "cancelled"})
            else:
                return json_response({"error": "Job could not be cancelled"}, status=400)

        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _process_images(self, request) -> web.Response:
        """Process a batch of images."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            data = await request.json()
            image_paths = data.get("image_paths", [])
            metadata = data.get("metadata", {})
            processing_options = data.get("processing_options", {})

            if not image_paths:
                return json_response({"error": "No image paths provided"}, status=400)

            # Create processing job
            job_data = {
                "type": "image_processing",
                "image_paths": image_paths,
                "metadata": metadata,
                "processing_options": processing_options,
                "priority": "normal",
            }

            job_id = await self.controller.add_processing_job(job_data)

            return json_response(
                {"job_id": job_id, "status": "queued", "image_count": len(image_paths)}
            )

        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _create_timelapse(self, request) -> web.Response:
        """Create a timelapse from processed images."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            data = await request.json()
            processed_images = data.get("processed_images", [])
            metadata = data.get("metadata", {})
            output_formats = data.get("output_formats", ["1080p"])

            if not processed_images:
                return json_response({"error": "No processed images provided"}, status=400)

            # Create timelapse assembly job
            job_data = {
                "type": "timelapse_assembly",
                "processed_images": processed_images,
                "metadata": metadata,
                "output_formats": output_formats,
                "priority": "low",
            }

            job_id = await self.controller.add_processing_job(job_data)

            return json_response(
                {"job_id": job_id, "status": "queued", "frame_count": len(processed_images)}
            )

        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_recent_timelapses(self, request) -> web.Response:
        """Get recent timelapses."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            limit = int(request.query.get("limit", 10))
            timelapses = await self.controller.get_recent_timelapses(limit)
            return json_response({"timelapses": timelapses})
        except ValueError:
            return json_response({"error": "Invalid limit parameter"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_statistics(self, request) -> web.Response:
        """Get processing service statistics."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            status = await self.controller.get_service_status()
            return json_response(
                {
                    "statistics": status.get("statistics", {}),
                    "components": status.get("components", {}),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _simulate_transfer(self, request) -> web.Response:
        """Simulate an incoming transfer (for testing)."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            data = await request.json()
            image_paths = data.get("image_paths", [])
            metadata = data.get("metadata", {})

            if not image_paths:
                return json_response({"error": "No image paths provided"}, status=400)

            transfer_id = await self.controller._transfer_receiver.simulate_incoming_transfer(
                image_paths, metadata
            )

            return json_response(
                {"transfer_id": transfer_id, "status": "simulated", "image_count": len(image_paths)}
            )

        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_pending_transfers(self, request) -> web.Response:
        """Get pending transfers."""
        if not self.controller:
            return json_response({"error": "Service not available"}, status=503)

        try:
            pending = await self.controller._transfer_receiver.get_pending_transfers()
            return json_response({"transfers": pending})
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    # Socket.IO event handlers

    def _setup_socketio_handlers(self) -> None:
        """Setup Socket.IO event handlers."""
        if not self.sio:
            return

        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection."""
            logger.info(f"WebSocket client connected: {sid}")
            return True

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            logger.info(f"WebSocket client disconnected: {sid}")

        @self.sio.event
        async def subscribe(sid, data):
            """Handle subscription to dashboard events."""
            if data == "dashboard":
                logger.info(f"Client {sid} subscribed to dashboard events")
                # Send initial status
                if self.controller:
                    try:
                        status = await self.controller.get_service_status()
                        await self.sio.emit(
                            "dashboard-event",
                            {
                                "type": "system.status",
                                "data": self._format_system_status(status),
                                "timestamp": datetime.now().isoformat(),
                            },
                            room=sid,
                        )
                    except Exception as e:
                        logger.error(f"Failed to send initial status: {e}")

    async def broadcast_dashboard_event(self, event_type: str, data: dict) -> None:
        """Broadcast dashboard event to all connected clients."""
        if not self.sio:
            return

        try:
            await self.sio.emit(
                "dashboard-event",
                {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()},
            )
        except Exception as e:
            logger.error(f"Failed to broadcast dashboard event: {e}")

    # New Dashboard API endpoints

    async def _get_recent_gallery(self, request) -> web.Response:
        """Get recent captures for gallery."""
        try:
            limit = int(request.query.get("limit", 6))

            # Mock data for Sprint 1 - replace with real data in Phase 2
            mock_captures = [
                {
                    "id": f"seq_{i:03d}",
                    "name": f"Mountain Vista {datetime.now().strftime('%Y-%m-%d')} #{i}",
                    "startTime": (datetime.now() - timedelta(hours=i * 2)).isoformat(),
                    "endTime": (datetime.now() - timedelta(hours=i * 2 - 1)).isoformat(),
                    "captureCount": 120 + i * 10,
                    "thumbnail": f"/api/v1/gallery/{i:03d}/thumbnail.jpg",
                    "metadata": {
                        "location": {
                            "latitude": 39.7392 + i * 0.001,
                            "longitude": -104.9903 + i * 0.001,
                            "name": f"Rocky Mountain View Point {i}",
                        },
                        "weather": {
                            "condition": [
                                "Clear",
                                "Partly Cloudy",
                                "Overcast",
                                "Clear",
                                "Partly Cloudy",
                            ][i % 5],
                            "temperature": 18 + i * 2,
                            "humidity": 45 + i * 5,
                            "wind_speed": 2.5 + i * 0.5,
                        },
                        "settings": {
                            "iso": 100,
                            "exposureTime": "1/250",
                            "whiteBalance": "daylight",
                            "imageFormat": "jpeg",
                            "quality": 95,
                            "hdr": {"enabled": i % 2 == 0, "brackets": 3, "evSteps": 2},
                        },
                        "duration": 3600 + i * 300,
                        "fileSize": 2048000 + i * 100000,
                    },
                    "status": ["completed", "processing", "completed", "completed", "capturing"][
                        i % 5
                    ],
                }
                for i in range(limit)
            ]

            return json_response(
                {
                    "data": mock_captures,
                    "status": 200,
                    "message": "Recent captures retrieved successfully",
                }
            )

        except ValueError:
            return json_response({"error": "Invalid limit parameter"}, status=400)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    async def _get_environmental_data(self, request) -> web.Response:
        """Get current environmental conditions."""
        try:
            # Mock environmental data for Sprint 1 - replace with real sensor data in Phase 2
            import math
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            hour_of_day = now.hour + now.minute / 60.0

            # Calculate mock sun position (simplified)
            sun_elevation = max(0, 50 * math.sin(math.pi * (hour_of_day - 6) / 12))
            sun_azimuth = (hour_of_day - 6) * 15  # degrees

            # Determine golden/blue hour
            is_golden_hour = 5 <= sun_elevation <= 15
            is_blue_hour = -6 <= sun_elevation <= 4

            # Next golden hour calculation (simplified)
            next_golden_hour = None
            if not is_golden_hour:
                if hour_of_day < 6:
                    next_golden_hour = now.replace(hour=6, minute=0, second=0).isoformat()
                elif hour_of_day > 18:
                    next_golden_hour = (
                        now.replace(hour=6, minute=0, second=0) + timedelta(days=1)
                    ).isoformat()
                else:
                    next_golden_hour = now.replace(hour=18, minute=30, second=0).isoformat()

            environmental_data = {
                "sunElevation": round(sun_elevation, 2),
                "sunAzimuth": round(sun_azimuth % 360, 2),
                "isGoldenHour": is_golden_hour,
                "isBluHour": is_blue_hour,
                "nextGoldenHour": next_golden_hour,
                "temperature": 18.5 + 5 * math.sin(math.pi * hour_of_day / 12),
                "humidity": 45 + 10 * math.sin(math.pi * hour_of_day / 24),
                "cloudCover": 25 + 20 * math.sin(math.pi * hour_of_day / 8),
                "windSpeed": 2.5 + 1.5 * math.sin(math.pi * hour_of_day / 6),
            }

            return json_response(
                {
                    "data": environmental_data,
                    "status": 200,
                    "message": "Environmental data retrieved successfully",
                }
            )

        except Exception as e:
            return json_response({"error": str(e)}, status=500)

    def _format_system_status(self, status: dict) -> dict:
        """Format system status for WebSocket transmission."""
        return {
            "service": {
                "capture": "running" if status["service"]["running"] else "stopped",
                "processing": "running" if status["service"]["running"] else "stopped",
                "camera": "connected",  # Mock for Sprint 1
            },
            "camera": {
                "isConnected": True,
                "model": "Arducam IMX519 16MP",
                "resolution": {"width": 4656, "height": 3496},
                "currentSettings": {
                    "iso": 100,
                    "exposureTime": "1/250",
                    "whiteBalance": "daylight",
                    "imageFormat": "jpeg",
                    "quality": 95,
                    "hdr": {"enabled": False, "brackets": 3, "evSteps": 2},
                },
            },
            "storage": {
                "used": 1024 * 1024 * 1024 * 50,  # 50GB
                "total": 1024 * 1024 * 1024 * 500,  # 500GB
                "available": 1024 * 1024 * 1024 * 450,  # 450GB
                "percentage": 10,
            },
            "resources": status.get("statistics", {}),
        }

    # Frontend API Contract Implementation (Sprint 3)
    async def _get_gallery_sequences(self, request) -> web.Response:
        """Get paginated list of timelapse sequences - maps to existing recent gallery."""
        try:
            # Call existing _get_recent_gallery method directly to get data
            # Skip the response transformation and get the data directly
            recent_data = await self._get_recent_gallery_data()

            # Transform to match frontend expectations
            return json_response(
                {
                    "data": recent_data,
                    "pagination": {
                        "page": 1,
                        "limit": 20,
                        "total": len(recent_data),
                        "hasNext": False,
                    },
                    "status": 200,
                    "message": "Gallery sequences retrieved successfully",
                }
            )
        except Exception as e:
            logger.error(f"Error getting gallery sequences: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _get_recent_gallery_data(self):
        """Get recent gallery data - helper method to avoid response processing issues."""
        # Return mock data that matches the existing gallery structure
        return [
            {
                "id": "seq-001",
                "name": "Morning Mountain Vista",
                "thumbnailUrl": "/api/gallery/sequences/seq-001/thumbnail",
                "captureCount": 1247,
                "duration": "12h 30m",
                "startTime": "2025-09-28T06:00:00Z",
                "endTime": "2025-09-28T18:30:00Z",
                "status": "completed",
                "location": "Rocky Mountain National Park",
                "weather": "Clear skies",
            },
            {
                "id": "seq-002",
                "name": "Sunset Over Valley",
                "thumbnailUrl": "/api/gallery/sequences/seq-002/thumbnail",
                "captureCount": 892,
                "duration": "8h 15m",
                "startTime": "2025-09-27T10:00:00Z",
                "endTime": "2025-09-27T18:15:00Z",
                "status": "completed",
                "location": "Yosemite Valley",
                "weather": "Partly cloudy",
            },
            {
                "id": "seq-003",
                "name": "Alpine Meadow Dawn",
                "thumbnailUrl": "/api/gallery/sequences/seq-003/thumbnail",
                "captureCount": 567,
                "duration": "6h 45m",
                "startTime": "2025-09-26T05:30:00Z",
                "endTime": "2025-09-26T12:15:00Z",
                "status": "processing",
                "location": "Mount Rainier",
                "weather": "Foggy conditions",
            },
        ]

    async def _get_sequence_details(self, request) -> web.Response:
        """Get detailed information for specific sequence."""
        try:
            sequence_id = request.match_info["id"]

            # Mock detailed sequence data - extend this with real implementation
            sequence_detail = {
                "id": sequence_id,
                "name": f"Mountain Sequence {sequence_id}",
                "captureCount": 1234,
                "startTime": "2025-09-28T06:00:00Z",
                "endTime": "2025-09-28T18:00:00Z",
                "location": {"lat": 45.0, "lon": -110.0, "elevation": 2500},
                "camera": {"model": "Professional DSLR", "lens": "24-70mm f/2.8"},
                "settings": {"iso": 100, "aperture": "f/8", "shutterSpeed": "1/125"},
                "status": "completed",
                "thumbnailUrl": f"/api/gallery/sequences/{sequence_id}/thumbnail",
                "videoUrl": f"/api/gallery/sequences/{sequence_id}/video",
                "metadata": {
                    "weather": "Clear skies",
                    "temperature": "14°C",
                    "conditions": "Excellent visibility",
                },
            }

            return json_response(
                {
                    "data": sequence_detail,
                    "status": 200,
                    "message": "Sequence details retrieved successfully",
                }
            )
        except Exception as e:
            logger.error(f"Error getting sequence details: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _delete_sequence(self, request) -> web.Response:
        """Delete a timelapse sequence."""
        try:
            sequence_id = request.match_info["id"]
            logger.info(f"Delete request for sequence: {sequence_id}")

            # TODO: Implement actual deletion logic
            # For now, return success to satisfy API contract
            return json_response(
                {
                    "data": {"id": sequence_id, "deleted": True},
                    "status": 200,
                    "message": f"Sequence {sequence_id} deleted successfully",
                }
            )
        except Exception as e:
            logger.error(f"Error deleting sequence: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _generate_timelapse(self, request) -> web.Response:
        """Start timelapse generation job."""
        try:
            # Parse request body for generation parameters
            try:
                data = await request.json()
            except:
                data = {}

            # Mock job creation - extend with real job queue implementation
            job_id = f"job-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            generation_job = {
                "id": job_id,
                "status": "queued",
                "sequenceId": data.get("sequenceId", "unknown"),
                "settings": {
                    "frameRate": data.get("frameRate", 24),
                    "resolution": data.get("resolution", "1080p"),
                    "format": data.get("format", "mp4"),
                    "quality": data.get("quality", "high"),
                },
                "progress": 0,
                "estimatedCompletion": (datetime.now() + timedelta(minutes=30)).isoformat(),
                "createdAt": datetime.now().isoformat(),
            }

            return json_response(
                {
                    "data": generation_job,
                    "status": 200,
                    "message": "Timelapse generation job created successfully",
                }
            )
        except Exception as e:
            logger.error(f"Error creating generation job: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _get_generation_jobs(self, request) -> web.Response:
        """Get status of timelapse generation jobs."""
        try:
            # Mock jobs data - extend with real job tracking
            jobs = [
                {
                    "id": "job-20250928-120000",
                    "status": "completed",
                    "sequenceId": "seq-001",
                    "progress": 100,
                    "outputUrl": "/api/gallery/videos/job-20250928-120000.mp4",
                    "createdAt": "2025-09-28T12:00:00Z",
                    "completedAt": "2025-09-28T12:25:00Z",
                },
                {
                    "id": "job-20250928-140000",
                    "status": "processing",
                    "sequenceId": "seq-002",
                    "progress": 45,
                    "estimatedCompletion": "2025-09-28T14:30:00Z",
                    "createdAt": "2025-09-28T14:00:00Z",
                },
            ]

            return json_response(
                {"data": jobs, "status": 200, "message": "Generation jobs retrieved successfully"}
            )
        except Exception as e:
            logger.error(f"Error getting generation jobs: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _get_analytics_data(self, request) -> web.Response:
        """Get system analytics and metrics."""
        try:
            # Mock analytics data - extend with real metrics collection
            analytics = {
                "overview": {
                    "totalSequences": 42,
                    "totalCaptures": 15678,
                    "totalStorageUsed": "156.7 GB",
                    "systemUptime": "5 days, 12 hours",
                },
                "performance": {
                    "avgCaptureTime": "2.3s",
                    "successRate": 98.7,
                    "errorRate": 1.3,
                    "systemLoad": {"cpu": 23.5, "memory": 45.2, "disk": 10.1},
                },
                "capture": {
                    "dailyStats": [
                        {"date": "2025-09-28", "captures": 287, "sequences": 3},
                        {"date": "2025-09-27", "captures": 312, "sequences": 4},
                        {"date": "2025-09-26", "captures": 298, "sequences": 2},
                    ],
                    "qualityMetrics": {"excellent": 78.2, "good": 18.5, "fair": 2.8, "poor": 0.5},
                },
                "environment": {
                    "weatherConditions": {
                        "clear": 65.2,
                        "cloudy": 23.1,
                        "rainy": 8.7,
                        "stormy": 3.0,
                    },
                    "bestCaptureHours": ["06:00", "07:00", "18:00", "19:00"],
                },
            }

            return json_response(
                {
                    "data": analytics,
                    "status": 200,
                    "message": "Analytics data retrieved successfully",
                }
            )
        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            return json_response({"error": str(e)}, status=500)

    # Camera API Handlers
    async def _camera_stream(self, request) -> web.StreamResponse:
        """Stream live camera feed as MJPEG."""
        if not camera_service or not camera_service.is_connected():
            return web.Response(status=503, text="Camera not available")

        try:
            # Start streaming if not already started
            await camera_service.start_streaming()

            response = StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "multipart/x-mixed-replace; boundary=frame",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Access-Control-Allow-Origin": "*",
                },
            )
            await response.prepare(request)

            # Stream MJPEG frames
            async for frame_data in camera_service.generate_mjpeg_stream():
                try:
                    await response.write(frame_data)
                except Exception as e:
                    logger.warning(f"Client disconnected from camera stream: {e}")
                    break

            return response

        except Exception as e:
            logger.error(f"Error in camera stream: {e}")
            return web.Response(status=500, text=str(e))

    async def _get_camera_status(self, request) -> web.Response:
        """Get current camera status."""
        try:
            if not camera_service:
                return json_response({"error": "Camera service not available"}, status=503)

            status = camera_service.get_status()
            return json_response(
                {"data": status, "status": 200, "message": "Camera status retrieved successfully"}
            )

        except Exception as e:
            logger.error(f"Error getting camera status: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _get_camera_settings(self, request) -> web.Response:
        """Get current camera settings."""
        try:
            if not camera_service:
                return json_response({"error": "Camera service not available"}, status=503)

            settings = camera_service.get_settings()
            return json_response(
                {
                    "data": settings,
                    "status": 200,
                    "message": "Camera settings retrieved successfully",
                }
            )

        except Exception as e:
            logger.error(f"Error getting camera settings: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _update_camera_settings(self, request) -> web.Response:
        """Update camera settings."""
        try:
            if not camera_service:
                return json_response({"error": "Camera service not available"}, status=503)

            data = await request.json()
            success = await camera_service.update_settings(data)

            if success:
                updated_settings = camera_service.get_settings()
                return json_response(
                    {
                        "data": updated_settings,
                        "status": 200,
                        "message": "Camera settings updated successfully",
                    }
                )
            else:
                return json_response({"error": "Failed to update camera settings"}, status=400)

        except Exception as e:
            logger.error(f"Error updating camera settings: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _manual_capture(self, request) -> web.Response:
        """Trigger manual image capture."""
        try:
            if not camera_service:
                return json_response({"error": "Camera service not available"}, status=503)

            # Parse optional settings override
            try:
                data = await request.json()
                settings_override = data.get("settings", None)
            except:
                settings_override = None

            # Capture image
            capture_result = await camera_service.capture_image(settings_override)

            return json_response(
                {"data": capture_result, "status": 200, "message": "Image captured successfully"}
            )

        except Exception as e:
            logger.error(f"Error during manual capture: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _start_camera_stream(self, request) -> web.Response:
        """Start camera streaming."""
        try:
            if not camera_service:
                return json_response({"error": "Camera service not available"}, status=503)

            await camera_service.start_streaming()
            return json_response(
                {"data": {"streaming": True}, "status": 200, "message": "Camera streaming started"}
            )

        except Exception as e:
            logger.error(f"Error starting camera stream: {e}")
            return json_response({"error": str(e)}, status=500)

    async def _stop_camera_stream(self, request) -> web.Response:
        """Stop camera streaming."""
        try:
            if not camera_service:
                return json_response({"error": "Camera service not available"}, status=503)

            await camera_service.stop_streaming()
            return json_response(
                {"data": {"streaming": False}, "status": 200, "message": "Camera streaming stopped"}
            )

        except Exception as e:
            logger.error(f"Error stopping camera stream: {e}")
            return json_response({"error": str(e)}, status=500)
