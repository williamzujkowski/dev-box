"""Core libvirt abstractions."""

from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.snapshot import Snapshot, SnapshotManager
from agent_vm.core.template import NetworkMode, ResourceProfile, VMTemplate
from agent_vm.core.vm import VM, VMError, VMState

__all__ = [
    "VM",
    "LibvirtConnection",
    "NetworkMode",
    "ResourceProfile",
    "Snapshot",
    "SnapshotManager",
    "VMError",
    "VMState",
    "VMTemplate",
]
