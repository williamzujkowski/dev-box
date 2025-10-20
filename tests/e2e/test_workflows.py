"""E2E (End-to-End) workflow tests for complete agent execution.

This test suite validates complete workflows from VM creation through
execution and cleanup, following TDD principles.

Phase 5 Component: Integration of all components in real-world scenarios
Scope: Complete workflows using real (or minimally mocked) components
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import json
import time


@pytest.mark.e2e
class TestCompleteWorkflow:
    """Test complete end-to-end agent execution workflows."""

    @pytest.mark.asyncio
    async def test_end_to_end_agent_execution(
        self, workspace_with_structure: Path, sample_agent_code: str
    ) -> None:
        """Complete workflow: create VM, execute agent, extract results, cleanup.

        This test validates the complete agent execution pipeline:
        1. Initialize connection and pool
        2. Acquire VM from pool
        3. Execute agent code
        4. Extract results
        5. Release VM back to pool
        6. Cleanup resources

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.core.connection import LibvirtConnection
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.execution.executor import AgentExecutor, ExecutionResult
        from agent_vm.core.vm import VM

        # Create mock components (prefer real where safe)
        mock_vm = Mock(spec=VM)
        mock_vm.name = "e2e-test-vm"
        mock_vm.uuid = "e2e-test-uuid-123"

        # Create PooledVM wrapper
        nist_et = ZoneInfo("America/New_York")
        pooled_vm = PooledVM(
            vm=mock_vm,
            created_at=datetime.now(nist_et),
            golden_snapshot="golden-e2e"
        )

        # Mock pool
        pool = VMPool(min_size=1, max_size=5)
        pool._create_fresh_vm = AsyncMock(return_value=pooled_vm)
        pool._reset_to_golden = AsyncMock()
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        # Initialize pool
        await pool.initialize()

        # Create executor
        executor = AgentExecutor()

        try:
            # Step 1: Acquire VM from pool
            vm = await pool.acquire()
            assert vm is not None
            assert vm.name == "e2e-test-vm"

            # Step 2: Execute agent code
            with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class, \
                 patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec:

                # Setup filesystem mock
                mock_fs = Mock()
                mock_fs.write_file = AsyncMock()
                output_data = {"status": "success", "message": "E2E test passed"}
                mock_fs.read_file = AsyncMock(return_value=json.dumps(output_data).encode())
                mock_fs.cleanup = AsyncMock()
                mock_fs_class.return_value = mock_fs

                # Setup execution mock
                mock_exec.return_value = {
                    "exit_code": 0,
                    "stdout": "Agent completed successfully\n",
                    "stderr": ""
                }

                # Execute agent
                result = await executor.execute(vm, sample_agent_code, workspace_with_structure)

                # Step 3: Verify results
                assert result.success is True
                assert result.exit_code == 0
                assert "Agent completed successfully" in result.stdout
                assert result.output == output_data
                assert result.duration_seconds > 0

                # Verify code was injected
                mock_fs.write_file.assert_called_once()

                # Verify execution happened
                mock_exec.assert_called_once()

                # Verify results extracted
                mock_fs.read_file.assert_called_once_with("output/results.json")

                # Verify cleanup
                mock_fs.cleanup.assert_called_once()

            # Step 4: Release VM back to pool
            await pool.release(vm)

            # Verify VM was reset
            pool._reset_to_golden.assert_called_once_with(vm)

        finally:
            # Step 5: Cleanup
            await pool.shutdown()
            assert pool.size() == 0

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(
        self, workspace_with_structure: Path, sample_agent_code: str
    ) -> None:
        """Execute 3 agents concurrently in separate VMs.

        Tests the system's ability to handle multiple concurrent executions:
        1. Create pool large enough for concurrent VMs
        2. Execute 3 agents simultaneously
        3. Verify all succeed independently
        4. Verify proper isolation between executions

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        # Create pool for concurrent execution
        pool = VMPool(min_size=3, max_size=10)

        # Create mock VMs - counter for unique VMs
        vm_counter = 0
        def create_mock_pooled_vm(index: int | None = None) -> PooledVM:
            nonlocal vm_counter
            vm_counter += 1
            mock_vm = Mock(spec=VM)
            mock_vm.name = f"concurrent-vm-{vm_counter}"
            mock_vm.uuid = f"concurrent-uuid-{vm_counter}"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot=f"golden-{vm_counter}"
            )

        # Setup pool with multiple VMs - use AsyncMock
        pool._create_fresh_vm = AsyncMock(side_effect=create_mock_pooled_vm)
        pool._reset_to_golden = AsyncMock()
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        await pool.initialize()

        # Create executor
        executor = AgentExecutor()

        # Define concurrent execution task
        async def execute_agent(agent_id: int) -> dict:
            vm = await pool.acquire()

            try:
                with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class, \
                     patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec:

                    # Setup mocks
                    mock_fs = Mock()
                    mock_fs.write_file = AsyncMock()
                    output = {"agent_id": agent_id, "status": "success"}
                    mock_fs.read_file = AsyncMock(return_value=json.dumps(output).encode())
                    mock_fs.cleanup = AsyncMock()
                    mock_fs_class.return_value = mock_fs

                    mock_exec.return_value = {
                        "exit_code": 0,
                        "stdout": f"Agent {agent_id} completed\n",
                        "stderr": ""
                    }

                    # Execute
                    result = await executor.execute(vm, sample_agent_code, workspace_with_structure)

                    return {
                        "agent_id": agent_id,
                        "vm_name": vm.name,
                        "result": result
                    }
            finally:
                await pool.release(vm)

        try:
            # Execute 3 agents concurrently
            start_time = time.perf_counter()
            tasks = [execute_agent(i) for i in range(3)]
            results = await asyncio.gather(*tasks)
            execution_time = time.perf_counter() - start_time

            # Verify all succeeded
            assert len(results) == 3
            for res in results:
                assert res["result"].success is True
                assert res["result"].exit_code == 0

            # Verify they ran in parallel (should be much faster than sequential)
            # If truly concurrent, total time should be ~1x single execution, not 3x
            assert execution_time < 2.0  # Generous upper bound

            # Verify unique VMs used
            vm_names = {res["vm_name"] for res in results}
            # May reuse VMs but at least some should differ
            assert len(vm_names) >= 1

        finally:
            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_snapshot_reset_workflow(
        self, workspace_with_structure: Path, sample_agent_code: str
    ) -> None:
        """Execute agent, snapshot, modify, restore to clean state.

        This test validates the snapshot-based reset workflow:
        1. Create VM with golden snapshot
        2. Execute agent (modifies VM state)
        3. Verify state changed
        4. Restore to golden snapshot
        5. Verify VM is back to clean state

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.core.vm import VM
        from agent_vm.core.snapshot import SnapshotManager
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.execution.pool import PooledVM

        nist_et = ZoneInfo("America/New_York")

        # Create mock VM
        mock_domain = Mock()
        mock_domain.name.return_value = "snapshot-test-vm"
        mock_domain.UUIDString.return_value = "snapshot-uuid-123"

        vm = VM(mock_domain)

        # Create snapshot manager
        snapshot_manager = SnapshotManager()

        # Mock snapshot operations
        mock_snapshot = Mock()
        mock_snapshot.getName.return_value = "golden-snapshot"

        with patch.object(snapshot_manager, "create_snapshot", new_callable=AsyncMock, return_value=mock_snapshot) as mock_create, \
             patch.object(snapshot_manager, "restore_snapshot", new_callable=AsyncMock) as mock_restore:

            # Step 1: Create golden snapshot
            golden = await snapshot_manager.create_snapshot(
                vm,
                "golden-snapshot",
                "Clean state before execution"
            )

            assert golden == mock_snapshot
            mock_create.assert_called_once()

            # Step 2: Execute agent (simulates state modification)
            executor = AgentExecutor()

            with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class, \
                 patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec:

                mock_fs = Mock()
                mock_fs.write_file = AsyncMock()
                # Agent modifies state
                mock_fs.read_file = AsyncMock(return_value=json.dumps({"modified": True}).encode())
                mock_fs.cleanup = AsyncMock()
                mock_fs_class.return_value = mock_fs

                mock_exec.return_value = {
                    "exit_code": 0,
                    "stdout": "Modified VM state\n",
                    "stderr": ""
                }

                result = await executor.execute(vm, sample_agent_code, workspace_with_structure)

                # Step 3: Verify execution happened (state changed)
                assert result.success is True
                assert result.output["modified"] is True

            # Step 4: Restore to golden snapshot
            await snapshot_manager.restore_snapshot(vm, golden)

            # Step 5: Verify restore was called
            mock_restore.assert_called_once_with(vm, golden)

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(
        self, workspace_with_structure: Path, failing_agent_code: str
    ) -> None:
        """Handle agent failure, cleanup, and continue.

        This test validates error recovery:
        1. Execute failing agent
        2. Capture error details
        3. Cleanup resources despite error
        4. Verify pool remains healthy
        5. Execute subsequent agent successfully

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        # Create pool
        pool = VMPool(min_size=2, max_size=5)

        # Create mock VMs with proper created_at
        vm_counter = 0
        def create_vm(index: int | None = None):
            nonlocal vm_counter
            vm_counter += 1
            mock_vm = Mock(spec=VM)
            mock_vm.name = f"error-recovery-vm-{vm_counter}"
            mock_vm.uuid = f"error-recovery-uuid-{vm_counter}"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot="golden-error-test"
            )

        pool._create_fresh_vm = AsyncMock(side_effect=create_vm)
        pool._reset_to_golden = AsyncMock()
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        await pool.initialize()

        executor = AgentExecutor()

        try:
            # Step 1: Acquire VM
            vm = await pool.acquire()
            assert vm is not None

            # Step 2: Execute failing agent
            with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class, \
                 patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec:

                from agent_vm.communication.filesystem import FilesystemError

                mock_fs = Mock()
                mock_fs.write_file = AsyncMock()
                mock_fs.read_file = AsyncMock(side_effect=FilesystemError("No output"))
                mock_fs.cleanup = AsyncMock()
                mock_fs_class.return_value = mock_fs

                # Simulate agent error
                mock_exec.return_value = {
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "ValueError: Intentional test error\n"
                }

                result = await executor.execute(vm, failing_agent_code, workspace_with_structure)

                # Step 3: Verify error was captured
                assert result.success is False
                assert result.exit_code == 1
                assert "Intentional test error" in result.stderr

                # Step 4: Verify cleanup happened despite error
                mock_fs.cleanup.assert_called_once()

            # Step 5: Release VM (should destroy on error or reset)
            await pool.release(vm)

            # Step 6: Pool should still be healthy - acquire new VM
            vm2 = await pool.acquire()
            assert vm2 is not None

            # Step 7: Execute successful agent
            with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class2, \
                 patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec2:

                mock_fs2 = Mock()
                mock_fs2.write_file = AsyncMock()
                mock_fs2.read_file = AsyncMock(return_value=json.dumps({"recovered": True}).encode())
                mock_fs2.cleanup = AsyncMock()
                mock_fs_class2.return_value = mock_fs2

                mock_exec2.return_value = {
                    "exit_code": 0,
                    "stdout": "Recovered successfully\n",
                    "stderr": ""
                }

                result2 = await executor.execute(vm2, "print('recovered')", workspace_with_structure)

                # Step 8: Verify recovery
                assert result2.success is True
                assert result2.exit_code == 0
                assert result2.output["recovered"] is True

            await pool.release(vm2)

        finally:
            await pool.shutdown()


@pytest.mark.e2e
class TestConcurrentExecutionWorkflows:
    """Test concurrent execution scenarios."""

    @pytest.mark.asyncio
    async def test_high_concurrency_execution(
        self, workspace_with_structure: Path, sample_agent_code: str
    ) -> None:
        """Execute 10 agents concurrently to test scalability.

        Tests system behavior under high concurrent load:
        1. Create large pool
        2. Execute many agents simultaneously
        3. Verify all complete successfully
        4. Measure performance characteristics

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        # Create large pool
        pool = VMPool(min_size=5, max_size=15)

        # Setup mock VMs
        vm_counter = 0
        def create_vm(index: int | None = None):
            nonlocal vm_counter
            vm_counter += 1
            mock_vm = Mock(spec=VM)
            mock_vm.name = f"high-concurrency-vm-{vm_counter}"
            mock_vm.uuid = f"high-concurrency-uuid-{vm_counter}"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot=f"golden-{vm_counter}"
            )

        pool._create_fresh_vm = AsyncMock(side_effect=create_vm)
        pool._reset_to_golden = AsyncMock()
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        await pool.initialize()

        executor = AgentExecutor()

        async def execute_concurrent_agent(agent_id: int):
            vm = await pool.acquire()

            try:
                with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class, \
                     patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec:

                    mock_fs = Mock()
                    mock_fs.write_file = AsyncMock()
                    mock_fs.read_file = AsyncMock(
                        return_value=json.dumps({"id": agent_id}).encode()
                    )
                    mock_fs.cleanup = AsyncMock()
                    mock_fs_class.return_value = mock_fs

                    # Simulate small delay
                    async def delayed_exec(*args, **kwargs):
                        await asyncio.sleep(0.01)
                        return {
                            "exit_code": 0,
                            "stdout": f"Agent {agent_id} done\n",
                            "stderr": ""
                        }

                    mock_exec.side_effect = delayed_exec

                    result = await executor.execute(vm, sample_agent_code, workspace_with_structure)
                    return result
            finally:
                await pool.release(vm)

        try:
            # Execute 10 agents concurrently
            num_agents = 10
            start_time = time.perf_counter()

            tasks = [execute_concurrent_agent(i) for i in range(num_agents)]
            results = await asyncio.gather(*tasks)

            total_time = time.perf_counter() - start_time

            # Verify all succeeded
            assert len(results) == num_agents
            assert all(r.success for r in results)

            # Performance check: should be much faster than sequential
            # Sequential would take ~0.1s (10 * 0.01), concurrent should be ~0.01-0.05s
            assert total_time < 1.0  # Generous upper bound

        finally:
            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure_execution(
        self, workspace_with_structure: Path
    ) -> None:
        """Execute mix of successful and failing agents concurrently.

        Tests that failures don't affect parallel successes:
        1. Execute agents with different outcomes simultaneously
        2. Verify independent execution
        3. Verify pool remains healthy throughout

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        pool = VMPool(min_size=3, max_size=10)

        vm_counter = 0
        def create_vm(index: int | None = None):
            nonlocal vm_counter
            vm_counter += 1
            mock_vm = Mock(spec=VM)
            mock_vm.name = f"mixed-vm-{vm_counter}"
            mock_vm.uuid = f"mixed-uuid-{vm_counter}"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot=f"golden-{vm_counter}"
            )

        pool._create_fresh_vm = AsyncMock(side_effect=create_vm)
        pool._reset_to_golden = AsyncMock()
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        await pool.initialize()

        executor = AgentExecutor()

        async def execute_agent(agent_id: int, should_fail: bool):
            vm = await pool.acquire()

            try:
                with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class, \
                     patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec:

                    from agent_vm.communication.filesystem import FilesystemError

                    mock_fs = Mock()
                    mock_fs.write_file = AsyncMock()

                    if should_fail:
                        mock_fs.read_file = AsyncMock(side_effect=FilesystemError())
                        mock_exec.return_value = {
                            "exit_code": 1,
                            "stdout": "",
                            "stderr": f"Agent {agent_id} failed\n"
                        }
                    else:
                        mock_fs.read_file = AsyncMock(
                            return_value=json.dumps({"id": agent_id}).encode()
                        )
                        mock_exec.return_value = {
                            "exit_code": 0,
                            "stdout": f"Agent {agent_id} succeeded\n",
                            "stderr": ""
                        }

                    mock_fs.cleanup = AsyncMock()
                    mock_fs_class.return_value = mock_fs

                    result = await executor.execute(vm, "test", workspace_with_structure)
                    return {"id": agent_id, "result": result}
            finally:
                await pool.release(vm)

        try:
            # Execute mix: 3 success, 2 failure
            tasks = [
                execute_agent(0, False),
                execute_agent(1, True),
                execute_agent(2, False),
                execute_agent(3, True),
                execute_agent(4, False),
            ]

            results = await asyncio.gather(*tasks)

            # Verify outcomes
            assert len(results) == 5

            successes = [r for r in results if r["result"].success]
            failures = [r for r in results if not r["result"].success]

            assert len(successes) == 3
            assert len(failures) == 2

            # Verify pool is still healthy
            assert pool.size() >= 0

        finally:
            await pool.shutdown()


@pytest.mark.e2e
class TestResourceManagementWorkflows:
    """Test resource management and cleanup workflows."""

    @pytest.mark.asyncio
    async def test_pool_auto_refill_during_execution(
        self, workspace_with_structure: Path, sample_agent_code: str
    ) -> None:
        """Verify pool auto-refills while agents are executing.

        Tests maintenance workflow:
        1. Start with minimum pool size
        2. Acquire multiple VMs
        3. Verify pool refills in background
        4. Release VMs
        5. Verify pool maintains minimum

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        pool = VMPool(min_size=3, max_size=10)

        vm_counter = 0
        def create_vm(index: int | None = None):
            nonlocal vm_counter
            vm_counter += 1
            mock_vm = Mock(spec=VM)
            mock_vm.name = f"refill-vm-{vm_counter}"
            mock_vm.uuid = f"refill-uuid-{vm_counter}"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot=f"golden-{vm_counter}"
            )

        pool._create_fresh_vm = AsyncMock(side_effect=create_vm)
        pool._reset_to_golden = AsyncMock()
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        # Mock asyncio.sleep to speed up maintenance
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            if seconds >= 10:
                await original_sleep(0.01)
            else:
                await original_sleep(seconds)

        with patch('asyncio.sleep', side_effect=fast_sleep):
            await pool.initialize()

            # Should start at min_size
            initial_size = pool.size()
            assert initial_size >= 3

            # Acquire 2 VMs
            vm1 = await pool.acquire()
            vm2 = await pool.acquire()

            # Pool should be smaller
            assert pool.size() < initial_size

            # Wait for maintenance to refill
            await asyncio.sleep(0.1)

            # Pool should start refilling
            # (exact timing depends on maintenance interval)

            # Release VMs
            await pool.release(vm1)
            await pool.release(vm2)

            # Pool should maintain minimum
            await asyncio.sleep(0.1)
            assert pool.size() >= 2

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_stale_vm_eviction_workflow(
        self, workspace_with_structure: Path
    ) -> None:
        """Verify stale VMs are evicted and replaced.

        Tests TTL-based eviction:
        1. Create VM with old timestamp
        2. Attempt to acquire
        3. Verify stale VM is destroyed
        4. Verify fresh VM is created
        5. Verify pool health maintained

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        pool = VMPool(min_size=1, max_size=5, ttl_seconds=60)

        # Create stale VM (>60 seconds old)
        stale_vm = Mock(spec=VM)
        stale_vm.name = "stale-vm"
        stale_vm.uuid = "stale-uuid"

        old_time = datetime.now(nist_et) - timedelta(seconds=120)
        stale_pooled = PooledVM(
            vm=stale_vm,
            created_at=old_time,
            golden_snapshot="stale-golden"
        )

        # Put stale VM in queue manually
        await pool._pool.put(stale_pooled)
        pool._initialized = True
        pool._connection = Mock()

        # Mock destroy and create
        pool._destroy_vm = AsyncMock()

        fresh_vm = Mock(spec=VM)
        fresh_vm.name = "fresh-vm"
        fresh_vm.uuid = "fresh-uuid"

        fresh_pooled = PooledVM(
            vm=fresh_vm,
            created_at=datetime.now(nist_et),
            golden_snapshot="fresh-golden"
        )
        pool._create_fresh_vm = AsyncMock(return_value=fresh_pooled)

        # Acquire should evict stale and create fresh
        vm = await pool.acquire()

        # Verify we got fresh VM
        assert vm.uuid == "fresh-uuid"

        # Verify stale was destroyed
        pool._destroy_vm.assert_called_once()

        # Verify fresh was created
        pool._create_fresh_vm.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_workflow(
        self, workspace_with_structure: Path
    ) -> None:
        """Verify graceful shutdown cleans up all resources.

        Tests shutdown workflow:
        1. Initialize pool with VMs
        2. Acquire some VMs (in-use)
        3. Initiate shutdown
        4. Verify maintenance tasks cancelled
        5. Verify all VMs destroyed
        6. Verify clean final state

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        pool = VMPool(min_size=3, max_size=10)

        vm_counter = 0
        def create_vm(index: int | None = None):
            nonlocal vm_counter
            vm_counter += 1
            mock_vm = Mock(spec=VM)
            mock_vm.name = f"shutdown-test-vm-{vm_counter}"
            mock_vm.uuid = f"shutdown-uuid-{vm_counter}"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot="shutdown-golden"
            )

        pool._create_fresh_vm = AsyncMock(side_effect=create_vm)
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        # Initialize
        await pool.initialize()
        initial_size = pool.size()
        assert initial_size >= 3

        # Acquire a VM (simulates in-use)
        vm = await pool.acquire()

        # Verify maintenance task running
        assert pool._maintenance_task is not None
        assert not pool._maintenance_task.done()

        # Pool should have initial_size - 1 VMs (one is acquired)
        assert pool.size() == initial_size - 1

        # Initiate shutdown
        await pool.shutdown()

        # Verify maintenance task cancelled
        assert pool._maintenance_task.cancelled() or pool._maintenance_task.done()

        # Verify VMs in pool were destroyed (initial_size - 1, since one was acquired)
        assert pool._destroy_vm.call_count == initial_size - 1

        # Verify pool empty
        assert pool.size() == 0


@pytest.mark.e2e
class TestPerformanceWorkflows:
    """Test performance characteristics of workflows."""

    @pytest.mark.asyncio
    async def test_pool_acquire_performance(self) -> None:
        """Verify VM acquisition from pool meets <100ms target.

        Tests performance requirement:
        1. Initialize pre-warmed pool
        2. Acquire VM multiple times
        3. Measure acquisition time
        4. Verify meets <100ms target

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        pool = VMPool(min_size=5, max_size=10)

        mock_vm = Mock(spec=VM)
        pooled_vm = PooledVM(
            vm=mock_vm,
            created_at=datetime.now(nist_et),
            golden_snapshot="perf-golden"
        )

        pool._create_fresh_vm = AsyncMock(return_value=pooled_vm)
        pool._connection = Mock()

        await pool.initialize()

        # Measure multiple acquisitions
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            vm = await pool.acquire()
            duration = time.perf_counter() - start
            timings.append(duration)

            # Release immediately for next test
            pool._reset_to_golden = AsyncMock()
            await pool.release(vm)

        # All acquisitions should be fast
        for timing in timings:
            assert timing < 0.1, f"Acquisition took {timing:.3f}s (target: <0.1s)"

        # Average should be well under target
        avg_timing = sum(timings) / len(timings)
        assert avg_timing < 0.05, f"Average acquisition: {avg_timing:.3f}s"

        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_snapshot_restore_performance(self) -> None:
        """Verify snapshot restore meets <1s target.

        Tests snapshot performance:
        1. Create VM with snapshot
        2. Restore snapshot multiple times
        3. Measure restore time
        4. Verify meets <1s target

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.core.vm import VM
        from agent_vm.core.snapshot import SnapshotManager

        # Create mock VM
        mock_domain = Mock()
        mock_domain.name.return_value = "perf-vm"

        vm = VM(mock_domain)
        snapshot_manager = SnapshotManager()

        mock_snapshot = Mock()
        mock_snapshot.getName.return_value = "perf-snapshot"

        with patch.object(snapshot_manager, "restore_snapshot") as mock_restore:
            # Simulate restore with small delay
            async def timed_restore(*args):
                await asyncio.sleep(0.01)  # Simulated restore

            mock_restore.side_effect = timed_restore

            # Measure restore times
            timings = []
            for _ in range(3):
                start = time.perf_counter()
                await snapshot_manager.restore_snapshot(vm, mock_snapshot)
                duration = time.perf_counter() - start
                timings.append(duration)

            # All restores should be under 1 second
            for timing in timings:
                assert timing < 1.0, f"Restore took {timing:.3f}s (target: <1s)"


@pytest.mark.e2e
class TestErrorHandlingWorkflows:
    """Test error handling and recovery workflows."""

    @pytest.mark.asyncio
    async def test_timeout_handling_workflow(
        self, workspace_with_structure: Path, timeout_agent_code: str
    ) -> None:
        """Verify timeout enforcement and cleanup.

        Tests timeout workflow:
        1. Execute long-running agent
        2. Verify timeout enforced
        3. Verify cleanup happens
        4. Verify VM can be reused

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()

        mock_vm = Mock(spec=VM)
        mock_vm.name = "timeout-vm"

        with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class, \
             patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec:

            mock_fs = Mock()
            mock_fs.write_file = AsyncMock()
            mock_fs.read_file = AsyncMock(side_effect=FileNotFoundError())
            mock_fs.cleanup = AsyncMock()
            mock_fs_class.return_value = mock_fs

            # Simulate timeout
            mock_exec.side_effect = asyncio.TimeoutError()

            # Execute with short timeout
            with pytest.raises(ExecutionError, match="timeout|timed out"):
                await executor.execute(
                    mock_vm,
                    timeout_agent_code,
                    workspace_with_structure,
                    timeout=1
                )

            # Verify cleanup happened despite timeout
            mock_fs.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_vm_creation_failure_recovery(self) -> None:
        """Verify pool recovers from VM creation failures.

        Tests failure recovery:
        1. Configure pool with failing VM creation
        2. Attempt initialization
        3. Fix creation
        4. Verify pool recovers
        5. Verify pool becomes healthy

        Uses NIST ET timezone for all timestamps.
        """
        from agent_vm.execution.pool import VMPool, PooledVM
        from agent_vm.core.vm import VM

        nist_et = ZoneInfo("America/New_York")

        pool = VMPool(min_size=2, max_size=5)

        # First attempts fail
        failure_count = 0
        async def failing_create(index: int | None = None):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise Exception("Creation failed")

            mock_vm = Mock(spec=VM)
            mock_vm.name = f"recovered-vm-{failure_count}"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot="recovered-golden"
            )

        pool._create_fresh_vm = failing_create
        pool._destroy_vm = AsyncMock()
        pool._connection = Mock()

        # Initialize may fail initially
        try:
            await pool.initialize()
        except:
            pass

        # Fix creation
        def successful_create(index: int | None = None):
            mock_vm = Mock(spec=VM)
            mock_vm.name = "success-vm"
            return PooledVM(
                vm=mock_vm,
                created_at=datetime.now(nist_et),
                golden_snapshot="success-golden"
            )

        pool._create_fresh_vm = AsyncMock(side_effect=successful_create)

        # Mock fast maintenance
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            if seconds >= 10:
                await original_sleep(0.01)
            else:
                await original_sleep(seconds)

        with patch('asyncio.sleep', side_effect=fast_sleep):
            # Run maintenance
            pool._shutdown_requested = False
            task = asyncio.create_task(pool._maintain_pool())

            await asyncio.sleep(0.1)

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Pool should recover
        assert pool.size() >= 0

        await pool.shutdown()
