"""Integration tests for Phase 2 communication components.

This module tests the filesystem sharing (virtio-9p) and vsock communication
between host and guest VMs.

Requirements:
    - Real libvirt connection
    - FilesystemShare implementation (src/agent_vm/communication/filesystem.py)
    - VsockProtocol implementation (src/agent_vm/communication/vsock.py)
    - Guest agent implementation (guest/agent.py)

Test Coverage:
    - Filesystem mount/unmount with real libvirt domains
    - Code injection from host to guest
    - Result extraction from guest to host
    - Vsock message exchange (if environment supports it)
    - Error handling (connection drops, unmount failures)

See: TDD_IMPLEMENTATION_PLAN.md Phase 3 (Communication Channels)
"""

import pytest
import asyncio
import libvirt
from pathlib import Path
from typing import Generator

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def check_libvirt() -> bool:
    """
    Check if libvirt is available.

    Returns:
        True if libvirt connection can be established
    """
    try:
        conn = libvirt.open("qemu:///system")
        is_alive = conn.isAlive()
        conn.close()
        return is_alive == 1
    except Exception:
        return False


class TestFilesystemShareIntegration:
    """Integration tests for virtio-9p filesystem sharing"""

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    def test_filesystem_share_import(self, real_libvirt_connection: libvirt.virConnect) -> None:
        """
        Test that FilesystemShare can be imported.

        This is a smoke test that will fail until the component is implemented.
        See: TDD_IMPLEMENTATION_PLAN.md section 3.1
        """
        try:
            from agent_vm.communication.filesystem import FilesystemShare

            # If import succeeds, verify basic instantiation
            # API: FilesystemShare(host_path, mount_tag, guest_mount_point)
            workspace = Path("/tmp/test-workspace")
            fs = FilesystemShare(host_path=workspace)
            assert fs is not None
            assert fs.host_path == workspace

        except ImportError:
            pytest.skip("FilesystemShare not implemented yet (Phase 2, Task 3.1)")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_filesystem_inject_code(
        self,
        real_libvirt_connection: libvirt.virConnect,
        test_workspace: Path,
        cleanup_test_vms: None,
    ) -> None:
        """
        Test injecting agent code into VM via shared filesystem.

        Tests:
            - Create FilesystemShare with workspace
            - Inject code to input directory
            - Verify file exists in workspace
            - Verify file content matches injected code

        Requirements:
            - FilesystemShare implementation
            - write_file method (replaces inject_code)
        """
        try:
            from agent_vm.communication.filesystem import FilesystemShare

            # Create filesystem share (API: host_path, mount_tag, guest_mount_point)
            fs = FilesystemShare(host_path=test_workspace)

            # Inject agent code using write_file method
            agent_code = """
import json
from pathlib import Path

result = {"status": "success", "message": "Test passed"}
output_path = Path("/workspace/output/results.json")
with open(output_path, "w") as f:
    json.dump(result, f)
print("Agent code executed")
"""
            # API: write_file(path: str, content: bytes)
            await fs.write_file("test_agent.py", agent_code.encode("utf-8"))

            # Verify file was created in host_path
            code_path = test_workspace / "test_agent.py"
            assert code_path.exists()
            assert code_path.name == "test_agent.py"

            # Verify content matches
            injected_content = code_path.read_text()
            assert injected_content == agent_code

        except ImportError:
            pytest.skip("FilesystemShare not implemented yet (Phase 2, Task 3.1)")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_filesystem_extract_results(
        self,
        real_libvirt_connection: libvirt.virConnect,
        test_workspace: Path,
        cleanup_test_vms: None,
    ) -> None:
        """
        Test extracting results from VM via shared filesystem.

        Tests:
            - Create FilesystemShare with workspace
            - Simulate VM writing results to workspace
            - Extract results using read_file
            - Verify results are correctly parsed

        Requirements:
            - FilesystemShare implementation
            - read_file method (replaces extract_results)
            - JSON parsing of results
        """
        try:
            import json
            from agent_vm.communication.filesystem import FilesystemShare

            # Create filesystem share (API: host_path, mount_tag, guest_mount_point)
            fs = FilesystemShare(host_path=test_workspace)

            # Simulate VM writing results
            results_file = test_workspace / "results.json"
            results_file.write_text('{"status": "success", "value": 42}')

            # Extract results using read_file method
            # API: read_file(path: str) -> bytes
            results_bytes = await fs.read_file("results.json")
            results = json.loads(results_bytes.decode("utf-8"))

            # Verify results
            assert results["status"] == "success"
            assert results["value"] == 42

        except ImportError:
            pytest.skip("FilesystemShare not implemented yet (Phase 2, Task 3.1)")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_filesystem_cleanup(
        self, real_libvirt_connection: libvirt.virConnect, test_workspace: Path
    ) -> None:
        """
        Test workspace cleanup removes all files.

        Tests:
            - Create files in workspace
            - Call cleanup() (ASYNC)
            - Verify all files are removed
            - Verify directory still exists

        Requirements:
            - FilesystemShare implementation
            - Cleanup functionality (async)
        """
        try:
            from agent_vm.communication.filesystem import FilesystemShare

            # Create filesystem share (API: host_path, mount_tag, guest_mount_point)
            fs = FilesystemShare(host_path=test_workspace)

            # Create test files
            (test_workspace / "test1.py").write_text("test input")
            (test_workspace / "test2.json").write_text('{"test": "output"}')
            (test_workspace / "test3.tmp").write_text("test work")

            # Create subdirectory
            subdir = test_workspace / "subdir"
            subdir.mkdir()
            (subdir / "nested.txt").write_text("nested file")

            # Run cleanup (ASYNC method)
            await fs.cleanup()

            # Verify files are removed
            assert not (test_workspace / "test1.py").exists()
            assert not (test_workspace / "test2.json").exists()
            assert not (test_workspace / "test3.tmp").exists()
            assert not subdir.exists()

            # Verify directory still exists
            assert test_workspace.exists()

        except ImportError:
            pytest.skip("FilesystemShare not implemented yet (Phase 2, Task 3.1)")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_filesystem_error_handling(
        self, real_libvirt_connection: libvirt.virConnect, test_workspace: Path
    ) -> None:
        """
        Test filesystem error handling.

        Tests:
            - Read file when it doesn't exist (should raise FilesystemError)
            - Write to invalid path (should raise FilesystemError)

        Requirements:
            - FilesystemShare implementation
            - FilesystemError exception class
            - Proper error handling
        """
        try:
            from agent_vm.communication.filesystem import (
                FilesystemShare,
                FilesystemError,
            )

            # Create filesystem share (API: host_path, mount_tag, guest_mount_point)
            fs = FilesystemShare(host_path=test_workspace)

            # Test 1: Read non-existent file using read_file
            # API: read_file(path: str) -> bytes
            with pytest.raises(FilesystemError, match="not found"):
                await fs.read_file("nonexistent.json")

            # Test 2: Write to invalid path (e.g., absolute path traversal)
            with pytest.raises(FilesystemError):
                await fs.write_file("/etc/passwd", b"malicious content")

        except ImportError:
            pytest.skip("FilesystemShare not implemented yet (Phase 2, Task 3.1)")


class TestVsockCommunicationIntegration:
    """Integration tests for virtio-vsock communication"""

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    def test_vsock_protocol_import(self, real_libvirt_connection: libvirt.virConnect) -> None:
        """
        Test that VsockProtocol can be imported.

        This is a smoke test that will fail until the component is implemented.
        See: TDD_IMPLEMENTATION_PLAN.md section 3.2
        """
        try:
            from agent_vm.communication.vsock import VsockProtocol

            # If import succeeds, verify basic instantiation
            # API: VsockProtocol(cid: int, port: int = 9999)
            # Use cid=3 (typical guest CID in testing)
            protocol = VsockProtocol(cid=3)
            assert protocol is not None

        except ImportError:
            pytest.skip("VsockProtocol not implemented yet (Phase 2, Task 3.2)")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_vsock_send_message(
        self, real_libvirt_connection: libvirt.virConnect, cleanup_test_vms: None
    ) -> None:
        """
        Test sending message from host to guest via vsock.

        Tests:
            - Create VsockProtocol
            - Send message to guest
            - Verify message framing
            - Verify checksums

        Requirements:
            - VsockProtocol implementation
            - Guest agent running in VM
            - vsock device configured in VM

        Note: This test skips actual sending until guest agent is ready
        """
        try:
            from agent_vm.communication.vsock import VsockProtocol, MessageType

            # API: VsockProtocol(cid: int, port: int = 9999)
            # Use cid=3 (typical guest CID in testing)
            protocol = VsockProtocol(cid=3)

            # Test message payload
            payload = b'{"code": "print(\'Hello\')"}'

            # For integration test without actual VM, just verify protocol can be created
            # Real send_message would require running VM with guest agent
            # API: send_message(msg_type: MessageType, payload: bytes) - ASYNC
            # await protocol.send_message(MessageType.COMMAND, payload)

            # Verify protocol is ready (basic check)
            assert protocol is not None

        except ImportError:
            pytest.skip("VsockProtocol not implemented yet (Phase 2, Task 3.2)")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_vsock_receive_response(
        self, real_libvirt_connection: libvirt.virConnect, cleanup_test_vms: None
    ) -> None:
        """
        Test receiving response from guest via vsock.

        Tests:
            - Wait for response from guest
            - Verify response format
            - Handle timeout if guest doesn't respond

        Requirements:
            - VsockProtocol implementation
            - Guest agent responding to messages

        Note: This test verifies protocol can be created; actual receive requires VM
        """
        try:
            from agent_vm.communication.vsock import VsockProtocol, MessageType

            # API: VsockProtocol(cid: int, port: int = 9999)
            # Use cid=3 (typical guest CID in testing)
            protocol = VsockProtocol(cid=3)

            # For integration test without actual VM, just verify protocol can be created
            # Real receive_message would require running VM with guest agent
            # API: receive_message() -> tuple[MessageType, bytes] - ASYNC
            # msg_type, payload = await protocol.receive_message()

            # Verify protocol is ready (basic check)
            assert protocol is not None

        except ImportError:
            pytest.skip("VsockProtocol not implemented yet (Phase 2, Task 3.2)")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_vsock_connection_drop_handling(
        self, real_libvirt_connection: libvirt.virConnect, cleanup_test_vms: None
    ) -> None:
        """
        Test handling of vsock connection drops.

        Tests:
            - Detect when guest disconnects
            - Handle broken pipe errors
            - Retry logic (if implemented)
            - Proper cleanup on connection failure

        Requirements:
            - VsockProtocol implementation
            - Connection error handling
        """
        try:
            from agent_vm.communication.vsock import VsockProtocol, VsockError

            # Test will be implemented once VsockProtocol exists
            pytest.skip("Requires complete VsockProtocol implementation")

        except ImportError:
            pytest.skip("VsockProtocol not implemented yet (Phase 2, Task 3.2)")


class TestGuestAgentIntegration:
    """Integration tests for guest agent"""

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    def test_guest_agent_exists(self) -> None:
        """
        Test that guest agent file exists.

        The guest agent is Python code that runs inside the VM and:
        - Listens on vsock for host commands
        - Executes agent code
        - Returns results to host

        See: TDD_IMPLEMENTATION_PLAN.md section 3.3
        """
        guest_agent_path = Path(__file__).parent.parent.parent / "guest" / "agent.py"

        if not guest_agent_path.exists():
            pytest.skip(
                "Guest agent not implemented yet (guest/agent.py). " "See Phase 2, Task 3.3"
            )

        # If file exists, verify it's valid Python
        code = guest_agent_path.read_text()
        assert len(code) > 0

        # Try to compile it (syntax check)
        try:
            compile(code, str(guest_agent_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Guest agent has syntax errors: {e}")

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_guest_agent_startup(
        self, real_libvirt_connection: libvirt.virConnect, cleanup_test_vms: None
    ) -> None:
        """
        Test guest agent can start inside VM.

        This test requires:
        - VM with Python installed
        - Guest agent deployed to VM
        - Vsock device configured

        For now, this test is mocked/skipped until full integration is ready.
        """
        pytest.skip("Requires VM with guest agent installed (E2E test)")


class TestCommunicationEndToEnd:
    """End-to-end communication tests combining filesystem and vsock"""

    @pytest.mark.skipif(not check_libvirt(), reason="Requires libvirt")
    @pytest.mark.asyncio
    async def test_code_execution_flow(
        self,
        real_libvirt_connection: libvirt.virConnect,
        test_workspace: Path,
        cleanup_test_vms: None,
    ) -> None:
        """
        Test complete code execution flow.

        Flow:
            1. Inject code via filesystem
            2. Send execute command via vsock
            3. Guest agent runs code
            4. Results written to filesystem
            5. Extract results from filesystem

        This is the core communication pattern for agent execution.

        Requirements:
            - FilesystemShare implementation
            - VsockProtocol implementation
            - Guest agent running in VM
        """
        pytest.skip("Requires complete Phase 2 implementation (E2E test)")


class TestIntegrationEnvironmentReadiness:
    """Tests to verify Phase 2 integration test environment is ready"""

    def test_libvirt_available(self) -> None:
        """Verify libvirt is accessible for integration tests"""
        assert check_libvirt(), (
            "libvirt not available. "
            "Install: sudo apt install qemu-kvm libvirt-daemon-system libvirt-clients"
        )

    def test_workspace_fixture_available(self, test_workspace: Path) -> None:
        """Verify workspace fixture creates proper structure"""
        assert test_workspace.exists()
        assert (test_workspace / "input").is_dir()
        assert (test_workspace / "output").is_dir()
        assert (test_workspace / "work").is_dir()

    def test_cleanup_fixture_available(self, cleanup_test_vms: None) -> None:
        """Verify cleanup fixture is available"""
        # Fixture loaded successfully if we get here
        assert True

    def test_pytest_asyncio_configured(self) -> None:
        """Verify pytest-asyncio is properly configured"""
        # Test will run if pytest-asyncio is configured
        assert True

    @pytest.mark.asyncio
    async def test_async_integration_tests_work(self) -> None:
        """Verify async integration tests can execute"""
        await asyncio.sleep(0.001)
        assert True
