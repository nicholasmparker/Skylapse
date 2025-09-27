"""Main capture service for the Skylapse timelapse system."""

import asyncio
import logging
import signal
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

from .camera_controller import CameraController
from .storage_manager import StorageManager
from .scheduler import CaptureScheduler
from .environmental_sensing import EnvironmentalSensor
from .transfer_manager import TransferManager
from .api_server import CaptureAPIServer
from .config_manager import SystemConfigManager
from .camera_types import EnvironmentalConditions, CaptureSettings

logger = logging.getLogger(__name__)


class CaptureService:
    """Main capture service orchestrating all components."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize the capture service."""
        self._config = SystemConfigManager(config_file)
        self._camera_controller = CameraController()
        self._storage_manager = StorageManager(
            buffer_path=self._config.get("storage.capture_buffer_path"),
            max_size_gb=self._config.get("storage.max_buffer_size_gb"),
            retention_hours=self._config.get("storage.buffer_retention_hours"),
        )
        self._scheduler = CaptureScheduler()
        self._environmental_sensor = EnvironmentalSensor()
        self._transfer_manager = TransferManager(
            {
                "queue_dir": self._config.get("storage.capture_buffer_path") + "/transfer_queue",
                "target_dir": "/opt/skylapse/transfers/incoming",
                "processing_host": self._config.get("network.processing_service_host"),
                "processing_port": self._config.get("network.processing_service_port"),
                "use_rsync": self._config.get("network.use_rsync", False),
                "max_retries": self._config.get("network.transfer_retry_attempts", 3),
            }
        )
        self._api_server = CaptureAPIServer(
            port=self._config.get("capture.service_port"), controller=self
        )

        self._is_running = False
        self._shutdown_event = asyncio.Event()
        self._capture_task: Optional[asyncio.Task] = None
        self._transfer_task: Optional[asyncio.Task] = None
        self._maintenance_task: Optional[asyncio.Task] = None

        # Performance monitoring
        self._service_start_time = time.time()
        self._last_health_check = time.time()

    async def start(self) -> None:
        """Start the capture service."""
        logger.info("Starting Skylapse capture service")

        try:
            # Initialize all components
            await self._initialize_components()

            # Start background tasks
            self._capture_task = asyncio.create_task(self._capture_loop())
            self._transfer_task = asyncio.create_task(self._transfer_loop())
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())

            # Start API server
            await self._api_server.start()

            self._is_running = True
            logger.info("Capture service started successfully")

            # Set up signal handlers
            self._setup_signal_handlers()

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Failed to start capture service: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the capture service gracefully."""
        if not self._is_running:
            return

        logger.info("Shutting down capture service")
        self._is_running = False

        # Stop API server
        await self._api_server.shutdown()

        # Cancel background tasks
        tasks = [self._capture_task, self._transfer_task, self._maintenance_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Shutdown components
        await self._shutdown_components()

        logger.info("Capture service shutdown complete")

    async def _initialize_components(self) -> None:
        """Initialize all service components."""
        logger.info("Initializing service components")

        # Initialize camera controller
        await self._camera_controller.initialize_camera()

        # Initialize storage manager
        await self._storage_manager.initialize()

        # Initialize environmental sensor
        await self._environmental_sensor.initialize()

        # Initialize transfer manager
        await self._transfer_manager.initialize()

        # Initialize scheduler
        await self._scheduler.initialize()

        logger.info("All components initialized successfully")

    async def _shutdown_components(self) -> None:
        """Shutdown all service components."""
        logger.info("Shutting down service components")

        # Shutdown in reverse order
        if self._scheduler:
            await self._scheduler.shutdown()

        if self._environmental_sensor:
            await self._environmental_sensor.shutdown()

        if self._transfer_manager:
            await self._transfer_manager.shutdown()

        if self._storage_manager:
            await self._storage_manager.shutdown()

        if self._camera_controller:
            await self._camera_controller.shutdown()

        logger.info("All components shut down")

    async def _capture_loop(self) -> None:
        """Main capture loop handling scheduled captures."""
        logger.info("Starting capture loop")

        while self._is_running:
            try:
                # Check if it's time for a capture
                if await self._scheduler.should_capture():
                    await self._perform_scheduled_capture()

                # Wait for next check interval
                await asyncio.sleep(self._config.get("capture.check_interval_seconds", 10))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

        logger.info("Capture loop stopped")

    async def _transfer_loop(self) -> None:
        """Background transfer processing loop."""
        logger.info("Starting transfer loop")

        while self._is_running:
            try:
                # Process pending transfers
                results = await self._transfer_manager.process_pending_transfers()

                if results:
                    completed = len([r for r in results if r["status"] == "completed"])
                    failed = len([r for r in results if r["status"] == "failed"])
                    logger.info(
                        f"Transfer batch completed: {completed} successful, {failed} failed"
                    )

                # Wait before next transfer check
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in transfer loop: {e}")
                await asyncio.sleep(10)

        logger.info("Transfer loop stopped")

    async def _maintenance_loop(self) -> None:
        """Background maintenance tasks."""
        logger.info("Starting maintenance loop")

        while self._is_running:
            try:
                # Perform storage cleanup
                await self._storage_manager.cleanup_old_files()

                # Update health metrics
                self._last_health_check = time.time()

                # Wait for next maintenance cycle
                cleanup_interval_hours = self._config.get("storage.cleanup_interval_hours", 6)
                await asyncio.sleep(cleanup_interval_hours * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(300)  # 5 minute pause on error

        logger.info("Maintenance loop stopped")

    async def _perform_scheduled_capture(self) -> None:
        """Perform a scheduled capture operation."""
        try:
            logger.info("Performing scheduled capture")

            # Get current environmental conditions
            conditions = await self._environmental_sensor.get_current_conditions()

            # Get optimal capture settings
            base_settings = self._scheduler.get_current_capture_settings()

            # Perform optimized capture
            result = await self._camera_controller.capture_optimized(
                conditions=conditions, base_settings=base_settings
            )

            # Store captured images
            stored_paths = await self._storage_manager.store_capture_result(result)

            # Schedule image transfer to processing service
            await self._schedule_image_transfer(stored_paths, result)

            # Update scheduler with capture result
            await self._scheduler.record_capture_result(result, conditions)

            logger.info(f"Scheduled capture completed: {len(stored_paths)} images stored")

        except Exception as e:
            logger.error(f"Scheduled capture failed: {e}")
            # Record failure with scheduler
            await self._scheduler.record_capture_failure(str(e))

    async def _schedule_image_transfer(self, image_paths: list[str], result) -> None:
        """Schedule transfer of captured images to processing service."""
        try:
            # Queue images for transfer
            transfer_id = await self._transfer_manager.queue_transfer(
                image_paths=image_paths,
                metadata={
                    "capture_metadata": result.metadata,
                    "capture_time_ms": result.capture_time_ms,
                    "quality_score": result.quality_score,
                    "actual_settings": {
                        "exposure_time_us": result.actual_settings.exposure_time_us,
                        "iso": result.actual_settings.iso,
                        "white_balance_k": result.actual_settings.white_balance_k,
                    },
                },
                priority="normal",
            )
            logger.info(f"Queued transfer {transfer_id} for {len(image_paths)} images")
        except Exception as e:
            logger.error(f"Failed to queue image transfer: {e}")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    # Public API methods for external control

    async def manual_capture(self, settings: Optional[CaptureSettings] = None) -> Dict[str, Any]:
        """Perform a manual capture operation."""
        try:
            logger.info("Performing manual capture")

            # Get current conditions
            conditions = await self._environmental_sensor.get_current_conditions()

            # Use provided settings or get defaults
            if settings is None:
                settings = CaptureSettings()

            # Perform capture
            result = await self._camera_controller.capture_optimized(
                conditions=conditions, base_settings=settings
            )

            # Store result
            stored_paths = await self._storage_manager.store_capture_result(result)

            return {
                "success": True,
                "capture_time_ms": result.capture_time_ms,
                "image_count": len(result.file_paths),
                "stored_paths": stored_paths,
                "quality_score": result.quality_score,
                "metadata": result.metadata,
            }

        except Exception as e:
            logger.error(f"Manual capture failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "capture_time_ms": 0,
                "image_count": 0,
                "stored_paths": [],
            }

    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        uptime_seconds = time.time() - self._service_start_time

        # Get component statuses
        camera_status = await self._camera_controller.get_camera_status()
        storage_status = await self._storage_manager.get_status()
        scheduler_status = await self._scheduler.get_status()
        environmental_status = await self._environmental_sensor.get_status()

        return {
            "service": {
                "running": self._is_running,
                "uptime_seconds": uptime_seconds,
                "last_health_check": self._last_health_check,
                "version": "1.0.0-sprint1",
            },
            "camera": camera_status,
            "storage": storage_status,
            "scheduler": scheduler_status,
            "environmental": environmental_status,
        }

    async def update_configuration(self, config_updates: Dict[str, Any]) -> bool:
        """Update service configuration at runtime."""
        try:
            self._config.update(config_updates)
            logger.info("Configuration updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False

    async def get_recent_captures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about recent captures."""
        return await self._storage_manager.get_recent_captures(limit)

    async def get_live_preview(self) -> Optional[bytes]:
        """Get live camera preview."""
        return await self._camera_controller.get_live_preview()


# Entry point for systemd service
async def main():
    """Main entry point for the capture service."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("/opt/skylapse/logs/capture.log")],
    )

    # Create and start service
    service = CaptureService()
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
