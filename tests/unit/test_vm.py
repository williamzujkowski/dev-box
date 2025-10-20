"""Test VM domain abstraction layer.

This test suite validates the VM class following TDD principles.
Tests are written FIRST (RED phase) before implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Any


class TestVMInitialization:
    """Test VM object initialization and properties."""

    def test_vm_initializes_with_domain(self, mock_domain: Mock) -> None:
        """VM wraps libvirt domain correctly.

        RED: This test will fail until VM class is implemented.
        """
        from agent_vm.core.vm import VM

        vm = VM(mock_domain)

        assert vm.name == "test-vm"
        assert vm.uuid == "test-uuid-123"
        assert vm._domain is mock_domain

    def test_vm_name_property(self, mock_domain: Mock) -> None:
        """VM name property calls domain.name()."""
        from agent_vm.core.vm import VM

        vm = VM(mock_domain)
        name = vm.name

        mock_domain.name.assert_called()
        assert name == "test-vm"

    def test_vm_uuid_property(self, mock_domain: Mock) -> None:
        """VM uuid property calls domain.UUIDString()."""
        from agent_vm.core.vm import VM

        vm = VM(mock_domain)
        uuid = vm.uuid

        mock_domain.UUIDString.assert_called()
        assert uuid == "test-uuid-123"

    def test_vm_domain_property_access(self, mock_domain: Mock) -> None:
        """VM provides access to underlying domain (when needed)."""
        from agent_vm.core.vm import VM

        vm = VM(mock_domain)
        assert vm._domain is mock_domain


class TestVMStateManagement:
    """Test VM state retrieval and monitoring."""

    def test_vm_get_state_running(self, mock_domain: Mock) -> None:
        """get_state() returns RUNNING for running VM."""
        from agent_vm.core.vm import VM, VMState

        mock_domain.state.return_value = [1, 1]  # VIR_DOMAIN_RUNNING

        vm = VM(mock_domain)
        state = vm.get_state()

        assert state == VMState.RUNNING
        mock_domain.state.assert_called_once()

    def test_vm_get_state_shutoff(self, mock_domain: Mock) -> None:
        """get_state() returns SHUTOFF for stopped VM."""
        from agent_vm.core.vm import VM, VMState

        mock_domain.state.return_value = [5, 0]  # VIR_DOMAIN_SHUTOFF

        vm = VM(mock_domain)
        state = vm.get_state()

        assert state == VMState.SHUTOFF

    def test_vm_get_state_paused(self, mock_domain: Mock) -> None:
        """get_state() returns PAUSED for paused VM."""
        from agent_vm.core.vm import VM, VMState

        mock_domain.state.return_value = [3, 0]  # VIR_DOMAIN_PAUSED

        vm = VM(mock_domain)
        state = vm.get_state()

        assert state == VMState.PAUSED

    def test_vm_get_state_crashed(self, mock_domain: Mock) -> None:
        """get_state() returns CRASHED for crashed VM."""
        from agent_vm.core.vm import VM, VMState

        mock_domain.state.return_value = [6, 0]  # VIR_DOMAIN_CRASHED

        vm = VM(mock_domain)
        state = vm.get_state()

        assert state == VMState.CRASHED

    def test_vm_get_state_unknown(self, mock_domain: Mock) -> None:
        """get_state() returns UNKNOWN for unrecognized states."""
        from agent_vm.core.vm import VM, VMState

        mock_domain.state.return_value = [99, 0]  # Invalid state code

        vm = VM(mock_domain)
        state = vm.get_state()

        assert state == VMState.UNKNOWN


class TestVMLifecycleStart:
    """Test VM start operations."""

    def test_vm_start_calls_domain_create(self, mock_domain: Mock) -> None:
        """Starting VM calls domain.create()."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = False

        vm = VM(mock_domain)
        vm.start()

        mock_domain.create.assert_called_once()

    def test_vm_start_skips_if_already_running(self, mock_domain: Mock) -> None:
        """Starting running VM is idempotent (does nothing)."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = True

        vm = VM(mock_domain)
        vm.start()

        mock_domain.create.assert_not_called()

    def test_vm_start_raises_on_failure(self, mock_domain: Mock) -> None:
        """Start raises VMError on libvirt failure."""
        from agent_vm.core.vm import VM, VMError
        import libvirt

        mock_domain.isActive.return_value = False

        # Mock libvirt error
        class MockLibvirtError(Exception):
            pass

        with patch("libvirt.libvirtError", MockLibvirtError):
            mock_domain.create.side_effect = MockLibvirtError("Start failed")

            vm = VM(mock_domain)
            with pytest.raises(VMError, match="Start failed"):
                vm.start()

    def test_vm_start_logs_event(self, mock_domain: Mock) -> None:
        """Start operation is logged."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = False

        with patch("agent_vm.core.vm.logger") as mock_logger:
            vm = VM(mock_domain)
            vm.start()

            # Verify logging occurred
            assert mock_logger.bind.called or mock_logger.info.called


class TestVMLifecycleStop:
    """Test VM stop operations."""

    def test_vm_stop_destroys_domain(self, mock_domain: Mock) -> None:
        """Stopping VM calls domain.destroy() by default."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = True

        vm = VM(mock_domain)
        vm.stop()

        mock_domain.destroy.assert_called_once()

    def test_vm_stop_graceful_shutdown(self, mock_domain: Mock) -> None:
        """Graceful stop calls domain.shutdown() instead of destroy()."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = True

        vm = VM(mock_domain)
        vm.stop(graceful=True)

        mock_domain.shutdown.assert_called_once()
        mock_domain.destroy.assert_not_called()

    def test_vm_stop_skips_if_not_running(self, mock_domain: Mock) -> None:
        """Stopping already stopped VM is idempotent."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = False

        vm = VM(mock_domain)
        vm.stop()

        mock_domain.destroy.assert_not_called()
        mock_domain.shutdown.assert_not_called()

    def test_vm_stop_raises_on_failure(self, mock_domain: Mock) -> None:
        """Stop raises VMError on libvirt failure."""
        from agent_vm.core.vm import VM, VMError

        mock_domain.isActive.return_value = True

        class MockLibvirtError(Exception):
            pass

        with patch("libvirt.libvirtError", MockLibvirtError):
            mock_domain.destroy.side_effect = MockLibvirtError("Stop failed")

            vm = VM(mock_domain)
            with pytest.raises(VMError, match="Stop failed"):
                vm.stop()

    def test_vm_stop_logs_event(self, mock_domain: Mock) -> None:
        """Stop operation is logged."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = True

        with patch("agent_vm.core.vm.logger") as mock_logger:
            vm = VM(mock_domain)
            vm.stop()

            # Verify logging occurred
            assert mock_logger.bind.called or mock_logger.info.called


class TestVMAsyncOperations:
    """Test async VM operations (wait_for_state)."""

    @pytest.mark.asyncio
    async def test_vm_wait_for_state_reaches_target(self, mock_domain: Mock) -> None:
        """wait_for_state() returns when target state is reached."""
        from agent_vm.core.vm import VM, VMState

        # Simulate state transition: SHUTDOWN -> RUNNING
        mock_domain.state.side_effect = [
            [4, 0],  # First check: SHUTDOWN
            [1, 1],  # Second check: RUNNING
        ]

        vm = VM(mock_domain)
        await vm.wait_for_state(VMState.RUNNING, timeout=5)

        # Should have checked state twice
        assert mock_domain.state.call_count == 2

    @pytest.mark.asyncio
    async def test_vm_wait_for_state_already_at_target(self, mock_domain: Mock) -> None:
        """wait_for_state() returns immediately if already at target."""
        from agent_vm.core.vm import VM, VMState

        mock_domain.state.return_value = [1, 1]  # Already RUNNING

        vm = VM(mock_domain)
        await vm.wait_for_state(VMState.RUNNING, timeout=5)

        # Should check state once and return immediately
        assert mock_domain.state.call_count == 1

    @pytest.mark.asyncio
    async def test_vm_wait_for_state_timeout(self, mock_domain: Mock) -> None:
        """wait_for_state() raises VMError on timeout."""
        from agent_vm.core.vm import VM, VMState, VMError

        mock_domain.state.return_value = [5, 0]  # Always SHUTOFF

        vm = VM(mock_domain)
        with pytest.raises(VMError, match="Timeout"):
            await vm.wait_for_state(VMState.RUNNING, timeout=0.1)

    @pytest.mark.asyncio
    async def test_vm_wait_for_state_custom_poll_interval(self, mock_domain: Mock) -> None:
        """wait_for_state() respects custom poll interval."""
        from agent_vm.core.vm import VM, VMState

        call_count = 0

        def state_side_effect(*args: Any) -> list[int]:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                return [1, 1]  # RUNNING after 3 calls
            return [5, 0]  # SHUTOFF

        mock_domain.state.side_effect = state_side_effect

        vm = VM(mock_domain)
        start_time = asyncio.get_event_loop().time()
        await vm.wait_for_state(VMState.RUNNING, timeout=5, poll_interval=0.1)
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have taken at least 2 poll intervals (3 checks - 1)
        assert elapsed >= 0.2
        assert mock_domain.state.call_count == 3

    @pytest.mark.asyncio
    async def test_vm_wait_for_state_logs_completion(self, mock_domain: Mock) -> None:
        """wait_for_state() logs when target state is reached."""
        from agent_vm.core.vm import VM, VMState

        mock_domain.state.return_value = [1, 1]  # RUNNING

        with patch("agent_vm.core.vm.logger") as mock_logger:
            vm = VM(mock_domain)
            await vm.wait_for_state(VMState.RUNNING)

            # Should log state reached
            assert mock_logger.bind.called or mock_logger.info.called


class TestVMStateEnum:
    """Test VMState enumeration."""

    def test_vm_state_enum_values(self) -> None:
        """VMState enum has all required states."""
        from agent_vm.core.vm import VMState

        required_states = [
            "RUNNING",
            "PAUSED",
            "SHUTDOWN",
            "SHUTOFF",
            "CRASHED",
            "UNKNOWN",
        ]

        for state_name in required_states:
            assert hasattr(VMState, state_name), f"VMState.{state_name} missing"

    def test_vm_state_values_are_strings(self) -> None:
        """VMState values are human-readable strings."""
        from agent_vm.core.vm import VMState

        assert isinstance(VMState.RUNNING.value, str)
        assert VMState.RUNNING.value == "running"


class TestVMErrorHandling:
    """Test VM error handling and edge cases."""

    def test_vm_error_is_exception(self) -> None:
        """VMError is a proper exception class."""
        from agent_vm.core.vm import VMError

        assert issubclass(VMError, Exception)

        # Should be able to raise and catch
        with pytest.raises(VMError):
            raise VMError("Test error")

    def test_vm_handles_domain_method_failure(self, mock_domain: Mock) -> None:
        """VM handles case where domain methods fail."""
        from agent_vm.core.vm import VM, VMError

        mock_domain.name.side_effect = Exception("Domain method failed")

        # Creating VM is fine, accessing name should handle error
        vm = VM(mock_domain)

        # This might raise or return a default value depending on implementation
        # For safety-critical operations, we want errors to be explicit
        with pytest.raises(Exception):
            _ = vm.name


class TestVMLogging:
    """Test VM logging and observability."""

    def test_vm_creates_bound_logger(self, mock_domain: Mock) -> None:
        """VM creates logger bound to VM name and UUID."""
        from agent_vm.core.vm import VM

        with patch("agent_vm.core.vm.logger") as mock_logger:
            bound_logger = Mock()
            mock_logger.bind.return_value = bound_logger

            vm = VM(mock_domain)

            # Verify logger was bound with VM context
            mock_logger.bind.assert_called_once()
            call_kwargs = mock_logger.bind.call_args[1]
            assert "vm_name" in call_kwargs
            assert "vm_uuid" in call_kwargs

    def test_vm_logs_lifecycle_events(self, mock_domain: Mock) -> None:
        """VM logs all lifecycle events with structured context."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = False

        with patch("agent_vm.core.vm.logger") as mock_logger:
            bound_logger = Mock()
            mock_logger.bind.return_value = bound_logger

            vm = VM(mock_domain)
            vm.start()

            # Verify info logging for start event
            assert bound_logger.info.called


class TestVMIntegrationScenarios:
    """Test realistic VM usage scenarios."""

    @pytest.mark.asyncio
    async def test_vm_typical_lifecycle_sequence(self, mock_domain: Mock) -> None:
        """Test typical VM lifecycle: start -> wait -> stop."""
        from agent_vm.core.vm import VM, VMState

        # Setup state transitions
        mock_domain.isActive.side_effect = [False, True, True]  # Start, running, stop
        mock_domain.state.return_value = [1, 1]  # RUNNING

        vm = VM(mock_domain)

        # Start VM
        vm.start()
        assert mock_domain.create.called

        # Wait for running state
        await vm.wait_for_state(VMState.RUNNING, timeout=5)

        # Stop VM
        vm.stop()
        assert mock_domain.destroy.called

    def test_vm_restart_scenario(self, mock_domain: Mock) -> None:
        """Test VM restart (stop -> start)."""
        from agent_vm.core.vm import VM

        vm = VM(mock_domain)

        # Stop
        mock_domain.isActive.return_value = True
        vm.stop()
        assert mock_domain.destroy.called

        # Start
        mock_domain.isActive.return_value = False
        vm.start()
        assert mock_domain.create.called

    def test_vm_force_stop_after_graceful_failure(self, mock_domain: Mock) -> None:
        """Test force stop after graceful shutdown fails."""
        from agent_vm.core.vm import VM

        mock_domain.isActive.return_value = True

        vm = VM(mock_domain)

        # Try graceful shutdown
        vm.stop(graceful=True)
        assert mock_domain.shutdown.called

        # Force stop
        mock_domain.shutdown.reset_mock()
        vm.stop(graceful=False)
        assert mock_domain.destroy.called


class TestVMStateMapping:
    """Test libvirt state code to VMState mapping."""

    def test_all_libvirt_states_mapped(self, mock_domain: Mock) -> None:
        """All libvirt domain states have corresponding VMState."""
        from agent_vm.core.vm import VM, VMState

        # Test all standard libvirt states
        state_mappings = [
            (0, VMState.UNKNOWN),  # VIR_DOMAIN_NOSTATE
            (1, VMState.RUNNING),  # VIR_DOMAIN_RUNNING
            (2, VMState.RUNNING),  # VIR_DOMAIN_BLOCKED (treat as running)
            (3, VMState.PAUSED),  # VIR_DOMAIN_PAUSED
            (4, VMState.SHUTDOWN),  # VIR_DOMAIN_SHUTDOWN
            (5, VMState.SHUTOFF),  # VIR_DOMAIN_SHUTOFF
            (6, VMState.CRASHED),  # VIR_DOMAIN_CRASHED
            (7, VMState.PAUSED),  # VIR_DOMAIN_PMSUSPENDED (treat as paused)
        ]

        vm = VM(mock_domain)

        for libvirt_code, expected_state in state_mappings:
            mock_domain.state.return_value = [libvirt_code, 0]
            actual_state = vm.get_state()
            assert (
                actual_state == expected_state
            ), f"State code {libvirt_code} should map to {expected_state}"
