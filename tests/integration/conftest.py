"""Shared fixtures for integration tests"""

import pytest
import libvirt
from pathlib import Path
from typing import Generator


@pytest.fixture(scope="module")
def real_libvirt_connection() -> Generator[libvirt.virConnect, None, None]:
    """
    Real libvirt connection for integration tests.

    Yields:
        Active libvirt connection

    Note:
        Requires KVM access and libvirt running
    """
    conn = libvirt.open("qemu:///system")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def test_workspace(tmp_path: Path) -> Path:
    """
    Temporary workspace for tests.

    Args:
        tmp_path: pytest temporary directory fixture

    Returns:
        Path to workspace with standard structure
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "input").mkdir()
    (workspace / "output").mkdir()
    (workspace / "work").mkdir()
    return workspace


@pytest.fixture
def cleanup_test_vms(real_libvirt_connection: libvirt.virConnect) -> Generator[None, None, None]:
    """
    Cleanup any test VMs after tests.

    Args:
        real_libvirt_connection: Active libvirt connection

    Yields:
        None (cleanup happens after test)
    """
    yield

    # Cleanup: destroy and undefine any VMs starting with "test-"
    for domain in real_libvirt_connection.listAllDomains():
        name = domain.name()
        if name.startswith("test-"):
            try:
                if domain.isActive():
                    domain.destroy()
                domain.undefine()
            except libvirt.libvirtError:
                # Ignore cleanup errors
                pass


@pytest.fixture(scope="session")
def verify_kvm_available() -> bool:
    """
    Verify KVM virtualization is available.

    Returns:
        True if KVM is available

    Raises:
        pytest.skip: If KVM is not available
    """
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
            if "vmx" not in cpuinfo and "svm" not in cpuinfo:
                pytest.skip("KVM virtualization not available (no vmx/svm in cpuinfo)")
        return True
    except Exception as e:
        pytest.skip(f"Cannot verify KVM availability: {e}")


@pytest.fixture(scope="session")
def verify_libvirt_networks() -> dict:
    """
    Verify required libvirt networks exist.

    Returns:
        Dictionary of network status

    Raises:
        pytest.skip: If required networks are missing
    """
    try:
        conn = libvirt.open("qemu:///system")
        networks = {net.name(): net.isActive() for net in conn.listAllNetworks()}
        conn.close()

        required_networks = ["agent-nat-filtered", "agent-isolated"]
        missing = [net for net in required_networks if net not in networks]

        if missing:
            pytest.skip(
                f"Required networks missing: {', '.join(missing)}. "
                "Run network setup from IMPLEMENTATION_GUIDE.md"
            )

        return networks
    except Exception as e:
        pytest.skip(f"Cannot verify libvirt networks: {e}")
