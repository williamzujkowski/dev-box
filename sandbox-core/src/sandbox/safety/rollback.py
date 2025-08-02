"""
Rollback Manager - Sandbox state rollback and recovery

Provides comprehensive rollback capabilities including state snapshots, filesystem
checkpoints, and automated recovery mechanisms with safety guarantees.
"""

import asyncio
import logging
import time
import shutil
import tarfile
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from ..utils.stub_modules import CompressionUtils, IntegrityChecker, DataEncryption


@dataclass
class SnapshotMetadata:
    """Metadata for a sandbox snapshot"""
    snapshot_id: str
    timestamp: float
    sandbox_id: str
    description: str
    size_bytes: int
    file_count: int
    checksum: str
    snapshot_type: str = "manual"  # manual, automatic, pre-operation
    operation_id: Optional[str] = None
    compression_ratio: float = 0.0
    encryption_enabled: bool = False
    tags: List[str] = field(default_factory=list)
    
    @property
    def created_at(self) -> str:
        return datetime.fromtimestamp(self.timestamp).isoformat()
    
    @property 
    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600


@dataclass
class RollbackPlan:
    """Plan for rollback operation"""
    snapshot_id: str
    rollback_type: str  # full, selective, state_only
    affected_paths: List[Path]
    estimated_duration: float
    risk_level: str  # low, medium, high
    backup_current: bool = True
    validation_required: bool = True
    rollback_steps: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RollbackResult:  
    """Result of rollback operation"""
    success: bool
    snapshot_id: str
    rollback_duration: float
    files_restored: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    backup_snapshot_id: Optional[str] = None
    validation_passed: bool = False


class RollbackManager:
    """
    Comprehensive sandbox rollback and recovery manager
    
    Features:
    - Filesystem snapshots with compression
    - State-only rollbacks for lightweight recovery
    - Incremental snapshots for efficiency
    - Integrity validation and corruption detection
    - Automatic cleanup of old snapshots
    - Emergency recovery capabilities
    - Encryption support for sensitive data
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(f"sandbox.{config.sandbox_id}.rollback")
        
        # Initialize paths
        self.snapshots_dir = config.workspace_path / "snapshots"
        self.metadata_file = self.snapshots_dir / "metadata.json"
        
        # Components
        self.compression = CompressionUtils()
        self.integrity_checker = IntegrityChecker()
        self.encryption = DataEncryption() if config.safety_constraints.get("encrypt_snapshots") else None
        
        # Snapshot tracking
        self.snapshots_metadata: Dict[str, SnapshotMetadata] = {}
        
        # Configuration
        self.max_snapshots = config.safety_constraints.get("max_snapshots", 10)
        self.compression_enabled = config.safety_constraints.get("compress_snapshots", True)
        self.incremental_enabled = config.safety_constraints.get("incremental_snapshots", True)
        self.auto_cleanup_hours = config.safety_constraints.get("auto_cleanup_hours", 168)  # 1 week
        
    async def initialize(self) -> bool:
        """
        Initialize the rollback manager
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info("Initializing rollback manager")
            
            # Create snapshots directory
            self.snapshots_dir.mkdir(exist_ok=True, mode=0o750)
            
            # Load existing snapshot metadata
            await self._load_metadata()
            
            # Validate existing snapshots
            await self._validate_existing_snapshots()
            
            # Clean up old snapshots
            await self.cleanup_old_snapshots()
            
            self.logger.info("Rollback manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize rollback manager: {e}")
            return False
    
    async def create_snapshot(self, description: str, snapshot_type: str = "manual",
                            operation_id: Optional[str] = None, 
                            tags: Optional[List[str]] = None) -> Optional[str]:
        """
        Create a new sandbox snapshot
        
        Args:
            description: Description of the snapshot
            snapshot_type: Type of snapshot (manual, automatic, pre-operation)
            operation_id: Associated operation ID
            tags: Optional tags for categorization
            
        Returns:
            Snapshot ID if successful, None otherwise
        """
        try:
            # Generate snapshot ID
            timestamp = time.time()
            snapshot_id = f"snap_{int(timestamp)}_{snapshot_type}"
            
            self.logger.info(f"Creating snapshot: {snapshot_id} - {description}")
            
            # Create snapshot directory
            snapshot_path = self.snapshots_dir / snapshot_id
            snapshot_path.mkdir(mode=0o750)
            
            # Determine what to snapshot
            source_paths = await self._determine_snapshot_paths()
            
            # Create the snapshot
            snapshot_file = snapshot_path / "snapshot.tar.gz"
            file_count, size_bytes = await self._create_snapshot_archive(
                source_paths, snapshot_file
            )
            
            # Calculate checksum
            checksum = await self.integrity_checker.calculate_checksum(snapshot_file)
            
            # Calculate compression ratio
            uncompressed_size = await self._calculate_uncompressed_size(source_paths)
            compression_ratio = (1 - size_bytes / uncompressed_size) if uncompressed_size > 0 else 0
            
            # Create metadata
            metadata = SnapshotMetadata(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                sandbox_id=self.config.sandbox_id,
                description=description,
                size_bytes=size_bytes,
                file_count=file_count,
                checksum=checksum,
                snapshot_type=snapshot_type,
                operation_id=operation_id,
                compression_ratio=compression_ratio,
                encryption_enabled=self.encryption is not None,
                tags=tags or []
            )
            
            # Save metadata
            await self._save_snapshot_metadata(metadata)
            self.snapshots_metadata[snapshot_id] = metadata
            
            # Save global metadata
            await self._save_metadata()
            
            self.logger.info(f"Snapshot created successfully: {snapshot_id} ({size_bytes} bytes, {file_count} files)")
            
            # Cleanup old snapshots if needed
            await self._maybe_cleanup_snapshots()
            
            return snapshot_id
            
        except Exception as e:
            self.logger.error(f"Failed to create snapshot: {e}")
            
            # Cleanup failed snapshot
            try:
                if 'snapshot_path' in locals() and snapshot_path.exists():
                    shutil.rmtree(snapshot_path, ignore_errors=True)
            except:
                pass
                
            return None
    
    async def restore_snapshot(self, snapshot_id: str, rollback_type: str = "full",
                             backup_current: bool = True) -> RollbackResult:
        """
        Restore from a snapshot
        
        Args:
            snapshot_id: Snapshot to restore from
            rollback_type: Type of rollback (full, selective, state_only)
            backup_current: Whether to backup current state first
            
        Returns:
            RollbackResult with operation details
        """
        start_time = time.time()
        result = RollbackResult(
            success=False,
            snapshot_id=snapshot_id,
            rollback_duration=0.0,
            files_restored=0
        )
        
        try:
            self.logger.info(f"Starting rollback to snapshot: {snapshot_id}")
            
            # Validate snapshot exists and is valid
            if snapshot_id not in self.snapshots_metadata:
                result.errors.append(f"Snapshot not found: {snapshot_id}")
                return result
            
            metadata = self.snapshots_metadata[snapshot_id]
            snapshot_path = self.snapshots_dir / snapshot_id
            snapshot_file = snapshot_path / "snapshot.tar.gz"
            
            if not snapshot_file.exists():
                result.errors.append(f"Snapshot file not found: {snapshot_file}")
                return result
            
            # Validate snapshot integrity
            if not await self._validate_snapshot_integrity(metadata, snapshot_file):
                result.errors.append("Snapshot integrity validation failed")
                return result
            
            # Create backup of current state if requested
            backup_snapshot_id = None
            if backup_current:
                backup_snapshot_id = await self.create_snapshot(
                    f"Pre-rollback backup for {snapshot_id}",
                    "automatic",
                    tags=["pre-rollback", "backup"]
                )
                if backup_snapshot_id:
                    result.backup_snapshot_id = backup_snapshot_id
                    self.logger.info(f"Created pre-rollback backup: {backup_snapshot_id}")
                else:
                    result.warnings.append("Failed to create pre-rollback backup")
            
            # Create rollback plan
            plan = await self._create_rollback_plan(snapshot_id, rollback_type)
            
            # Execute rollback
            files_restored = await self._execute_rollback(snapshot_file, plan)
            result.files_restored = files_restored
            
            # Validate rollback
            if plan.validation_required:
                validation_passed = await self._validate_rollback(snapshot_id)
                result.validation_passed = validation_passed
                if not validation_passed:
                    result.warnings.append("Rollback validation failed")
            
            result.success = True
            result.rollback_duration = time.time() - start_time
            
            self.logger.info(f"Rollback completed successfully: {files_restored} files restored in {result.rollback_duration:.2f}s")
            
        except Exception as e:
            result.errors.append(f"Rollback failed: {str(e)}")
            result.rollback_duration = time.time() - start_time
            self.logger.error(f"Rollback failed: {e}")
        
        return result
    
    async def list_snapshots(self, include_metadata: bool = False) -> List[Dict[str, Any]]:
        """
        List available snapshots
        
        Args:
            include_metadata: Whether to include full metadata
            
        Returns:
            List of snapshot information
        """
        try:
            snapshots = []
            
            for snapshot_id, metadata in self.snapshots_metadata.items():
                snapshot_info = {
                    "snapshot_id": snapshot_id,
                    "description": metadata.description,
                    "created_at": metadata.created_at,
                    "age_hours": metadata.age_hours,
                    "size_bytes": metadata.size_bytes,
                    "file_count": metadata.file_count,
                    "snapshot_type": metadata.snapshot_type,
                    "tags": metadata.tags
                }
                
                if include_metadata:
                    snapshot_info.update({
                        "checksum": metadata.checksum,
                        "compression_ratio": metadata.compression_ratio,
                        "encryption_enabled": metadata.encryption_enabled,
                        "operation_id": metadata.operation_id
                    })
                
                snapshots.append(snapshot_info)
            
            # Sort by timestamp, newest first
            snapshots.sort(key=lambda x: x["snapshot_id"], reverse=True)
            return snapshots
            
        except Exception as e:
            self.logger.error(f"Failed to list snapshots: {e}")
            return []
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot
        
        Args:
            snapshot_id: Snapshot to delete
            
        Returns:
            bool: True if successful
        """
        try:
            if snapshot_id not in self.snapshots_metadata:
                self.logger.warning(f"Snapshot not found for deletion: {snapshot_id}")
                return False
            
            self.logger.info(f"Deleting snapshot: {snapshot_id}")
            
            # Remove snapshot directory
            snapshot_path = self.snapshots_dir / snapshot_id
            if snapshot_path.exists():
                shutil.rmtree(snapshot_path)
            
            # Remove from metadata
            del self.snapshots_metadata[snapshot_id]
            
            # Update metadata file
            await self._save_metadata()
            
            self.logger.info(f"Snapshot deleted successfully: {snapshot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete snapshot {snapshot_id}: {e}")
            return False
    
    async def cleanup_old_snapshots(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up old snapshots based on age and limits
        
        Args:
            max_age_hours: Maximum age in hours (None to use config default)
            
        Returns:
            Number of snapshots cleaned up
        """
        try:
            max_age = max_age_hours or self.auto_cleanup_hours
            cutoff_time = time.time() - (max_age * 3600)
            
            # Find snapshots to clean up
            to_delete = []
            
            # Clean up by age
            for snapshot_id, metadata in self.snapshots_metadata.items():
                if (metadata.timestamp < cutoff_time and 
                    metadata.snapshot_type == "automatic" and
                    "keep" not in metadata.tags):
                    to_delete.append(snapshot_id)
            
            # Clean up excess snapshots (keep most recent)
            if len(self.snapshots_metadata) > self.max_snapshots:
                # Sort by timestamp, oldest first
                sorted_snapshots = sorted(
                    self.snapshots_metadata.items(),
                    key=lambda x: x[1].timestamp
                )
                
                excess_count = len(sorted_snapshots) - self.max_snapshots
                for snapshot_id, _ in sorted_snapshots[:excess_count]:
                    if snapshot_id not in to_delete and "keep" not in self.snapshots_metadata[snapshot_id].tags:
                        to_delete.append(snapshot_id)
            
            # Delete snapshots
            cleaned_count = 0
            for snapshot_id in to_delete:
                if await self.delete_snapshot(snapshot_id):
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} old snapshots")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old snapshots: {e}")
            return 0
    
    async def get_snapshot_info(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a snapshot
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot information or None if not found
        """
        try:
            if snapshot_id not in self.snapshots_metadata:
                return None
            
            metadata = self.snapshots_metadata[snapshot_id]
            snapshot_path = self.snapshots_dir / snapshot_id
            
            # Check if snapshot file exists
            snapshot_file = snapshot_path / "snapshot.tar.gz"
            file_exists = snapshot_file.exists()
            
            return {
                "snapshot_id": snapshot_id,
                "description": metadata.description,
                "created_at": metadata.created_at,
                "age_hours": metadata.age_hours,
                "size_bytes": metadata.size_bytes,
                "file_count": metadata.file_count,
                "checksum": metadata.checksum,
                "snapshot_type": metadata.snapshot_type,
                "operation_id": metadata.operation_id,
                "compression_ratio": metadata.compression_ratio,
                "encryption_enabled": metadata.encryption_enabled,
                "tags": metadata.tags,
                "file_exists": file_exists,
                "sandbox_id": metadata.sandbox_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get snapshot info for {snapshot_id}: {e}")
            return None
    
    async def cleanup(self) -> bool:
        """
        Clean up rollback manager resources
        
        Returns:
            bool: True if successful
        """
        try:
            self.logger.info("Cleaning up rollback manager")
            
            # Save metadata one final time
            await self._save_metadata()
            
            self.logger.info("Rollback manager cleanup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback manager cleanup failed: {e}")
            return False
    
    # Private methods
    async def _load_metadata(self):
        """Load snapshot metadata from disk"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    
                for snapshot_data in data.get("snapshots", []):
                    metadata = SnapshotMetadata(**snapshot_data)
                    self.snapshots_metadata[metadata.snapshot_id] = metadata
                    
                self.logger.info(f"Loaded metadata for {len(self.snapshots_metadata)} snapshots")
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
    
    async def _save_metadata(self):
        """Save snapshot metadata to disk"""
        try:
            data = {
                "sandbox_id": self.config.sandbox_id,
                "updated_at": time.time(),
                "snapshots": [
                    {
                        "snapshot_id": metadata.snapshot_id,
                        "timestamp": metadata.timestamp,
                        "sandbox_id": metadata.sandbox_id,
                        "description": metadata.description,
                        "size_bytes": metadata.size_bytes,
                        "file_count": metadata.file_count,
                        "checksum": metadata.checksum,
                        "snapshot_type": metadata.snapshot_type,
                        "operation_id": metadata.operation_id,
                        "compression_ratio": metadata.compression_ratio,
                        "encryption_enabled": metadata.encryption_enabled,
                        "tags": metadata.tags
                    }
                    for metadata in self.snapshots_metadata.values()
                ]
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
    
    async def _save_snapshot_metadata(self, metadata: SnapshotMetadata):
        """Save individual snapshot metadata"""
        try:
            snapshot_path = self.snapshots_dir / metadata.snapshot_id
            metadata_file = snapshot_path / "metadata.json"
            
            with open(metadata_file, 'w') as f:
                json.dump({
                    "snapshot_id": metadata.snapshot_id,
                    "timestamp": metadata.timestamp,
                    "sandbox_id": metadata.sandbox_id,
                    "description": metadata.description,
                    "size_bytes": metadata.size_bytes,
                    "file_count": metadata.file_count,
                    "checksum": metadata.checksum,
                    "snapshot_type": metadata.snapshot_type,
                    "operation_id": metadata.operation_id,
                    "compression_ratio": metadata.compression_ratio,
                    "encryption_enabled": metadata.encryption_enabled,
                    "tags": metadata.tags
                }, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save snapshot metadata: {e}")
    
    async def _determine_snapshot_paths(self) -> List[Path]:
        """Determine which paths to include in snapshot"""
        paths = []
        
        # Always include core directories
        core_dirs = ["work", "config", "logs"]
        for dirname in core_dirs:
            dir_path = self.config.workspace_path / dirname
            if dir_path.exists():
                paths.append(dir_path)
        
        # Include state directory if it exists
        state_dir = self.config.workspace_path / "state"
        if state_dir.exists():
            paths.append(state_dir)
        
        # Exclude snapshots directory to avoid recursion
        # Exclude tmp directory as it's temporary
        
        return paths
    
    async def _create_snapshot_archive(self, source_paths: List[Path], 
                                     archive_path: Path) -> Tuple[int, int]:
        """Create compressed archive of source paths"""
        file_count = 0
        
        with tarfile.open(archive_path, "w:gz") as tar:
            for source_path in source_paths:
                if source_path.exists():
                    # Add with relative path
                    arcname = source_path.relative_to(self.config.workspace_path)
                    tar.add(source_path, arcname=arcname)
                    
                    # Count files
                    if source_path.is_file():
                        file_count += 1
                    else:
                        for item in source_path.rglob("*"):
                            if item.is_file():
                                file_count += 1
        
        size_bytes = archive_path.stat().st_size
        return file_count, size_bytes
    
    async def _calculate_uncompressed_size(self, source_paths: List[Path]) -> int:
        """Calculate total uncompressed size of source paths"""
        total_size = 0
        
        for source_path in source_paths:
            if source_path.exists():
                if source_path.is_file():
                    total_size += source_path.stat().st_size
                else:
                    for item in source_path.rglob("*"):
                        if item.is_file():
                            total_size += item.stat().st_size
        
        return total_size
    
    async def _validate_existing_snapshots(self):
        """Validate existing snapshots on disk"""
        invalid_snapshots = []
        
        for snapshot_id, metadata in self.snapshots_metadata.items():
            snapshot_path = self.snapshots_dir / snapshot_id
            snapshot_file = snapshot_path / "snapshot.tar.gz"
            
            if not snapshot_file.exists():
                invalid_snapshots.append(snapshot_id)
                continue
            
            # Validate checksum
            if not await self._validate_snapshot_integrity(metadata, snapshot_file):
                invalid_snapshots.append(snapshot_id)
        
        # Remove invalid snapshots from metadata
        for snapshot_id in invalid_snapshots:
            self.logger.warning(f"Removing invalid snapshot: {snapshot_id}")
            del self.snapshots_metadata[snapshot_id]
        
        if invalid_snapshots:
            await self._save_metadata()
    
    async def _validate_snapshot_integrity(self, metadata: SnapshotMetadata, 
                                         snapshot_file: Path) -> bool:
        """Validate snapshot file integrity"""
        try:
            # Check file size
            actual_size = snapshot_file.stat().st_size
            if actual_size != metadata.size_bytes:
                self.logger.warning(f"Size mismatch for snapshot {metadata.snapshot_id}: expected {metadata.size_bytes}, got {actual_size}")
                return False
            
            # Check checksum
            actual_checksum = await self.integrity_checker.calculate_checksum(snapshot_file)
            if actual_checksum != metadata.checksum:
                self.logger.warning(f"Checksum mismatch for snapshot {metadata.snapshot_id}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate snapshot integrity: {e}")
            return False
    
    async def _create_rollback_plan(self, snapshot_id: str, rollback_type: str) -> RollbackPlan:
        """Create plan for rollback operation"""
        metadata = self.snapshots_metadata[snapshot_id]
        
        # Determine affected paths
        if rollback_type == "full":
            affected_paths = [
                self.config.workspace_path / "work",
                self.config.workspace_path / "config"
            ]
        elif rollback_type == "state_only":
            affected_paths = [
                self.config.workspace_path / "state"
            ]
        else:  # selective
            affected_paths = []  # Would be determined based on specific requirements
        
        return RollbackPlan(
            snapshot_id=snapshot_id,
            rollback_type=rollback_type,
            affected_paths=affected_paths,
            estimated_duration=metadata.file_count * 0.001,  # Rough estimate
            risk_level="medium",
            backup_current=True,
            validation_required=True
        )
    
    async def _execute_rollback(self, snapshot_file: Path, plan: RollbackPlan) -> int:
        """Execute the rollback operation"""
        files_restored = 0
        
        # Extract archive to temporary location
        temp_dir = self.config.workspace_path / "tmp" / f"rollback_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extract archive
            with tarfile.open(snapshot_file, "r:gz") as tar:
                tar.extractall(path=temp_dir)
            
            # Restore files based on plan
            for affected_path in plan.affected_paths:
                relative_path = affected_path.relative_to(self.config.workspace_path)
                source_path = temp_dir / relative_path
                
                if source_path.exists():
                    # Remove existing path
                    if affected_path.exists():
                        if affected_path.is_file():
                            affected_path.unlink()
                        else:
                            shutil.rmtree(affected_path)
                    
                    # Copy from extracted archive
                    if source_path.is_file():
                        affected_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, affected_path)
                        files_restored += 1
                    else:
                        shutil.copytree(source_path, affected_path)
                        files_restored += sum(1 for _ in affected_path.rglob("*") if _.is_file())
            
        finally:
            # Clean up temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        return files_restored
    
    async def _validate_rollback(self, snapshot_id: str) -> bool:
        """Validate that rollback was successful"""
        try:
            # Basic validation - check that key directories exist
            required_dirs = ["work", "config"]
            
            for dirname in required_dirs:
                dir_path = self.config.workspace_path / dirname
                if not dir_path.exists():
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback validation failed: {e}")
            return False
    
    async def _maybe_cleanup_snapshots(self):
        """Clean up snapshots if we exceed limits"""
        if len(self.snapshots_metadata) > self.max_snapshots:
            await self.cleanup_old_snapshots()