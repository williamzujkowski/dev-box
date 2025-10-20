"""Unit tests for snapshot management.

Tests cover the complete snapshot lifecycle:
- Creating snapshots with metadata
- Listing snapshots
- Restoring VMs to snapshots
- Deleting snapshots
- Error handling
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
from agent_vm.core.snapshot import SnapshotManager, Snapshot, SnapshotError


class TestSnapshot:
    """Test Snapshot dataclass"""

    def test_snapshot_creation_with_metadata(self):
        """Snapshot stores name, description, and timestamp"""
        snap = Snapshot(
            name="test-snap",
            description="Test snapshot",
            created_at=datetime.now(),
        )

        assert snap.name == "test-snap"
        assert snap.description == "Test snapshot"
        assert snap.created_at is not None
        assert snap._snap_obj is None

    def test_snapshot_optional_fields(self):
        """Snapshot has sensible defaults for optional fields"""
        snap = Snapshot(name="minimal-snap")

        assert snap.name == "minimal-snap"
        assert snap.description == ""
        assert snap.created_at is None
        assert snap._snap_obj is None


class TestSnapshotManager:
    """Test snapshot management operations"""

    def test_create_snapshot(self, mock_vm):
        """Create snapshot of VM with metadata"""
        manager = SnapshotManager()

        # Configure mock
        mock_snap_obj = Mock()
        mock_vm._domain.snapshotCreateXML.return_value = mock_snap_obj

        # Create snapshot
        snapshot = manager.create_snapshot(mock_vm, name="test-snap", description="Test snapshot")

        # Verify
        assert snapshot.name == "test-snap"
        assert snapshot.description == "Test snapshot"
        assert snapshot.created_at is not None
        assert snapshot._snap_obj is mock_snap_obj

        # Verify XML generation and call
        mock_vm._domain.snapshotCreateXML.assert_called_once()
        xml_arg = mock_vm._domain.snapshotCreateXML.call_args[0][0]
        assert "<name>test-snap</name>" in xml_arg
        assert "<description>Test snapshot</description>" in xml_arg

    def test_create_snapshot_with_empty_description(self, mock_vm):
        """Create snapshot without description"""
        manager = SnapshotManager()

        mock_snap_obj = Mock()
        mock_vm._domain.snapshotCreateXML.return_value = mock_snap_obj

        snapshot = manager.create_snapshot(mock_vm, name="no-desc-snap")

        assert snapshot.name == "no-desc-snap"
        assert snapshot.description == ""
        mock_vm._domain.snapshotCreateXML.assert_called_once()

    def test_create_snapshot_handles_libvirt_error(self, mock_vm):
        """Create snapshot raises SnapshotError on libvirt failure"""
        import libvirt

        manager = SnapshotManager()

        # Mock libvirt error
        mock_vm._domain.snapshotCreateXML.side_effect = libvirt.libvirtError(
            "Snapshot creation failed"
        )

        # Verify exception raised
        with pytest.raises(SnapshotError, match="Failed to create snapshot"):
            manager.create_snapshot(mock_vm, name="fail-snap")

    def test_list_snapshots(self, mock_vm):
        """List all snapshots for VM"""
        manager = SnapshotManager()

        # Configure mock snapshots
        mock_snap1 = Mock()
        mock_snap1.getName.return_value = "snap1"

        mock_snap2 = Mock()
        mock_snap2.getName.return_value = "snap2"

        mock_vm._domain.listAllSnapshots.return_value = [mock_snap1, mock_snap2]

        # List snapshots
        snapshots = manager.list_snapshots(mock_vm)

        # Verify
        assert len(snapshots) == 2
        assert snapshots[0].name == "snap1"
        assert snapshots[0]._snap_obj is mock_snap1
        assert snapshots[1].name == "snap2"
        assert snapshots[1]._snap_obj is mock_snap2

    def test_list_snapshots_empty(self, mock_vm):
        """List snapshots returns empty list when no snapshots exist"""
        manager = SnapshotManager()

        mock_vm._domain.listAllSnapshots.return_value = []

        snapshots = manager.list_snapshots(mock_vm)

        assert snapshots == []

    def test_list_snapshots_handles_libvirt_error(self, mock_vm):
        """List snapshots returns empty list on libvirt error"""
        import libvirt

        manager = SnapshotManager()

        mock_vm._domain.listAllSnapshots.side_effect = libvirt.libvirtError(
            "Failed to list snapshots"
        )

        # Should not raise, returns empty list
        snapshots = manager.list_snapshots(mock_vm)

        assert snapshots == []

    def test_restore_snapshot(self, mock_vm):
        """Restore VM to snapshot state"""
        manager = SnapshotManager()

        # Create snapshot object
        mock_snap_obj = Mock()
        snapshot = Snapshot(name="test-snap", _snap_obj=mock_snap_obj)

        # Restore
        manager.restore_snapshot(mock_vm, snapshot)

        # Verify
        mock_vm._domain.revertToSnapshot.assert_called_once_with(mock_snap_obj)

    def test_restore_snapshot_handles_libvirt_error(self, mock_vm):
        """Restore snapshot raises SnapshotError on failure"""
        import libvirt

        manager = SnapshotManager()

        mock_snap_obj = Mock()
        snapshot = Snapshot(name="test-snap", _snap_obj=mock_snap_obj)

        mock_vm._domain.revertToSnapshot.side_effect = libvirt.libvirtError("Restore failed")

        with pytest.raises(SnapshotError, match="Failed to restore snapshot"):
            manager.restore_snapshot(mock_vm, snapshot)

    def test_delete_snapshot(self):
        """Delete snapshot removes it"""
        manager = SnapshotManager()

        # Create snapshot with mock object
        mock_snap_obj = Mock()
        snapshot = Snapshot(name="test-snap", _snap_obj=mock_snap_obj)

        # Delete
        manager.delete_snapshot(snapshot)

        # Verify
        mock_snap_obj.delete.assert_called_once()

    def test_delete_snapshot_handles_libvirt_error(self):
        """Delete snapshot raises SnapshotError on failure"""
        import libvirt

        manager = SnapshotManager()

        mock_snap_obj = Mock()
        mock_snap_obj.delete.side_effect = libvirt.libvirtError("Delete failed")

        snapshot = Snapshot(name="test-snap", _snap_obj=mock_snap_obj)

        with pytest.raises(SnapshotError, match="Failed to delete snapshot"):
            manager.delete_snapshot(snapshot)


class TestSnapshotIntegration:
    """Integration tests for snapshot workflows"""

    def test_create_and_restore_workflow(self, mock_vm):
        """Complete workflow: create snapshot, restore to it"""
        manager = SnapshotManager()

        # Create snapshot
        mock_snap_obj = Mock()
        mock_vm._domain.snapshotCreateXML.return_value = mock_snap_obj

        snapshot = manager.create_snapshot(mock_vm, name="golden", description="Golden state")

        # Verify creation
        assert snapshot.name == "golden"
        assert snapshot._snap_obj is mock_snap_obj

        # Restore
        manager.restore_snapshot(mock_vm, snapshot)

        # Verify restore
        mock_vm._domain.revertToSnapshot.assert_called_once_with(mock_snap_obj)

    def test_create_list_delete_workflow(self, mock_vm):
        """Complete workflow: create, list, delete snapshots"""
        manager = SnapshotManager()

        # Create snapshots
        mock_snap1 = Mock()
        mock_snap1.getName.return_value = "snap1"
        mock_snap2 = Mock()
        mock_snap2.getName.return_value = "snap2"

        mock_vm._domain.snapshotCreateXML.side_effect = [mock_snap1, mock_snap2]

        snapshot1 = manager.create_snapshot(mock_vm, name="snap1")
        snapshot2 = manager.create_snapshot(mock_vm, name="snap2")

        # List snapshots
        mock_vm._domain.listAllSnapshots.return_value = [mock_snap1, mock_snap2]
        snapshots = manager.list_snapshots(mock_vm)

        assert len(snapshots) == 2
        assert {s.name for s in snapshots} == {"snap1", "snap2"}

        # Delete one snapshot
        manager.delete_snapshot(snapshot1)
        mock_snap1.delete.assert_called_once()

        # List should now return one less
        mock_vm._domain.listAllSnapshots.return_value = [mock_snap2]
        snapshots = manager.list_snapshots(mock_vm)

        assert len(snapshots) == 1
        assert snapshots[0].name == "snap2"
