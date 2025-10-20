"""Snapshot management for VM state persistence.

This module provides snapshot lifecycle management:
- Creating snapshots with metadata (name, description, timestamp)
- Listing all snapshots for a VM
- Restoring VMs to snapshot states
- Deleting snapshots

Snapshots use libvirt's internal snapshot mechanism for speed (<1s restore).
All operations are logged with structured logging for audit trails.
"""

from dataclasses import dataclass
from datetime import datetime

import libvirt
import structlog

from agent_vm.core.vm import VM

logger = structlog.get_logger()


@dataclass
class Snapshot:
    """Snapshot metadata and reference.

    Attributes:
        name: Snapshot name (unique per VM)
        description: Optional human-readable description
        created_at: Timestamp when snapshot was created
        _snap_obj: Internal libvirt snapshot object (private)
    """

    name: str
    description: str = ""
    created_at: datetime | None = None
    _snap_obj: libvirt.virDomainSnapshot | None = None


class SnapshotError(Exception):
    """Snapshot operation error.

    Raised when snapshot operations fail (create, restore, delete, list).
    """

    pass


class SnapshotManager:
    """VM snapshot lifecycle management.

    Provides high-level snapshot operations with error handling,
    structured logging, and metadata tracking.

    Example:
        >>> manager = SnapshotManager()
        >>> snapshot = manager.create_snapshot(vm, "golden", "Clean state")
        >>> # Do risky operations...
        >>> manager.restore_snapshot(vm, snapshot)  # Back to clean state
    """

    def create_snapshot(self, vm: VM, name: str, description: str = "") -> Snapshot:
        """Create VM snapshot with metadata.

        Creates an internal snapshot for fast restoration (<1s).
        Snapshot includes name, description, and creation timestamp.

        Args:
            vm: VM to snapshot
            name: Snapshot name (must be unique for this VM)
            description: Optional description of snapshot purpose

        Returns:
            Snapshot object with metadata and internal reference

        Raises:
            SnapshotError: If snapshot creation fails

        Example:
            >>> snapshot = manager.create_snapshot(
            ...     vm,
            ...     name="pre-test",
            ...     description="Clean state before running tests"
            ... )
            >>> print(f"Created: {snapshot.name} at {snapshot.created_at}")
        """
        try:
            # Generate snapshot XML with metadata
            snap_xml = f"""
            <domainsnapshot>
                <name>{name}</name>
                <description>{description}</description>
            </domainsnapshot>
            """

            # Create snapshot via libvirt
            snap_obj = vm._domain.snapshotCreateXML(snap_xml)

            logger.info(
                "snapshot_created",
                vm=vm.name,
                vm_uuid=vm.uuid,
                snapshot=name,
                description=description,
            )

            return Snapshot(
                name=name,
                description=description,
                created_at=datetime.now(),
                _snap_obj=snap_obj,
            )

        except libvirt.libvirtError as e:
            logger.error(
                "snapshot_create_failed",
                vm=vm.name,
                vm_uuid=vm.uuid,
                snapshot=name,
                error=str(e),
            )
            raise SnapshotError(f"Failed to create snapshot '{name}': {e}") from e

    def list_snapshots(self, vm: VM) -> list[Snapshot]:
        """List all snapshots for VM.

        Retrieves all snapshots with their metadata. Returns empty list
        if no snapshots exist or if listing fails.

        Args:
            vm: VM to query for snapshots

        Returns:
            List of Snapshot objects (may be empty)

        Example:
            >>> snapshots = manager.list_snapshots(vm)
            >>> for snap in snapshots:
            ...     print(f"{snap.name}: {snap.description}")
        """
        try:
            snap_objs = vm._domain.listAllSnapshots()

            snapshots = [Snapshot(name=snap.getName(), _snap_obj=snap) for snap in snap_objs]

            logger.info(
                "snapshots_listed",
                vm=vm.name,
                vm_uuid=vm.uuid,
                count=len(snapshots),
            )

            return snapshots

        except libvirt.libvirtError as e:
            logger.error(
                "snapshot_list_failed",
                vm=vm.name,
                vm_uuid=vm.uuid,
                error=str(e),
            )
            # Return empty list instead of raising - non-critical error
            return []

    def restore_snapshot(self, vm: VM, snapshot: Snapshot) -> None:
        """Restore VM to snapshot state.

        Reverts VM to the exact state captured in the snapshot.
        This is a fast operation (<1s) for internal snapshots.

        IMPORTANT: VM should be stopped before restoring for best results,
        though libvirt supports live reversion for some snapshot types.

        Args:
            vm: VM to restore
            snapshot: Snapshot to restore to

        Raises:
            SnapshotError: If restore fails

        Example:
            >>> snapshot = manager.create_snapshot(vm, "clean")
            >>> # Do operations that may break VM...
            >>> manager.restore_snapshot(vm, snapshot)  # Back to clean!
        """
        if snapshot._snap_obj is None:
            raise SnapshotError(f"Cannot restore snapshot '{snapshot.name}': no snapshot object")

        try:
            vm._domain.revertToSnapshot(snapshot._snap_obj)

            logger.info(
                "snapshot_restored",
                vm=vm.name,
                vm_uuid=vm.uuid,
                snapshot=snapshot.name,
            )

        except libvirt.libvirtError as e:
            logger.error(
                "snapshot_restore_failed",
                vm=vm.name,
                vm_uuid=vm.uuid,
                snapshot=snapshot.name,
                error=str(e),
            )
            raise SnapshotError(f"Failed to restore snapshot '{snapshot.name}': {e}") from e

    def delete_snapshot(self, snapshot: Snapshot) -> None:
        """Delete snapshot and free resources.

        Removes snapshot and reclaims disk space. This operation
        is irreversible.

        Args:
            snapshot: Snapshot to delete

        Raises:
            SnapshotError: If deletion fails

        Example:
            >>> old_snapshot = snapshots[0]
            >>> manager.delete_snapshot(old_snapshot)
            >>> # Snapshot and its disk space are now freed
        """
        if snapshot._snap_obj is None:
            raise SnapshotError(f"Cannot delete snapshot '{snapshot.name}': no snapshot object")

        try:
            snapshot._snap_obj.delete()

            logger.info("snapshot_deleted", snapshot=snapshot.name)

        except libvirt.libvirtError as e:
            logger.error("snapshot_delete_failed", snapshot=snapshot.name, error=str(e))
            raise SnapshotError(f"Failed to delete snapshot '{snapshot.name}': {e}") from e
