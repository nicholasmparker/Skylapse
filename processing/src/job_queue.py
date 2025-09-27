"""Job queue management for processing tasks."""

import json
import logging
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobQueue:
    """Manages processing job queue and status tracking."""

    def __init__(self, queue_dir: str = "/tmp/skylapse_queue"):
        """Initialize job queue."""
        self.queue_dir = Path(queue_dir)
        self._is_initialized = False
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._pending_jobs: List[str] = []
        self._stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "pending_jobs": 0,
            "in_progress_jobs": 0,
        }

    async def initialize(self) -> None:
        """Initialize job queue system."""
        logger.info("Initializing job queue")

        # Create queue directory
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        # Load existing jobs from disk
        await self._load_existing_jobs()

        self._is_initialized = True
        logger.info(f"Job queue initialized with {len(self._jobs)} existing jobs")

    async def shutdown(self) -> None:
        """Shutdown job queue."""
        logger.info("Shutting down job queue")

        # Save all jobs to disk
        await self._save_all_jobs()

        self._is_initialized = False

    async def add_job(self, job_data: Dict[str, Any]) -> str:
        """Add a new job to the queue."""
        if not self._is_initialized:
            raise RuntimeError("Job queue not initialized")

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create job record
        job = {
            "id": job_id,
            "status": JobStatus.PENDING.value,
            "created_at": time.time(),
            "updated_at": time.time(),
            "priority": job_data.get("priority", "normal"),
            "job_type": job_data.get("type", "unknown"),
            "data": job_data,
            "error_message": None,
            "processing_time_ms": None,
            "retry_count": 0,
            "max_retries": job_data.get("max_retries", 3),
        }

        # Add to internal tracking
        self._jobs[job_id] = job
        self._pending_jobs.append(job_id)

        # Save to disk
        await self._save_job(job_id)

        # Update statistics
        self._stats["total_jobs"] += 1
        self._stats["pending_jobs"] += 1

        logger.info(f"Added job {job_id}: {job['job_type']}")
        return job_id

    async def get_next_job(self) -> Optional[Dict[str, Any]]:
        """Get the next job to process."""
        if not self._is_initialized or not self._pending_jobs:
            return None

        # Sort pending jobs by priority and creation time
        self._pending_jobs.sort(
            key=lambda job_id: (
                self._get_priority_weight(self._jobs[job_id]["priority"]),
                self._jobs[job_id]["created_at"],
            )
        )

        # Get highest priority job
        job_id = self._pending_jobs.pop(0)
        job = self._jobs[job_id]

        # Mark as in progress
        job["status"] = JobStatus.IN_PROGRESS.value
        job["updated_at"] = time.time()
        job["processing_start_time"] = time.time()

        # Update statistics
        self._stats["pending_jobs"] -= 1
        self._stats["in_progress_jobs"] += 1

        # Save updated job
        await self._save_job(job_id)

        logger.debug(f"Dispatched job {job_id} for processing")
        return job

    async def mark_job_completed(self, job_id: str) -> None:
        """Mark a job as completed."""
        if job_id not in self._jobs:
            logger.warning(f"Attempted to mark unknown job as completed: {job_id}")
            return

        job = self._jobs[job_id]
        job["status"] = JobStatus.COMPLETED.value
        job["updated_at"] = time.time()

        # Calculate processing time
        if "processing_start_time" in job:
            processing_time = (time.time() - job["processing_start_time"]) * 1000
            job["processing_time_ms"] = processing_time

        # Update statistics
        self._stats["in_progress_jobs"] -= 1
        self._stats["completed_jobs"] += 1

        # Save updated job
        await self._save_job(job_id)

        logger.info(f"Job {job_id} completed")

    async def mark_job_failed(self, job_id: str, error_message: str) -> None:
        """Mark a job as failed."""
        if job_id not in self._jobs:
            logger.warning(f"Attempted to mark unknown job as failed: {job_id}")
            return

        job = self._jobs[job_id]
        job["retry_count"] += 1

        if job["retry_count"] <= job["max_retries"]:
            # Retry the job
            job["status"] = JobStatus.PENDING.value
            job["error_message"] = error_message
            job["updated_at"] = time.time()

            # Add back to pending queue with delay
            self._pending_jobs.append(job_id)

            logger.info(f"Job {job_id} failed, retry {job['retry_count']}/{job['max_retries']}")
        else:
            # Max retries exceeded
            job["status"] = JobStatus.FAILED.value
            job["error_message"] = error_message
            job["updated_at"] = time.time()

            # Update statistics
            self._stats["in_progress_jobs"] -= 1
            self._stats["failed_jobs"] += 1

            logger.error(
                f"Job {job_id} failed permanently after {job['retry_count']} retries: "
                f"{error_message}"
            )

        # Save updated job
        await self._save_job(job_id)

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a specific job."""
        if job_id not in self._jobs:
            return {"error": "Job not found"}

        job = self._jobs[job_id].copy()
        # Remove large data fields for status response
        if "data" in job:
            job["data_summary"] = {
                "type": job["data"].get("type"),
                "image_count": len(job["data"].get("image_paths", [])),
                "priority": job["data"].get("priority"),
            }
            del job["data"]

        return job

    def _get_priority_weight(self, priority: str) -> int:
        """Get numerical weight for priority sorting."""
        priority_weights = {"urgent": 0, "high": 1, "normal": 2, "low": 3, "background": 4}
        return priority_weights.get(priority, 2)

    async def _save_job(self, job_id: str) -> None:
        """Save job to disk."""
        job_file = self.queue_dir / f"{job_id}.json"

        try:
            with open(job_file, "w") as f:
                json.dump(self._jobs[job_id], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job {job_id}: {e}")

    async def _save_all_jobs(self) -> None:
        """Save all jobs to disk."""
        for job_id in self._jobs:
            await self._save_job(job_id)

    async def _load_existing_jobs(self) -> None:
        """Load existing jobs from disk."""
        if not self.queue_dir.exists():
            return

        loaded_count = 0
        for job_file in self.queue_dir.glob("*.json"):
            try:
                with open(job_file, "r") as f:
                    job = json.load(f)

                job_id = job["id"]
                self._jobs[job_id] = job

                # Add to pending queue if not completed/failed
                if job["status"] in [JobStatus.PENDING.value, JobStatus.IN_PROGRESS.value]:
                    # Reset in-progress jobs to pending on restart
                    if job["status"] == JobStatus.IN_PROGRESS.value:
                        job["status"] = JobStatus.PENDING.value

                    self._pending_jobs.append(job_id)

                loaded_count += 1

            except Exception as e:
                logger.error(f"Failed to load job from {job_file}: {e}")

        # Update statistics
        self._update_stats()

        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} existing jobs from disk")

    def _update_stats(self) -> None:
        """Update job statistics."""
        self._stats = {
            "total_jobs": len(self._jobs),
            "completed_jobs": len(
                [j for j in self._jobs.values() if j["status"] == JobStatus.COMPLETED.value]
            ),
            "failed_jobs": len(
                [j for j in self._jobs.values() if j["status"] == JobStatus.FAILED.value]
            ),
            "pending_jobs": len(
                [j for j in self._jobs.values() if j["status"] == JobStatus.PENDING.value]
            ),
            "in_progress_jobs": len(
                [j for j in self._jobs.values() if j["status"] == JobStatus.IN_PROGRESS.value]
            ),
        }

    async def cleanup_old_jobs(self, max_age_hours: int = 72) -> int:
        """Clean up old completed/failed jobs."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        jobs_removed = 0

        jobs_to_remove = []
        for job_id, job in self._jobs.items():
            if (
                job["status"] in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]
                and job["updated_at"] < cutoff_time
            ):
                jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            # Remove job file
            job_file = self.queue_dir / f"{job_id}.json"
            try:
                job_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove job file {job_file}: {e}")

            # Remove from memory
            del self._jobs[job_id]
            jobs_removed += 1

        if jobs_removed > 0:
            self._update_stats()
            logger.info(f"Cleaned up {jobs_removed} old jobs")

        return jobs_removed

    async def get_status(self) -> Dict[str, Any]:
        """Get job queue status and statistics."""
        return {
            "initialized": self._is_initialized,
            "queue_directory": str(self.queue_dir),
            "statistics": self._stats.copy(),
            "pending_queue_length": len(self._pending_jobs),
        }

    async def get_recent_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs sorted by creation time."""
        jobs_list = list(self._jobs.values())
        jobs_list.sort(key=lambda x: x["updated_at"], reverse=True)

        # Return summary info for recent jobs
        recent_jobs = []
        for job in jobs_list[:limit]:
            job_summary = {
                "id": job["id"],
                "status": job["status"],
                "job_type": job["job_type"],
                "priority": job["priority"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
                "processing_time_ms": job.get("processing_time_ms"),
                "retry_count": job["retry_count"],
            }
            recent_jobs.append(job_summary)

        return recent_jobs

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]

        # Can only cancel pending jobs
        if job["status"] != JobStatus.PENDING.value:
            return False

        job["status"] = JobStatus.CANCELLED.value
        job["updated_at"] = time.time()

        # Remove from pending queue
        if job_id in self._pending_jobs:
            self._pending_jobs.remove(job_id)

        # Update statistics
        self._stats["pending_jobs"] -= 1

        # Save updated job
        await self._save_job(job_id)

        logger.info(f"Cancelled job {job_id}")
        return True
