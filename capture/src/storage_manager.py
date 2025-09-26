"""Storage management for captured images and metadata."""

import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta, date

from .camera_types import CaptureResult

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages local storage of captured images and metadata."""

    def __init__(self, buffer_path: str, max_size_gb: float = 100, retention_hours: int = 48):
        """Initialize storage manager."""
        self.buffer_path = Path(buffer_path)
        self.max_size_gb = max_size_gb
        self.retention_hours = retention_hours

        # Storage structure
        self.images_dir = self.buffer_path / "images"
        self.metadata_dir = self.buffer_path / "metadata"
        self.transfer_queue_dir = self.buffer_path / "transfer_queue"

        self._is_initialized = False
        self._cleanup_runs = 0
        self._total_files_cleaned = 0

    async def initialize(self) -> None:
        """Initialize storage directories and cleanup old files."""
        logger.info(f"Initializing storage manager at {self.buffer_path}")

        # Create directory structure
        self.buffer_path.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
        self.transfer_queue_dir.mkdir(exist_ok=True)

        # Initial cleanup
        await self.cleanup_old_files()

        # Check available space
        await self._check_available_space()

        self._is_initialized = True
        logger.info("Storage manager initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown storage manager."""
        logger.info("Shutting down storage manager")
        self._is_initialized = False

    async def store_capture_result(self, result: CaptureResult) -> List[str]:
        """
        Store capture result to local buffer and return new file paths.
        """
        if not self._is_initialized:
            raise RuntimeError("Storage manager not initialized")

        stored_paths = []
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds

        # Create date-based directory structure YYYY/MM/DD
        date_dir = self.images_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Also create corresponding metadata directory structure
        metadata_date_dir = self.metadata_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
        metadata_date_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy images to storage buffer
            for i, source_path in enumerate(result.file_paths):
                source_file = Path(source_path)

                # Generate storage filename
                if len(result.file_paths) > 1:
                    # Sequence: add index suffix
                    storage_filename = f"{timestamp}_{i:03d}{source_file.suffix}"
                else:
                    # Single image
                    storage_filename = f"{timestamp}{source_file.suffix}"

                storage_path = date_dir / storage_filename

                # Copy file
                shutil.copy2(source_path, storage_path)
                stored_paths.append(str(storage_path))

                # Clean up temporary file if it was in temp directory
                if "/tmp/" in str(source_path) or "TemporaryItems" in str(source_path):
                    try:
                        source_file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file {source_path}: {e}")

            # Store metadata in date-based directory structure
            metadata_file = metadata_date_dir / f"{timestamp}.json"
            # Ensure metadata directory exists
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            # Create settings dict for top-level compatibility - ensure JSON serializable
            def make_serializable(obj):
                """Convert object to JSON serializable format."""
                if hasattr(obj, '__dict__'):
                    return obj.__dict__
                elif hasattr(obj, 'value') and hasattr(obj, 'name'):  # Enum
                    return obj.value
                else:
                    return obj

            actual_settings_dict = {
                'exposure_time_us': result.actual_settings.exposure_time_us,
                'iso': result.actual_settings.iso,
                'white_balance_k': result.actual_settings.white_balance_k,
                'format': result.actual_settings.format,
                'quality': result.actual_settings.quality,
                'exposure_compensation': result.actual_settings.exposure_compensation,
                'focus_distance_mm': result.actual_settings.focus_distance_mm,
                'autofocus_enabled': result.actual_settings.autofocus_enabled,
                'white_balance_mode': make_serializable(result.actual_settings.white_balance_mode),
                'hdr_bracket_stops': list(result.actual_settings.hdr_bracket_stops),
                'processing_hints': dict(result.actual_settings.processing_hints)
            }

            # Ensure all values in result.metadata are JSON serializable
            safe_metadata = {}
            for k, v in result.metadata.items():
                safe_metadata[k] = make_serializable(v)

            metadata = {
                'timestamp': time.time(),
                'capture_time_ms': result.capture_time_ms,  # Top-level for test compatibility
                'quality_score': result.quality_score,  # Top-level for test compatibility
                'metadata': safe_metadata,  # Original metadata at top level - safely serialized
                'actual_settings': actual_settings_dict,  # Top-level for test compatibility
                'capture_result': {
                    'file_paths': stored_paths,
                    'metadata': safe_metadata,
                    'capture_time_ms': result.capture_time_ms,
                    'quality_score': result.quality_score,
                    'settings': actual_settings_dict
                },
                'storage_info': {
                    'stored_at': timestamp,
                    'image_count': len(stored_paths),
                    'total_size_bytes': sum(Path(p).stat().st_size for p in stored_paths)
                }
            }

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Add to transfer queue
            await self._add_to_transfer_queue(stored_paths, metadata_file)

            logger.info(f"Stored capture result: {len(stored_paths)} images, "
                       f"total size: {sum(Path(p).stat().st_size for p in stored_paths) / 1024 / 1024:.1f}MB")

            return stored_paths

        except Exception as e:
            # Clean up partial storage on error
            for path in stored_paths:
                try:
                    Path(path).unlink()
                except:
                    pass

            logger.error(f"Failed to store capture result: {e}")
            raise

    async def _add_to_transfer_queue(self, image_paths: List[str], metadata_file: Path) -> None:
        """Add captured images to transfer queue."""
        # Add each image as a separate queue item for better granular control
        for image_path in image_paths:
            queue_item = {
                'timestamp': time.time(),
                'file_path': image_path,  # Single file path for compatibility
                'image_paths': [image_path],  # Keep for backward compatibility
                'metadata_file': str(metadata_file),
                'status': 'pending',
                'retry_count': 0
            }

            queue_file = self.transfer_queue_dir / f"transfer_{int(time.time() * 1000)}_{Path(image_path).stem}.json"

            with open(queue_file, 'w') as f:
                json.dump(queue_item, f)

        logger.debug(f"Added {len(image_paths)} images to transfer queue")

    async def cleanup_old_files(self) -> Dict[str, Any]:
        """Clean up old files based on retention policy."""
        logger.info("Starting storage cleanup")
        self._cleanup_runs += 1

        cleanup_stats = {
            'files_removed': 0,
            'space_freed_mb': 0,
            'errors': 0
        }

        cutoff_time = time.time() - (self.retention_hours * 3600)

        try:
            # Clean up old images (recursive search through date directories)
            for image_file in self.images_dir.rglob('*'):
                if image_file.is_file() and image_file.stat().st_mtime < cutoff_time:
                    file_size = image_file.stat().st_size
                    image_file.unlink()
                    cleanup_stats['files_removed'] += 1
                    cleanup_stats['space_freed_mb'] += file_size / (1024 * 1024)

            # Clean up old metadata (recursive search through date directories)
            for metadata_file in self.metadata_dir.rglob('*'):
                if metadata_file.is_file() and metadata_file.stat().st_mtime < cutoff_time:
                    metadata_file.unlink()
                    cleanup_stats['files_removed'] += 1

            # Clean up processed transfer queue items
            for queue_file in self.transfer_queue_dir.iterdir():
                if queue_file.is_file():
                    try:
                        with open(queue_file, 'r') as f:
                            queue_item = json.load(f)

                        if (queue_item.get('status') == 'completed' and
                            queue_item.get('timestamp', 0) < cutoff_time):
                            queue_file.unlink()
                            cleanup_stats['files_removed'] += 1
                    except Exception as e:
                        logger.warning(f"Error processing queue file {queue_file}: {e}")
                        cleanup_stats['errors'] += 1

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            cleanup_stats['errors'] += 1

        # Update total files cleaned counter
        self._total_files_cleaned += cleanup_stats['files_removed']

        logger.info(f"Cleanup completed: {cleanup_stats['files_removed']} files removed, "
                   f"{cleanup_stats['space_freed_mb']:.1f}MB freed")

        return cleanup_stats

    async def _check_available_space(self) -> Dict[str, float]:
        """Check available disk space and enforce limits."""
        storage_stat = shutil.disk_usage(self.buffer_path)

        total_gb = storage_stat.total / (1024**3)
        used_gb = (storage_stat.total - storage_stat.free) / (1024**3)
        free_gb = storage_stat.free / (1024**3)

        # Calculate current buffer usage
        buffer_size_bytes = self._get_directory_size_bytes(self.images_dir)
        buffer_size_gb = buffer_size_bytes / (1024**3)

        space_info = {
            'total_gb': total_gb,
            'used_gb': used_gb,
            'free_gb': free_gb,
            'buffer_size_gb': buffer_size_gb,
            'buffer_limit_gb': self.max_size_gb
        }

        # Emergency cleanup if buffer is too large
        if buffer_size_gb > self.max_size_gb:
            logger.warning(f"Buffer size ({buffer_size_gb:.1f}GB) exceeds limit "
                          f"({self.max_size_gb}GB), performing emergency cleanup")
            # First try normal cleanup to remove old files
            await self.cleanup_old_files()
            # If still over limit, do more aggressive cleanup
            await self._emergency_cleanup()

        # Warning if low on disk space
        if free_gb < 5.0:  # Less than 5GB free
            logger.warning(f"Low disk space: {free_gb:.1f}GB remaining")

        return space_info

    async def _emergency_cleanup(self) -> None:
        """Emergency cleanup when buffer size exceeds limits."""
        logger.warning("Performing emergency cleanup")

        # Get all image files sorted by modification time (oldest first)
        image_files = []
        for image_file in self.images_dir.iterdir():
            if image_file.is_file():
                image_files.append((image_file.stat().st_mtime, image_file))

        image_files.sort()  # Oldest first

        # Remove oldest files until we're under the limit
        target_size = self.max_size_gb * 0.8 * (1024**3)  # 80% of limit
        current_size = sum(f.stat().st_size for _, f in image_files)

        removed_count = 0
        for mtime, image_file in image_files:
            if current_size <= target_size:
                break

            file_size = image_file.stat().st_size

            # Also remove corresponding metadata
            timestamp_str = image_file.stem.split('_')[0] + '_' + image_file.stem.split('_')[1]
            metadata_file = self.metadata_dir / f"{timestamp_str}.json"

            image_file.unlink()
            current_size -= file_size
            removed_count += 1

            if metadata_file.exists():
                metadata_file.unlink()

        logger.warning(f"Emergency cleanup completed: removed {removed_count} files")

    async def get_status(self) -> Dict[str, Any]:
        """Get current storage status."""
        if not self._is_initialized:
            return {'initialized': False}

        space_info = await self._check_available_space()

        # Count files
        image_count = len([f for f in self.images_dir.iterdir() if f.is_file()])
        metadata_count = len([f for f in self.metadata_dir.iterdir() if f.is_file()])
        queue_count = len([f for f in self.transfer_queue_dir.iterdir() if f.is_file()])

        return {
            'initialized': True,
            'buffer_path': str(self.buffer_path),
            'space_info': space_info,
            'file_counts': {
                'images': image_count,
                'metadata': metadata_count,
                'transfer_queue': queue_count
            },
            'retention_hours': self.retention_hours,
            'max_size_gb': self.max_size_gb
        }

    async def get_recent_captures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about recent captures."""
        recent_captures = []

        # Get metadata files sorted by modification time (newest first)
        metadata_files = []
        for metadata_file in self.metadata_dir.iterdir():
            if metadata_file.is_file() and metadata_file.suffix == '.json':
                metadata_files.append((metadata_file.stat().st_mtime, metadata_file))

        metadata_files.sort(reverse=True)  # Newest first

        for mtime, metadata_file in metadata_files[:limit]:
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

                recent_captures.append({
                    'timestamp': metadata['timestamp'],
                    'image_count': metadata['storage_info']['image_count'],
                    'total_size_bytes': metadata['storage_info']['total_size_bytes'],
                    'capture_time_ms': metadata['capture_result']['capture_time_ms'],
                    'quality_score': metadata['capture_result']['quality_score'],
                    'file_paths': metadata['capture_result']['file_paths']
                })

            except Exception as e:
                logger.warning(f"Failed to read metadata {metadata_file}: {e}")

        return recent_captures

    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get detailed storage usage information."""
        if not self._is_initialized:
            return {'initialized': False}

        # Calculate storage statistics
        total_files = 0
        total_size_bytes = 0
        image_files = 0
        image_size_bytes = 0
        metadata_files = 0
        metadata_size_bytes = 0
        transfer_queue_files = 0
        transfer_queue_size_bytes = 0

        # Count images
        for image_file in self.images_dir.rglob('*'):
            if image_file.is_file():
                size = image_file.stat().st_size
                image_files += 1
                image_size_bytes += size
                total_files += 1
                total_size_bytes += size

        # Count metadata
        for metadata_file in self.metadata_dir.rglob('*'):
            if metadata_file.is_file():
                size = metadata_file.stat().st_size
                metadata_files += 1
                metadata_size_bytes += size
                total_files += 1
                total_size_bytes += size

        # Count transfer queue
        for queue_file in self.transfer_queue_dir.rglob('*'):
            if queue_file.is_file():
                size = queue_file.stat().st_size
                transfer_queue_files += 1
                transfer_queue_size_bytes += size
                total_files += 1
                total_size_bytes += size

        # Get disk usage
        storage_stat = shutil.disk_usage(self.buffer_path)
        disk_free_bytes = storage_stat.free
        disk_total_bytes = storage_stat.total

        # Calculate usage percentage
        usage_percentage = (total_size_bytes / (self.max_size_gb * 1024 * 1024 * 1024)) * 100

        return {
            'total_files': total_files,
            'total_size_bytes': total_size_bytes,
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'total_size_gb': total_size_bytes / (1024 * 1024 * 1024),
            'usage_percentage': usage_percentage,  # Add for test compatibility
            'by_type': {
                'images': {
                    'count': image_files,
                    'size_bytes': image_size_bytes,
                    'size_mb': image_size_bytes / (1024 * 1024)
                },
                'metadata': {
                    'count': metadata_files,
                    'size_bytes': metadata_size_bytes,
                    'size_mb': metadata_size_bytes / (1024 * 1024)
                },
                'transfer_queue': {
                    'count': transfer_queue_files,
                    'size_bytes': transfer_queue_size_bytes,
                    'size_mb': transfer_queue_size_bytes / (1024 * 1024)
                }
            },
            'disk_usage': {
                'free_bytes': disk_free_bytes,
                'free_gb': disk_free_bytes / (1024 * 1024 * 1024),
                'total_bytes': disk_total_bytes,
                'total_gb': disk_total_bytes / (1024 * 1024 * 1024),
                'utilization_pct': ((disk_total_bytes - disk_free_bytes) / disk_total_bytes) * 100
            },
            'buffer_usage': {
                'current_gb': total_size_bytes / (1024 * 1024 * 1024),
                'limit_gb': self.max_size_gb,
                'utilization_pct': usage_percentage
            }
        }

    async def get_files_by_date_range(self, start_date: date, end_date: date) -> List[Path]:
        """Get all files within a specific date range."""
        if not self._is_initialized:
            return []

        matching_files = []
        start_timestamp = datetime.combine(start_date, datetime.min.time()).timestamp()
        end_timestamp = datetime.combine(end_date, datetime.max.time()).timestamp()

        # Check image files
        for image_file in self.images_dir.rglob('*'):
            if image_file.is_file():
                file_mtime = image_file.stat().st_mtime
                if start_timestamp <= file_mtime <= end_timestamp:
                    matching_files.append(image_file)

        # Sort by modification time
        matching_files.sort(key=lambda f: f.stat().st_mtime)
        return matching_files

    async def mark_for_transfer(self, file_path: Path) -> None:
        """Mark a specific file for transfer to processing service."""
        if not self._is_initialized:
            raise RuntimeError("Storage manager not initialized")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if already in queue to prevent duplicates
        existing_queue = await self.get_transfer_queue()
        for item in existing_queue:
            if item['file_path'] == str(file_path):
                logger.debug(f"File already in transfer queue: {file_path}")
                return

        # Create transfer queue entry
        queue_item = {
            'timestamp': time.time(),
            'file_path': str(file_path),  # Single file path for compatibility
            'image_paths': [str(file_path)],  # Keep for backward compatibility
            'metadata_file': None,  # Find metadata file if exists
            'status': 'pending',
            'retry_count': 0,
            'marked_for_transfer_at': time.time()
        }

        # Try to find associated metadata
        timestamp_str = file_path.stem
        # Extract date part (assuming format like "20250925_215900_725_000")
        parts = timestamp_str.split('_')
        if len(parts) >= 3:
            metadata_timestamp = '_'.join(parts[:3])  # "20250925_215900_725"
            metadata_file = self.metadata_dir / f"{metadata_timestamp}.json"
            if metadata_file.exists():
                queue_item['metadata_file'] = str(metadata_file)

        # Save queue item
        queue_file = self.transfer_queue_dir / f"manual_transfer_{int(time.time() * 1000)}_{file_path.stem}.json"
        with open(queue_file, 'w') as f:
            json.dump(queue_item, f, indent=2)

        logger.info(f"Marked file for transfer: {file_path}")

    async def get_transfer_queue(self) -> List[Dict[str, Any]]:
        """Get current transfer queue status."""
        if not self._is_initialized:
            return []

        queue_items = []

        for queue_file in self.transfer_queue_dir.rglob('*.json'):
            if queue_file.is_file():
                try:
                    with open(queue_file, 'r') as f:
                        queue_item = json.load(f)

                    # Only include pending and failed items, not completed ones
                    if queue_item.get('status') != 'completed':
                        queue_item['queue_file'] = str(queue_file)
                        queue_items.append(queue_item)
                except Exception as e:
                    logger.warning(f"Failed to read queue file {queue_file}: {e}")

        # Sort by timestamp (oldest first)
        queue_items.sort(key=lambda x: x.get('timestamp', 0))
        return queue_items

    async def mark_transfer_complete(self, file_path: Path, success: bool = True) -> None:
        """Mark a transfer as complete or failed."""
        if not self._is_initialized:
            return

        file_path = Path(file_path)
        updated_count = 0

        # Find and update ALL queue items for this file (there might be duplicates)
        for queue_file in self.transfer_queue_dir.rglob('*.json'):
            if queue_file.is_file():
                try:
                    with open(queue_file, 'r') as f:
                        queue_item = json.load(f)

                    # Check if this queue item contains our file
                    if (str(file_path) in queue_item.get('image_paths', []) or
                        queue_item.get('file_path') == str(file_path)):
                        queue_item['status'] = 'completed' if success else 'failed'
                        queue_item['completed_at'] = time.time()
                        queue_item['success'] = success

                        with open(queue_file, 'w') as f:
                            json.dump(queue_item, f, indent=2)

                        updated_count += 1
                        logger.info(f"Marked transfer {'complete' if success else 'failed'}: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to update queue file {queue_file}: {e}")

        if updated_count == 0:
            logger.warning(f"No transfer queue entry found for file: {file_path}")
        else:
            logger.info(f"Updated {updated_count} queue entries for file: {file_path}")

    def _get_directory_size_gb(self, path: Path) -> float:
        """Get directory size in GB."""
        return self._get_directory_size_bytes(path) / (1024 ** 3)

    def _get_directory_size_bytes(self, path: Path) -> int:
        """Get directory size in bytes."""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        if not self._is_initialized:
            return {'initialized': False}

        # Get basic usage info
        usage_info = await self.get_storage_usage()

        # Calculate additional statistics
        current_time = time.time()
        last_24h = current_time - (24 * 3600)
        last_week = current_time - (7 * 24 * 3600)

        files_last_24h = 0
        files_last_week = 0
        size_last_24h = 0
        size_last_week = 0

        # Count recent files
        for image_file in self.images_dir.rglob('*'):
            if image_file.is_file():
                mtime = image_file.stat().st_mtime
                size = image_file.stat().st_size

                if mtime >= last_24h:
                    files_last_24h += 1
                    size_last_24h += size

                if mtime >= last_week:
                    files_last_week += 1
                    size_last_week += size

        # Get transfer queue stats
        transfer_queue = await self.get_transfer_queue()
        pending_transfers = len([item for item in transfer_queue if item.get('status') == 'pending'])
        completed_transfers = len([item for item in transfer_queue if item.get('status') == 'completed'])
        failed_transfers = len([item for item in transfer_queue if item.get('status') == 'failed'])

        # Calculate total files across all types
        total_files = (usage_info['by_type']['images']['count'] +
                      usage_info['by_type']['metadata']['count'] +
                      usage_info['by_type']['transfer_queue']['count'])

        # Find oldest file
        oldest_file_age_hours = 0
        oldest_timestamp = float('inf')
        for image_file in self.images_dir.rglob('*'):
            if image_file.is_file():
                mtime = image_file.stat().st_mtime
                if mtime < oldest_timestamp:
                    oldest_timestamp = mtime

        if oldest_timestamp != float('inf'):
            oldest_file_age_hours = (current_time - oldest_timestamp) / 3600

        return {
            'initialized': True,
            'total_files': total_files,  # Top-level for test compatibility
            'total_size_bytes': usage_info['total_size_bytes'],  # Top-level for test compatibility
            'total_size_mb': usage_info['total_size_mb'],  # Top-level for test compatibility
            'oldest_file_age_hours': oldest_file_age_hours,  # Top-level for test compatibility
            'cleanup_runs': self._cleanup_runs,  # Top-level for test compatibility
            'files_cleaned': self._total_files_cleaned,  # Top-level for test compatibility
            'current_usage': usage_info,
            'activity': {
                'files_last_24h': files_last_24h,
                'files_last_week': files_last_week,
                'size_last_24h_mb': size_last_24h / (1024 * 1024),
                'size_last_week_mb': size_last_week / (1024 * 1024),
                'average_file_size_mb': (usage_info['by_type']['images']['size_mb'] /
                                       max(1, usage_info['by_type']['images']['count']))
            },
            'transfer_queue': {
                'total_items': len(transfer_queue),
                'pending': pending_transfers,
                'completed': completed_transfers,
                'failed': failed_transfers,
                'success_rate': (completed_transfers / max(1, len(transfer_queue))) * 100
            },
            'retention': {
                'retention_hours': self.retention_hours,
                'cleanup_threshold_gb': self.max_size_gb
            }
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        return False  # Don't suppress exceptions