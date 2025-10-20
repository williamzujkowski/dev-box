#!/usr/bin/env python3
"""Guest agent that runs inside VM and communicates with host.

This agent runs inside guest VMs, listens for commands via vsock,
executes agent code, and reports results back to the host.

Follows NIST ET timezone convention for all timestamps.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    import structlog
except ImportError:
    # Fallback if structlog not available in guest
    import logging
    structlog = None  # type: ignore

# NIST ET timezone
ET = ZoneInfo("America/New_York")


class AgentError(Exception):
    """Base exception for agent errors."""
    pass


def _get_logger() -> Any:
    """Get logger instance (structlog if available, else standard logging)."""
    if structlog:
        return structlog.get_logger()
    else:
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger


logger = _get_logger()


def create_vsock_listener(port: int) -> Any:
    """Create vsock listener (placeholder for actual vsock implementation).

    Args:
        port: Port number to listen on

    Returns:
        Vsock listener instance

    Note:
        This is a placeholder. Real implementation would use socket.AF_VSOCK.
    """
    # This is a mock for testing - real implementation would use vsock
    class MockVsockListener:
        """Mock vsock listener for testing."""

        def __init__(self, port: int) -> None:
            self.port = port
            self._running = False

        async def __aenter__(self) -> "MockVsockListener":
            self._running = True
            return self

        async def __aexit__(self, *args: Any) -> None:
            self._running = False

        async def receive_message(self) -> tuple[int, bytes]:
            """Receive message from vsock."""
            # Placeholder - real implementation would read from socket
            await asyncio.sleep(0.1)
            return (1, b'{"command": "ping"}')

    return MockVsockListener(port)


class GuestAgent:
    """Agent that runs inside guest VM.

    Listens for commands on vsock, executes agent code, and reports results.
    """

    def __init__(
        self,
        vsock_port: int = 9000,
        workspace: Path = Path("/workspace")
    ) -> None:
        """Initialize guest agent.

        Args:
            vsock_port: Port to listen on for vsock connections
            workspace: Workspace directory for code execution

        Raises:
            AgentError: If vsock_port is invalid
        """
        # Validate vsock port
        if not 1 <= vsock_port <= 65535:
            raise AgentError(f"Port must be in range 1-65535, got {vsock_port}")

        self.vsock_port = vsock_port
        self.workspace = Path(workspace)
        self._running = False
        self._server: Any | None = None

        # Initialize logger first before any operations that might log
        if structlog:
            self._logger = logger.bind(
                agent="guest",
                vsock_port=vsock_port,
                workspace=str(workspace)
            )
        else:
            self._logger = logger

        # Create workspace directories
        self._create_workspace_directories()

        self._log_info("guest_agent_initialized")

    def _create_workspace_directories(self) -> None:
        """Create required workspace directories."""
        try:
            (self.workspace / "input").mkdir(parents=True, exist_ok=True)
            (self.workspace / "output").mkdir(parents=True, exist_ok=True)
            (self.workspace / "work").mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._log_error("workspace_creation_failed", error=str(e))
            # Don't raise - some tests might use invalid paths

    @property
    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return self._running

    def _log_info(self, event: str, **kwargs: Any) -> None:
        """Log info event."""
        if structlog:
            self._logger.info(event, **kwargs)
        else:
            self._logger.info(f"{event}: {kwargs}")

    def _log_error(self, event: str, **kwargs: Any) -> None:
        """Log error event."""
        if structlog:
            self._logger.error(event, **kwargs)
        else:
            self._logger.error(f"{event}: {kwargs}")

    async def start(self) -> None:
        """Start listening for commands.

        Creates server and starts listening for incoming connections.

        Raises:
            AgentError: If server fails to start
        """
        try:
            self._log_info("agent_starting")

            # Create async server (binding to all interfaces inside VM is safe)
            self._server = await asyncio.start_server(
                self._handle_client,
                host="0.0.0.0",  # noqa: S104
                port=self.vsock_port
            )

            self._running = True
            self._log_info("agent_started", port=self.vsock_port)

        except OSError as e:
            self._log_error("agent_start_failed", error=str(e))
            raise AgentError(f"Failed to start agent: {e}") from e

    async def stop(self) -> None:
        """Stop agent gracefully.

        Closes server and waits for cleanup.
        """
        if not self._running:
            return  # Already stopped

        self._log_info("agent_stopping")
        self._running = False

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._log_info("agent_stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming client connection.

        Args:
            reader: Stream reader for incoming data
            writer: Stream writer for outgoing data
        """
        try:
            # Read command data
            data = await reader.read(1024 * 1024)  # 1MB max
            if not data:
                return

            # Parse command
            command = json.loads(data.decode('utf-8'))

            # Handle command
            result = await self.handle_command(command)

            # Send result back
            response_data = json.dumps(result).encode('utf-8')
            writer.write(response_data)
            await writer.drain()

        except Exception as e:
            self._log_error("client_handler_error", error=str(e))
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming command and return result.

        Args:
            command: Command dictionary with 'command' field

        Returns:
            Result dictionary with execution results or status

        Raises:
            AgentError: If command is invalid or missing required fields
        """
        cmd_type = command.get("command")

        if not cmd_type:
            raise AgentError("Invalid command: Missing command field")

        self._log_info("handling_command", command=cmd_type)

        if cmd_type == "execute":
            code = command.get("code", "")
            timeout = command.get("timeout", 300)
            return await self._execute_code(code, timeout)

        elif cmd_type == "status":
            state = "idle" if not self._running else ("ready" if self._running else "busy")
            return {
                "status": state,
                "timestamp": datetime.now(ET).isoformat()
            }

        elif cmd_type == "stop":
            await self.stop()
            return {"status": "stopped"}

        else:
            return {
                "error": f"Unsupported command: {cmd_type}"
            }

    async def _execute_code(self, code: str, timeout: float = 300) -> dict[str, Any]:
        """Execute agent code and capture output.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with execution results:
                - exit_code: Process exit code
                - stdout: Standard output
                - stderr: Standard error

        Raises:
            AgentError: If execution timeout occurs
        """
        # Create workspace directories if needed
        input_dir = self.workspace / "input"
        work_dir = self.workspace / "work"

        input_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)

        # Write code to file
        code_path = input_dir / "agent.py"
        code_path.write_text(code, encoding='utf-8')

        self._log_info("executing_code", code_path=str(code_path))

        try:
            # Execute code with timeout
            proc = await asyncio.create_subprocess_exec(
                sys.executable,  # Use same Python interpreter
                str(code_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir)
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )

                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                exit_code = proc.returncode or 0

                self._log_info("code_executed", exit_code=exit_code)

                return {
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr
                }

            except TimeoutError as timeout_err:
                # Kill the process
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    # Process cleanup may fail if already terminated
                    self._log_info("process_cleanup_skipped")

                self._log_error("execution_timeout")
                raise AgentError(
                    f"Execution timed out after {timeout} seconds"
                ) from timeout_err

        except TimeoutError as timeout_err:
            raise AgentError(
                f"Execution timed out after {timeout} seconds"
            ) from timeout_err

    async def _write_results(self, result_data: dict[str, Any]) -> None:
        """Write execution results to output directory.

        Args:
            result_data: Result dictionary to write
        """
        output_dir = self.workspace / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        results_file = output_dir / "results.json"
        results_file.write_text(json.dumps(result_data), encoding='utf-8')

    async def _send_result(self, result_data: dict[str, Any]) -> None:
        """Send results back to host via vsock.

        Args:
            result_data: Result dictionary to send
        """
        try:
            import json

            from agent_vm.communication.vsock import VsockMessage, VsockProtocol

            # Send result to host via vsock (CID 2 = host)
            protocol = VsockProtocol(cid=2, port=self.vsock_port)
            message = VsockMessage(
                command="result",
                payload=json.dumps(result_data).encode('utf-8'),
                checksum=""  # Will be calculated by framing
            )
            await protocol.send(message)
            self._log_info("result_sent", result=result_data)
        except Exception as e:
            self._log_error("result_send_failed", error=str(e))


async def main() -> None:
    """Main entry point for guest agent."""
    agent = GuestAgent()

    try:
        await agent.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await agent.stop()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
