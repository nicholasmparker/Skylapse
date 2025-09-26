"""Transfer receiver for handling incoming images from capture service."""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TransferReceiver:
    """Handles receiving and processing of transferred images from capture service."""

    def __init__(self, transfer_dir: str = "/tmp/skylapse_transfers"):
        """Initialize transfer receiver."""
        self.transfer_dir = Path(transfer_dir)
        self.incoming_dir = self.transfer_dir / "incoming"
        self.processing_dir = self.transfer_dir / "processing"
        self.completed_dir = self.transfer_dir / "completed"

        self._is_initialized = False
        self._transfer_stats = {
            'transfers_received': 0,
            'images_received': 0,
            'bytes_received': 0,
            'transfer_errors': 0
        }

    async def initialize(self) -> None:
        """Initialize transfer receiver system."""
        logger.info("Initializing transfer receiver")

        # Create directory structure
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.completed_dir.mkdir(parents=True, exist_ok=True)

        # Clean up any incomplete transfers from previous runs
        await self._cleanup_incomplete_transfers()

        self._is_initialized = True
        logger.info("Transfer receiver initialized")

    async def shutdown(self) -> None:
        """Shutdown transfer receiver."""
        logger.info("Shutting down transfer receiver")
        self._is_initialized = False

    async def check_for_transfers(self) -> List[Dict[str, Any]]:
        """
        Check for new incoming transfers and process them.

        This is a stub implementation for Sprint 1.
        Phase 2 will implement real rsync/SSH transfer monitoring.
        """
        if not self._is_initialized:
            return []

        new_transfers = []

        # Check for transfer manifest files in incoming directory
        for manifest_file in self.incoming_dir.glob("transfer_*.json"):
            try:
                transfer_data = await self._process_transfer_manifest(manifest_file)
                if transfer_data:
                    new_transfers.append(transfer_data)
            except Exception as e:
                logger.error(f"Failed to process transfer manifest {manifest_file}: {e}")
                self._transfer_stats['transfer_errors'] += 1

        return new_transfers

    async def _process_transfer_manifest(self, manifest_file: Path) -> Optional[Dict[str, Any]]:
        """Process a transfer manifest file."""
        try:
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

            transfer_id = manifest.get('transfer_id', manifest_file.stem)

            # Verify all files exist
            image_paths = []
            total_size = 0

            for image_file in manifest.get('image_files', []):
                image_path = self.incoming_dir / image_file
                if image_path.exists():
                    image_paths.append(str(image_path))
                    total_size += image_path.stat().st_size
                else:
                    logger.warning(f"Missing image file in transfer: {image_path}")

            if not image_paths:
                logger.warning(f"No valid images found in transfer {transfer_id}")
                return None

            # Move manifest to processing directory
            processing_manifest = self.processing_dir / manifest_file.name
            manifest_file.rename(processing_manifest)

            # Update statistics
            self._transfer_stats['transfers_received'] += 1
            self._transfer_stats['images_received'] += len(image_paths)
            self._transfer_stats['bytes_received'] += total_size

            transfer_data = {
                'id': transfer_id,
                'manifest_path': str(processing_manifest),
                'image_paths': image_paths,
                'image_count': len(image_paths),
                'total_size_bytes': total_size,
                'metadata': manifest.get('metadata', {}),
                'received_at': time.time()
            }

            logger.info(f"Processed transfer {transfer_id}: {len(image_paths)} images, "
                       f"{total_size / 1024 / 1024:.1f}MB")

            return transfer_data

        except Exception as e:
            logger.error(f"Error processing transfer manifest {manifest_file}: {e}")
            return None

    async def _cleanup_incomplete_transfers(self) -> None:
        """Clean up incomplete transfers from previous runs."""
        logger.info("Cleaning up incomplete transfers")

        cleanup_count = 0

        # Move any orphaned files back to incoming
        for processing_file in self.processing_dir.iterdir():
            if processing_file.is_file():
                target_path = self.incoming_dir / processing_file.name
                processing_file.rename(target_path)
                cleanup_count += 1

        if cleanup_count > 0:
            logger.info(f"Moved {cleanup_count} files back to incoming directory")

    async def mark_transfer_completed(self, transfer_id: str) -> None:
        """Mark a transfer as completed and archive it."""
        manifest_file = self.processing_dir / f"transfer_{transfer_id}.json"

        if manifest_file.exists():
            # Move to completed directory
            completed_manifest = self.completed_dir / manifest_file.name
            manifest_file.rename(completed_manifest)

            # Update completed manifest with completion time
            try:
                with open(completed_manifest, 'r') as f:
                    manifest = json.load(f)

                manifest['completed_at'] = time.time()

                with open(completed_manifest, 'w') as f:
                    json.dump(manifest, f, indent=2)

            except Exception as e:
                logger.warning(f"Failed to update completed manifest: {e}")

            logger.debug(f"Marked transfer {transfer_id} as completed")

    async def simulate_incoming_transfer(
        self,
        image_paths: List[str],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Simulate an incoming transfer for testing purposes.

        This method is used for Sprint 1 testing and development.
        """
        transfer_id = f"sim_{int(time.time() * 1000)}"

        # Copy images to incoming directory
        incoming_files = []
        for i, image_path in enumerate(image_paths):
            source_file = Path(image_path)
            if source_file.exists():
                target_file = self.incoming_dir / f"{transfer_id}_{i:03d}{source_file.suffix}"

                # Copy file
                import shutil
                shutil.copy2(source_file, target_file)
                incoming_files.append(target_file.name)

        # Create transfer manifest
        manifest = {
            'transfer_id': transfer_id,
            'image_files': incoming_files,
            'metadata': metadata,
            'created_at': time.time(),
            'simulated_transfer': True
        }

        manifest_file = self.incoming_dir / f"transfer_{transfer_id}.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Simulated incoming transfer {transfer_id} with {len(incoming_files)} images")
        return transfer_id

    async def get_status(self) -> Dict[str, Any]:
        """Get transfer receiver status."""
        # Count files in each directory
        incoming_count = len(list(self.incoming_dir.glob("*.json")))
        processing_count = len(list(self.processing_dir.glob("*.json")))
        completed_count = len(list(self.completed_dir.glob("*.json")))

        return {
            'initialized': self._is_initialized,
            'transfer_directory': str(self.transfer_dir),
            'queue_counts': {
                'incoming': incoming_count,
                'processing': processing_count,
                'completed': completed_count
            },
            'statistics': self._transfer_stats.copy()
        }

    async def get_pending_transfers(self) -> List[Dict[str, Any]]:
        """Get list of pending transfers."""
        pending = []

        for manifest_file in self.incoming_dir.glob("transfer_*.json"):
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)

                pending.append({
                    'transfer_id': manifest.get('transfer_id', manifest_file.stem),
                    'image_count': len(manifest.get('image_files', [])),
                    'created_at': manifest.get('created_at'),
                    'metadata': manifest.get('metadata', {})
                })

            except Exception as e:
                logger.warning(f"Failed to read pending transfer manifest {manifest_file}: {e}")

        return pending

    # Future methods for Phase 2 implementation

    async def _setup_rsync_monitoring(self, rsync_config: Dict[str, Any]) -> None:
        """Setup rsync transfer monitoring (Phase 2)."""
        # TODO: Implement rsync monitoring
        # - Monitor rsync target directory
        # - Validate transfer completeness
        # - Handle interrupted transfers
        pass

    async def _setup_ssh_key_auth(self, ssh_config: Dict[str, Any]) -> None:
        """Setup SSH key authentication for secure transfers (Phase 2)."""
        # TODO: Implement SSH key management
        # - Generate/manage SSH keys
        # - Configure authorized_keys
        # - Test connectivity
        pass

    async def _monitor_network_transfers(self) -> None:
        """Monitor network-based file transfers (Phase 2)."""
        # TODO: Implement network transfer monitoring
        # - Watch for incoming rsync transfers
        # - Monitor transfer progress
        # - Handle network interruptions
        pass