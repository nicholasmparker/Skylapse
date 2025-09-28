"""Schedule storage and persistence management."""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schedule_models import (
    ScheduleRule,
    ScheduleStatus,
    ScheduleValidationError,
    validate_schedule_data,
)

logger = logging.getLogger(__name__)


class ScheduleStorageManager:
    """Manages persistence and retrieval of schedule rules."""

    def __init__(self, storage_path: str = "/opt/skylapse/data/schedules"):
        """Initialize schedule storage manager."""
        self.storage_path = Path(storage_path)
        self.schedules_file = self.storage_path / "schedules.json"
        self._schedules: Dict[str, ScheduleRule] = {}
        self._is_initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize storage and load existing schedules."""
        logger.info(f"Initializing schedule storage at {self.storage_path}")

        try:
            # Create storage directory if it doesn't exist
            self.storage_path.mkdir(parents=True, exist_ok=True)

            # Load existing schedules
            await self._load_schedules()

            self._is_initialized = True
            logger.info(f"Schedule storage initialized with {len(self._schedules)} schedules")

        except Exception as e:
            logger.error(f"Failed to initialize schedule storage: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown storage manager."""
        if self._is_initialized:
            await self._save_schedules()
            logger.info("Schedule storage shutdown complete")

    async def create_schedule(self, schedule_data: Dict[str, Any]) -> ScheduleRule:
        """Create a new schedule rule."""
        async with self._lock:
            # Validate input data
            validate_schedule_data(schedule_data)

            # Generate ID if not provided
            if "id" not in schedule_data:
                schedule_data["id"] = str(uuid.uuid4())

            # Check for duplicate ID
            if schedule_data["id"] in self._schedules:
                raise ScheduleValidationError(
                    f"Schedule with ID {schedule_data['id']} already exists"
                )

            # Check for duplicate name
            for existing_schedule in self._schedules.values():
                if existing_schedule.name == schedule_data["name"]:
                    raise ScheduleValidationError(
                        f"Schedule with name '{schedule_data['name']}' already exists"
                    )

            # Create schedule rule
            schedule = ScheduleRule.from_dict(schedule_data)

            # Calculate initial next execution
            next_exec = schedule.calculate_next_execution()
            schedule.next_execution = next_exec.isoformat() if next_exec else None

            # Store schedule
            self._schedules[schedule.id] = schedule

            # Persist to disk
            await self._save_schedules()

            logger.info(f"Created schedule: {schedule.name} (ID: {schedule.id})")
            return schedule

    async def get_schedule(self, schedule_id: str) -> Optional[ScheduleRule]:
        """Get a schedule by ID."""
        async with self._lock:
            return self._schedules.get(schedule_id)

    async def get_all_schedules(self) -> List[ScheduleRule]:
        """Get all schedules."""
        async with self._lock:
            return list(self._schedules.values())

    async def update_schedule(
        self, schedule_id: str, update_data: Dict[str, Any]
    ) -> Optional[ScheduleRule]:
        """Update an existing schedule."""
        async with self._lock:
            if schedule_id not in self._schedules:
                return None

            # Validate update data
            validate_schedule_data(update_data)

            # Check for name conflicts (excluding current schedule)
            new_name = update_data.get("name")
            if new_name:
                for existing_id, existing_schedule in self._schedules.items():
                    if existing_id != schedule_id and existing_schedule.name == new_name:
                        raise ScheduleValidationError(
                            f"Schedule with name '{new_name}' already exists"
                        )

            # Update the schedule
            current_schedule = self._schedules[schedule_id]
            updated_data = current_schedule.to_dict()
            updated_data.update(update_data)
            updated_data["id"] = schedule_id  # Ensure ID doesn't change

            # Create updated schedule
            updated_schedule = ScheduleRule.from_dict(updated_data)

            # Recalculate next execution if schedule parameters changed
            next_exec = updated_schedule.calculate_next_execution()
            updated_schedule.next_execution = next_exec.isoformat() if next_exec else None

            # Store updated schedule
            self._schedules[schedule_id] = updated_schedule

            # Persist to disk
            await self._save_schedules()

            logger.info(f"Updated schedule: {updated_schedule.name} (ID: {schedule_id})")
            return updated_schedule

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        async with self._lock:
            if schedule_id not in self._schedules:
                return False

            schedule_name = self._schedules[schedule_id].name
            del self._schedules[schedule_id]

            # Persist to disk
            await self._save_schedules()

            logger.info(f"Deleted schedule: {schedule_name} (ID: {schedule_id})")
            return True

    async def get_active_schedules(self) -> List[ScheduleRule]:
        """Get all active and enabled schedules."""
        async with self._lock:
            return [
                schedule
                for schedule in self._schedules.values()
                if schedule.enabled and schedule.status == ScheduleStatus.ACTIVE
            ]

    async def get_schedules_ready_for_execution(
        self, current_time: Optional[datetime] = None
    ) -> List[ScheduleRule]:
        """Get schedules that are ready for execution."""
        if current_time is None:
            current_time = datetime.now()

        async with self._lock:
            ready_schedules = []

            for schedule in self._schedules.values():
                if not schedule.enabled or schedule.status != ScheduleStatus.ACTIVE:
                    continue

                if schedule.next_execution:
                    try:
                        next_exec = datetime.fromisoformat(
                            schedule.next_execution.replace("Z", "+00:00")
                        )
                        if next_exec <= current_time:
                            ready_schedules.append(schedule)
                    except ValueError:
                        logger.warning(f"Invalid next_execution format for schedule {schedule.id}")

            return ready_schedules

    async def update_execution_status(
        self, schedule_id: str, success: bool = True, execution_time: Optional[datetime] = None
    ) -> bool:
        """Update execution status for a schedule."""
        async with self._lock:
            if schedule_id not in self._schedules:
                return False

            schedule = self._schedules[schedule_id]
            schedule.update_execution_status(success, execution_time)

            # Persist to disk
            await self._save_schedules()

            logger.info(f"Updated execution status for schedule {schedule.name}: success={success}")
            return True

    async def set_schedule_status(self, schedule_id: str, status: ScheduleStatus) -> bool:
        """Set the status of a schedule."""
        async with self._lock:
            if schedule_id not in self._schedules:
                return False

            schedule = self._schedules[schedule_id]
            old_status = schedule.status
            schedule.status = status

            # Recalculate next execution if status changed to active
            if status == ScheduleStatus.ACTIVE and old_status != ScheduleStatus.ACTIVE:
                next_exec = schedule.calculate_next_execution()
                schedule.next_execution = next_exec.isoformat() if next_exec else None

            # Persist to disk
            await self._save_schedules()

            logger.info(
                f"Set schedule {schedule.name} status from {old_status.value} to {status.value}"
            )
            return True

    async def get_schedule_statistics(self) -> Dict[str, Any]:
        """Get statistics about schedules."""
        async with self._lock:
            total_schedules = len(self._schedules)
            active_schedules = len(
                [
                    s
                    for s in self._schedules.values()
                    if s.enabled and s.status == ScheduleStatus.ACTIVE
                ]
            )
            paused_schedules = len(
                [s for s in self._schedules.values() if s.status == ScheduleStatus.PAUSED]
            )
            error_schedules = len(
                [s for s in self._schedules.values() if s.status == ScheduleStatus.ERROR]
            )

            total_executions = sum(s.execution_count for s in self._schedules.values())

            # Find next execution time
            next_execution = None
            for schedule in self._schedules.values():
                if (
                    schedule.enabled
                    and schedule.status == ScheduleStatus.ACTIVE
                    and schedule.next_execution
                ):
                    try:
                        exec_time = datetime.fromisoformat(
                            schedule.next_execution.replace("Z", "+00:00")
                        )
                        if next_execution is None or exec_time < next_execution:
                            next_execution = exec_time
                    except ValueError:
                        pass

            return {
                "total_schedules": total_schedules,
                "active_schedules": active_schedules,
                "paused_schedules": paused_schedules,
                "error_schedules": error_schedules,
                "total_executions": total_executions,
                "next_execution": next_execution.isoformat() if next_execution else None,
                "storage_path": str(self.storage_path),
                "is_initialized": self._is_initialized,
            }

    async def _load_schedules(self) -> None:
        """Load schedules from disk."""
        if not self.schedules_file.exists():
            logger.info("No existing schedules file found, starting with empty schedule list")
            self._schedules = {}
            return

        try:
            with open(self.schedules_file, "r") as f:
                data = json.load(f)

            self._schedules = {}
            for schedule_data in data.get("schedules", []):
                try:
                    schedule = ScheduleRule.from_dict(schedule_data)
                    self._schedules[schedule.id] = schedule
                except Exception as e:
                    logger.error(
                        f"Failed to load schedule {schedule_data.get('id', 'unknown')}: {e}"
                    )

            logger.info(f"Loaded {len(self._schedules)} schedules from disk")

        except Exception as e:
            logger.error(f"Failed to load schedules from {self.schedules_file}: {e}")
            # Start with empty schedules on load error
            self._schedules = {}

    async def _save_schedules(self) -> None:
        """Save schedules to disk."""
        try:
            # Convert schedules to serializable format
            schedules_data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "schedules": [schedule.to_dict() for schedule in self._schedules.values()],
            }

            # Write to temporary file first, then rename for atomic operation
            temp_file = self.schedules_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(schedules_data, f, indent=2)

            # Atomic rename
            temp_file.replace(self.schedules_file)

            logger.debug(f"Saved {len(self._schedules)} schedules to disk")

        except Exception as e:
            logger.error(f"Failed to save schedules to {self.schedules_file}: {e}")
            raise

    async def recalculate_all_schedules(self) -> None:
        """Recalculate next execution times for all active schedules."""
        async with self._lock:
            current_time = datetime.now()
            updated_count = 0

            for schedule in self._schedules.values():
                if schedule.enabled and schedule.status == ScheduleStatus.ACTIVE:
                    old_next = schedule.next_execution
                    next_exec = schedule.calculate_next_execution(current_time)
                    schedule.next_execution = next_exec.isoformat() if next_exec else None

                    if schedule.next_execution != old_next:
                        updated_count += 1

            if updated_count > 0:
                await self._save_schedules()
                logger.info(f"Recalculated next execution times for {updated_count} schedules")

    async def cleanup_completed_schedules(self, max_age_days: int = 30) -> int:
        """Clean up old completed schedules."""
        async with self._lock:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            schedules_to_remove = []

            for schedule_id, schedule in self._schedules.items():
                if schedule.status == ScheduleStatus.COMPLETED:
                    try:
                        created_date = datetime.fromisoformat(
                            schedule.created_at.replace("Z", "+00:00")
                        )
                        if created_date < cutoff_date:
                            schedules_to_remove.append(schedule_id)
                    except ValueError:
                        # If we can't parse the date, consider it for removal
                        schedules_to_remove.append(schedule_id)

            # Remove old schedules
            for schedule_id in schedules_to_remove:
                del self._schedules[schedule_id]

            if schedules_to_remove:
                await self._save_schedules()
                logger.info(
                    f"Cleaned up {len(schedules_to_remove)} completed schedules older than {max_age_days} days"
                )

            return len(schedules_to_remove)
