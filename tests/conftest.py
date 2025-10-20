"""Shared pytest fixtures for agent-vm tests.

This module provides reusable fixtures for testing VM management components.
Fixtures are organized by scope and functionality.
"""

import pytest
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, MagicMock
import tempfile
import shutil


# ============================================================================
# Connection Fixtures
# ============================================================================


@pytest.fixture
def mock_libvirt_connection() -> Mock:
    """Mock libvirt connection object.

    Returns:
        Mock connection with standard methods configured
    """
    conn = Mock()
    conn.is_connected.return_value = True
    conn.isAlive.return_value = 1
    conn.getURI.return_value = "qemu:///system"
    conn.getVersion.return_value = 9000000  # Version 9.0.0
    conn.close.return_value = None
    return conn


@pytest.fixture
def mock_libvirt_open(monkeypatch) -> Mock:
    """Mock libvirt.open() for connection tests.

    Returns:
        Mock open function
    """
    mock_open = Mock()
    mock_conn = Mock()
    mock_conn.isAlive.return_value = 1
    mock_open.return_value = mock_conn

    # This will be used in connection tests
    return mock_open


# ============================================================================
# Domain (VM) Fixtures
# ============================================================================


@pytest.fixture
def mock_domain() -> Mock:
    """Mock libvirt domain (VM) object.

    Returns:
        Mock domain with standard VM operations configured
    """
    domain = Mock()

    # Basic properties
    domain.name.return_value = "test-vm"
    domain.UUIDString.return_value = "test-uuid-123"
    domain.ID.return_value = 1

    # State management
    domain.isActive.return_value = False
    domain.state.return_value = [5, 0]  # VIR_DOMAIN_SHUTOFF

    # Lifecycle operations
    domain.create.return_value = 0
    domain.destroy.return_value = 0
    domain.shutdown.return_value = 0
    domain.reboot.return_value = 0

    # Snapshot operations
    domain.snapshotCreateXML.return_value = Mock()
    domain.listAllSnapshots.return_value = []
    domain.revertToSnapshot.return_value = 0

    # Info
    domain.info.return_value = [
        1,  # state: running
        2048,  # max memory (MiB)
        2048,  # memory (MiB)
        2,  # num CPUs
        0,  # CPU time
    ]

    # XML definition
    domain.XMLDesc.return_value = """
    <domain type='kvm'>
      <name>test-vm</name>
      <uuid>test-uuid-123</uuid>
      <memory unit='MiB'>2048</memory>
      <vcpu>2</vcpu>
    </domain>
    """

    return domain


@pytest.fixture
def mock_vm(mock_domain: Mock) -> Mock:
    """Mock VM instance wrapping a domain.

    This fixture requires the VM class to be implemented.
    For RED phase, this will fail until VM class exists.

    Args:
        mock_domain: Mock domain fixture

    Returns:
        Mock VM instance
    """
    try:
        from agent_vm.core.vm import VM

        return VM(mock_domain)
    except ImportError:
        # RED phase - VM class doesn't exist yet
        mock_vm = Mock()
        mock_vm.name = "test-vm"
        mock_vm.uuid = "test-uuid-123"
        mock_vm._domain = mock_domain
        return mock_vm


@pytest.fixture
def mock_running_domain() -> Mock:
    """Mock domain in running state.

    Returns:
        Mock domain configured as running
    """
    domain = Mock()
    domain.name.return_value = "running-vm"
    domain.UUIDString.return_value = "running-uuid-456"
    domain.isActive.return_value = True
    domain.state.return_value = [1, 1]  # VIR_DOMAIN_RUNNING
    domain.destroy.return_value = 0
    domain.shutdown.return_value = 0
    return domain


# ============================================================================
# Snapshot Fixtures
# ============================================================================


@pytest.fixture
def mock_snapshot() -> Mock:
    """Mock libvirt snapshot object.

    Returns:
        Mock snapshot with standard operations
    """
    snapshot = Mock()
    snapshot.getName.return_value = "test-snapshot"
    snapshot.getXMLDesc.return_value = """
    <domainsnapshot>
      <name>test-snapshot</name>
      <description>Test snapshot</description>
    </domainsnapshot>
    """
    snapshot.delete.return_value = 0
    return snapshot


# ============================================================================
# Filesystem Fixtures
# ============================================================================


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create temporary workspace directory.

    Yields:
        Path to temporary workspace directory

    Cleanup:
        Removes workspace after test
    """
    workspace = Path(tempfile.mkdtemp(prefix="agent_vm_test_"))
    try:
        yield workspace
    finally:
        if workspace.exists():
            shutil.rmtree(workspace)


@pytest.fixture
def workspace_with_structure(temp_workspace: Path) -> Path:
    """Create workspace with standard directory structure.

    Args:
        temp_workspace: Base temporary workspace

    Returns:
        Path to workspace with input/output/work directories
    """
    (temp_workspace / "input").mkdir(parents=True, exist_ok=True)
    (temp_workspace / "output").mkdir(parents=True, exist_ok=True)
    (temp_workspace / "work").mkdir(parents=True, exist_ok=True)
    return temp_workspace


# ============================================================================
# Template Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def sample_vm_xml() -> str:
    """Sample VM XML definition for testing.

    Returns:
        Valid libvirt domain XML string
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<domain type='kvm'>
  <name>test-agent-vm</name>
  <uuid>12345678-1234-1234-1234-123456789abc</uuid>
  <memory unit='MiB'>2048</memory>
  <vcpu placement='static'>2</vcpu>
  <os>
    <type arch='x86_64' machine='pc-q35'>hvm</type>
    <boot dev='hd'/>
  </os>
  <cpu mode='host-passthrough'/>
  <features>
    <acpi/>
    <apic/>
  </features>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='writeback'/>
      <source file='/var/lib/libvirt/images/test.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <source network='agent-nat-filtered'/>
      <model type='virtio'/>
      <filterref filter='agent-network-filter'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
  </devices>
</domain>
"""


@pytest.fixture
def minimal_vm_xml() -> str:
    """Minimal VM XML for basic testing.

    Returns:
        Minimal valid libvirt domain XML
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<domain type='kvm'>
  <name>minimal-vm</name>
  <memory unit='MiB'>1024</memory>
  <vcpu>1</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
  </os>
  <devices>
    <disk type='file' device='disk'>
      <source file='/var/lib/libvirt/images/minimal.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
  </devices>
</domain>
"""


# ============================================================================
# Execution Fixtures
# ============================================================================


@pytest.fixture
def sample_agent_code() -> str:
    """Sample agent code for execution testing.

    Returns:
        Python code string for testing agent execution
    """
    return """
import json
import sys
from pathlib import Path

# Agent logic
result = {
    "status": "success",
    "message": "Agent executed successfully",
    "data": {"test": "passed"}
}

# Write results
output_path = Path("/workspace/output/results.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)

print("Agent completed successfully")
"""


@pytest.fixture
def failing_agent_code() -> str:
    """Agent code that raises an error.

    Returns:
        Python code that will fail during execution
    """
    return """
raise ValueError("Intentional test error")
"""


@pytest.fixture
def timeout_agent_code() -> str:
    """Agent code that runs indefinitely.

    Returns:
        Python code that will timeout
    """
    return """
import time
while True:
    time.sleep(1)
"""


# ============================================================================
# Pool Fixtures
# ============================================================================


@pytest.fixture
def pooled_vm_mock() -> Mock:
    """Create mock VM for PooledVM.

    Returns:
        PooledVM instance with mock VM
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from agent_vm.execution.pool import PooledVM
    from agent_vm.core.vm import VM

    mock_vm = Mock(spec=VM)
    mock_vm.name = "test-pooled-vm"
    mock_vm.uuid = "test-pooled-uuid"

    nist_et = ZoneInfo("America/New_York")
    return PooledVM(
        vm=mock_vm,
        created_at=datetime.now(nist_et),
        golden_snapshot="test-golden"
    )


# ============================================================================
# Mock Libvirt Module (for unit tests without libvirt)
# ============================================================================


@pytest.fixture
def mock_libvirt_module(monkeypatch):
    """Mock the entire libvirt module for unit tests.

    This allows testing without libvirt installed.
    """
    mock_libvirt = Mock()

    # Mock libvirt exceptions
    class LibvirtError(Exception):
        pass

    mock_libvirt.libvirtError = LibvirtError

    # Mock libvirt.open
    mock_conn = Mock()
    mock_conn.isAlive.return_value = 1
    mock_libvirt.open.return_value = mock_conn

    # Mock state constants
    mock_libvirt.VIR_DOMAIN_NOSTATE = 0
    mock_libvirt.VIR_DOMAIN_RUNNING = 1
    mock_libvirt.VIR_DOMAIN_BLOCKED = 2
    mock_libvirt.VIR_DOMAIN_PAUSED = 3
    mock_libvirt.VIR_DOMAIN_SHUTDOWN = 4
    mock_libvirt.VIR_DOMAIN_SHUTOFF = 5
    mock_libvirt.VIR_DOMAIN_CRASHED = 6

    # Patch the module
    monkeypatch.setattr("libvirt", mock_libvirt)

    return mock_libvirt


# ============================================================================
# Integration Test Markers
# ============================================================================


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require libvirt)"
    )
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests (slow)")
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "requires_kvm: marks tests that require KVM/hardware virtualization",
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )


# ============================================================================
# Auto-cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Auto-cleanup fixture that runs after each test.

    Ensures test artifacts don't leak between tests.
    """
    # Setup: nothing to do before test
    yield

    # Teardown: cleanup after test
    # This can be extended to clean up specific resources
    pass
