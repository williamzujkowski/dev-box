"""Agent code execution in isolated VMs.

This module provides the AgentExecutor class for executing agent code
within isolated VMs with timeout enforcement, error handling, and result extraction.

Follows NIST ET timezone convention for all timestamps.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import structlog

from agent_vm.communication.filesystem import FilesystemError, FilesystemShare
from agent_vm.core.vm import VM

ET = ZoneInfo("America/New_York")
logger = structlog.get_logger()


class ExecutionError(Exception):
    """Agent execution error."""

    pass


@dataclass(frozen=True)
class ExecutionResult:
    """Agent execution result with NIST ET timestamps.

    Attributes:
        success: Whether execution completed successfully (exit code 0)
        exit_code: Process exit code
        stdout: Standard output from execution
        stderr: Standard error from execution
        duration_seconds: Execution duration in seconds
        output: Optional parsed output dictionary from results.json
    """

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    output: dict[str, Any] | None = None


class AgentExecutor:
    """Execute agent code in isolated VMs.

    Provides code injection, execution with timeout enforcement,
    result extraction, and comprehensive error handling.

    Example:
        >>> executor = AgentExecutor()
        >>> result = await executor.execute(
        ...     vm=my_vm,
        ...     agent_code="print('Hello')",
        ...     workspace=Path("/tmp/workspace")
        ... )
        >>> assert result.success
        >>> print(result.stdout)
        Hello
    """

    def __init__(self, default_timeout: int = 300, max_timeout: int = 3600) -> None:
        """Initialize AgentExecutor.

        Args:
            default_timeout: Default execution timeout in seconds
            max_timeout: Maximum allowed timeout in seconds

        Raises:
            ExecutionError: If timeouts are invalid
        """
        if default_timeout <= 0:
            raise ExecutionError("Timeout must be positive")
        if max_timeout <= 0:
            raise ExecutionError("Timeout must be positive")
        if default_timeout > max_timeout:
            raise ExecutionError("Default timeout cannot exceed max timeout")

        self.default_timeout = default_timeout
        self.max_timeout = max_timeout
        self._logger = logger.bind(
            component="agent_executor",
            default_timeout=default_timeout,
            max_timeout=max_timeout,
        )

    async def execute(
        self,
        vm: VM,
        agent_code: str,
        workspace: Path,
        timeout: int | None = None,
    ) -> ExecutionResult:
        """Execute agent code in VM with timeout enforcement.

        Args:
            vm: VM instance to execute in
            agent_code: Python code to execute
            workspace: Workspace directory path
            timeout: Execution timeout (uses default if None)

        Returns:
            ExecutionResult with execution details

        Raises:
            ExecutionError: If execution fails or times out
            ValueError: If workspace doesn't exist or code is empty
        """
        # Validate inputs
        if not workspace.exists():
            raise ValueError(f"Workspace does not exist: {workspace}")

        if not agent_code or not agent_code.strip():
            raise ValueError("Agent code cannot be empty")

        # Use default timeout if not specified
        if timeout is None:
            timeout = self.default_timeout

        # Validate timeout
        if timeout <= 0:
            raise ExecutionError("Timeout must be positive")
        if timeout > self.max_timeout:
            raise ExecutionError(f"Timeout {timeout}s exceeds maximum {self.max_timeout}s")

        start_time = datetime.now(ET)
        self._logger.info(
            "execution_started",
            vm=vm.name,
            timeout=timeout,
            code_length=len(agent_code),
        )

        fs_share = FilesystemShare(workspace)

        try:
            # Inject code into VM
            await fs_share.write_file("input/agent.py", agent_code.encode())

            # Execute code in VM
            try:
                result_dict = await asyncio.wait_for(
                    self._execute_in_vm(vm, "/workspace/input/agent.py"),
                    timeout=float(timeout),
                )
            except TimeoutError as timeout_err:
                self._logger.error(
                    "execution_timeout",
                    vm=vm.name,
                    timeout=timeout,
                )
                raise ExecutionError(
                    f"Execution timed out after {timeout} seconds"
                ) from timeout_err

            # Extract results if available
            output_dict = None
            try:
                results_content = await fs_share.read_file("output/results.json")
                output_dict = json.loads(results_content.decode())
            except (FilesystemError, json.JSONDecodeError):
                # Results file optional or malformed
                pass

            # Calculate duration
            duration = (datetime.now(ET) - start_time).total_seconds()

            # Create result
            exec_result = ExecutionResult(
                success=result_dict["exit_code"] == 0,
                exit_code=result_dict["exit_code"],
                stdout=result_dict["stdout"],
                stderr=result_dict["stderr"],
                duration_seconds=duration,
                output=output_dict,
            )

            self._logger.info(
                "execution_completed",
                vm=vm.name,
                exit_code=exec_result.exit_code,
                duration=duration,
                success=exec_result.success,
            )

            return exec_result

        finally:
            # Always cleanup filesystem share
            try:
                await fs_share.cleanup()
            except Exception as cleanup_err:
                self._logger.warning("cleanup_failed", error=str(cleanup_err))

    async def _execute_in_vm(self, vm: VM, script_path: str) -> dict[str, Any]:
        """Execute script in VM (placeholder for vsock communication).

        This is a simplified implementation that will be replaced with
        actual vsock communication to the guest agent.

        Args:
            vm: VM instance
            script_path: Path to script inside VM

        Returns:
            Dictionary with exit_code, stdout, stderr
        """
        # TODO(Phase 6): Replace with actual vsock communication to guest agent
        # This placeholder simulates execution. The full implementation requires:
        # 1. VsockProtocol.send() to transmit execute command to guest agent
        # 2. Guest agent to execute script_path and capture stdout/stderr
        # 3. VsockProtocol.receive() to get execution results
        # See: IMPLEMENTATION_GUIDE.md Phase 2 (Communication) for vsock integration
        await asyncio.sleep(0.1)  # Simulate execution delay

        return {
            "exit_code": 0,
            "stdout": "Simulated execution output",
            "stderr": "",
        }
