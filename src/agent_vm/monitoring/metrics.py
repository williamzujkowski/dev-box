"""Prometheus metrics collection for agent VM monitoring.

This module implements comprehensive metrics collection for VM resource usage,
agent execution, and security events. All timestamps use NIST ET timezone.
"""

import asyncio
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger()


class MetricsError(Exception):
    """Metrics operation error"""

    pass


class MetricsCollector:
    """
    Prometheus metrics collector for agent VM system.

    Collects and exposes metrics for:
    - VM resource usage (CPU, memory, disk, network)
    - Lifecycle events (boot, snapshot restore)
    - VM pool operations
    - Agent execution
    - Security violations

    All timestamps use NIST ET (America/New_York) timezone.

    Example:
        >>> collector = MetricsCollector()
        >>> collector.record_vm_cpu_usage("vm-123", "agent-abc", 45.5)
        >>> await collector.collect_vm_stats(vm, agent_id="agent-abc")
    """

    def __init__(self) -> None:
        """
        Initialize metrics collector.

        Creates all Prometheus metric objects with proper labels and documentation.
        Sets timezone to NIST ET (America/New_York).
        """
        self.timezone = ZoneInfo("America/New_York")
        self._logger = logger.bind(component="metrics_collector")

        # VM Resource Metrics (Gauges)
        self.vm_cpu_usage = Gauge(
            "agent_vm_cpu_usage_percent", "VM CPU usage percentage", ["vm_id", "agent_id"]
        )

        self.vm_memory_usage = Gauge(
            "agent_vm_memory_usage_bytes", "VM memory usage in bytes", ["vm_id", "agent_id"]
        )

        self.vm_disk_read_bytes = Counter(
            "agent_vm_disk_read_bytes_total",
            "Total bytes read from disk",
            ["vm_id", "agent_id", "device"],
        )

        self.vm_disk_write_bytes = Counter(
            "agent_vm_disk_write_bytes_total",
            "Total bytes written to disk",
            ["vm_id", "agent_id", "device"],
        )

        self.vm_network_rx_bytes = Counter(
            "agent_vm_network_rx_bytes_total",
            "Total bytes received on network",
            ["vm_id", "agent_id", "interface"],
        )

        self.vm_network_tx_bytes = Counter(
            "agent_vm_network_tx_bytes_total",
            "Total bytes transmitted on network",
            ["vm_id", "agent_id", "interface"],
        )

        # Lifecycle Metrics (Histograms)
        self.vm_boot_duration = Histogram(
            "agent_vm_boot_duration_seconds", "VM boot duration in seconds", ["vm_id"]
        )

        self.snapshot_restore_duration = Histogram(
            "agent_vm_snapshot_restore_duration_seconds",
            "Snapshot restore duration in seconds",
            ["vm_id"],
        )

        # VM Pool Metrics
        self.pool_size = Gauge("agent_vm_pool_size", "Current VM pool size", ["pool_id"])

        self.pool_acquire_duration = Histogram(
            "agent_vm_pool_acquire_duration_seconds",
            "VM pool acquisition duration in seconds",
            ["pool_id"],
        )

        # Execution Metrics
        self.execution_duration = Histogram(
            "agent_execution_duration_seconds",
            "Agent execution duration in seconds",
            ["agent_id", "status"],
        )

        self.execution_total = Counter(
            "agent_execution_total", "Total agent executions", ["agent_id", "status"]
        )

        self.execution_timeout_total = Counter(
            "agent_execution_timeout_total", "Total agent execution timeouts", ["agent_id"]
        )

        # Safety Metrics (Counters)
        self.resource_limit_violations = Counter(
            "agent_resource_limit_violations_total",
            "Total resource limit violations",
            ["vm_id", "resource_type"],
        )

        self.network_connection_attempts = Counter(
            "agent_network_connection_attempts_total",
            "Total network connection attempts",
            ["vm_id", "allowed"],
        )

        self.syscall_violations = Counter(
            "agent_syscall_violations_total", "Total syscall violations", ["vm_id", "syscall"]
        )

        self._logger.info("metrics_collector_initialized")

    def get_current_timestamp(self) -> datetime:
        """
        Get current timestamp in NIST ET timezone.

        Returns:
            Current datetime with America/New_York timezone

        Example:
            >>> collector = MetricsCollector()
            >>> ts = collector.get_current_timestamp()
            >>> ts.tzinfo.key
            'America/New_York'
        """
        return datetime.now(self.timezone)

    def _validate_label(self, label: str, name: str) -> None:
        """
        Validate metric label value.

        Args:
            label: Label value to validate
            name: Label name (for error messages)

        Raises:
            MetricsError: If label is empty or invalid
        """
        if not label or not label.strip():
            raise MetricsError(f"Label '{name}' cannot be empty")

    def _validate_percentage(self, value: float, name: str) -> None:
        """
        Validate percentage value (0-100).

        Args:
            value: Percentage value to validate
            name: Metric name (for error messages)

        Raises:
            MetricsError: If value is outside 0-100 range
        """
        if value < 0 or value > 100:
            raise MetricsError(f"{name} must be between 0 and 100, got {value}")

    def _validate_non_negative(self, value: float, name: str) -> None:
        """
        Validate non-negative value.

        Args:
            value: Value to validate
            name: Metric name (for error messages)

        Raises:
            MetricsError: If value is negative
        """
        if value < 0:
            raise MetricsError(f"{name} must be non-negative, got {value}")

    def record_vm_cpu_usage(self, vm_id: str, agent_id: str, cpu_percent: float) -> None:
        """
        Record VM CPU usage percentage.

        Args:
            vm_id: VM identifier
            agent_id: Agent identifier
            cpu_percent: CPU usage percentage (0-100)

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(agent_id, "agent_id")
        self._validate_percentage(cpu_percent, "cpu_percent")

        self.vm_cpu_usage.labels(vm_id=vm_id, agent_id=agent_id).set(cpu_percent)
        self._logger.debug(
            "vm_cpu_usage_recorded", vm_id=vm_id, agent_id=agent_id, cpu_percent=cpu_percent
        )

    def record_vm_memory_usage(self, vm_id: str, agent_id: str, memory_bytes: int) -> None:
        """
        Record VM memory usage in bytes.

        Args:
            vm_id: VM identifier
            agent_id: Agent identifier
            memory_bytes: Memory usage in bytes

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(agent_id, "agent_id")
        self._validate_non_negative(memory_bytes, "memory_bytes")

        self.vm_memory_usage.labels(vm_id=vm_id, agent_id=agent_id).set(memory_bytes)
        self._logger.debug(
            "vm_memory_usage_recorded", vm_id=vm_id, agent_id=agent_id, memory_bytes=memory_bytes
        )

    def record_vm_disk_read(self, vm_id: str, agent_id: str, device: str, bytes_read: int) -> None:
        """
        Record VM disk read bytes (cumulative).

        Args:
            vm_id: VM identifier
            agent_id: Agent identifier
            device: Disk device name (e.g., "vda")
            bytes_read: Bytes read from disk

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(agent_id, "agent_id")
        self._validate_label(device, "device")
        self._validate_non_negative(bytes_read, "bytes_read")

        self.vm_disk_read_bytes.labels(vm_id=vm_id, agent_id=agent_id, device=device).inc(
            bytes_read
        )

    def record_vm_disk_write(
        self, vm_id: str, agent_id: str, device: str, bytes_written: int
    ) -> None:
        """
        Record VM disk write bytes (cumulative).

        Args:
            vm_id: VM identifier
            agent_id: Agent identifier
            device: Disk device name (e.g., "vda")
            bytes_written: Bytes written to disk

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(agent_id, "agent_id")
        self._validate_label(device, "device")
        self._validate_non_negative(bytes_written, "bytes_written")

        self.vm_disk_write_bytes.labels(vm_id=vm_id, agent_id=agent_id, device=device).inc(
            bytes_written
        )

    def record_vm_network_rx(
        self, vm_id: str, agent_id: str, interface: str, bytes_received: int
    ) -> None:
        """
        Record VM network receive bytes (cumulative).

        Args:
            vm_id: VM identifier
            agent_id: Agent identifier
            interface: Network interface name (e.g., "eth0")
            bytes_received: Bytes received on network

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(agent_id, "agent_id")
        self._validate_label(interface, "interface")
        self._validate_non_negative(bytes_received, "bytes_received")

        self.vm_network_rx_bytes.labels(vm_id=vm_id, agent_id=agent_id, interface=interface).inc(
            bytes_received
        )

    def record_vm_network_tx(
        self, vm_id: str, agent_id: str, interface: str, bytes_transmitted: int
    ) -> None:
        """
        Record VM network transmit bytes (cumulative).

        Args:
            vm_id: VM identifier
            agent_id: Agent identifier
            interface: Network interface name (e.g., "eth0")
            bytes_transmitted: Bytes transmitted on network

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(agent_id, "agent_id")
        self._validate_label(interface, "interface")
        self._validate_non_negative(bytes_transmitted, "bytes_transmitted")

        self.vm_network_tx_bytes.labels(vm_id=vm_id, agent_id=agent_id, interface=interface).inc(
            bytes_transmitted
        )

    def record_vm_boot_duration(self, vm_id: str, duration_seconds: float) -> None:
        """
        Record VM boot duration.

        Args:
            vm_id: VM identifier
            duration_seconds: Boot duration in seconds

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_non_negative(duration_seconds, "duration_seconds")

        self.vm_boot_duration.labels(vm_id=vm_id).observe(duration_seconds)
        self._logger.info(
            "vm_boot_duration_recorded", vm_id=vm_id, duration_seconds=duration_seconds
        )

    def record_snapshot_restore_duration(self, vm_id: str, duration_seconds: float) -> None:
        """
        Record snapshot restore duration.

        Args:
            vm_id: VM identifier
            duration_seconds: Restore duration in seconds

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_non_negative(duration_seconds, "duration_seconds")

        self.snapshot_restore_duration.labels(vm_id=vm_id).observe(duration_seconds)
        self._logger.info(
            "snapshot_restore_duration_recorded", vm_id=vm_id, duration_seconds=duration_seconds
        )

    def record_pool_size(self, pool_id: str, size: int) -> None:
        """
        Record current VM pool size.

        Args:
            pool_id: Pool identifier
            size: Current pool size

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(pool_id, "pool_id")
        self._validate_non_negative(size, "size")

        self.pool_size.labels(pool_id=pool_id).set(size)
        self._logger.debug("pool_size_recorded", pool_id=pool_id, size=size)

    def record_pool_acquire_duration(self, pool_id: str, duration_seconds: float) -> None:
        """
        Record VM pool acquisition duration.

        Args:
            pool_id: Pool identifier
            duration_seconds: Acquisition duration in seconds

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(pool_id, "pool_id")
        self._validate_non_negative(duration_seconds, "duration_seconds")

        self.pool_acquire_duration.labels(pool_id=pool_id).observe(duration_seconds)
        self._logger.debug(
            "pool_acquire_duration_recorded", pool_id=pool_id, duration_seconds=duration_seconds
        )

    def record_execution_duration(
        self, agent_id: str, status: str, duration_seconds: float
    ) -> None:
        """
        Record agent execution duration.

        Args:
            agent_id: Agent identifier
            status: Execution status ("success", "failure", "timeout")
            duration_seconds: Execution duration in seconds

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(agent_id, "agent_id")
        self._validate_label(status, "status")
        self._validate_non_negative(duration_seconds, "duration_seconds")

        self.execution_duration.labels(agent_id=agent_id, status=status).observe(duration_seconds)
        self._logger.info(
            "execution_duration_recorded",
            agent_id=agent_id,
            status=status,
            duration_seconds=duration_seconds,
        )

    def record_execution_total(self, agent_id: str, status: str) -> None:
        """
        Record agent execution count.

        Args:
            agent_id: Agent identifier
            status: Execution status ("success", "failure", "timeout")

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(agent_id, "agent_id")
        self._validate_label(status, "status")

        self.execution_total.labels(agent_id=agent_id, status=status).inc()
        self._logger.debug("execution_total_incremented", agent_id=agent_id, status=status)

    def record_execution_timeout(self, agent_id: str) -> None:
        """
        Record agent execution timeout.

        Args:
            agent_id: Agent identifier

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(agent_id, "agent_id")

        self.execution_timeout_total.labels(agent_id=agent_id).inc()
        self._logger.warning("execution_timeout_recorded", agent_id=agent_id)

    def record_resource_limit_violation(self, vm_id: str, resource_type: str) -> None:
        """
        Record resource limit violation.

        Args:
            vm_id: VM identifier
            resource_type: Resource type ("cpu", "memory", "disk", "network")

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(resource_type, "resource_type")

        self.resource_limit_violations.labels(vm_id=vm_id, resource_type=resource_type).inc()
        self._logger.warning(
            "resource_limit_violation_recorded", vm_id=vm_id, resource_type=resource_type
        )

    def record_network_connection_attempt(self, vm_id: str, allowed: bool) -> None:
        """
        Record network connection attempt.

        Args:
            vm_id: VM identifier
            allowed: Whether connection was allowed

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")

        self.network_connection_attempts.labels(vm_id=vm_id, allowed=str(allowed).lower()).inc()
        self._logger.debug("network_connection_attempt_recorded", vm_id=vm_id, allowed=allowed)

    def record_syscall_violation(self, vm_id: str, syscall: str) -> None:
        """
        Record syscall violation (blocked syscall attempt).

        Args:
            vm_id: VM identifier
            syscall: Syscall name (e.g., "ptrace")

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(vm_id, "vm_id")
        self._validate_label(syscall, "syscall")

        self.syscall_violations.labels(vm_id=vm_id, syscall=syscall).inc()
        self._logger.warning("syscall_violation_recorded", vm_id=vm_id, syscall=syscall)

    async def collect_vm_stats(self, vm: Any, agent_id: str) -> None:
        """
        Collect and record all VM statistics asynchronously.

        Args:
            vm: VM instance with get_stats() method
            agent_id: Agent identifier

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(agent_id, "agent_id")

        try:
            stats = vm.get_stats()

            # Record resource metrics
            self.record_vm_cpu_usage(vm.id, agent_id, stats.cpu_percent)
            self.record_vm_memory_usage(vm.id, agent_id, stats.memory_bytes)

            # Record disk I/O
            for device, bytes_read in stats.disk_read_bytes.items():
                self.record_vm_disk_read(vm.id, agent_id, device, bytes_read)

            for device, bytes_written in stats.disk_write_bytes.items():
                self.record_vm_disk_write(vm.id, agent_id, device, bytes_written)

            # Record network I/O
            for interface, bytes_rx in stats.network_rx_bytes.items():
                self.record_vm_network_rx(vm.id, agent_id, interface, bytes_rx)

            for interface, bytes_tx in stats.network_tx_bytes.items():
                self.record_vm_network_tx(vm.id, agent_id, interface, bytes_tx)

            self._logger.debug("vm_stats_collected", vm_id=vm.id, agent_id=agent_id)

        except Exception as e:
            self._logger.error(
                "vm_stats_collection_failed", vm_id=vm.id, agent_id=agent_id, error=str(e)
            )
            # Don't raise - metrics collection should not crash the system

    async def collect_batch_vm_stats(self, vms: list[Any], agent_id: str) -> None:
        """
        Collect statistics from multiple VMs in parallel.

        Args:
            vms: List of VM instances
            agent_id: Agent identifier

        Raises:
            MetricsError: If inputs are invalid
        """
        self._validate_label(agent_id, "agent_id")

        tasks = [self.collect_vm_stats(vm, agent_id) for vm in vms]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._logger.info("batch_vm_stats_collected", vm_count=len(vms), agent_id=agent_id)
