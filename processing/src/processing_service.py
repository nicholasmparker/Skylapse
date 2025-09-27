"""Main processing service for the Skylapse timelapse system."""

import asyncio
import logging
import signal
import time
from typing import Any, Dict, List, Optional

from .api_server import ProcessingAPIServer
from .config_manager import ProcessingConfigManager
from .image_processor import ImageProcessor
from .job_queue import JobQueue
from .timelapse_assembler import TimelapseAssembler
from .transfer_receiver import TransferReceiver

logger = logging.getLogger(__name__)


class ProcessingService:
    """Main processing service orchestrating image processing and timelapse assembly."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize the processing service."""
        self._config = ProcessingConfigManager(config_file)
        self._image_processor = ImageProcessor()
        self._timelapse_assembler = TimelapseAssembler()
        self._transfer_receiver = TransferReceiver()
        self._job_queue = JobQueue()
        self._api_server = ProcessingAPIServer(
            port=self._config.get("api.port", 8081), controller=self
        )

        self._is_running = False
        self._shutdown_event = asyncio.Event()
        self._processing_task: Optional[asyncio.Task] = None
        self._transfer_task: Optional[asyncio.Task] = None
        self._maintenance_task: Optional[asyncio.Task] = None

        # Performance monitoring
        self._service_start_time = time.time()
        self._processing_stats = {
            "images_processed": 0,
            "timelapses_created": 0,
            "processing_errors": 0,
            "average_processing_time_ms": 0.0,
        }

    async def start(self) -> None:
        """Start the processing service."""
        logger.info("Starting Skylapse processing service")

        try:
            # Initialize all components
            await self._initialize_components()

            # Start background tasks
            self._processing_task = asyncio.create_task(self._processing_loop())
            self._transfer_task = asyncio.create_task(self._transfer_loop())
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())

            # Start API server
            await self._api_server.start()

            self._is_running = True
            logger.info("Processing service started successfully")

            # Set up signal handlers
            self._setup_signal_handlers()

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Failed to start processing service: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the processing service gracefully."""
        if not self._is_running:
            return

        logger.info("Shutting down processing service")
        self._is_running = False

        # Stop API server
        await self._api_server.shutdown()

        # Cancel background tasks
        tasks = [self._processing_task, self._transfer_task, self._maintenance_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Shutdown components
        await self._shutdown_components()

        logger.info("Processing service shutdown complete")

    async def _initialize_components(self) -> None:
        """Initialize all service components."""
        logger.info("Initializing processing service components")

        # Initialize image processor
        await self._image_processor.initialize()

        # Initialize timelapse assembler
        await self._timelapse_assembler.initialize()

        # Initialize transfer receiver
        await self._transfer_receiver.initialize()

        # Initialize job queue
        await self._job_queue.initialize()

        logger.info("All processing components initialized successfully")

    async def _shutdown_components(self) -> None:
        """Shutdown all service components."""
        logger.info("Shutting down processing service components")

        if self._job_queue:
            await self._job_queue.shutdown()

        if self._transfer_receiver:
            await self._transfer_receiver.shutdown()

        if self._timelapse_assembler:
            await self._timelapse_assembler.shutdown()

        if self._image_processor:
            await self._image_processor.shutdown()

        logger.info("All processing components shut down")

    async def _processing_loop(self) -> None:
        """Main processing loop handling image processing jobs."""
        logger.info("Starting processing loop")

        while self._is_running:
            try:
                # Get next job from queue
                job = await self._job_queue.get_next_job()
                if job:
                    await self._process_job(job)
                else:
                    # No jobs available, wait a bit
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(10)  # Pause before retry

        logger.info("Processing loop stopped")

    async def _transfer_loop(self) -> None:
        """Background loop handling incoming file transfers."""
        logger.info("Starting transfer receiver loop")

        while self._is_running:
            try:
                # Check for new transfers
                new_transfers = await self._transfer_receiver.check_for_transfers()

                for transfer in new_transfers:
                    # Create processing job for new transfer
                    await self._job_queue.add_job(
                        {
                            "type": "image_processing",
                            "transfer_id": transfer["id"],
                            "image_paths": transfer["image_paths"],
                            "metadata": transfer["metadata"],
                            "priority": "normal",
                        }
                    )

                # Wait before next check
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in transfer loop: {e}")
                await asyncio.sleep(10)

        logger.info("Transfer receiver loop stopped")

    async def _maintenance_loop(self) -> None:
        """Background maintenance tasks."""
        logger.info("Starting maintenance loop")

        while self._is_running:
            try:
                # Cleanup old processed files
                await self._cleanup_old_files()

                # Update service statistics
                await self._update_statistics()

                # Wait for next maintenance cycle
                await asyncio.sleep(3600)  # Every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(300)

        logger.info("Maintenance loop stopped")

    async def _process_job(self, job: Dict[str, Any]) -> None:
        """Process a single job from the queue."""
        job_id = job.get("id")
        job_type = job.get("type")

        logger.info(f"Processing job {job_id}: {job_type}")
        start_time = time.time()

        try:
            if job_type == "image_processing":
                await self._process_images_job(job)
            elif job_type == "timelapse_assembly":
                await self._process_timelapse_job(job)
            else:
                logger.warning(f"Unknown job type: {job_type}")
                await self._job_queue.mark_job_failed(job_id, f"Unknown job type: {job_type}")
                return

            # Mark job as completed
            processing_time = (time.time() - start_time) * 1000
            await self._job_queue.mark_job_completed(job_id)

            # Update statistics
            self._processing_stats["images_processed"] += len(job.get("image_paths", []))
            self._update_average_processing_time(processing_time)

            logger.info(f"Job {job_id} completed in {processing_time:.1f}ms")

        except Exception as e:
            # Mark job as failed
            await self._job_queue.mark_job_failed(job_id, str(e))
            self._processing_stats["processing_errors"] += 1

            logger.error(f"Job {job_id} failed: {e}")

    async def _process_images_job(self, job: Dict[str, Any]) -> None:
        """Process images for enhancement and preparation."""
        image_paths = job["image_paths"]
        metadata = job.get("metadata", {})

        # Process each image
        processed_results = []
        for image_path in image_paths:
            result = await self._image_processor.process_image(
                image_path=image_path,
                metadata=metadata,
                processing_options=job.get("processing_options", {}),
            )
            processed_results.append(result)

        # Check if we should create a timelapse
        if self._should_create_timelapse(processed_results):
            # Queue timelapse assembly job
            await self._job_queue.add_job(
                {
                    "type": "timelapse_assembly",
                    "processed_images": processed_results,
                    "metadata": metadata,
                    "priority": "low",
                }
            )

    async def _process_timelapse_job(self, job: Dict[str, Any]) -> None:
        """Process timelapse assembly job."""
        processed_images = job["processed_images"]
        metadata = job.get("metadata", {})

        # Assemble timelapse
        timelapse_result = await self._timelapse_assembler.create_timelapse(
            images=processed_images, metadata=metadata, output_formats=["1080p", "4k"]
        )

        if timelapse_result["success"]:
            self._processing_stats["timelapses_created"] += 1
            logger.info(f"Timelapse created: {timelapse_result['output_path']}")

    def _should_create_timelapse(self, processed_results: List[Dict[str, Any]]) -> bool:
        """Determine if processed images should be assembled into a timelapse."""
        # For Sprint 1, use simple heuristics
        # Phase 2 will add intelligent sequence detection

        # Check if we have enough images from the same session
        if len(processed_results) < 10:
            return False

        # Check time span (should be at least 10 minutes)
        timestamps = [r.get("timestamp", 0) for r in processed_results]
        if timestamps:
            time_span = max(timestamps) - min(timestamps)
            if time_span < 600:  # 10 minutes
                return False

        return True

    async def _cleanup_old_files(self) -> None:
        """Clean up old processed files."""
        # Stub for Sprint 1 - will implement proper cleanup logic
        logger.debug("Performing maintenance cleanup")

    async def _update_statistics(self) -> None:
        """Update service statistics."""
        # Update any derived statistics
        uptime = time.time() - self._service_start_time
        logger.debug(f"Service uptime: {uptime:.1f}s")

    def _update_average_processing_time(self, processing_time_ms: float) -> None:
        """Update running average of processing times."""
        current_avg = self._processing_stats["average_processing_time_ms"]
        processed_count = self._processing_stats["images_processed"]

        if processed_count > 0:
            self._processing_stats["average_processing_time_ms"] = (
                current_avg * (processed_count - 1) + processing_time_ms
            ) / processed_count

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    # Public API methods

    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        uptime_seconds = time.time() - self._service_start_time

        return {
            "service": {
                "running": self._is_running,
                "uptime_seconds": uptime_seconds,
                "version": "1.0.0-sprint1",
            },
            "components": {
                "image_processor": await self._image_processor.get_status(),
                "timelapse_assembler": await self._timelapse_assembler.get_status(),
                "job_queue": await self._job_queue.get_status(),
                "transfer_receiver": await self._transfer_receiver.get_status(),
            },
            "statistics": self._processing_stats,
        }

    async def add_processing_job(self, job_data: Dict[str, Any]) -> str:
        """Add a new processing job to the queue."""
        return await self._job_queue.add_job(job_data)

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a specific job."""
        return await self._job_queue.get_job_status(job_id)

    async def get_recent_timelapses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about recently created timelapses."""
        return await self._timelapse_assembler.get_recent_timelapses(limit)


# Entry point for Docker container
async def main():
    """Main entry point for the processing service."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )

    # Create and start service
    service = ProcessingService()
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
