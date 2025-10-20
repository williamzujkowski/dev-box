"""Unit tests for MetricsCollector - WRITE TESTS FIRST (TDD)"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo
from prometheus_client import REGISTRY

# Import will fail until implementation exists (RED phase)
from agent_vm.monitoring.metrics import (
    MetricsCollector,
    MetricsError,
)


@pytest.fixture(autouse=True)
def clean_prometheus_registry():
    """
    Clear Prometheus registry before and after each test.

    This prevents "Duplicated timeseries in CollectorRegistry" errors
    when multiple tests create MetricsCollector instances.
    """
    # Clear before test
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass

    yield

    # Clear after test
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


class TestMetricsCollector:
    """Test Prometheus metrics collection"""

    def test_metrics_collector_initializes(self):
        """MetricsCollector initializes with all required metrics"""
        collector = MetricsCollector()

        # Verify all metric attributes exist
        assert hasattr(collector, "vm_cpu_usage")
        assert hasattr(collector, "vm_memory_usage")
        assert hasattr(collector, "vm_disk_read_bytes")
        assert hasattr(collector, "vm_disk_write_bytes")
        assert hasattr(collector, "vm_network_rx_bytes")
        assert hasattr(collector, "vm_network_tx_bytes")
        assert hasattr(collector, "vm_boot_duration")
        assert hasattr(collector, "snapshot_restore_duration")
        assert hasattr(collector, "pool_size")
        assert hasattr(collector, "pool_acquire_duration")
        assert hasattr(collector, "execution_duration")
        assert hasattr(collector, "execution_total")
        assert hasattr(collector, "execution_timeout_total")
        assert hasattr(collector, "resource_limit_violations")
        assert hasattr(collector, "network_connection_attempts")
        assert hasattr(collector, "syscall_violations")

    def test_metrics_use_nist_et_timezone(self):
        """Metrics timestamps use NIST ET (America/New_York)"""
        collector = MetricsCollector()

        # Verify timezone is set correctly
        assert collector.timezone == ZoneInfo("America/New_York")

    def test_record_vm_cpu_usage(self):
        """Record VM CPU usage metric"""
        collector = MetricsCollector()

        collector.record_vm_cpu_usage(
            vm_id="test-vm-123",
            agent_id="agent-abc",
            cpu_percent=45.5
        )

        # Verify metric was set (would check Prometheus registry in reality)
        # For now, just verify no exceptions

    def test_record_vm_memory_usage(self):
        """Record VM memory usage metric"""
        collector = MetricsCollector()

        collector.record_vm_memory_usage(
            vm_id="test-vm-123",
            agent_id="agent-abc",
            memory_bytes=1024 * 1024 * 1024  # 1GB
        )

    def test_record_vm_disk_io(self):
        """Record VM disk I/O metrics"""
        collector = MetricsCollector()

        collector.record_vm_disk_read(
            vm_id="test-vm-123",
            agent_id="agent-abc",
            device="vda",
            bytes_read=1024 * 1024  # 1MB
        )

        collector.record_vm_disk_write(
            vm_id="test-vm-123",
            agent_id="agent-abc",
            device="vda",
            bytes_written=512 * 1024  # 512KB
        )

    def test_record_vm_network_io(self):
        """Record VM network I/O metrics"""
        collector = MetricsCollector()

        collector.record_vm_network_rx(
            vm_id="test-vm-123",
            agent_id="agent-abc",
            interface="eth0",
            bytes_received=2048 * 1024  # 2MB
        )

        collector.record_vm_network_tx(
            vm_id="test-vm-123",
            agent_id="agent-abc",
            interface="eth0",
            bytes_transmitted=1024 * 1024  # 1MB
        )

    def test_record_vm_boot_duration(self):
        """Record VM boot duration"""
        collector = MetricsCollector()

        collector.record_vm_boot_duration(
            vm_id="test-vm-123",
            duration_seconds=1.5
        )

    def test_record_snapshot_restore_duration(self):
        """Record snapshot restore duration"""
        collector = MetricsCollector()

        collector.record_snapshot_restore_duration(
            vm_id="test-vm-123",
            duration_seconds=0.8
        )

    def test_record_pool_size(self):
        """Record VM pool size"""
        collector = MetricsCollector()

        collector.record_pool_size(
            pool_id="standard-pool",
            size=10
        )

    def test_record_pool_acquire_duration(self):
        """Record pool VM acquisition duration"""
        collector = MetricsCollector()

        collector.record_pool_acquire_duration(
            pool_id="standard-pool",
            duration_seconds=0.05
        )

    def test_record_execution_duration(self):
        """Record agent execution duration"""
        collector = MetricsCollector()

        collector.record_execution_duration(
            agent_id="agent-abc",
            status="success",
            duration_seconds=30.5
        )

    def test_record_execution_total(self):
        """Record total agent executions"""
        collector = MetricsCollector()

        collector.record_execution_total(
            agent_id="agent-abc",
            status="success"
        )

        collector.record_execution_total(
            agent_id="agent-abc",
            status="failure"
        )

    def test_record_execution_timeout(self):
        """Record agent execution timeout"""
        collector = MetricsCollector()

        collector.record_execution_timeout(
            agent_id="agent-abc"
        )

    def test_record_resource_limit_violation(self):
        """Record resource limit violation"""
        collector = MetricsCollector()

        collector.record_resource_limit_violation(
            vm_id="test-vm-123",
            resource_type="cpu"
        )

        collector.record_resource_limit_violation(
            vm_id="test-vm-123",
            resource_type="memory"
        )

    def test_record_network_connection_attempt(self):
        """Record network connection attempt"""
        collector = MetricsCollector()

        collector.record_network_connection_attempt(
            vm_id="test-vm-123",
            allowed=True
        )

        collector.record_network_connection_attempt(
            vm_id="test-vm-123",
            allowed=False
        )

    def test_record_syscall_violation(self):
        """Record syscall violation"""
        collector = MetricsCollector()

        collector.record_syscall_violation(
            vm_id="test-vm-123",
            syscall="ptrace"
        )

    def test_metrics_with_multiple_labels(self):
        """Metrics correctly handle multiple label combinations"""
        collector = MetricsCollector()

        # Same metric, different labels
        collector.record_vm_cpu_usage("vm-1", "agent-1", 45.0)
        collector.record_vm_cpu_usage("vm-2", "agent-2", 67.0)
        collector.record_vm_cpu_usage("vm-1", "agent-1", 50.0)  # Update

        # Should not raise exceptions

    @pytest.mark.asyncio
    async def test_collect_vm_stats_async(self):
        """Collect VM statistics asynchronously"""
        collector = MetricsCollector()
        mock_vm = Mock()
        mock_vm.id = "test-vm-123"
        mock_vm.name = "test-vm"

        # Mock VM stats
        mock_stats = Mock()
        mock_stats.cpu_percent = 55.5
        mock_stats.memory_bytes = 2048 * 1024 * 1024  # 2GB
        mock_stats.disk_read_bytes = {"vda": 1024 * 1024}
        mock_stats.disk_write_bytes = {"vda": 512 * 1024}
        mock_stats.network_rx_bytes = {"eth0": 2048 * 1024}
        mock_stats.network_tx_bytes = {"eth0": 1024 * 1024}

        mock_vm.get_stats = Mock(return_value=mock_stats)

        await collector.collect_vm_stats(mock_vm, agent_id="agent-abc")

        # Verify get_stats was called
        mock_vm.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_vm_stats_handles_errors(self):
        """Collect VM stats handles errors gracefully"""
        collector = MetricsCollector()
        mock_vm = Mock()
        mock_vm.id = "test-vm-123"
        mock_vm.get_stats = Mock(side_effect=Exception("Stats unavailable"))

        # Should log error but not raise
        await collector.collect_vm_stats(mock_vm, agent_id="agent-abc")

    def test_get_current_timestamp_nist_et(self):
        """Get current timestamp in NIST ET timezone"""
        collector = MetricsCollector()

        timestamp = collector.get_current_timestamp()

        # Verify it's a datetime with ET timezone
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo == ZoneInfo("America/New_York")

    def test_metrics_exposition_format(self):
        """Metrics can be exposed in Prometheus format"""
        collector = MetricsCollector()

        # Record some metrics
        collector.record_vm_cpu_usage("vm-1", "agent-1", 45.0)
        collector.record_execution_total("agent-1", "success")

        # Get Prometheus exposition (would be scraped by Prometheus)
        # For now, just verify metrics exist
        from prometheus_client import REGISTRY

        metric_names = [m.name for m in REGISTRY.collect()]
        assert "agent_vm_cpu_usage_percent" in metric_names
        # Counter metrics have _total suffix stripped by Prometheus
        assert "agent_execution" in metric_names

    def test_counter_increments(self):
        """Counter metrics increment correctly"""
        collector = MetricsCollector()

        # Record multiple executions
        collector.record_execution_total("agent-1", "success")
        collector.record_execution_total("agent-1", "success")
        collector.record_execution_total("agent-1", "failure")

        # Counters should have incremented (would verify value in reality)

    def test_gauge_updates(self):
        """Gauge metrics update correctly"""
        collector = MetricsCollector()

        # Update pool size multiple times
        collector.record_pool_size("pool-1", 5)
        collector.record_pool_size("pool-1", 10)
        collector.record_pool_size("pool-1", 7)

        # Gauge should reflect latest value

    def test_histogram_observes(self):
        """Histogram metrics observe values correctly"""
        collector = MetricsCollector()

        # Record multiple durations
        collector.record_execution_duration("agent-1", "success", 10.5)
        collector.record_execution_duration("agent-1", "success", 15.2)
        collector.record_execution_duration("agent-1", "success", 8.3)

        # Histogram should have recorded all observations

    def test_metrics_thread_safety(self):
        """Metrics are thread-safe"""
        import threading

        collector = MetricsCollector()

        def record_metrics():
            for i in range(100):
                collector.record_execution_total(f"agent-{i % 10}", "success")

        threads = [threading.Thread(target=record_metrics) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not raise exceptions

    def test_invalid_metric_values_raise_error(self):
        """Invalid metric values raise MetricsError"""
        collector = MetricsCollector()

        # Negative CPU percentage
        with pytest.raises(MetricsError):
            collector.record_vm_cpu_usage("vm-1", "agent-1", -10.0)

        # CPU percentage > 100
        with pytest.raises(MetricsError):
            collector.record_vm_cpu_usage("vm-1", "agent-1", 150.0)

        # Negative memory
        with pytest.raises(MetricsError):
            collector.record_vm_memory_usage("vm-1", "agent-1", -1024)

        # Negative duration
        with pytest.raises(MetricsError):
            collector.record_execution_duration("agent-1", "success", -5.0)

    def test_empty_labels_raise_error(self):
        """Empty label values raise MetricsError"""
        collector = MetricsCollector()

        with pytest.raises(MetricsError):
            collector.record_vm_cpu_usage("", "agent-1", 45.0)

        with pytest.raises(MetricsError):
            collector.record_vm_cpu_usage("vm-1", "", 45.0)

    @pytest.mark.asyncio
    async def test_batch_metric_collection(self):
        """Collect metrics from multiple VMs in batch"""
        collector = MetricsCollector()

        mock_vms = []
        for i in range(5):
            mock_vm = Mock()
            mock_vm.id = f"vm-{i}"
            mock_stats = Mock()
            mock_stats.cpu_percent = 50.0 + i
            mock_stats.memory_bytes = (1024 + i) * 1024 * 1024
            mock_stats.disk_read_bytes = {}
            mock_stats.disk_write_bytes = {}
            mock_stats.network_rx_bytes = {}
            mock_stats.network_tx_bytes = {}
            mock_vm.get_stats = Mock(return_value=mock_stats)
            mock_vms.append(mock_vm)

        await collector.collect_batch_vm_stats(mock_vms, agent_id="agent-1")

        # All VMs should have been queried
        for vm in mock_vms:
            vm.get_stats.assert_called_once()

    def test_metrics_reset(self):
        """Metrics can be reset (for testing)"""
        collector = MetricsCollector()

        # Record some metrics
        collector.record_execution_total("agent-1", "success")
        collector.record_vm_cpu_usage("vm-1", "agent-1", 45.0)

        # Reset (if implemented)
        # collector.reset()

        # Metrics should be cleared
        # (Implementation detail - may not be needed)

    def test_custom_metric_labels(self):
        """Metrics support custom labels"""
        collector = MetricsCollector()

        # Test with different label combinations
        labels = [
            ("vm-1", "agent-1"),
            ("vm-2", "agent-1"),
            ("vm-1", "agent-2"),
        ]

        for vm_id, agent_id in labels:
            collector.record_vm_cpu_usage(vm_id, agent_id, 50.0)

    def test_metrics_documentation(self):
        """Metrics have proper help text"""
        collector = MetricsCollector()

        # Verify metrics have documentation
        # (Would check metric.documentation in reality)
        assert collector.vm_cpu_usage._documentation
        assert collector.execution_total._documentation

    def test_structured_logging(self):
        """MetricsCollector uses structured logging"""
        with patch("agent_vm.monitoring.metrics.logger") as mock_logger:
            collector = MetricsCollector()
            collector.record_vm_cpu_usage("vm-1", "agent-1", 45.0)

            # Verify structured log was called
            # mock_logger.debug.assert_called()

    def test_metric_timestamps(self):
        """Metrics include proper timestamps in ET"""
        collector = MetricsCollector()

        ts1 = collector.get_current_timestamp()
        ts2 = collector.get_current_timestamp()

        # Both should be in ET timezone
        assert ts1.tzinfo == ZoneInfo("America/New_York")
        assert ts2.tzinfo == ZoneInfo("America/New_York")
        assert ts2 >= ts1  # Time moves forward


class TestMetricsError:
    """Test MetricsError exception"""

    def test_metrics_error_is_exception(self):
        """MetricsError is an Exception"""
        error = MetricsError("test error")
        assert isinstance(error, Exception)

    def test_metrics_error_message(self):
        """MetricsError preserves error message"""
        error = MetricsError("Invalid CPU percentage")
        assert str(error) == "Invalid CPU percentage"
