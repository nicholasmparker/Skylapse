"""File transfer management for sending images to processing service."""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TransferManager:
    """
    Manages file transfers from capture service to processing service.

    This implementation provides both local transfer (for single-machine setup)
    and network transfer capabilities (for distributed setup).
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize transfer manager with configuration."""
        self._config = config
        self._is_initialized = False

        # Transfer directories
        self._queue_dir = Path(config.get("queue_dir", "/opt/skylapse/transfer_queue"))
        self._target_dir = Path(config.get("target_dir", "/opt/skylapse/transfers/incoming"))

        # Network configuration
        self._processing_host = config.get("processing_host", "localhost")
        self._processing_port = config.get("processing_port", 8081)
        self._use_rsync = config.get("use_rsync", False)
        self._rsync_user = config.get("rsync_user", "skylapse")

        # Transfer statistics
        self._transfer_stats = {
            "transfers_queued": 0,
            "transfers_completed": 0,
            "transfers_failed": 0,
            "bytes_transferred": 0,
            "average_transfer_time_ms": 0.0,
        }

        self._pending_transfers: List[str] = []

    async def initialize(self) -> None:
        """Initialize transfer manager."""
        logger.info("Initializing transfer manager")

        # Create directories
        self._queue_dir.mkdir(parents=True, exist_ok=True)

        # Load pending transfers from disk
        await self._load_pending_transfers()

        # For local setup, ensure target directory exists
        if not self._use_rsync:
            self._target_dir.mkdir(parents=True, exist_ok=True)

        self._is_initialized = True
        logger.info(f"Transfer manager initialized: {'rsync' if self._use_rsync else 'local'} mode")

    async def shutdown(self) -> None:
        """Shutdown transfer manager."""
        logger.info("Shutting down transfer manager")
        self._is_initialized = False

    async def queue_transfer(
        self, image_paths: List[str], metadata: Dict[str, Any], priority: str = "normal"
    ) -> str:
        """Queue images for transfer to processing service."""
        if not self._is_initialized:
            raise RuntimeError("Transfer manager not initialized")

        # Generate transfer ID
        transfer_id = f"transfer_{int(time.time() * 1000)}"

        # Create transfer manifest
        manifest = {
            "transfer_id": transfer_id,
            "created_at": time.time(),
            "priority": priority,
            "image_paths": image_paths,
            "metadata": metadata,
            "status": "queued",
            "retry_count": 0,
            "max_retries": self._config.get("max_retries", 3),
        }

        # Save manifest to queue
        manifest_file = self._queue_dir / f"{transfer_id}.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        # Add to pending list
        self._pending_transfers.append(transfer_id)

        # Update statistics
        self._transfer_stats["transfers_queued"] += 1

        logger.info(f"Queued transfer {transfer_id}: {len(image_paths)} images")
        return transfer_id

    async def process_pending_transfers(self) -> List[Dict[str, Any]]:
        """Process all pending transfers."""
        if not self._is_initialized or not self._pending_transfers:
            return []

        results = []

        # Process transfers in order
        transfers_to_process = self._pending_transfers.copy()
        for transfer_id in transfers_to_process:
            try:
                result = await self._process_single_transfer(transfer_id)
                results.append(result)

                # Remove from pending list if completed or failed permanently
                if result["status"] in ["completed", "failed"]:
                    self._pending_transfers.remove(transfer_id)

            except Exception as e:
                logger.error(f"Error processing transfer {transfer_id}: {e}")
                results.append({"transfer_id": transfer_id, "status": "error", "error": str(e)})

        return results

    async def _process_single_transfer(self, transfer_id: str) -> Dict[str, Any]:
        """Process a single transfer."""
        manifest_file = self._queue_dir / f"{transfer_id}.json"

        if not manifest_file.exists():
            return {
                "transfer_id": transfer_id,
                "status": "error",
                "error": "Manifest file not found",
            }

        # Load transfer manifest
        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        start_time = time.time()

        try:
            # Mark as in progress
            manifest["status"] = "in_progress"
            manifest["processing_start_time"] = start_time

            # Save updated manifest
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)

            # Perform the transfer
            if self._use_rsync:
                result = await self._transfer_via_rsync(manifest)
            else:
                result = await self._transfer_local(manifest)

            # Calculate transfer time
            transfer_time_ms = (time.time() - start_time) * 1000

            if result["success"]:
                # Mark as completed
                manifest["status"] = "completed"
                manifest["completed_at"] = time.time()
                manifest["transfer_time_ms"] = transfer_time_ms

                # Update statistics
                self._transfer_stats["transfers_completed"] += 1
                self._transfer_stats["bytes_transferred"] += result["bytes_transferred"]
                self._update_average_transfer_time(transfer_time_ms)

                logger.info(f"Transfer {transfer_id} completed in {transfer_time_ms:.1f}ms")

            else:
                # Handle failure
                manifest["retry_count"] += 1
                if manifest["retry_count"] <= manifest["max_retries"]:
                    # Retry later
                    manifest["status"] = "queued"
                    manifest["last_error"] = result["error"]
                    logger.warning(f"Transfer {transfer_id} failed, will retry: {result['error']}")
                else:
                    # Failed permanently
                    manifest["status"] = "failed"
                    manifest["final_error"] = result["error"]
                    self._transfer_stats["transfers_failed"] += 1
                    logger.error(f"Transfer {transfer_id} failed permanently: {result['error']}")

            # Save final manifest
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)

            return {
                "transfer_id": transfer_id,
                "status": manifest["status"],
                "transfer_time_ms": transfer_time_ms if result["success"] else 0,
                "bytes_transferred": result.get("bytes_transferred", 0),
                "error": result.get("error"),
            }

        except Exception as e:
            # Handle unexpected errors
            manifest["status"] = "error"
            manifest["error"] = str(e)

            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)

            logger.error(f"Unexpected error in transfer {transfer_id}: {e}")
            return {"transfer_id": transfer_id, "status": "error", "error": str(e)}

    async def _transfer_local(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Transfer files locally (same machine)."""
        try:
            transfer_id = manifest["transfer_id"]
            image_paths = manifest["image_paths"]

            transferred_files = []
            total_bytes = 0

            # Copy each image file
            for source_path in image_paths:
                source_file = Path(source_path)

                if not source_file.exists():
                    logger.warning(f"Source file not found: {source_path}")
                    continue

                # Generate target filename
                target_filename = f"{transfer_id}_{source_file.name}"
                target_path = self._target_dir / target_filename

                # Copy file
                shutil.copy2(source_file, target_path)
                transferred_files.append(target_filename)
                total_bytes += target_path.stat().st_size

            # Create transfer manifest in target directory
            target_manifest = {
                "transfer_id": transfer_id,
                "image_files": transferred_files,
                "metadata": manifest["metadata"],
                "created_at": manifest["created_at"],
                "transferred_at": time.time(),
            }

            manifest_path = self._target_dir / f"transfer_{transfer_id}.json"
            with open(manifest_path, "w") as f:
                json.dump(target_manifest, f, indent=2)

            return {
                "success": True,
                "bytes_transferred": total_bytes,
                "files_transferred": len(transferred_files),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "bytes_transferred": 0}

    async def _transfer_via_rsync(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transfer files via rsync (network transfer).

        This is a stub for Sprint 1. Phase 2 will implement full rsync support.
        """
        # For Sprint 1, simulate rsync transfer by falling back to local transfer
        # Phase 2 will implement actual rsync with SSH
        logger.info("Rsync transfer not implemented in Sprint 1, using local transfer")
        return await self._transfer_local(manifest)

    async def _load_pending_transfers(self) -> None:
        """Load pending transfers from disk on startup."""
        if not self._queue_dir.exists():
            return

        loaded_count = 0
        for manifest_file in self._queue_dir.glob("transfer_*.json"):
            try:
                with open(manifest_file, "r") as f:
                    manifest = json.load(f)

                transfer_id = manifest["transfer_id"]

                # Add pending/queued transfers back to the list
                if manifest.get("status") in ["queued", "in_progress"]:
                    # Reset in-progress to queued on restart
                    if manifest["status"] == "in_progress":
                        manifest["status"] = "queued"
                        with open(manifest_file, "w") as f:
                            json.dump(manifest, f, indent=2)

                    self._pending_transfers.append(transfer_id)
                    loaded_count += 1

            except Exception as e:
                logger.warning(f"Failed to load transfer manifest {manifest_file}: {e}")

        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} pending transfers")

    def _update_average_transfer_time(self, transfer_time_ms: float) -> None:
        """Update running average of transfer times."""
        current_avg = self._transfer_stats["average_transfer_time_ms"]
        completed_count = self._transfer_stats["transfers_completed"]

        if completed_count > 0:
            self._transfer_stats["average_transfer_time_ms"] = (
                current_avg * (completed_count - 1) + transfer_time_ms
            ) / completed_count

    async def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        """Get status of a specific transfer."""
        manifest_file = self._queue_dir / f"{transfer_id}.json"

        if not manifest_file.exists():
            return {"error": "Transfer not found"}

        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        return {
            "transfer_id": transfer_id,
            "status": manifest["status"],
            "created_at": manifest["created_at"],
            "image_count": len(manifest["image_paths"]),
            "retry_count": manifest.get("retry_count", 0),
            "transfer_time_ms": manifest.get("transfer_time_ms"),
            "error": manifest.get("last_error") or manifest.get("final_error"),
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get transfer manager status and statistics."""
        return {
            "initialized": self._is_initialized,
            "transfer_mode": "rsync" if self._use_rsync else "local",
            "processing_host": self._processing_host,
            "pending_transfers": len(self._pending_transfers),
            "statistics": self._transfer_stats.copy(),
            "configuration": {
                "queue_dir": str(self._queue_dir),
                "target_dir": str(self._target_dir),
                "max_retries": self._config.get("max_retries", 3),
            },
        }

    async def cleanup_old_transfers(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed transfer manifests."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0

        for manifest_file in self._queue_dir.glob("transfer_*.json"):
            try:
                with open(manifest_file, "r") as f:
                    manifest = json.load(f)

                # Only clean up completed or failed transfers
                if (
                    manifest.get("status") in ["completed", "failed"]
                    and manifest.get("created_at", 0) < cutoff_time
                ):

                    manifest_file.unlink()
                    cleaned_count += 1

            except Exception as e:
                logger.warning(f"Error during cleanup of {manifest_file}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old transfer manifests")

        return cleaned_count

    # Future methods for Phase 2 implementation

    async def _setup_rsync_ssh(self, ssh_config: Dict[str, Any]) -> None:
        """Setup SSH configuration for rsync transfers (Phase 2)."""
        # TODO: Implement SSH key setup and rsync configuration
        pass

    async def _execute_rsync_command(
        self, source_files: List[str], target_path: str
    ) -> Dict[str, Any]:
        """Execute rsync command for file transfer (Phase 2)."""
        # TODO: Implement actual rsync execution with proper error handling
        pass

    async def _monitor_transfer_progress(self, transfer_id: str) -> None:
        """Monitor progress of ongoing transfer (Phase 2)."""
        # TODO: Implement transfer progress monitoring
        pass
