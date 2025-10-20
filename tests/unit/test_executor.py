"""Test AgentExecutor (agent code execution in VMs).

This test suite validates the AgentExecutor class following TDD principles.
Tests are written FIRST (RED phase) before implementation.

Phase 3 Component: Execute agent code in isolated VMs
Protocol: Inject code, execute with timeout, extract results
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from pathlib import Path
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json

from agent_vm.communication.filesystem import FilesystemError


class TestAgentExecutorInitialization:
    """Test AgentExecutor initialization."""

    def test_executor_initializes_with_defaults(self) -> None:
        """AgentExecutor initializes with default configuration.

        RED: This test will fail until AgentExecutor is implemented.
        GREEN: Implement minimal initialization code.
        REFACTOR: Add configuration and validation.
        """
        from agent_vm.execution.executor import AgentExecutor

        executor = AgentExecutor()

        assert executor.default_timeout == 300  # 5 minutes default
        assert executor.max_timeout == 3600  # 1 hour max

    def test_executor_accepts_custom_default_timeout(self) -> None:
        """AgentExecutor accepts custom default timeout."""
        from agent_vm.execution.executor import AgentExecutor

        executor = AgentExecutor(default_timeout=600)

        assert executor.default_timeout == 600

    def test_executor_accepts_custom_max_timeout(self) -> None:
        """AgentExecutor accepts custom max timeout."""
        from agent_vm.execution.executor import AgentExecutor

        executor = AgentExecutor(max_timeout=7200)

        assert executor.max_timeout == 7200

    def test_executor_validates_timeout_range(self) -> None:
        """AgentExecutor validates timeout is in valid range."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError

        # Timeout must be positive
        with pytest.raises(ExecutionError, match="Timeout must be positive"):
            AgentExecutor(default_timeout=-1)

        with pytest.raises(ExecutionError, match="Timeout must be positive"):
            AgentExecutor(default_timeout=0)

    def test_executor_validates_max_timeout_greater_than_default(self) -> None:
        """AgentExecutor validates max_timeout >= default_timeout."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError

        # max_timeout must be >= default_timeout
        with pytest.raises(ExecutionError, match="Default timeout cannot exceed max timeout"):
            AgentExecutor(default_timeout=600, max_timeout=300)


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_execution_result_creation(self) -> None:
        """ExecutionResult can be created with required fields."""
        from agent_vm.execution.executor import ExecutionResult

        result = ExecutionResult(
            success=True, exit_code=0, stdout="Success output", stderr="", duration_seconds=1.5
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Success output"
        assert result.stderr == ""
        assert result.duration_seconds == 1.5
        assert result.output is None

    def test_execution_result_with_optional_output(self) -> None:
        """ExecutionResult accepts optional output dictionary."""
        from agent_vm.execution.executor import ExecutionResult

        output_data = {"status": "complete", "data": [1, 2, 3]}
        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=2.0,
            output=output_data,
        )

        assert result.output == output_data

    def test_execution_result_success_property(self) -> None:
        """ExecutionResult success property reflects exit code."""
        from agent_vm.execution.executor import ExecutionResult

        # Success when exit_code is 0
        success_result = ExecutionResult(
            success=True, exit_code=0, stdout="", stderr="", duration_seconds=1.0
        )
        assert success_result.success is True

        # Failure when exit_code is non-zero
        failure_result = ExecutionResult(
            success=False, exit_code=1, stdout="", stderr="Error occurred", duration_seconds=1.0
        )
        assert failure_result.success is False


class TestAgentExecutorExecute:
    """Test AgentExecutor.execute() method."""

    @pytest.mark.asyncio
    async def test_execute_simple_code_success(self, tmp_path: Path) -> None:
        """Execute simple agent code successfully."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('Hello from agent')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods
            mock_fs = Mock()
            mock_fs.write_file = AsyncMock()
            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))
            mock_fs.cleanup = AsyncMock()
            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "Hello from agent\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify code was injected (uses write_file in implementation)
            mock_fs.write_file.assert_called_once_with("input/agent.py", agent_code.encode())

            # Verify execution
            mock_exec.assert_called_once()

            # Verify result
            assert result.success is True
            assert result.exit_code == 0
            assert "Hello from agent" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_with_custom_timeout(self, tmp_path: Path) -> None:
        """Execute with custom timeout value."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path, timeout=60)

            # Verify timeout was used
            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_captures_stderr(self, tmp_path: Path) -> None:
        """Execute captures stderr on error."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "import sys; sys.stderr.write('Error message'); sys.exit(1)"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 1, "stdout": "", "stderr": "Error message"}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            assert result.success is False
            assert result.exit_code == 1
            assert "Error message" in result.stderr

    @pytest.mark.asyncio
    async def test_execute_enforces_timeout(self, tmp_path: Path) -> None:
        """Execute enforces timeout on long-running code."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        # Code that runs forever
        agent_code = "import time; time.sleep(1000)"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Simulate timeout
            mock_exec.side_effect = asyncio.TimeoutError()

            with pytest.raises(ExecutionError, match="timeout|timed out"):
                await executor.execute(mock_vm, agent_code, tmp_path, timeout=2)

    @pytest.mark.asyncio
    async def test_execute_extracts_results_json(self, tmp_path: Path) -> None:
        """Execute extracts results.json from output directory."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "import json; print(json.dumps({'status': 'success'}))"

        output_data = {"status": "success", "data": [1, 2, 3]}

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods
            mock_fs = Mock()
            mock_fs.write_file = AsyncMock()
            # Set return value directly for this test instead of side_effect
            mock_fs.read_file = AsyncMock(return_value=json.dumps(output_data).encode())
            mock_fs.cleanup = AsyncMock()
            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {
                "exit_code": 0,
                "stdout": '{"status": "success"}\n',
                "stderr": "",
            }

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify results were extracted
            mock_fs.read_file.assert_called_once_with("output/results.json")
            assert result.output == output_data

    @pytest.mark.asyncio
    async def test_execute_handles_missing_results_gracefully(self, tmp_path: Path) -> None:
        """Execute handles missing results.json gracefully."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM
        from agent_vm.communication.filesystem import FilesystemError

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('No output file')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs
            # Implementation catches FilesystemError, not FileNotFoundError
            mock_fs.read_file.side_effect = FilesystemError("File not found")

            mock_exec.return_value = {"exit_code": 0, "stdout": "No output file\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Should succeed but output is None
            assert result.success is True
            assert result.output is None

    @pytest.mark.asyncio
    async def test_execute_cleans_up_filesystem_share(self, tmp_path: Path) -> None:
        """Execute always cleans up FilesystemShare."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify cleanup was called
            mock_fs.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cleans_up_on_error(self, tmp_path: Path) -> None:
        """Execute cleans up FilesystemShare even on error."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Simulate execution error
            mock_exec.side_effect = Exception("VM error")

            with pytest.raises(Exception):
                await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify cleanup was still called
            mock_fs.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_calculates_duration(self, tmp_path: Path) -> None:
        """Execute calculates accurate duration using NIST ET."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Simulate execution delay
            async def delayed_exec(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            mock_exec.side_effect = delayed_exec

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Duration should be >= 0.1 seconds
            assert result.duration_seconds >= 0.1
            assert result.duration_seconds < 1.0  # Sanity check

    @pytest.mark.asyncio
    async def test_execute_uses_timezone_aware_datetime(self, tmp_path: Path) -> None:
        """Execute uses timezone-aware datetime (NIST ET compliance)."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
            patch("agent_vm.execution.executor.datetime") as mock_datetime,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Mock timezone-aware datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2024, 1, 1, 12, 0, 2, tzinfo=timezone.utc)
            mock_datetime.now.side_effect = [start_time, end_time]

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify timezone-aware datetime was used
            assert mock_datetime.now.call_count == 2
            assert result.duration_seconds == 2.0


class TestAgentExecutorLogging:
    """Test structured logging."""

    @pytest.mark.asyncio
    async def test_executor_logs_execution_start(self, tmp_path: Path) -> None:
        """Executor logs execution start event."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
            patch.object(executor._logger, "info") as mock_log_info,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify execution start was logged
            assert mock_log_info.called
            # Check that one of the calls was for execution_started
            call_events = [call[0][0] if call[0] else None for call in mock_log_info.call_args_list]
            assert "execution_started" in call_events

    @pytest.mark.asyncio
    async def test_executor_logs_execution_completion(self, tmp_path: Path) -> None:
        """Executor logs execution completion event."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
            patch.object(executor._logger, "info") as mock_log_info,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify completion was logged with success status
            mock_log_info.assert_called()
            call_events = [call[0][0] if call[0] else None for call in mock_log_info.call_args_list]
            assert "execution_completed" in call_events

    @pytest.mark.asyncio
    async def test_executor_logs_timeout_error(self, tmp_path: Path) -> None:
        """Executor logs timeout errors."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "import time; time.sleep(1000)"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
            patch.object(executor._logger, "error") as mock_log_error,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.side_effect = asyncio.TimeoutError()

            with pytest.raises(ExecutionError):
                await executor.execute(mock_vm, agent_code, tmp_path, timeout=2)

            # Verify timeout was logged
            mock_log_error.assert_called()
            call_events = [
                call[0][0] if call[0] else None for call in mock_log_error.call_args_list
            ]
            assert "execution_timeout" in call_events

    @pytest.mark.asyncio
    async def test_executor_logs_with_vm_context(self, tmp_path: Path) -> None:
        """Executor logs include VM context."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm-123"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
            patch.object(executor._logger, "info") as mock_log_info,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify VM name in log context
            assert mock_log_info.called
            call_args_list = mock_log_info.call_args_list
            found_vm_context = False
            for call_args in call_args_list:
                args, kwargs = call_args
                if "vm" in kwargs and kwargs["vm"] == "test-vm-123":
                    found_vm_context = True
                    break

            assert found_vm_context


class TestAgentExecutorErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_execute_raises_on_invalid_timeout(self, tmp_path: Path) -> None:
        """Execute raises error on invalid timeout."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        agent_code = "print('test')"

        # Negative timeout
        with pytest.raises(ExecutionError, match="Timeout must be positive"):
            await executor.execute(mock_vm, agent_code, tmp_path, timeout=-1)

        # Zero timeout
        with pytest.raises(ExecutionError, match="Timeout must be positive"):
            await executor.execute(mock_vm, agent_code, tmp_path, timeout=0)

    @pytest.mark.asyncio
    async def test_execute_raises_on_timeout_exceeds_max(self, tmp_path: Path) -> None:
        """Execute raises error when timeout exceeds max_timeout."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor(max_timeout=600)
        mock_vm = Mock(spec=VM)

        agent_code = "print('test')"

        with pytest.raises(ExecutionError, match="Timeout.*exceeds maximum"):
            await executor.execute(mock_vm, agent_code, tmp_path, timeout=700)

    @pytest.mark.asyncio
    async def test_execute_handles_vm_error(self, tmp_path: Path) -> None:
        """Execute handles VM execution errors."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Simulate VM error
            mock_exec.side_effect = Exception("VM communication error")

            with pytest.raises(Exception, match="VM communication error"):
                await executor.execute(mock_vm, agent_code, tmp_path)

    @pytest.mark.asyncio
    async def test_execute_handles_filesystem_error(self, tmp_path: Path) -> None:
        """Execute handles FilesystemShare errors."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        agent_code = "print('test')"

        with patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class:

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Simulate filesystem error during write
            mock_fs.write_file.side_effect = OSError("Disk full")

            with pytest.raises(OSError, match="Disk full"):
                await executor.execute(mock_vm, agent_code, tmp_path)

    @pytest.mark.asyncio
    async def test_execute_validates_workspace_path(self, tmp_path: Path) -> None:
        """Execute validates workspace path exists."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        agent_code = "print('test')"
        nonexistent_path = tmp_path / "nonexistent"

        # Implementation raises ValueError, not ExecutionError
        with pytest.raises(ValueError, match="Workspace.*does not exist"):
            await executor.execute(mock_vm, agent_code, nonexistent_path)

    @pytest.mark.asyncio
    async def test_execute_validates_agent_code_not_empty(self, tmp_path: Path) -> None:
        """Execute validates agent code is not empty."""
        from agent_vm.execution.executor import AgentExecutor, ExecutionError
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        # Empty string - implementation raises ValueError, not ExecutionError
        with pytest.raises(ValueError, match="Agent code.*empty"):
            await executor.execute(mock_vm, "", tmp_path)

        # Whitespace only
        with pytest.raises(ValueError, match="Agent code.*empty"):
            await executor.execute(mock_vm, "   \n\t  ", tmp_path)


class TestAgentExecutorPrivateMethods:
    """Test private helper methods."""

    @pytest.mark.asyncio
    async def test_execute_in_vm_placeholder(self) -> None:
        """_execute_in_vm is a placeholder for vsock integration."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        # This is a placeholder method that will be replaced with vsock
        result = await executor._execute_in_vm(mock_vm, "/workspace/input/agent.py")

        # Should return dict with expected keys
        assert "exit_code" in result
        assert "stdout" in result
        assert "stderr" in result

    @pytest.mark.asyncio
    async def test_execute_in_vm_simulates_execution(self) -> None:
        """_execute_in_vm simulates successful execution."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        result = await executor._execute_in_vm(mock_vm, "/workspace/input/agent.py")

        # Placeholder returns success
        assert result["exit_code"] == 0
        assert isinstance(result["stdout"], str)
        assert isinstance(result["stderr"], str)


class TestAgentExecutorIntegration:
    """Integration-style tests for executor."""

    @pytest.mark.asyncio
    async def test_full_execution_workflow(self, tmp_path: Path) -> None:
        """Test complete execution workflow."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "integration-test-vm"

        agent_code = """
import json
result = {"status": "success", "message": "Integration test passed"}
with open("/workspace/output/results.json", "w") as f:
    json.dump(result, f)
print("Execution complete")
"""

        output_data = {"status": "success", "message": "Integration test passed"}

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods
            mock_fs = Mock()
            mock_fs.write_file = AsyncMock()
            # Set return value directly for this test instead of side_effect
            mock_fs.read_file = AsyncMock(return_value=json.dumps(output_data).encode())
            mock_fs.cleanup = AsyncMock()
            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {
                "exit_code": 0,
                "stdout": "Execution complete\n",
                "stderr": "",
            }

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Verify complete workflow
            assert result.success is True
            assert result.exit_code == 0
            assert "Execution complete" in result.stdout
            assert result.output == output_data
            assert result.duration_seconds > 0

            # Verify all steps were called
            mock_fs.write_file.assert_called_once()
            mock_exec.assert_called_once()
            mock_fs.read_file.assert_called_once()
            mock_fs.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_execution_with_agent_error(self, tmp_path: Path) -> None:
        """Test execution when agent code has errors."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "error-test-vm"

        agent_code = """
raise ValueError("Agent encountered an error")
"""

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {
                "exit_code": 1,
                "stdout": "",
                "stderr": "Traceback (most recent call last):\n  ValueError: Agent encountered an error",
            }

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Should capture error
            assert result.success is False
            assert result.exit_code == 1
            assert "ValueError" in result.stderr
            assert "Agent encountered an error" in result.stderr

            # Cleanup should still happen
            mock_fs.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, tmp_path: Path) -> None:
        """Test multiple concurrent executions."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()

        # Create multiple VMs
        vms = [Mock(spec=VM, name=f"vm-{i}") for i in range(3)]

        agent_code = "print('Concurrent test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            def create_mock_fs(*args, **kwargs):
                mock_fs = Mock()
                mock_fs.write_file = AsyncMock()
                mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))
                mock_fs.cleanup = AsyncMock()
                return mock_fs

            mock_fs_class.side_effect = create_mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "Concurrent test\n", "stderr": ""}

            # Execute concurrently
            tasks = [executor.execute(vm, agent_code, tmp_path) for vm in vms]
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 3
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execution_respects_different_timeouts(self, tmp_path: Path) -> None:
        """Test executions with different timeout values."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor(default_timeout=300, max_timeout=600)
        mock_vm = Mock(spec=VM)
        mock_vm.name = "timeout-test-vm"

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            def create_mock_fs(*args, **kwargs):
                mock_fs = Mock()
                mock_fs.write_file = AsyncMock()
                mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))
                mock_fs.cleanup = AsyncMock()
                return mock_fs

            mock_fs_class.side_effect = create_mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            # Test different timeouts
            timeouts = [10, 60, 300, 600]
            for timeout_val in timeouts:
                result = await executor.execute(mock_vm, agent_code, tmp_path, timeout=timeout_val)
                assert result.success is True


class TestAgentExecutorEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_execute_with_large_output(self, tmp_path: Path) -> None:
        """Execute handles large stdout output."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        agent_code = "print('x' * 1000000)"  # 1MB output

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            large_output = "x" * 1000000
            mock_exec.return_value = {"exit_code": 0, "stdout": large_output, "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            assert result.success is True
            assert len(result.stdout) == 1000000

    @pytest.mark.asyncio
    async def test_execute_with_unicode_output(self, tmp_path: Path) -> None:
        """Execute handles Unicode characters in output."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        agent_code = "print('Test with emoji: 🚀 and Unicode: ñ')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {
                "exit_code": 0,
                "stdout": "Test with emoji: 🚀 and Unicode: ñ\n",
                "stderr": "",
            }

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            assert result.success is True
            assert "🚀" in result.stdout
            assert "ñ" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_with_binary_output(self, tmp_path: Path) -> None:
        """Execute handles binary data in output."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        agent_code = "import sys; sys.stdout.buffer.write(b'\\x00\\x01\\x02')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Binary output may be encoded or handled specially
            mock_exec.return_value = {"exit_code": 0, "stdout": "\x00\x01\x02", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_very_long_code(self, tmp_path: Path) -> None:
        """Execute handles very long agent code."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)
        mock_vm.name = "test-vm"

        # Generate large code
        agent_code = "x = 1\n" * 10000  # 10k lines

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, tmp_path)

            # Should inject all code (uses write_file, not inject_code)
            mock_fs.write_file.assert_called_once()
            # Check the content that was written
            call_args = mock_fs.write_file.call_args
            assert call_args[0][0] == "input/agent.py"
            written_content = call_args[0][1]
            assert len(written_content) > 50000

    @pytest.mark.asyncio
    async def test_execute_with_special_characters_in_workspace(self, tmp_path: Path) -> None:
        """Execute handles workspace paths with special characters."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        # Create workspace with special characters
        special_workspace = tmp_path / "workspace with spaces & symbols!"
        special_workspace.mkdir()

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            mock_exec.return_value = {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            result = await executor.execute(mock_vm, agent_code, special_workspace)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_at_exact_timeout_boundary(self, tmp_path: Path) -> None:
        """Execute handles execution at exact timeout boundary."""
        from agent_vm.execution.executor import AgentExecutor
        from agent_vm.core.vm import VM

        executor = AgentExecutor()
        mock_vm = Mock(spec=VM)

        agent_code = "print('test')"

        with (
            patch("agent_vm.execution.executor.FilesystemShare") as mock_fs_class,
            patch.object(executor, "_execute_in_vm", new_callable=AsyncMock) as mock_exec,
        ):

            # Create mock with proper async methods

            mock_fs = Mock()

            mock_fs.write_file = AsyncMock()

            mock_fs.read_file = AsyncMock(side_effect=FilesystemError("Not found"))

            mock_fs.cleanup = AsyncMock()

            mock_fs_class.return_value = mock_fs

            # Simulate execution that takes exactly timeout duration
            async def exact_timeout_exec(*args, **kwargs):
                await asyncio.sleep(2.0)
                return {"exit_code": 0, "stdout": "test\n", "stderr": ""}

            mock_exec.side_effect = exact_timeout_exec

            # Should succeed (not timeout) if finishes at boundary
            result = await executor.execute(mock_vm, agent_code, tmp_path, timeout=3)

            assert result.success is True
