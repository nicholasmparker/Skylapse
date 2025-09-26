"""REST API server for processing service control and monitoring."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

try:
    from aiohttp import web
    from aiohttp.web import json_response
except ImportError:
    web = None
    json_response = None

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
        self._is_running = False

        if web is None:
            logger.warning("aiohttp not available, API server will be disabled")

    async def start(self) -> None:
        """Start the API server."""
        if web is None:
            logger.warning("Processing API server disabled - aiohttp not available")
            return

        logger.info(f"Starting processing API server on port {self.port}")

        try:
            self.app = web.Application()
            self._setup_routes()

            # Add middleware
            self.app.middlewares.append(self._error_middleware)
            self.app.middlewares.append(self._logging_middleware)

            # Start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await self.site.start()

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

    def _setup_routes(self) -> None:
        """Setup API routes."""
        if web is None:
            return

        # Health check
        self.app.router.add_get('/health', self._health_check)

        # Status and information
        self.app.router.add_get('/status', self._get_status)

        # Job management
        self.app.router.add_post('/jobs', self._create_job)
        self.app.router.add_get('/jobs/{job_id}', self._get_job_status)
        self.app.router.add_get('/jobs', self._list_recent_jobs)
        self.app.router.add_delete('/jobs/{job_id}', self._cancel_job)

        # Processing operations
        self.app.router.add_post('/process/images', self._process_images)
        self.app.router.add_post('/process/timelapse', self._create_timelapse)

        # Results and outputs
        self.app.router.add_get('/timelapses', self._get_recent_timelapses)
        self.app.router.add_get('/statistics', self._get_statistics)

        # Transfer management (for testing)
        self.app.router.add_post('/transfers/simulate', self._simulate_transfer)
        self.app.router.add_get('/transfers/pending', self._get_pending_transfers)

    @web.middleware
    async def _error_middleware(self, request, handler):
        """Error handling middleware."""
        try:
            return await handler(request)
        except Exception as e:
            logger.error(f"Processing API error: {e}\n{traceback.format_exc()}")
            return json_response({
                'error': str(e),
                'type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }, status=500)

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
            return json_response({'status': 'unhealthy', 'reason': 'no_controller'}, status=503)

        try:
            status = await self.controller.get_service_status()
            if status['service']['running']:
                return json_response({
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0.0-sprint1'
                })
            else:
                return json_response({
                    'status': 'unhealthy',
                    'reason': 'service_not_running'
                }, status=503)

        except Exception as e:
            return json_response({
                'status': 'unhealthy',
                'reason': str(e)
            }, status=503)

    async def _get_status(self, request) -> web.Response:
        """Get comprehensive service status."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            status = await self.controller.get_service_status()
            return json_response(status)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _create_job(self, request) -> web.Response:
        """Create a new processing job."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            job_data = await request.json()
            job_id = await self.controller.add_processing_job(job_data)

            return json_response({
                'job_id': job_id,
                'status': 'created'
            })

        except json.JSONDecodeError:
            return json_response({'error': 'Invalid JSON in request body'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _get_job_status(self, request) -> web.Response:
        """Get status of a specific job."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            job_id = request.match_info['job_id']
            status = await self.controller.get_job_status(job_id)
            return json_response(status)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _list_recent_jobs(self, request) -> web.Response:
        """List recent jobs."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            limit = int(request.query.get('limit', 10))
            jobs = await self.controller._job_queue.get_recent_jobs(limit)
            return json_response({'jobs': jobs})
        except ValueError:
            return json_response({'error': 'Invalid limit parameter'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _cancel_job(self, request) -> web.Response:
        """Cancel a job."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            job_id = request.match_info['job_id']
            success = await self.controller._job_queue.cancel_job(job_id)

            if success:
                return json_response({'status': 'cancelled'})
            else:
                return json_response({'error': 'Job could not be cancelled'}, status=400)

        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _process_images(self, request) -> web.Response:
        """Process a batch of images."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            data = await request.json()
            image_paths = data.get('image_paths', [])
            metadata = data.get('metadata', {})
            processing_options = data.get('processing_options', {})

            if not image_paths:
                return json_response({'error': 'No image paths provided'}, status=400)

            # Create processing job
            job_data = {
                'type': 'image_processing',
                'image_paths': image_paths,
                'metadata': metadata,
                'processing_options': processing_options,
                'priority': 'normal'
            }

            job_id = await self.controller.add_processing_job(job_data)

            return json_response({
                'job_id': job_id,
                'status': 'queued',
                'image_count': len(image_paths)
            })

        except json.JSONDecodeError:
            return json_response({'error': 'Invalid JSON in request body'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _create_timelapse(self, request) -> web.Response:
        """Create a timelapse from processed images."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            data = await request.json()
            processed_images = data.get('processed_images', [])
            metadata = data.get('metadata', {})
            output_formats = data.get('output_formats', ['1080p'])

            if not processed_images:
                return json_response({'error': 'No processed images provided'}, status=400)

            # Create timelapse assembly job
            job_data = {
                'type': 'timelapse_assembly',
                'processed_images': processed_images,
                'metadata': metadata,
                'output_formats': output_formats,
                'priority': 'low'
            }

            job_id = await self.controller.add_processing_job(job_data)

            return json_response({
                'job_id': job_id,
                'status': 'queued',
                'frame_count': len(processed_images)
            })

        except json.JSONDecodeError:
            return json_response({'error': 'Invalid JSON in request body'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _get_recent_timelapses(self, request) -> web.Response:
        """Get recent timelapses."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            limit = int(request.query.get('limit', 10))
            timelapses = await self.controller.get_recent_timelapses(limit)
            return json_response({'timelapses': timelapses})
        except ValueError:
            return json_response({'error': 'Invalid limit parameter'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _get_statistics(self, request) -> web.Response:
        """Get processing service statistics."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            status = await self.controller.get_service_status()
            return json_response({
                'statistics': status.get('statistics', {}),
                'components': status.get('components', {}),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _simulate_transfer(self, request) -> web.Response:
        """Simulate an incoming transfer (for testing)."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            data = await request.json()
            image_paths = data.get('image_paths', [])
            metadata = data.get('metadata', {})

            if not image_paths:
                return json_response({'error': 'No image paths provided'}, status=400)

            transfer_id = await self.controller._transfer_receiver.simulate_incoming_transfer(
                image_paths, metadata
            )

            return json_response({
                'transfer_id': transfer_id,
                'status': 'simulated',
                'image_count': len(image_paths)
            })

        except json.JSONDecodeError:
            return json_response({'error': 'Invalid JSON in request body'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

    async def _get_pending_transfers(self, request) -> web.Response:
        """Get pending transfers."""
        if not self.controller:
            return json_response({'error': 'Service not available'}, status=503)

        try:
            pending = await self.controller._transfer_receiver.get_pending_transfers()
            return json_response({'transfers': pending})
        except Exception as e:
            return json_response({'error': str(e)}, status=500)