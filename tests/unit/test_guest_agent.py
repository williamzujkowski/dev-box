"""Test guest agent (runs inside VM).

This test suite validates the GuestAgent class following TDD principles.
Tests are written FIRST (RED phase) before implementation.

Phase 2 Component: Guest-side agent for handling host commands
Protocol: Listens on vsock, executes commands, reports results
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import asyncio
from typing import Any, Dict


class TestGuestAgentInitialization:
    """Test GuestAgent initialization."""

    def test_agent_initializes_with_defaults(self) -> None:
        """GuestAgent initializes with default vsock port.

        RED: This test will fail until GuestAgent is implemented.
        GREEN: Implement minimal initialization code.
        REFACTOR: Add configuration and validation.
        """
        from guest.agent import GuestAgent

        agent = GuestAgent()

        assert agent.vsock_port == 9000  # Default port
        assert agent.workspace == Path("/workspace")

    def test_agent_accepts_custom_vsock_port(self) -> None:
        """GuestAgent accepts custom vsock port."""
        from guest.agent import GuestAgent

        agent = GuestAgent(vsock_port=5555)

        assert agent.vsock_port == 5555

    def test_agent_accepts_custom_workspace(self) -> None:
        """GuestAgent accepts custom workspace path."""
        from guest.agent import GuestAgent

        custom_workspace = Path("/custom/workspace")
        agent = GuestAgent(workspace=custom_workspace)

        assert agent.workspace == custom_workspace

    def test_agent_validates_vsock_port(self) -> None:
        """GuestAgent validates vsock port is in valid range."""
        from guest.agent import GuestAgent, AgentError

        # Port must be in valid range (1-65535)
        with pytest.raises(AgentError, match="Port must be"):
            GuestAgent(vsock_port=0)

        with pytest.raises(AgentError, match="Port must be"):
            GuestAgent(vsock_port=70000)

    def test_agent_creates_workspace_directories(self, tmp_path: Path) -> None:
        """GuestAgent creates required workspace directories."""
        from guest.agent import GuestAgent

        workspace = tmp_path / "agent_workspace"
        agent = GuestAgent(workspace=workspace)

        # Should create input, output, work directories
        assert (workspace / "input").exists()
        assert (workspace / "output").exists()
        assert (workspace / "work").exists()


class TestGuestAgentStartStop:
    """Test agent startup and shutdown."""

    @pytest.mark.asyncio
    async def test_agent_starts_listening(self) -> None:
        """Agent starts listening on vsock port."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        with patch("asyncio.start_server") as mock_server:
            mock_server.return_value = AsyncMock()

            await agent.start()

            # Verify server started
            mock_server.assert_called_once()
            call_args = mock_server.call_args
            # Should listen on vsock port
            assert agent.is_running

    @pytest.mark.asyncio
    async def test_agent_stops_gracefully(self) -> None:
        """Agent stops listening and cleans up resources."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        with patch("asyncio.start_server") as mock_server:
            mock_server_instance = AsyncMock()
            mock_server.return_value = mock_server_instance

            await agent.start()
            await agent.stop()

            # Verify server stopped
            mock_server_instance.close.assert_called_once()
            mock_server_instance.wait_closed.assert_called_once()
            assert not agent.is_running

    @pytest.mark.asyncio
    async def test_agent_handles_start_failure(self) -> None:
        """Agent handles startup failure gracefully."""
        from guest.agent import GuestAgent, AgentError

        agent = GuestAgent()

        with patch("asyncio.start_server", side_effect=OSError("Address in use")):
            with pytest.raises(AgentError, match="Failed to start|Address in use"):
                await agent.start()

    @pytest.mark.asyncio
    async def test_agent_stop_is_idempotent(self) -> None:
        """Stopping an already stopped agent is safe."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        # Stop without starting
        await agent.stop()  # Should not raise

        assert not agent.is_running


class TestGuestAgentCommandHandling:
    """Test command reception and handling."""

    @pytest.mark.asyncio
    async def test_agent_handles_execute_command(self) -> None:
        """Agent handles EXECUTE command."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        # Mock command data
        command_data = {
            "command": "execute",
            "code": "print('Hello from agent')",
            "timeout": 300
        }

        with patch.object(agent, "_execute_code", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "exit_code": 0,
                "stdout": "Hello from agent\n",
                "stderr": ""
            }

            result = await agent.handle_command(command_data)

            # Verify execution was called
            mock_execute.assert_called_once()
            assert result["exit_code"] == 0
            assert "Hello from agent" in result["stdout"]

    @pytest.mark.asyncio
    async def test_agent_handles_status_command(self) -> None:
        """Agent handles STATUS command."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        command_data = {
            "command": "status"
        }

        result = await agent.handle_command(command_data)

        # Verify status response
        assert "status" in result
        assert result["status"] in ["idle", "busy", "ready"]

    @pytest.mark.asyncio
    async def test_agent_handles_stop_command(self) -> None:
        """Agent handles STOP command."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        command_data = {
            "command": "stop"
        }

        with patch.object(agent, "stop", new_callable=AsyncMock) as mock_stop:
            await agent.handle_command(command_data)

            # Verify stop was called
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_handles_unknown_command(self) -> None:
        """Agent handles unknown command gracefully."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        command_data = {
            "command": "unknown_command"
        }

        result = await agent.handle_command(command_data)

        # Should return error result
        assert "error" in result
        assert "unknown" in result["error"].lower() or "unsupported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_agent_validates_command_format(self) -> None:
        """Agent validates command data structure."""
        from guest.agent import GuestAgent, AgentError

        agent = GuestAgent()

        # Missing command field
        invalid_data = {"not_a_command": "value"}

        with pytest.raises(AgentError, match="Invalid command|Missing command"):
            await agent.handle_command(invalid_data)


class TestGuestAgentCodeExecution:
    """Test agent code execution."""

    @pytest.mark.asyncio
    async def test_execute_code_runs_python_script(self, tmp_path: Path) -> None:
        """_execute_code runs Python script and captures output."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        code = "print('Test output')"

        result = await agent._execute_code(code, timeout=10)

        assert result["exit_code"] == 0
        assert "Test output" in result["stdout"]
        assert result["stderr"] == ""

    @pytest.mark.asyncio
    async def test_execute_code_captures_error_output(self, tmp_path: Path) -> None:
        """_execute_code captures stderr on error."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        code = "import sys; sys.stderr.write('Error message'); sys.exit(1)"

        result = await agent._execute_code(code, timeout=10)

        assert result["exit_code"] == 1
        assert "Error message" in result["stderr"]

    @pytest.mark.asyncio
    async def test_execute_code_enforces_timeout(self, tmp_path: Path) -> None:
        """_execute_code enforces timeout on long-running code."""
        from guest.agent import GuestAgent, AgentError

        agent = GuestAgent(workspace=tmp_path)

        # Code that runs forever
        code = "import time; time.sleep(1000)"

        with pytest.raises(AgentError, match="timeout|timed out"):
            await agent._execute_code(code, timeout=1)

    @pytest.mark.asyncio
    async def test_execute_code_writes_to_file_first(self, tmp_path: Path) -> None:
        """_execute_code writes code to file before executing."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        code = "print('test')"

        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"test\n", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            await agent._execute_code(code, timeout=10)

            # Verify code was written to input directory
            code_file = tmp_path / "input" / "agent.py"
            assert code_file.exists()
            assert code_file.read_text() == code

    @pytest.mark.asyncio
    async def test_execute_code_runs_in_work_directory(self, tmp_path: Path) -> None:
        """_execute_code runs script in work directory."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        code = "import os; print(os.getcwd())"

        result = await agent._execute_code(code, timeout=10)

        # Output should contain work directory path
        work_dir = str(tmp_path / "work")
        assert work_dir in result["stdout"]

    @pytest.mark.asyncio
    async def test_execute_code_handles_syntax_errors(self, tmp_path: Path) -> None:
        """_execute_code handles Python syntax errors."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        code = "print('unclosed string"  # Syntax error

        result = await agent._execute_code(code, timeout=10)

        assert result["exit_code"] != 0
        assert "SyntaxError" in result["stderr"] or result["exit_code"] == 1


class TestGuestAgentResultReporting:
    """Test result reporting back to host."""

    @pytest.mark.asyncio
    async def test_agent_writes_results_to_output(self, tmp_path: Path) -> None:
        """Agent writes execution results to output directory."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        result_data = {
            "exit_code": 0,
            "stdout": "Success",
            "stderr": ""
        }

        await agent._write_results(result_data)

        # Verify results file created
        results_file = tmp_path / "output" / "results.json"
        assert results_file.exists()

        import json
        written_data = json.loads(results_file.read_text())
        assert written_data == result_data

    @pytest.mark.asyncio
    async def test_agent_sends_results_over_vsock(self) -> None:
        """Agent sends results back to host via vsock."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        result_data = {
            "exit_code": 0,
            "stdout": "Success",
            "stderr": ""
        }

        with patch("agent_vm.communication.vsock.VsockProtocol") as mock_protocol:
            mock_protocol_instance = AsyncMock()
            mock_protocol.return_value = mock_protocol_instance

            await agent._send_result(result_data)

            # Verify vsock send was called
            mock_protocol_instance.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_handles_result_send_failure(self) -> None:
        """Agent handles vsock send failure gracefully."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        result_data = {"exit_code": 0}

        with patch("agent_vm.communication.vsock.VsockProtocol") as mock_protocol:
            mock_protocol_instance = AsyncMock()
            mock_protocol_instance.send.side_effect = OSError("Connection lost")
            mock_protocol.return_value = mock_protocol_instance

            # Should log error but not crash
            with patch.object(agent._logger, 'error') as mock_error:
                await agent._send_result(result_data)

                # Verify error was logged
                mock_error.assert_called()


class TestGuestAgentLogging:
    """Test structured logging."""

    @pytest.mark.asyncio
    async def test_agent_logs_startup(self) -> None:
        """Agent logs startup event."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        with patch("asyncio.start_server", new_callable=AsyncMock):
            with patch.object(agent._logger, 'info') as mock_info:
                await agent.start()

                # Verify startup logging
                mock_info.assert_called()
                call_args = str(mock_info.call_args)
                assert "agent_started" in call_args or "start" in call_args.lower()

    @pytest.mark.asyncio
    async def test_agent_logs_command_reception(self) -> None:
        """Agent logs command reception."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        command_data = {"command": "status"}

        with patch.object(agent._logger, 'info') as mock_info:
            await agent.handle_command(command_data)

            # Verify command logging
            mock_info.assert_called()

    @pytest.mark.asyncio
    async def test_agent_logs_execution_results(self, tmp_path: Path) -> None:
        """Agent logs execution results."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        code = "print('test')"

        with patch.object(agent._logger, 'info') as mock_info:
            await agent._execute_code(code, timeout=10)

            # Verify execution logging
            mock_info.assert_called()

    @pytest.mark.asyncio
    async def test_agent_logs_errors(self) -> None:
        """Agent logs errors with context."""
        from guest.agent import GuestAgent, AgentError

        agent = GuestAgent()

        with patch("asyncio.start_server", side_effect=OSError("Port in use")):
            with patch.object(agent._logger, 'error') as mock_error:
                try:
                    await agent.start()
                except AgentError:
                    pass

                # Verify error logging
                mock_error.assert_called()
                call_args = str(mock_error.call_args)
                assert "error" in call_args.lower()


class TestGuestAgentProperties:
    """Test property accessors."""

    def test_is_running_false_initially(self) -> None:
        """is_running is False before start."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        assert not agent.is_running

    @pytest.mark.asyncio
    async def test_is_running_true_after_start(self) -> None:
        """is_running is True after start."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        with patch("asyncio.start_server", new_callable=AsyncMock):
            await agent.start()

            assert agent.is_running

    @pytest.mark.asyncio
    async def test_is_running_false_after_stop(self) -> None:
        """is_running is False after stop."""
        from guest.agent import GuestAgent

        agent = GuestAgent()

        with patch("asyncio.start_server", new_callable=AsyncMock):
            await agent.start()
            await agent.stop()

            assert not agent.is_running


class TestGuestAgentIntegration:
    """Integration-style tests for guest agent."""

    @pytest.mark.asyncio
    async def test_full_workflow_start_execute_stop(self, tmp_path: Path) -> None:
        """Test complete workflow: start → execute → stop."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        with patch("asyncio.start_server", new_callable=AsyncMock):
            # Start agent
            await agent.start()
            assert agent.is_running

            # Execute command
            command_data = {
                "command": "execute",
                "code": "print('Integration test')",
                "timeout": 10
            }

            result = await agent.handle_command(command_data)
            assert result["exit_code"] == 0

            # Stop agent
            await agent.stop()
            assert not agent.is_running

    @pytest.mark.asyncio
    async def test_agent_handles_multiple_commands_sequentially(self, tmp_path: Path) -> None:
        """Agent handles multiple commands in sequence."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        # Execute multiple commands
        commands = [
            {"command": "status"},
            {"command": "execute", "code": "print('Test 1')", "timeout": 10},
            {"command": "status"},
            {"command": "execute", "code": "print('Test 2')", "timeout": 10},
        ]

        for cmd in commands:
            result = await agent.handle_command(cmd)
            assert "error" not in result or result.get("exit_code") == 0


class TestGuestAgentEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_execute_code_with_empty_string(self, tmp_path: Path) -> None:
        """Agent handles empty code string."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        # Empty code should still execute (but do nothing)
        result = await agent._execute_code("", timeout=10)

        # Should succeed (empty script is valid Python)
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_code_with_unicode_characters(self, tmp_path: Path) -> None:
        """Agent handles code with Unicode characters."""
        from guest.agent import GuestAgent

        agent = GuestAgent(workspace=tmp_path)

        code = "print('Test with emoji: 🚀 and Unicode: ñ')"

        result = await agent._execute_code(code, timeout=10)

        assert result["exit_code"] == 0
        assert "🚀" in result["stdout"]

    @pytest.mark.asyncio
    async def test_workspace_with_spaces_in_path(self, tmp_path: Path) -> None:
        """Agent handles workspace paths with spaces."""
        from guest.agent import GuestAgent

        workspace = tmp_path / "my workspace with spaces"
        agent = GuestAgent(workspace=workspace)

        # Should work without errors
        assert agent.workspace.exists()
