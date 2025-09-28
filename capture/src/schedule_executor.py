"""Schedule execution engine for managing automated captures."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .camera_types import CaptureSettings, EnvironmentalConditions
from .schedule_models import ScheduleRule, ScheduleStatus
from .schedule_storage import ScheduleStorageManager

logger = logging.getLogger(__name__)


class ScheduleExecutor:
    """Executes scheduled capture operations based on stored schedules."""

    def __init__(self, schedule_storage: ScheduleStorageManager):
        """Initialize schedule executor."""
        self.schedule_storage = schedule_storage
        self._is_running = False
        self._execution_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the schedule execution engine."""
        if self._is_running:
            return

        logger.info("Starting schedule executor")
        self._is_running = True
        self._execution_task = asyncio.create_task(self._execution_loop())

    async def stop(self) -> None:
        """Stop the schedule execution engine."""
        if not self._is_running:
            return

        logger.info("Stopping schedule executor")
        self._is_running = False

        if self._execution_task and not self._execution_task.done():
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass

    async def _execution_loop(self) -> None:
        """Main execution loop for checking and executing schedules."""
        logger.info("Schedule execution loop started")

        while self._is_running:
            try:
                # Check for schedules ready for execution
                ready_schedules = await self.schedule_storage.get_schedules_ready_for_execution()

                for schedule in ready_schedules:
                    await self._execute_schedule(schedule)

                # Wait before next check (every 30 seconds)
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in schedule execution loop: {e}")
                await asyncio.sleep(10)  # Brief pause on error

        logger.info("Schedule execution loop stopped")

    async def _execute_schedule(self, schedule: ScheduleRule) -> None:
        """Execute a single schedule."""
        try:
            logger.info(f"Executing schedule: {schedule.name} (ID: {schedule.id})")

            # Check if conditions are met (if specified)
            if schedule.conditions and not await self._check_conditions(schedule):
                logger.info(f"Conditions not met for schedule {schedule.name}, skipping execution")
                # Reschedule for next interval
                await self.schedule_storage.update_execution_status(schedule.id, success=True)
                return

            # Get capture settings
            capture_settings = self._get_capture_settings(schedule)

            # Here we would trigger the actual capture
            # For now, we'll simulate a successful capture
            # In the real implementation, this would call the camera controller
            await self._simulate_capture(schedule, capture_settings)

            # Update execution status
            await self.schedule_storage.update_execution_status(schedule.id, success=True)

            logger.info(f"Successfully executed schedule: {schedule.name}")

        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule.name}: {e}")
            await self.schedule_storage.update_execution_status(schedule.id, success=False)

    async def _check_conditions(self, schedule: ScheduleRule) -> bool:
        """Check if environmental conditions are met for schedule execution."""
        if not schedule.conditions:
            return True

        # TODO: Integrate with environmental sensing
        # For now, return True to allow execution
        # In the real implementation, this would check:
        # - Weather conditions if weather_dependent is True
        # - Light levels against min_light_level
        # - Wind speed against max_wind_speed

        return True

    def _get_capture_settings(self, schedule: ScheduleRule) -> CaptureSettings:
        """Convert schedule capture settings to CaptureSettings object."""
        settings = CaptureSettings()

        if schedule.capture_settings.preset:
            # Handle preset-based settings
            settings.processing_hints = {"preset": schedule.capture_settings.preset}

        elif schedule.capture_settings.manual:
            # Handle manual settings
            manual = schedule.capture_settings.manual
            settings.iso = manual.get("iso", 100)
            settings.exposure_time_us = self._exposure_time_to_microseconds(
                manual.get("exposureTime", "1/125")
            )
            settings.quality = manual.get("quality", 95)

            if manual.get("hdrBracketing", False):
                settings.hdr_bracket_stops = [-1, 0, 1]  # 3-stop HDR

        # Add schedule metadata
        settings.processing_hints = settings.processing_hints or {}
        settings.processing_hints.update(
            {"schedule_id": schedule.id, "schedule_name": schedule.name}
        )

        return settings

    def _exposure_time_to_microseconds(self, exposure_time_str: str) -> int:
        """Convert exposure time string to microseconds."""
        try:
            if "/" in exposure_time_str:
                # Handle fractional exposure times like "1/125"
                numerator, denominator = exposure_time_str.split("/")
                seconds = float(numerator) / float(denominator)
            else:
                # Handle decimal exposure times
                seconds = float(exposure_time_str)

            return int(seconds * 1_000_000)  # Convert to microseconds

        except (ValueError, ZeroDivisionError):
            logger.warning(f"Invalid exposure time format: {exposure_time_str}, using default")
            return 8000  # Default to 1/125 second

    async def _simulate_capture(self, schedule: ScheduleRule, settings: CaptureSettings) -> None:
        """Simulate a capture operation (placeholder for real implementation)."""
        # In the real implementation, this would:
        # 1. Call the camera controller to perform capture
        # 2. Store the captured images
        # 3. Queue them for transfer to processing service

        # For now, just log the simulated capture
        logger.info(f"[SIMULATED] Capturing with schedule {schedule.name}")
        logger.info(f"[SIMULATED] Settings: ISO={settings.iso}, Quality={settings.quality}")

        # Simulate capture time
        await asyncio.sleep(1)

    async def get_next_scheduled_capture(self) -> Optional[Dict[str, Any]]:
        """Get information about the next scheduled capture."""
        schedules = await self.schedule_storage.get_active_schedules()

        next_execution = None
        next_schedule = None

        for schedule in schedules:
            if schedule.next_execution:
                try:
                    exec_time = datetime.fromisoformat(
                        schedule.next_execution.replace("Z", "+00:00")
                    )
                    if next_execution is None or exec_time < next_execution:
                        next_execution = exec_time
                        next_schedule = schedule
                except ValueError:
                    continue

        if next_schedule and next_execution:
            return {
                "schedule_id": next_schedule.id,
                "schedule_name": next_schedule.name,
                "next_execution": next_execution.isoformat(),
                "interval_minutes": next_schedule.interval_minutes,
                "capture_settings": next_schedule.capture_settings.to_dict(),
            }

        return None

    async def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a specific schedule."""
        return await self.schedule_storage.set_schedule_status(schedule_id, ScheduleStatus.PAUSED)

    async def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        return await self.schedule_storage.set_schedule_status(schedule_id, ScheduleStatus.ACTIVE)

    async def get_execution_statistics(self) -> Dict[str, Any]:
        """Get statistics about schedule execution."""
        stats = await self.schedule_storage.get_schedule_statistics()

        # Add execution-specific statistics
        stats.update(
            {"executor_running": self._is_running, "last_check": datetime.now().isoformat()}
        )

        return stats

    # Integration methods for backward compatibility with existing scheduler

    async def should_capture(self, conditions: Optional[EnvironmentalConditions] = None) -> bool:
        """Check if any schedule indicates a capture should happen now."""
        ready_schedules = await self.schedule_storage.get_schedules_ready_for_execution()
        return len(ready_schedules) > 0

    def get_current_capture_settings(self) -> CaptureSettings:
        """Get capture settings for the next ready schedule."""
        # This is a synchronous method for compatibility
        # In practice, we'd need to redesign this to be async
        # For now, return default settings
        return CaptureSettings(quality=95, format="JPEG", iso=100)

    async def record_capture_result(
        self, result, conditions: Optional[EnvironmentalConditions] = None
    ) -> None:
        """Record the result of a capture operation."""
        # For compatibility with existing code
        # The new system handles this through update_execution_status
        pass

    async def record_capture_failure(self, error_message: str) -> None:
        """Record a capture failure."""
        # For compatibility with existing code
        logger.warning(f"Capture failure recorded: {error_message}")

    async def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        stats = await self.get_execution_statistics()
        return {
            "initialized": True,
            "running": self._is_running,
            "statistics": stats,
            "next_capture": await self.get_next_scheduled_capture(),
        }
