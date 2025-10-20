"""VM domain abstraction layer.

This module provides a high-level abstraction over libvirt domains (VMs),
offering lifecycle management, state monitoring, and async operations.

Key Features:
- Clean VM lifecycle (start, stop, wait for states)
- Graceful and force shutdown options
- Async wait_for_state with timeout enforcement
- Structured logging with VM context
- Type-safe with strict mypy compliance
"""

import asyncio
from enum import Enum
from typing import cast

import libvirt
import structlog
from structlog.stdlib import BoundLogger

logger = structlog.get_logger()


class VMState(Enum):
    """VM state enumeration.

    Maps libvirt domain states to human-readable values.

    States:
        RUNNING: VM is actively running
        PAUSED: VM is paused (suspended)
        SHUTDOWN: VM is shutting down
        SHUTOFF: VM is powered off
        CRASHED: VM has crashed
        UNKNOWN: VM state is unknown or invalid
    """

    RUNNING = "running"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    SHUTOFF = "shutoff"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


class VMError(Exception):
    """VM operation error.

    Raised when VM operations fail due to libvirt errors or
    invalid state transitions.
    """

    pass


class VM:
    """High-level abstraction over libvirt domain.

    Provides lifecycle management, state monitoring, and async operations
    for KVM virtual machines.

    Attributes:
        name: VM name (from libvirt domain)
        uuid: VM UUID (from libvirt domain)

    Example:
        >>> with LibvirtConnection() as conn:
        ...     domain = conn.connection.lookupByName("my-vm")
        ...     vm = VM(domain)
        ...     vm.start()
        ...     await vm.wait_for_state(VMState.RUNNING, timeout=30)
        ...     vm.stop(graceful=True)
    """

    def __init__(self, domain: libvirt.virDomain) -> None:
        """Initialize VM wrapper.

        Args:
            domain: libvirt virDomain instance to wrap
        """
        self._domain = domain

        # Try to create bound logger, but don't fail if domain methods fail
        # This allows VM creation to succeed even if domain is in bad state
        try:
            self._logger = logger.bind(vm_name=self.name, vm_uuid=self.uuid)
        except Exception:
            # Logger will be created on first use if initial binding fails
            self._logger = None

    def _get_logger(self) -> BoundLogger:
        """Get or create bound logger with VM context.

        Returns:
            Logger bound to VM name and UUID
        """
        if self._logger is None:
            # structlog's bind() returns Any, but we know it's a BoundLogger
            self._logger = cast(BoundLogger, logger.bind(vm_name=self.name, vm_uuid=self.uuid))
        return cast(BoundLogger, self._logger)

    @property
    def name(self) -> str:
        """Get VM name.

        Returns:
            VM name from libvirt domain
        """
        return str(self._domain.name())

    @property
    def uuid(self) -> str:
        """Get VM UUID.

        Returns:
            VM UUID string from libvirt domain
        """
        return str(self._domain.UUIDString())

    def get_state(self) -> VMState:
        """Get current VM state.

        Maps libvirt state codes to VMState enum values.

        Returns:
            Current VM state

        Raises:
            VMError: If state retrieval fails

        State Mappings:
            0 (NOSTATE) -> UNKNOWN
            1 (RUNNING) -> RUNNING
            2 (BLOCKED) -> RUNNING (treat as running)
            3 (PAUSED) -> PAUSED
            4 (SHUTDOWN) -> SHUTDOWN
            5 (SHUTOFF) -> SHUTOFF
            6 (CRASHED) -> CRASHED
            7 (PMSUSPENDED) -> PAUSED (treat as paused)
            Other -> UNKNOWN
        """
        try:
            state_info = self._domain.state()
            state_code = state_info[0]

            # Map libvirt state codes to VMState enum
            state_map = {
                0: VMState.UNKNOWN,  # VIR_DOMAIN_NOSTATE
                1: VMState.RUNNING,  # VIR_DOMAIN_RUNNING
                2: VMState.RUNNING,  # VIR_DOMAIN_BLOCKED (treat as running)
                3: VMState.PAUSED,  # VIR_DOMAIN_PAUSED
                4: VMState.SHUTDOWN,  # VIR_DOMAIN_SHUTDOWN
                5: VMState.SHUTOFF,  # VIR_DOMAIN_SHUTOFF
                6: VMState.CRASHED,  # VIR_DOMAIN_CRASHED
                7: VMState.PAUSED,  # VIR_DOMAIN_PMSUSPENDED (treat as paused)
            }

            return state_map.get(state_code, VMState.UNKNOWN)

        except libvirt.libvirtError as e:
            self._get_logger().error("vm_get_state_failed", error=str(e))
            raise VMError(f"Failed to get VM state: {e}") from e

    def start(self) -> None:
        """Start the VM.

        Starts the VM if it's not already running. Idempotent - does nothing
        if VM is already running.

        Raises:
            VMError: If start operation fails

        Example:
            >>> vm.start()
            >>> # VM is now starting
        """
        try:
            # Check if already running
            if self._domain.isActive():
                self._get_logger().info("vm_already_running")
                return

            self._get_logger().info("vm_starting")
            self._domain.create()
            self._get_logger().info("vm_started")

        except libvirt.libvirtError as e:
            self._get_logger().error("vm_start_failed", error=str(e))
            raise VMError(f"Start failed: {e}") from e

    def stop(self, graceful: bool = False) -> None:
        """Stop the VM.

        Stops the VM using either graceful shutdown or force destroy.
        Idempotent - does nothing if VM is already stopped.

        Args:
            graceful: If True, use graceful shutdown (domain.shutdown()).
                     If False, force destroy (domain.destroy()). Default: False.

        Raises:
            VMError: If stop operation fails

        Example:
            >>> vm.stop(graceful=True)  # Try graceful shutdown
            >>> await vm.wait_for_state(VMState.SHUTOFF, timeout=30)
            >>> # If timeout, use force stop:
            >>> vm.stop(graceful=False)
        """
        try:
            # Check if already stopped
            if not self._domain.isActive():
                self._get_logger().info("vm_already_stopped")
                return

            if graceful:
                self._get_logger().info("vm_stopping_graceful")
                self._domain.shutdown()
                self._get_logger().info("vm_shutdown_initiated")
            else:
                self._get_logger().info("vm_stopping_force")
                self._domain.destroy()
                self._get_logger().info("vm_destroyed")

        except libvirt.libvirtError as e:
            self._get_logger().error("vm_stop_failed", error=str(e), graceful=graceful)
            raise VMError(f"Stop failed: {e}") from e

    async def wait_for_state(
        self, desired_state: VMState, timeout: float = 30.0, poll_interval: float = 0.5
    ) -> None:
        """Wait for VM to reach desired state.

        Polls VM state until it reaches the desired state or timeout expires.
        Uses asyncio for non-blocking polling.

        Args:
            desired_state: Target VM state to wait for
            timeout: Maximum time to wait in seconds (default: 30.0)
            poll_interval: Time between state checks in seconds (default: 0.5)

        Raises:
            VMError: If timeout expires before reaching desired state

        Example:
            >>> vm.start()
            >>> await vm.wait_for_state(VMState.RUNNING, timeout=30)
            >>> # VM is now running
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            current_state = self.get_state()

            if current_state == desired_state:
                elapsed = asyncio.get_event_loop().time() - start_time
                self._get_logger().info(
                    "vm_state_reached", desired_state=desired_state.value, elapsed=f"{elapsed:.2f}s"
                )
                return

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self._get_logger().error(
                    "vm_state_timeout",
                    desired_state=desired_state.value,
                    current_state=current_state.value,
                    timeout=timeout,
                )
                raise VMError(
                    f"Timeout waiting for state {desired_state.value} "
                    f"(current: {current_state.value}, timeout: {timeout}s)"
                )

            # Sleep before next check
            await asyncio.sleep(poll_interval)
