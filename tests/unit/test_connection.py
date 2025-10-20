"""Test libvirt connection management.

This test suite validates the LibvirtConnection class following TDD principles.
Tests are written FIRST (RED phase) before implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any


class TestLibvirtConnection:
    """Test libvirt connection management lifecycle."""

    @patch("libvirt.open")
    def test_connection_opens_successfully(self, mock_libvirt_open: Mock) -> None:
        """Connection opens to qemu:///system URI.

        RED: This test will fail until LibvirtConnection is implemented.
        GREEN: Implement minimal code to pass.
        REFACTOR: Improve code quality while keeping test green.
        """
        from agent_vm.core.connection import LibvirtConnection

        # Setup mock
        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        # Execute
        conn = LibvirtConnection()
        conn.open()

        # Verify
        mock_libvirt_open.assert_called_once_with("qemu:///system")
        assert conn.is_connected()

    @patch("libvirt.open")
    def test_connection_opens_with_custom_uri(self, mock_libvirt_open: Mock) -> None:
        """Connection accepts custom URI parameter."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        custom_uri = "qemu+ssh://remote/system"
        conn = LibvirtConnection(uri=custom_uri)
        conn.open()

        mock_libvirt_open.assert_called_once_with(custom_uri)

    @patch("libvirt.open")
    def test_connection_handles_failure(self, mock_libvirt_open: Mock) -> None:
        """Connection raises ConnectionError on failure.

        Verifies proper error handling and custom exception raising.
        """
        from agent_vm.core.connection import LibvirtConnection, ConnectionError

        # Setup mock to fail
        mock_libvirt_open.side_effect = Exception("Connection refused")

        # Execute and verify
        conn = LibvirtConnection()
        with pytest.raises(ConnectionError) as exc_info:
            conn.open()

        assert "Connection refused" in str(exc_info.value)

    @patch("libvirt.open")
    def test_connection_handles_libvirt_error(self, mock_libvirt_open: Mock) -> None:
        """Connection properly handles libvirt-specific errors."""
        from agent_vm.core.connection import LibvirtConnection, ConnectionError
        import libvirt

        # Create a mock libvirt error
        class MockLibvirtError(Exception):
            pass

        # Patch libvirt.libvirtError
        with patch("libvirt.libvirtError", MockLibvirtError):
            mock_libvirt_open.side_effect = MockLibvirtError("Failed to connect")

            conn = LibvirtConnection()
            with pytest.raises(ConnectionError):
                conn.open()

    @patch("libvirt.open")
    def test_connection_closes_gracefully(self, mock_libvirt_open: Mock) -> None:
        """Connection closes and cleans up resources."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()
        assert conn.is_connected()

        conn.close()

        mock_conn.close.assert_called_once()
        assert not conn.is_connected()

    @patch("libvirt.open")
    def test_connection_close_is_idempotent(self, mock_libvirt_open: Mock) -> None:
        """Closing an already closed connection is safe."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()
        conn.close()

        # Close again - should not raise error
        conn.close()

        # close() should only be called once on the underlying connection
        assert mock_conn.close.call_count == 1

    @patch("libvirt.open")
    def test_connection_context_manager_opens_and_closes(self, mock_libvirt_open: Mock) -> None:
        """Connection works as context manager (with statement)."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        with LibvirtConnection() as conn:
            assert conn.is_connected()
            mock_libvirt_open.assert_called_once()

        # After context exits, connection should be closed
        mock_conn.close.assert_called_once()

    @patch("libvirt.open")
    def test_connection_context_manager_closes_on_exception(self, mock_libvirt_open: Mock) -> None:
        """Connection closes even if exception occurs in context."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        with pytest.raises(ValueError):
            with LibvirtConnection() as conn:
                assert conn.is_connected()
                raise ValueError("Test error")

        # Connection should still be closed despite exception
        mock_conn.close.assert_called_once()

    @patch("libvirt.open")
    def test_connection_property_returns_connection(self, mock_libvirt_open: Mock) -> None:
        """Connection property returns underlying libvirt connection."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()

        # Access the connection property
        underlying = conn.connection
        assert underlying is mock_conn

    @patch("libvirt.open")
    def test_connection_property_raises_when_not_connected(self, mock_libvirt_open: Mock) -> None:
        """Connection property raises error when not connected."""
        from agent_vm.core.connection import LibvirtConnection, ConnectionError

        conn = LibvirtConnection()
        # Don't open connection

        with pytest.raises(ConnectionError, match="Not connected"):
            _ = conn.connection

    @patch("libvirt.open")
    def test_is_connected_returns_false_initially(self, mock_libvirt_open: Mock) -> None:
        """is_connected() returns False before opening."""
        from agent_vm.core.connection import LibvirtConnection

        conn = LibvirtConnection()
        assert not conn.is_connected()

    @patch("libvirt.open")
    def test_is_connected_checks_alive_status(self, mock_libvirt_open: Mock) -> None:
        """is_connected() uses isAlive() to verify connection health."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 0  # Dead connection
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()

        # Even though we opened, connection is not alive
        assert not conn.is_connected()
        mock_conn.isAlive.assert_called()

    @patch("libvirt.open")
    def test_multiple_open_calls_are_safe(self, mock_libvirt_open: Mock) -> None:
        """Opening an already open connection is idempotent."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()
        conn.open()  # Second open should be safe

        # Should only open once
        assert mock_libvirt_open.call_count == 1

    @patch("libvirt.open")
    def test_connection_logs_open_event(self, mock_libvirt_open: Mock) -> None:
        """Connection logs successful open event.

        This verifies structured logging is working.
        """
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        with patch("agent_vm.core.connection.logger") as mock_logger:
            conn = LibvirtConnection()
            conn.open()

            # Verify logging occurred
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert "libvirt_connection_opened" in str(call_args)

    @patch("libvirt.open")
    def test_connection_logs_close_event(self, mock_libvirt_open: Mock) -> None:
        """Connection logs close event."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        with patch("agent_vm.core.connection.logger") as mock_logger:
            conn = LibvirtConnection()
            conn.open()
            mock_logger.reset_mock()  # Clear open logs

            conn.close()

            # Verify close logging
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert "libvirt_connection_closed" in str(call_args)

    @patch("libvirt.open")
    def test_connection_logs_failure(self, mock_libvirt_open: Mock) -> None:
        """Connection logs error on failure."""
        from agent_vm.core.connection import LibvirtConnection, ConnectionError

        mock_libvirt_open.side_effect = Exception("Connection failed")

        with patch("agent_vm.core.connection.logger") as mock_logger:
            conn = LibvirtConnection()

            with pytest.raises(ConnectionError):
                conn.open()

            # Verify error logging
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args
            assert "libvirt_connection_failed" in str(call_args)


class TestConnectionErrorHandling:
    """Test error handling edge cases."""

    @patch("libvirt.open")
    def test_connection_handles_none_return(self, mock_libvirt_open: Mock) -> None:
        """Connection handles case where libvirt.open returns None."""
        from agent_vm.core.connection import LibvirtConnection, ConnectionError

        mock_libvirt_open.return_value = None

        conn = LibvirtConnection()
        # This should either handle None gracefully or raise ConnectionError
        # Implementation choice: let's require it to raise an error
        with pytest.raises(ConnectionError):
            conn.open()

    @patch("libvirt.open")
    def test_close_handles_connection_failure_gracefully(self, mock_libvirt_open: Mock) -> None:
        """Close handles case where connection.close() fails."""
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_conn.close.side_effect = Exception("Close failed")
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()

        # close() should handle the exception gracefully
        # It should still set internal state to None
        conn.close()

        assert not conn.is_connected()


class TestConnectionThreadSafety:
    """Test thread-safety considerations (design for future)."""

    @patch("libvirt.open")
    def test_connection_has_thread_safe_design(self, mock_libvirt_open: Mock) -> None:
        """Connection is designed with thread-safety in mind.

        Note: Full thread-safety testing requires concurrent execution.
        This test verifies the design supports thread-safety.
        """
        from agent_vm.core.connection import LibvirtConnection

        mock_conn = Mock()
        mock_conn.isAlive.return_value = 1
        mock_libvirt_open.return_value = mock_conn

        # Each connection should be independent
        conn1 = LibvirtConnection()
        conn2 = LibvirtConnection()

        conn1.open()
        conn2.open()

        # Both should be independent
        assert conn1.is_connected()
        assert conn2.is_connected()

        conn1.close()
        # conn2 should still be connected
        assert not conn1.is_connected()
        assert conn2.is_connected()

        conn2.close()
