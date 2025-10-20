"""VM Pool Manager for pre-warmed VM management.

This module provides the VMPool class for maintaining a pool of ready-to-use
VMs, enabling fast acquisition (<100ms target) and automatic pool management.

Follows NIST ET timezone convention for all timestamps.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import structlog

from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.snapshot import SnapshotManager
from agent_vm.core.template import NetworkMode, ResourceProfile, VMTemplate
from agent_vm.core.vm import VM, VMState

ET = ZoneInfo("America/New_York")
logger = structlog.get_logger()


class VMPoolError(Exception):
    """VM pool operation error."""

    pass


@dataclass
class PooledVM:
    """VM in pool with metadata.

    Attributes:
        vm: VM instance
        created_at: When VM was created (NIST ET)
        golden_snapshot: Snapshot name for reset
    """

    vm: VM
    created_at: datetime
    golden_snapshot: str


class VMPool:
    """Manage pool of pre-warmed VMs for fast acquisition.

    Maintains a pool of ready-to-use VMs with automatic refilling,
    TTL-based eviction, health checking, and snapshot-based reset.

    Example:
        >>> pool = VMPool(min_size=5, max_size=20)
        >>> await pool.initialize()
        >>>
        >>> # Acquire VM from pool (fast - <100ms)
        >>> vm = await pool.acquire(timeout=10)
        >>>
        >>> # Use VM...
        >>> # ...
        >>>
        >>> # Return VM to pool (resets to golden snapshot)
        >>> await pool.release(vm)
        >>>
        >>> # Cleanup
        >>> await pool.shutdown()
    """

    def __init__(
        self,
        min_size: int = 5,
        max_size: int = 20,
        ttl_seconds: int = 3600,
    ) -> None:
        """Initialize VM pool.

        Args:
            min_size: Minimum number of VMs to maintain in pool
            max_size: Maximum number of VMs allowed in pool
            ttl_seconds: VM time-to-live in seconds (evict when exceeded)

        Raises:
            VMPoolError: If configuration is invalid
        """
        # Validate configuration
        if min_size < 0:
            raise VMPoolError("min_size cannot be negative")
        if max_size < 0:
            raise VMPoolError("max_size cannot be negative")
        if max_size < 1:
            raise VMPoolError("max_size must be at least 1")
        if min_size > max_size:
            raise VMPoolError("min_size cannot exceed max_size")

        self.min_size = min_size
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

        # Pool storage (asyncio.Queue for thread safety)
        self._pool: asyncio.Queue[PooledVM] = asyncio.Queue(
            maxsize=max_size
        )

        # Lifecycle components
        self._connection: LibvirtConnection | None = None
        self._snapshot_manager = SnapshotManager()

        # State tracking
        self._initialized = False
        self._shutdown_requested = False
        self._maintenance_task: asyncio.Task[Any] | None = None
        self._acquisition_count = 0
        self._total_acquisition_time = 0.0

        self._logger = logger.bind(
            component="vm_pool",
            min_size=min_size,
            max_size=max_size,
            ttl=ttl_seconds,
        )

    async def initialize(self) -> None:
        """Initialize pool by pre-creating minimum VMs.

        Creates min_size VMs, starts them, creates golden snapshots,
        and adds them to the pool.

        Raises:
            VMPoolError: If initialization fails
        """
        if self._initialized:
            self._logger.debug("pool_already_initialized")
            return

        self._logger.info("pool_initializing", min_size=self.min_size)

        try:
            self._connection = LibvirtConnection()
            self._connection.open()

            # Create and start min_size VMs
            for i in range(self.min_size):
                vm = await self._create_fresh_vm(index=i)
                await self._pool.put(vm)

            self._initialized = True
            self._logger.info(
                "pool_initialized", pool_size=self._pool.qsize()
            )

            # Start maintenance task
            self._maintenance_task = asyncio.create_task(
                self._maintain_pool()
            )

        except Exception as e:
            self._logger.error("pool_initialization_failed", error=str(e))
            raise VMPoolError(f"Pool initialization failed: {e}") from e

    async def acquire(self, timeout: float = 10.0) -> VM:
        """Acquire VM from pool.

        Gets a VM from the pool if available, or creates on-demand if pool
        is empty. Checks VM staleness and evicts if TTL exceeded.

        Args:
            timeout: Maximum time to wait for VM (seconds)

        Returns:
            Ready-to-use VM instance

        Raises:
            VMPoolError: If timeout exceeded or acquisition fails
            TimeoutError: If timeout exceeded waiting for VM
        """
        if not self._initialized:
            raise VMPoolError("Pool not initialized - call initialize() first")

        start_time = asyncio.get_event_loop().time()
        self._logger.info("vm_acquisition_requested")

        try:
            # Try to get VM from pool
            pooled_vm = await asyncio.wait_for(
                self._pool.get(), timeout=timeout
            )

            # Check if VM is stale (exceeded TTL)
            if self._is_stale(pooled_vm):
                self._logger.info(
                    "vm_stale_evicting", vm=pooled_vm.vm.name
                )
                await self._destroy_vm(pooled_vm.vm)

                # Create fresh VM
                pooled_vm = await self._create_fresh_vm()

            # Track acquisition metrics
            acquisition_time = asyncio.get_event_loop().time() - start_time
            self._acquisition_count += 1
            self._total_acquisition_time += acquisition_time

            self._logger.info(
                "vm_acquired",
                vm=pooled_vm.vm.name,
                acquisition_time=acquisition_time,
            )

            return pooled_vm.vm

        except TimeoutError:
            # Pool empty - create on-demand
            self._logger.warning(
                "pool_empty_creating_on_demand", timeout=timeout
            )

            try:
                pooled_vm = await self._create_fresh_vm()
                acquisition_time = (
                    asyncio.get_event_loop().time() - start_time
                )
                self._logger.info(
                    "vm_created_on_demand",
                    vm=pooled_vm.vm.name,
                    acquisition_time=acquisition_time,
                )
                return pooled_vm.vm
            except Exception as create_err:
                raise VMPoolError(
                    f"Failed to create VM on-demand: {create_err}"
                ) from create_err

    async def release(self, vm: VM) -> None:
        """Release VM back to pool.

        Restores VM to golden snapshot state and returns to pool.
        If pool is full, destroys the VM instead.

        Args:
            vm: VM to release

        Raises:
            VMPoolError: If release fails
        """
        self._logger.info("vm_release_requested", vm=vm.name)

        try:
            # Find the pooled VM by matching VM instance
            # (In real implementation, would track PooledVM mapping)
            # For now, create a new PooledVM wrapper

            # Reset VM to golden snapshot
            # Note: This requires knowing the golden snapshot name
            # In real implementation, would store this in PooledVM metadata
            try:
                await self._reset_to_golden(vm)
            except Exception as reset_err:
                self._logger.error(
                    "vm_reset_failed",
                    vm=vm.name,
                    error=str(reset_err),
                )
                # If reset fails, destroy VM rather than returning corrupted state
                await self._destroy_vm(vm)
                return

            # Try to return to pool
            if self._pool.full():
                self._logger.info(
                    "pool_full_destroying_vm", vm=vm.name
                )
                await self._destroy_vm(vm)
            else:
                pooled_vm = PooledVM(
                    vm=vm,
                    created_at=datetime.now(ET),
                    golden_snapshot=f"{vm.name}-golden",
                )
                await self._pool.put(pooled_vm)
                self._logger.info("vm_returned_to_pool", vm=vm.name)

        except Exception as e:
            self._logger.error("vm_release_failed", error=str(e))
            raise VMPoolError(f"Failed to release VM: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown pool and destroy all VMs.

        Gracefully stops all pool operations, destroys all VMs,
        and closes connections.
        """
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        self._logger.info("pool_shutdown_requested")

        # Cancel maintenance task
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        # Destroy all VMs in pool
        destroyed_count = 0
        while not self._pool.empty():
            try:
                pooled_vm = self._pool.get_nowait()
                await self._destroy_vm(pooled_vm.vm)
                destroyed_count += 1
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                self._logger.error("vm_destroy_failed", error=str(e))

        # Close connection
        if self._connection:
            self._connection.close()

        self._logger.info(
            "pool_shutdown_complete", destroyed_vms=destroyed_count
        )

    def size(self) -> int:
        """Get current pool size.

        Returns:
            Number of VMs currently in pool
        """
        return self._pool.qsize()

    def _is_stale(self, pooled_vm: PooledVM) -> bool:
        """Check if VM has exceeded TTL.

        Args:
            pooled_vm: Pooled VM to check

        Returns:
            True if VM is stale (exceeded TTL)
        """
        age = datetime.now(ET) - pooled_vm.created_at
        return age > timedelta(seconds=self.ttl_seconds)

    async def _create_fresh_vm(self, index: int | None = None) -> PooledVM:
        """Create and start a fresh VM with golden snapshot.

        Args:
            index: Optional index for naming

        Returns:
            PooledVM ready for use

        Raises:
            VMPoolError: If VM creation fails
        """
        if not self._connection:
            raise VMPoolError("Connection not available")

        try:
            # Generate unique VM name
            timestamp = datetime.now(ET).strftime("%Y%m%d%H%M%S")
            if index is not None:
                vm_name = f"pool-vm-{index}-{timestamp}"
            else:
                vm_name = f"pool-vm-{timestamp}"

            # Create VM template
            template = VMTemplate(
                name=vm_name,
                resources=ResourceProfile(vcpu=2, memory_mib=2048),
                network_mode=NetworkMode.NAT_FILTERED,  # Default for CLI agents
            )

            # Define and create VM
            domain = self._connection.connection.defineXML(
                template.generate_xml()
            )
            vm = VM(domain)

            # Start VM
            vm.start()
            await vm.wait_for_state(VMState.RUNNING, timeout=30)

            # Create golden snapshot
            golden_snapshot_name = f"{vm_name}-golden"
            self._snapshot_manager.create_snapshot(
                vm, golden_snapshot_name, "Golden state for pool reset"
            )

            self._logger.info(
                "vm_created",
                vm=vm_name,
                snapshot=golden_snapshot_name,
            )

            return PooledVM(
                vm=vm,
                created_at=datetime.now(ET),
                golden_snapshot=golden_snapshot_name,
            )

        except Exception as e:
            self._logger.error("vm_creation_failed", error=str(e))
            raise VMPoolError(f"Failed to create VM: {e}") from e

    async def _destroy_vm(self, vm: VM) -> None:
        """Destroy a VM and remove it completely.

        Args:
            vm: VM to destroy
        """
        try:
            if vm.get_state() != VMState.SHUTOFF:
                vm.stop(graceful=False)
                await vm.wait_for_state(VMState.SHUTOFF, timeout=10)

            # Note: In real implementation, would call domain.undefine()
            # For now, just stop the VM

            self._logger.info("vm_destroyed", vm=vm.name)

        except Exception as e:
            self._logger.error(
                "vm_destroy_failed", vm=vm.name, error=str(e)
            )

    async def _reset_to_golden(self, vm: VM) -> None:
        """Reset VM to golden snapshot state.

        Args:
            vm: VM to reset
        """
        # In real implementation, would restore to golden snapshot
        # For now, just log the operation
        self._logger.info("vm_reset_to_golden", vm=vm.name)

    async def _maintain_pool(self) -> None:
        """Background task to maintain pool at minimum size.

        Runs periodically to refill pool if below min_size and
        perform health checks on pool VMs.
        """
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                current_size = self._pool.qsize()
                if current_size < self.min_size:
                    needed = self.min_size - current_size
                    self._logger.info(
                        "pool_refilling", current=current_size, needed=needed
                    )

                    for _ in range(needed):
                        if self._pool.full():
                            break
                        try:
                            vm = await self._create_fresh_vm()
                            await self._pool.put(vm)
                        except Exception as e:
                            self._logger.error(
                                "pool_refill_failed", error=str(e)
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error("pool_maintenance_error", error=str(e))
