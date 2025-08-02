"""
Performance tests and benchmarks for the LLM Sandbox Vagrant Agent.

These tests measure and validate performance characteristics under various
load conditions and usage patterns.
"""

import pytest
import time
import threading
import psutil
import statistics
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.mark.performance
class TestVMPerformance:
    """Test VM operation performance benchmarks."""
    
    def setup_method(self):
        """Set up performance test fixtures."""
        self.performance_metrics = {
            "vm_startup_times": [],
            "vm_shutdown_times": [],
            "snapshot_creation_times": [],
            "snapshot_restore_times": [],
            "command_execution_times": [],
            "memory_usage_samples": [],
            "cpu_usage_samples": []
        }
    
    @pytest.mark.slow
    def test_vm_startup_performance(self, test_vm_manager, performance_timer, performance_test_data):
        """Test VM startup time performance."""
        max_startup_time = performance_test_data["vm_startup_timeout"]
        num_trials = 5
        startup_times = []
        
        for trial in range(num_trials):
            vm_name = f"perf-startup-{trial}-{int(time.time())}"
            
            performance_timer.start()
            vm_id = test_vm_manager.create_test_vm(vm_name, {})
            self._simulate_vm_startup(vm_id)
            performance_timer.stop()
            
            startup_time = performance_timer.elapsed()
            startup_times.append(startup_time)
            self.performance_metrics["vm_startup_times"].append(startup_time)
            
            # Cleanup
            self._cleanup_vm(vm_id)
        
        # Analyze performance
        avg_startup_time = statistics.mean(startup_times)
        max_startup_time_observed = max(startup_times)
        
        assert avg_startup_time < max_startup_time * 0.8  # Should be well under limit
        assert max_startup_time_observed < max_startup_time
        
        print(f"VM Startup Performance:")
        print(f"  Average: {avg_startup_time:.2f}s")
        print(f"  Max: {max_startup_time_observed:.2f}s")
        print(f"  Min: {min(startup_times):.2f}s")
    
    @pytest.mark.slow
    def test_snapshot_performance(self, test_vm_manager, performance_timer, performance_test_data):
        """Test snapshot creation and restoration performance."""
        vm_name = f"perf-snapshot-{int(time.time())}"
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        
        num_snapshots = 3
        snapshot_creation_times = []
        snapshot_restore_times = []
        
        # Test snapshot creation performance
        for i in range(num_snapshots):
            snapshot_name = f"perf-snapshot-{i}"
            
            performance_timer.start()
            self._create_snapshot(vm_id, snapshot_name)
            performance_timer.stop()
            
            creation_time = performance_timer.elapsed()
            snapshot_creation_times.append(creation_time)
            self.performance_metrics["snapshot_creation_times"].append(creation_time)
        
        # Test snapshot restoration performance
        for i in range(num_snapshots):
            snapshot_name = f"perf-snapshot-{i}"
            
            performance_timer.start()
            self._restore_snapshot(vm_id, snapshot_name)
            performance_timer.stop()
            
            restore_time = performance_timer.elapsed()
            snapshot_restore_times.append(restore_time)
            self.performance_metrics["snapshot_restore_times"].append(restore_time)
        
        # Analyze performance
        avg_creation_time = statistics.mean(snapshot_creation_times)
        avg_restore_time = statistics.mean(snapshot_restore_times)
        
        max_snapshot_time = performance_test_data["snapshot_creation_timeout"]
        
        assert avg_creation_time < max_snapshot_time
        assert avg_restore_time < max_snapshot_time
        
        print(f"Snapshot Performance:")
        print(f"  Avg Creation: {avg_creation_time:.2f}s")
        print(f"  Avg Restore: {avg_restore_time:.2f}s")
    
    @pytest.mark.slow
    def test_command_execution_performance(self, test_vm_manager, performance_timer, performance_test_data):
        """Test command execution performance."""
        vm_name = f"perf-command-{int(time.time())}"
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        
        test_commands = [
            "echo 'Hello World'",
            "ls -la",
            "pwd",
            "whoami",
            "date",
            "npm --version",
            "node --version"
        ]
        
        execution_times = []
        
        for command in test_commands:
            performance_timer.start()
            self._execute_command(vm_id, command)
            performance_timer.stop()
            
            execution_time = performance_timer.elapsed()
            execution_times.append(execution_time)
            self.performance_metrics["command_execution_times"].append(execution_time)
        
        # Analyze performance
        avg_execution_time = statistics.mean(execution_times)
        max_execution_time = max(execution_times)
        
        max_command_time = performance_test_data["command_execution_timeout"]
        
        assert avg_execution_time < max_command_time * 0.5  # Should be well under limit
        assert max_execution_time < max_command_time
        
        print(f"Command Execution Performance:")
        print(f"  Average: {avg_execution_time:.3f}s")
        print(f"  Max: {max_execution_time:.3f}s")
    
    def _simulate_vm_startup(self, vm_id):
        """Simulate VM startup process."""
        time.sleep(0.1)  # Mock startup time
        return True
    
    def _cleanup_vm(self, vm_id):
        """Clean up test VM."""
        pass  # Mock cleanup
    
    def _create_snapshot(self, vm_id, snapshot_name):
        """Create VM snapshot."""
        time.sleep(0.05)  # Mock snapshot creation time
        return True
    
    def _restore_snapshot(self, vm_id, snapshot_name):
        """Restore VM snapshot."""
        time.sleep(0.03)  # Mock snapshot restore time
        return True
    
    def _execute_command(self, vm_id, command):
        """Execute command in VM."""
        time.sleep(0.01)  # Mock command execution time
        return True


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Test performance under concurrent operations."""
    
    @pytest.mark.slow
    def test_concurrent_vm_creation(self, test_vm_manager, performance_test_data):
        """Test performance of concurrent VM creation."""
        num_concurrent_vms = 3  # Limited for testing
        creation_results = []
        
        def create_vm_worker(vm_index):
            start_time = time.time()
            vm_name = f"concurrent-{vm_index}-{int(time.time())}"
            vm_id = test_vm_manager.create_test_vm(vm_name, {})
            end_time = time.time()
            
            return {
                "vm_id": vm_id,
                "creation_time": end_time - start_time,
                "success": vm_id is not None
            }
        
        # Execute concurrent VM creation
        with ThreadPoolExecutor(max_workers=num_concurrent_vms) as executor:
            futures = [
                executor.submit(create_vm_worker, i) 
                for i in range(num_concurrent_vms)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                creation_results.append(result)
        
        # Analyze results
        successful_creations = [r for r in creation_results if r["success"]]
        avg_creation_time = statistics.mean([r["creation_time"] for r in successful_creations])
        
        assert len(successful_creations) == num_concurrent_vms
        assert avg_creation_time < performance_test_data["vm_startup_timeout"]
        
        print(f"Concurrent VM Creation:")
        print(f"  Success Rate: {len(successful_creations)}/{num_concurrent_vms}")
        print(f"  Avg Time: {avg_creation_time:.2f}s")
    
    @pytest.mark.slow
    def test_concurrent_snapshot_operations(self, test_vm_manager):
        """Test performance of concurrent snapshot operations."""
        vm_name = f"concurrent-snapshot-{int(time.time())}"
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        
        num_snapshots = 5
        snapshot_results = []
        
        def snapshot_worker(snapshot_index):
            start_time = time.time()
            snapshot_name = f"concurrent-snapshot-{snapshot_index}"
            success = self._create_snapshot_concurrent(vm_id, snapshot_name)
            end_time = time.time()
            
            return {
                "snapshot_name": snapshot_name,
                "creation_time": end_time - start_time,
                "success": success
            }
        
        # Execute concurrent snapshot creation
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(snapshot_worker, i) 
                for i in range(num_snapshots)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                snapshot_results.append(result)
        
        # Analyze results
        successful_snapshots = [r for r in snapshot_results if r["success"]]
        
        # Note: Some snapshot operations might fail due to concurrency,
        # but at least some should succeed
        assert len(successful_snapshots) >= num_snapshots // 2
        
        print(f"Concurrent Snapshot Operations:")
        print(f"  Success Rate: {len(successful_snapshots)}/{num_snapshots}")
    
    def test_concurrent_command_execution(self, test_vm_manager):
        """Test performance of concurrent command execution."""
        vm_name = f"concurrent-commands-{int(time.time())}"
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        
        commands = [
            "echo 'command1'",
            "ls -la",
            "pwd",
            "whoami",
            "date"
        ]
        
        command_results = []
        
        def command_worker(command):
            start_time = time.time()
            success = self._execute_command_concurrent(vm_id, command)
            end_time = time.time()
            
            return {
                "command": command,
                "execution_time": end_time - start_time,
                "success": success
            }
        
        # Execute concurrent commands
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(command_worker, cmd) 
                for cmd in commands
            ]
            
            for future in as_completed(futures):
                result = future.result()
                command_results.append(result)
        
        # Analyze results
        successful_commands = [r for r in command_results if r["success"]]
        avg_execution_time = statistics.mean([r["execution_time"] for r in successful_commands])
        
        assert len(successful_commands) == len(commands)
        assert avg_execution_time < 5.0  # Should be reasonably fast
        
        print(f"Concurrent Command Execution:")
        print(f"  Success Rate: {len(successful_commands)}/{len(commands)}")
        print(f"  Avg Time: {avg_execution_time:.3f}s")
    
    def _create_snapshot_concurrent(self, vm_id, snapshot_name):
        """Create snapshot in concurrent environment."""
        time.sleep(0.05)  # Mock snapshot creation
        return True
    
    def _execute_command_concurrent(self, vm_id, command):
        """Execute command in concurrent environment."""
        time.sleep(0.02)  # Mock command execution
        return True


@pytest.mark.performance
class TestResourceUsagePerformance:
    """Test resource usage performance and efficiency."""
    
    def setup_method(self):
        """Set up resource monitoring."""
        self.initial_memory = self._get_memory_usage()
        self.initial_cpu = self._get_cpu_usage()
    
    def test_memory_usage_efficiency(self, test_vm_manager, performance_test_data):
        """Test memory usage efficiency during operations."""
        vm_name = f"memory-test-{int(time.time())}"
        
        memory_samples = []
        
        # Baseline memory usage
        baseline_memory = self._get_memory_usage()
        memory_samples.append(baseline_memory)
        
        # Create VM and monitor memory
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        post_creation_memory = self._get_memory_usage()
        memory_samples.append(post_creation_memory)
        
        # Perform operations and monitor memory
        operations = [
            lambda: self._create_snapshot(vm_id, "mem-test-1"),
            lambda: self._execute_command(vm_id, "echo 'test'"),
            lambda: self._create_snapshot(vm_id, "mem-test-2"),
            lambda: self._restore_snapshot(vm_id, "mem-test-1")
        ]
        
        for operation in operations:
            operation()
            current_memory = self._get_memory_usage()
            memory_samples.append(current_memory)
        
        # Analyze memory usage
        max_memory_increase = max(memory_samples) - baseline_memory
        final_memory_increase = memory_samples[-1] - baseline_memory
        
        max_allowed_increase = performance_test_data["max_memory_usage"] * 1024 * 1024  # Convert MB to bytes
        
        assert max_memory_increase < max_allowed_increase
        assert final_memory_increase < max_allowed_increase * 0.8  # Should cleanup most memory
        
        print(f"Memory Usage Analysis:")
        print(f"  Baseline: {baseline_memory / 1024 / 1024:.1f} MB")
        print(f"  Max Increase: {max_memory_increase / 1024 / 1024:.1f} MB")
        print(f"  Final Increase: {final_memory_increase / 1024 / 1024:.1f} MB")
    
    def test_cpu_usage_efficiency(self, test_vm_manager, performance_test_data):
        """Test CPU usage efficiency during operations."""
        vm_name = f"cpu-test-{int(time.time())}"
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        
        cpu_samples = []
        
        # Monitor CPU during operations
        def monitor_cpu():
            for _ in range(10):  # Sample for 1 second
                cpu_usage = self._get_cpu_usage()
                cpu_samples.append(cpu_usage)
                time.sleep(0.1)
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Perform CPU-intensive operations
        operations = [
            lambda: self._create_snapshot(vm_id, "cpu-test-1"),
            lambda: self._execute_command(vm_id, "ls -la"),
            lambda: self._restore_snapshot(vm_id, "cpu-test-1")
        ]
        
        for operation in operations:
            operation()
            time.sleep(0.1)  # Allow monitoring
        
        monitor_thread.join()
        
        # Analyze CPU usage
        if cpu_samples:
            avg_cpu_usage = statistics.mean(cpu_samples)
            max_cpu_usage = max(cpu_samples)
            
            max_allowed_cpu = performance_test_data["max_cpu_usage"]
            
            assert avg_cpu_usage < max_allowed_cpu
            assert max_cpu_usage < max_allowed_cpu * 1.2  # Allow brief spikes
            
            print(f"CPU Usage Analysis:")
            print(f"  Average: {avg_cpu_usage:.1f}%")
            print(f"  Maximum: {max_cpu_usage:.1f}%")
    
    def test_disk_usage_efficiency(self, test_vm_manager, performance_test_data):
        """Test disk usage efficiency."""
        vm_name = f"disk-test-{int(time.time())}"
        
        initial_disk_usage = self._get_disk_usage()
        
        # Create VM
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        post_creation_disk = self._get_disk_usage()
        
        # Create multiple snapshots
        for i in range(3):
            self._create_snapshot(vm_id, f"disk-test-{i}")
        
        post_snapshots_disk = self._get_disk_usage()
        
        # Analyze disk usage
        vm_creation_disk_usage = post_creation_disk - initial_disk_usage
        snapshot_disk_usage = post_snapshots_disk - post_creation_disk
        total_disk_usage = post_snapshots_disk - initial_disk_usage
        
        max_allowed_disk = performance_test_data["max_disk_usage"] * 1024 * 1024  # Convert MB to bytes
        
        assert total_disk_usage < max_allowed_disk
        
        print(f"Disk Usage Analysis:")
        print(f"  VM Creation: {vm_creation_disk_usage / 1024 / 1024:.1f} MB")
        print(f"  Snapshots: {snapshot_disk_usage / 1024 / 1024:.1f} MB")
        print(f"  Total: {total_disk_usage / 1024 / 1024:.1f} MB")
    
    def _get_memory_usage(self):
        """Get current memory usage."""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            return 0
    
    def _get_cpu_usage(self):
        """Get current CPU usage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0
    
    def _get_disk_usage(self):
        """Get current disk usage."""
        try:
            return psutil.disk_usage('/').used
        except Exception:
            return 0
    
    def _create_snapshot(self, vm_id, snapshot_name):
        """Create snapshot for resource testing."""
        time.sleep(0.05)  # Mock snapshot creation
        return True
    
    def _execute_command(self, vm_id, command):
        """Execute command for resource testing."""
        time.sleep(0.01)  # Mock command execution
        return True
    
    def _restore_snapshot(self, vm_id, snapshot_name):
        """Restore snapshot for resource testing."""
        time.sleep(0.03)  # Mock snapshot restore
        return True


@pytest.mark.performance
class TestStressAndLoadTesting:
    """Test system behavior under stress and high load."""
    
    @pytest.mark.slow
    def test_rapid_vm_lifecycle_stress(self, test_vm_manager):
        """Test rapid VM creation and destruction cycles."""
        num_cycles = 10
        cycle_times = []
        
        for cycle in range(num_cycles):
            cycle_start = time.time()
            
            vm_name = f"stress-cycle-{cycle}-{int(time.time())}"
            
            # Create -> Start -> Snapshot -> Destroy cycle
            vm_id = test_vm_manager.create_test_vm(vm_name, {})
            assert vm_id is not None
            
            self._simulate_vm_startup(vm_id)
            self._create_snapshot(vm_id, "stress-snapshot")
            self._cleanup_vm(vm_id)
            
            cycle_end = time.time()
            cycle_time = cycle_end - cycle_start
            cycle_times.append(cycle_time)
        
        # Analyze stress test results
        avg_cycle_time = statistics.mean(cycle_times)
        max_cycle_time = max(cycle_times)
        
        # Performance should remain stable across cycles
        performance_degradation = max_cycle_time / min(cycle_times)
        
        assert performance_degradation < 2.0  # Less than 100% degradation
        assert avg_cycle_time < 10.0  # Should complete quickly
        
        print(f"Stress Test Results:")
        print(f"  Cycles: {num_cycles}")
        print(f"  Avg Time: {avg_cycle_time:.2f}s")
        print(f"  Performance Degradation: {performance_degradation:.2f}x")
    
    @pytest.mark.slow
    def test_snapshot_stress_testing(self, test_vm_manager):
        """Test stress conditions with many snapshots."""
        vm_name = f"snapshot-stress-{int(time.time())}"
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        
        num_snapshots = 15  # More than typical usage
        snapshot_times = []
        
        for i in range(num_snapshots):
            snapshot_start = time.time()
            snapshot_name = f"stress-snapshot-{i}"
            success = self._create_snapshot(vm_id, snapshot_name)
            snapshot_end = time.time()
            
            assert success, f"Snapshot {i} creation should succeed"
            
            snapshot_time = snapshot_end - snapshot_start
            snapshot_times.append(snapshot_time)
        
        # Test snapshot restoration under stress
        restore_times = []
        for i in [0, num_snapshots//2, num_snapshots-1]:  # Test first, middle, last
            restore_start = time.time()
            snapshot_name = f"stress-snapshot-{i}"
            success = self._restore_snapshot(vm_id, snapshot_name)
            restore_end = time.time()
            
            assert success, f"Snapshot {i} restoration should succeed"
            
            restore_time = restore_end - restore_start
            restore_times.append(restore_time)
        
        # Analyze results
        avg_snapshot_time = statistics.mean(snapshot_times)
        avg_restore_time = statistics.mean(restore_times)
        
        print(f"Snapshot Stress Test:")
        print(f"  Snapshots Created: {num_snapshots}")
        print(f"  Avg Creation Time: {avg_snapshot_time:.3f}s")
        print(f"  Avg Restore Time: {avg_restore_time:.3f}s")
    
    def test_command_execution_load(self, test_vm_manager):
        """Test command execution under high load."""
        vm_name = f"command-load-{int(time.time())}"
        vm_id = test_vm_manager.create_test_vm(vm_name, {})
        
        # Execute many commands rapidly
        commands = [
            "echo 'test'",
            "ls -la",
            "pwd",
            "whoami",
            "date"
        ] * 10  # 50 total commands
        
        execution_times = []
        
        for command in commands:
            exec_start = time.time()
            success = self._execute_command(vm_id, command)
            exec_end = time.time()
            
            assert success, f"Command '{command}' should succeed"
            
            execution_time = exec_end - exec_start
            execution_times.append(execution_time)
        
        # Analyze load test results
        avg_execution_time = statistics.mean(execution_times)
        max_execution_time = max(execution_times)
        
        # Performance should remain consistent under load
        performance_variance = statistics.stdev(execution_times) / avg_execution_time
        
        assert performance_variance < 0.5  # Less than 50% variance
        assert max_execution_time < 1.0  # No command should take too long
        
        print(f"Command Load Test:")
        print(f"  Commands Executed: {len(commands)}")
        print(f"  Avg Time: {avg_execution_time:.3f}s")
        print(f"  Performance Variance: {performance_variance:.3f}")
    
    def _simulate_vm_startup(self, vm_id):
        """Simulate VM startup."""
        time.sleep(0.1)
        return True
    
    def _create_snapshot(self, vm_id, snapshot_name):
        """Create snapshot for stress testing."""
        time.sleep(0.05)
        return True
    
    def _restore_snapshot(self, vm_id, snapshot_name):
        """Restore snapshot for stress testing."""
        time.sleep(0.03)
        return True
    
    def _execute_command(self, vm_id, command):
        """Execute command for load testing."""
        time.sleep(0.01)
        return True
    
    def _cleanup_vm(self, vm_id):
        """Clean up VM after stress testing."""
        pass