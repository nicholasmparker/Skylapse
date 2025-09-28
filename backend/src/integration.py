"""
Integration module for connecting existing processing backend with new real-time server.
Provides event broadcasting capabilities to replace broken Socket.IO implementation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class RealTimeBroadcaster:
    """
    Integrates with the new production WebSocket server to broadcast events.
    Replaces the broken Socket.IO broadcasting in the original processing backend.
    """

    def __init__(self, realtime_server_url: str = "http://realtime-backend:8082"):
        self.realtime_server_url = realtime_server_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        """Initialize the broadcaster."""
        self.session = aiohttp.ClientSession()
        logger.info(f"Real-time broadcaster initialized for {self.realtime_server_url}")

    async def shutdown(self) -> None:
        """Shutdown the broadcaster."""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Real-time broadcaster shutdown complete")

    async def broadcast_event(self, channel: str, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Broadcast an event to all subscribers of a channel.

        Args:
            channel: Channel name (e.g., 'dashboard')
            event_type: Event type (e.g., 'system.status', 'capture.progress')
            data: Event data payload

        Returns:
            bool: True if broadcast was successful
        """
        if not self.session:
            logger.warning("Broadcaster not initialized")
            return False

        try:
            message = {
                "channel": channel,
                "message": {
                    "type": "dashboard_event",
                    "event": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                },
            }

            async with self.session.post(
                f"{self.realtime_server_url}/broadcast",
                json=message,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.debug(f"Broadcast '{event_type}' to {result.get('sent_to', 0)} clients")
                    return True
                else:
                    logger.warning(f"Broadcast failed: HTTP {response.status}")
                    return False

        except asyncio.TimeoutError:
            logger.warning(f"Broadcast timeout for event '{event_type}'")
            return False
        except Exception as e:
            logger.error(f"Broadcast error for event '{event_type}': {e}")
            return False

    # Convenience methods for common dashboard events

    async def broadcast_system_status(self, status_data: Dict[str, Any]) -> bool:
        """Broadcast system status update."""
        return await self.broadcast_event("dashboard", "system.status", status_data)

    async def broadcast_capture_progress(self, progress_data: Dict[str, Any]) -> bool:
        """Broadcast capture progress update."""
        return await self.broadcast_event("dashboard", "capture.progress", progress_data)

    async def broadcast_resource_update(self, resource_data: Dict[str, Any]) -> bool:
        """Broadcast resource metrics update."""
        return await self.broadcast_event("dashboard", "resource.update", resource_data)

    async def broadcast_capture_complete(self, capture_data: Dict[str, Any]) -> bool:
        """Broadcast capture completion."""
        return await self.broadcast_event("dashboard", "capture.complete", capture_data)

    async def broadcast_error(self, error_data: Dict[str, Any]) -> bool:
        """Broadcast error notification."""
        return await self.broadcast_event("dashboard", "error.occurred", error_data)

    async def check_health(self) -> bool:
        """Check if the real-time server is healthy."""
        if not self.session:
            return False

        try:
            async with self.session.get(
                f"{self.realtime_server_url}/health", timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                return response.status == 200
        except Exception:
            return False


# Global broadcaster instance
_broadcaster: Optional[RealTimeBroadcaster] = None


def get_broadcaster() -> RealTimeBroadcaster:
    """Get the global broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = RealTimeBroadcaster()
    return _broadcaster


async def initialize_broadcaster() -> None:
    """Initialize the global broadcaster."""
    broadcaster = get_broadcaster()
    await broadcaster.start()


async def shutdown_broadcaster() -> None:
    """Shutdown the global broadcaster."""
    global _broadcaster
    if _broadcaster:
        await _broadcaster.shutdown()
        _broadcaster = None


# Integration functions for existing processing backend
class ProcessingBackendIntegration:
    """
    Integration class that can be added to the existing processing backend
    to enable real-time event broadcasting.
    """

    def __init__(self):
        self.broadcaster = get_broadcaster()

    async def start(self) -> None:
        """Start the integration."""
        await self.broadcaster.start()
        logger.info("Processing backend real-time integration started")

    async def shutdown(self) -> None:
        """Shutdown the integration."""
        await self.broadcaster.shutdown()
        logger.info("Processing backend real-time integration shutdown")

    # Methods to be called from existing processing backend

    async def on_job_started(self, job_id: str, job_type: str, job_data: Dict[str, Any]) -> None:
        """Called when a processing job starts."""
        await self.broadcaster.broadcast_capture_progress(
            {
                "job_id": job_id,
                "type": job_type,
                "status": "started",
                "progress": 0,
                "data": job_data,
            }
        )

    async def on_job_progress(
        self, job_id: str, progress: float, status: str = "processing"
    ) -> None:
        """Called when a job makes progress."""
        await self.broadcaster.broadcast_capture_progress(
            {"job_id": job_id, "status": status, "progress": progress}
        )

    async def on_job_completed(self, job_id: str, result: Dict[str, Any]) -> None:
        """Called when a job completes."""
        await self.broadcaster.broadcast_capture_complete(
            {"job_id": job_id, "status": "completed", "result": result}
        )

    async def on_job_failed(self, job_id: str, error: str) -> None:
        """Called when a job fails."""
        await self.broadcaster.broadcast_error(
            {"job_id": job_id, "error": {"message": error, "type": "job_failed"}}
        )

    async def on_system_status_change(self, status: Dict[str, Any]) -> None:
        """Called when system status changes."""
        await self.broadcaster.broadcast_system_status(status)

    async def on_resource_update(self, metrics: Dict[str, Any]) -> None:
        """Called when resource metrics are updated."""
        await self.broadcaster.broadcast_resource_update(metrics)


# Example integration for existing processing API server
def integrate_with_processing_api_server():
    """
    Example of how to integrate the new real-time broadcaster with the existing
    ProcessingAPIServer class. This should be added to the existing codebase.
    """

    # This code should be added to the existing ProcessingAPIServer class:

    """
    class ProcessingAPIServer:
        def __init__(self, port: int = 8081, controller=None):
            # ... existing initialization ...
            self.realtime_integration = ProcessingBackendIntegration()

        async def start(self) -> None:
            # ... existing start logic ...

            # Add real-time integration startup
            try:
                await self.realtime_integration.start()
                logger.info("Real-time integration enabled")
            except Exception as e:
                logger.warning(f"Real-time integration failed to start: {e}")

        async def shutdown(self) -> None:
            # Add real-time integration shutdown
            try:
                await self.realtime_integration.shutdown()
            except Exception as e:
                logger.warning(f"Real-time integration shutdown error: {e}")

            # ... existing shutdown logic ...

        # Modify existing event methods to broadcast:

        async def _create_job(self, request) -> web.Response:
            # ... existing job creation logic ...

            # Add real-time broadcasting
            await self.realtime_integration.on_job_started(job_id, job_data.get('type'), job_data)

            # ... rest of existing logic ...

        # Add similar integration points throughout the existing code
    """


if __name__ == "__main__":
    # Test the integration
    async def test_integration():
        integration = ProcessingBackendIntegration()
        await integration.start()

        # Test event broadcasting
        await integration.on_system_status_change(
            {
                "service": {"capture": "running", "processing": "running"},
                "timestamp": datetime.now().isoformat(),
            }
        )

        await integration.shutdown()

    asyncio.run(test_integration())
