"""Communication channels between host and guest VMs."""

from agent_vm.communication.filesystem import FilesystemShare
from agent_vm.communication.vsock import VsockMessage, VsockProtocol

__all__ = ["FilesystemShare", "VsockMessage", "VsockProtocol"]
