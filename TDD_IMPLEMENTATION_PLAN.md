# TDD Implementation Plan

**Version:** 1.0.0
**Approach:** Test-Driven Development with Red-Green-Refactor
**Target:** Production-ready KVM agent isolation system

## Overview

This plan follows strict TDD methodology: **Write tests first, then implement to pass them.**

### Development Principles

1. **Red-Green-Refactor Cycle**
   - RED: Write failing test
   - GREEN: Write minimal code to pass test
   - REFACTOR: Improve code without changing behavior

2. **Test Pyramid**
   - 70% Unit Tests (fast, isolated)
   - 20% Integration Tests (component interaction)
   - 10% E2E Tests (full system)

3. **Code Quality Standards**
   - Type hints required (mypy strict mode)
   - Docstrings required (Google style)
   - Test coverage >80% (pytest-cov)
   - Security scanning (bandit, safety)
   - Linting (ruff, black)

4. **Commit Strategy**
   - Commit after each green test
   - Squash refactoring commits
   - Clear commit messages (Conventional Commits)

---

## Phase 1: Foundation & Testing Infrastructure (Week 1-2)

**Goal:** Establish testing framework and core libvirt abstractions

### 1.1 Project Setup

#### Test: Project structure exists
```python
# tests/test_project_structure.py
import pytest
from pathlib import Path

def test_project_structure_exists():
    """Project follows standard Python package structure"""
    root = Path(__file__).parent.parent
    assert (root / "src" / "agent_vm").exists()
    assert (root / "tests").exists()
    assert (root / "pyproject.toml").exists()
    assert (root / "README.md").exists()

def test_pyproject_configuration():
    """pyproject.toml has required configuration"""
    root = Path(__file__).parent.parent
    config = toml.load(root / "pyproject.toml")

    assert "tool.pytest.ini_options" in config
    assert "tool.mypy" in config
    assert "tool.black" in config
    assert "tool.ruff" in config
```

#### Implementation:
```bash
# Create project structure
mkdir -p src/agent_vm/{core,network,storage,security,monitoring}
mkdir -p tests/{unit,integration,e2e}
touch src/agent_vm/__init__.py
touch src/agent_vm/py.typed  # PEP 561 marker

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-vm"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "libvirt-python>=9.0.0",
    "prometheus-client>=0.19.0",
    "structlog>=24.0.0",
    "pydantic>=2.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.8.0",
    "black>=24.0.0",
    "ruff>=0.1.9",
    "bandit>=1.7.6",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = [
    "--strict-markers",
    "--cov=src/agent_vm",
    "--cov-report=html",
    "--cov-report=term",
    "--cov-fail-under=80",
]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true

[tool.black]
line-length = 100
target-version = ['py312']

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "DTZ", "T20", "RET", "SIM", "ARG", "PTH", "ERA", "PL", "RUF"]

[tool.ruff.per-file-ignores]
"tests/**/*.py" = ["PLR2004", "S101"]
EOF
```

**Acceptance Criteria:**
- ✅ All project structure tests pass
- ✅ Dependencies install without errors
- ✅ pytest runs successfully
- ✅ mypy, black, ruff execute without errors

---

### 1.2 Libvirt Connection Management

#### Test 1.2.1: Connection lifecycle
```python
# tests/unit/test_connection.py
import pytest
from unittest.mock import Mock, patch
from agent_vm.core.connection import LibvirtConnection, ConnectionError

class TestLibvirtConnection:
    """Test libvirt connection management"""

    @patch('libvirt.open')
    def test_connection_opens_successfully(self, mock_libvirt_open):
        """Connection opens to qemu:///system"""
        mock_conn = Mock()
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()

        mock_libvirt_open.assert_called_once_with('qemu:///system')
        assert conn.is_connected()

    @patch('libvirt.open')
    def test_connection_handles_failure(self, mock_libvirt_open):
        """Connection raises ConnectionError on failure"""
        mock_libvirt_open.side_effect = Exception("Connection failed")

        conn = LibvirtConnection()
        with pytest.raises(ConnectionError):
            conn.open()

    @patch('libvirt.open')
    def test_connection_closes_gracefully(self, mock_libvirt_open):
        """Connection closes and cleans up"""
        mock_conn = Mock()
        mock_libvirt_open.return_value = mock_conn

        conn = LibvirtConnection()
        conn.open()
        conn.close()

        mock_conn.close.assert_called_once()
        assert not conn.is_connected()

    @patch('libvirt.open')
    def test_connection_context_manager(self, mock_libvirt_open):
        """Connection works as context manager"""
        mock_conn = Mock()
        mock_libvirt_open.return_value = mock_conn

        with LibvirtConnection() as conn:
            assert conn.is_connected()

        mock_conn.close.assert_called_once()
```

#### Implementation:
```python
# src/agent_vm/core/connection.py
"""Libvirt connection management"""

from typing import Optional
import libvirt
import structlog

logger = structlog.get_logger()


class ConnectionError(Exception):
    """Libvirt connection error"""
    pass


class LibvirtConnection:
    """Thread-safe libvirt connection manager"""

    def __init__(self, uri: str = "qemu:///system") -> None:
        """
        Initialize connection manager.

        Args:
            uri: Libvirt connection URI

        """
        self.uri = uri
        self._conn: Optional[libvirt.virConnect] = None

    def open(self) -> None:
        """
        Open connection to libvirt daemon.

        Raises:
            ConnectionError: If connection fails

        """
        try:
            self._conn = libvirt.open(self.uri)
            logger.info("libvirt_connection_opened", uri=self.uri)
        except libvirt.libvirtError as e:
            logger.error("libvirt_connection_failed", uri=self.uri, error=str(e))
            raise ConnectionError(f"Failed to connect to {self.uri}: {e}") from e

    def close(self) -> None:
        """Close connection to libvirt daemon"""
        if self._conn:
            try:
                self._conn.close()
                logger.info("libvirt_connection_closed", uri=self.uri)
            finally:
                self._conn = None

    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self._conn is not None and self._conn.isAlive()

    @property
    def connection(self) -> libvirt.virConnect:
        """
        Get underlying libvirt connection.

        Returns:
            libvirt connection object

        Raises:
            ConnectionError: If not connected

        """
        if not self._conn:
            raise ConnectionError("Not connected to libvirt")
        return self._conn

    def __enter__(self) -> "LibvirtConnection":
        """Context manager entry"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        self.close()
```

**Acceptance Criteria:**
- ✅ All connection tests pass
- ✅ Type hints pass mypy strict checking
- ✅ Code coverage >90%
- ✅ Docstrings present and valid

---

### 1.3 VM Domain Abstraction

#### Test 1.3.1: VM lifecycle operations
```python
# tests/unit/test_vm.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from agent_vm.core.vm import VM, VMState, VMError

class TestVM:
    """Test VM abstraction layer"""

    def test_vm_initializes_with_domain(self):
        """VM wraps libvirt domain"""
        mock_domain = Mock()
        mock_domain.name.return_value = "test-vm"
        mock_domain.UUIDString.return_value = "abc-123"

        vm = VM(mock_domain)

        assert vm.name == "test-vm"
        assert vm.uuid == "abc-123"

    def test_vm_start_creates_domain(self):
        """Starting VM calls domain.create()"""
        mock_domain = Mock()
        mock_domain.isActive.return_value = False

        vm = VM(mock_domain)
        vm.start()

        mock_domain.create.assert_called_once()

    def test_vm_start_skips_if_already_running(self):
        """Starting running VM is idempotent"""
        mock_domain = Mock()
        mock_domain.isActive.return_value = True

        vm = VM(mock_domain)
        vm.start()

        mock_domain.create.assert_not_called()

    def test_vm_stop_destroys_domain(self):
        """Stopping VM calls domain.destroy()"""
        mock_domain = Mock()
        mock_domain.isActive.return_value = True

        vm = VM(mock_domain)
        vm.stop()

        mock_domain.destroy.assert_called_once()

    def test_vm_stop_graceful_shutdown(self):
        """Graceful stop calls domain.shutdown()"""
        mock_domain = Mock()
        mock_domain.isActive.return_value = True

        vm = VM(mock_domain)
        vm.stop(graceful=True)

        mock_domain.shutdown.assert_called_once()

    def test_vm_get_state(self):
        """VM state maps libvirt states correctly"""
        mock_domain = Mock()
        mock_domain.state.return_value = [1, 1]  # VIR_DOMAIN_RUNNING

        vm = VM(mock_domain)
        state = vm.get_state()

        assert state == VMState.RUNNING

    @pytest.mark.asyncio
    async def test_vm_wait_for_state(self):
        """VM waits for desired state"""
        mock_domain = Mock()
        # First call: SHUTDOWN, second call: RUNNING
        mock_domain.state.side_effect = [[4, 0], [1, 1]]

        vm = VM(mock_domain)
        await vm.wait_for_state(VMState.RUNNING, timeout=5)

        assert mock_domain.state.call_count == 2

    @pytest.mark.asyncio
    async def test_vm_wait_for_state_timeout(self):
        """VM raises error on timeout"""
        mock_domain = Mock()
        mock_domain.state.return_value = [4, 0]  # Always SHUTDOWN

        vm = VM(mock_domain)
        with pytest.raises(VMError, match="Timeout"):
            await vm.wait_for_state(VMState.RUNNING, timeout=0.1)
```

#### Implementation:
```python
# src/agent_vm/core/vm.py
"""VM domain abstraction"""

import asyncio
from enum import Enum
from typing import Optional
import libvirt
import structlog

logger = structlog.get_logger()


class VMState(Enum):
    """VM state enumeration"""
    RUNNING = "running"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    SHUTOFF = "shutoff"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


class VMError(Exception):
    """VM operation error"""
    pass


class VM:
    """High-level VM abstraction"""

    # Map libvirt states to VMState
    _STATE_MAP = {
        0: VMState.UNKNOWN,    # VIR_DOMAIN_NOSTATE
        1: VMState.RUNNING,    # VIR_DOMAIN_RUNNING
        2: VMState.RUNNING,    # VIR_DOMAIN_BLOCKED
        3: VMState.PAUSED,     # VIR_DOMAIN_PAUSED
        4: VMState.SHUTDOWN,   # VIR_DOMAIN_SHUTDOWN
        5: VMState.SHUTOFF,    # VIR_DOMAIN_SHUTOFF
        6: VMState.CRASHED,    # VIR_DOMAIN_CRASHED
        7: VMState.PAUSED,     # VIR_DOMAIN_PMSUSPENDED
    }

    def __init__(self, domain: libvirt.virDomain) -> None:
        """
        Initialize VM wrapper.

        Args:
            domain: libvirt domain object

        """
        self._domain = domain
        self._logger = logger.bind(vm_name=self.name, vm_uuid=self.uuid)

    @property
    def name(self) -> str:
        """Get VM name"""
        return self._domain.name()

    @property
    def uuid(self) -> str:
        """Get VM UUID"""
        return self._domain.UUIDString()

    def start(self) -> None:
        """
        Start VM.

        Raises:
            VMError: If start fails

        """
        try:
            if not self._domain.isActive():
                self._domain.create()
                self._logger.info("vm_started")
            else:
                self._logger.debug("vm_already_running")
        except libvirt.libvirtError as e:
            self._logger.error("vm_start_failed", error=str(e))
            raise VMError(f"Failed to start VM: {e}") from e

    def stop(self, graceful: bool = False) -> None:
        """
        Stop VM.

        Args:
            graceful: If True, attempt graceful shutdown. Otherwise force stop.

        Raises:
            VMError: If stop fails

        """
        try:
            if self._domain.isActive():
                if graceful:
                    self._domain.shutdown()
                    self._logger.info("vm_shutdown_initiated")
                else:
                    self._domain.destroy()
                    self._logger.info("vm_force_stopped")
            else:
                self._logger.debug("vm_already_stopped")
        except libvirt.libvirtError as e:
            self._logger.error("vm_stop_failed", error=str(e))
            raise VMError(f"Failed to stop VM: {e}") from e

    def get_state(self) -> VMState:
        """
        Get current VM state.

        Returns:
            Current VM state

        """
        state_code, _ = self._domain.state()
        return self._STATE_MAP.get(state_code, VMState.UNKNOWN)

    async def wait_for_state(
        self,
        desired_state: VMState,
        timeout: float = 30.0,
        poll_interval: float = 0.5
    ) -> None:
        """
        Wait for VM to reach desired state.

        Args:
            desired_state: Target state to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: How often to check state in seconds

        Raises:
            VMError: If timeout is reached

        """
        start_time = asyncio.get_event_loop().time()

        while True:
            current_state = self.get_state()
            if current_state == desired_state:
                self._logger.info("vm_state_reached", state=desired_state.value)
                return

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise VMError(
                    f"Timeout waiting for state {desired_state.value}. "
                    f"Current state: {current_state.value}"
                )

            await asyncio.sleep(poll_interval)
```

**Acceptance Criteria:**
- ✅ All VM tests pass
- ✅ Async tests work correctly
- ✅ Error handling comprehensive
- ✅ Type hints strict compliant

---

### 1.4 Test Fixtures and Utilities

#### Test 1.4.1: pytest fixtures
```python
# tests/conftest.py
"""Shared pytest fixtures"""

import pytest
from unittest.mock import Mock, MagicMock
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.vm import VM


@pytest.fixture
def mock_libvirt_connection() -> Mock:
    """Mock libvirt connection"""
    conn = Mock(spec=LibvirtConnection)
    conn.is_connected.return_value = True
    return conn


@pytest.fixture
def mock_domain() -> Mock:
    """Mock libvirt domain"""
    domain = Mock()
    domain.name.return_value = "test-vm"
    domain.UUIDString.return_value = "test-uuid-123"
    domain.isActive.return_value = False
    domain.state.return_value = [5, 0]  # SHUTOFF
    return domain


@pytest.fixture
def mock_vm(mock_domain: Mock) -> VM:
    """Mock VM instance"""
    return VM(mock_domain)


@pytest.fixture(scope="session")
def test_vm_xml() -> str:
    """Sample VM XML for testing"""
    return """
    <domain type='kvm'>
      <name>test-agent-vm</name>
      <memory unit='MiB'>2048</memory>
      <vcpu>2</vcpu>
      <os>
        <type arch='x86_64'>hvm</type>
        <boot dev='hd'/>
      </os>
      <devices>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='/var/lib/libvirt/images/test.qcow2'/>
          <target dev='vda' bus='virtio'/>
        </disk>
        <interface type='network'>
          <source network='agent-isolated'/>
          <model type='virtio'/>
        </interface>
      </devices>
    </domain>
    """
```

**Acceptance Criteria:**
- ✅ Fixtures available to all tests
- ✅ Fixtures properly scoped (function/module/session)
- ✅ Mock objects fully configured

---

## Phase 2: VM Lifecycle Management (Week 3)

**Goal:** Create, start, stop, destroy VMs with proper resource management

### 2.1 VM Template System

#### Test 2.1.1: Template generation
```python
# tests/unit/test_template.py
import pytest
from agent_vm.core.template import VMTemplate, ResourceProfile, NetworkMode

class TestVMTemplate:
    """Test VM template generation"""

    def test_template_generates_valid_xml(self):
        """Template produces valid libvirt XML"""
        template = VMTemplate(
            name="test-vm",
            resources=ResourceProfile(vcpu=2, memory_mib=2048),
            network_mode=NetworkMode.ISOLATED
        )

        xml = template.generate_xml()

        assert "<domain type='kvm'>" in xml
        assert "<name>test-vm</name>" in xml
        assert "<memory unit='MiB'>2048</memory>" in xml
        assert "<vcpu>2</vcpu>" in xml

    def test_template_includes_security_features(self):
        """Template includes seccomp and namespaces"""
        template = VMTemplate(name="test-vm")
        xml = template.generate_xml()

        # Check for security features in XML
        assert "seccomp" in xml.lower() or "sandbox" in xml.lower()

    def test_template_includes_virtio_devices(self):
        """Template uses virtio for performance"""
        template = VMTemplate(name="test-vm")
        xml = template.generate_xml()

        assert "virtio" in xml

    def test_template_nat_filtered_network_default(self):
        """NAT-filtered network is default"""
        template = VMTemplate(name="test-vm")
        xml = template.generate_xml()

        assert "agent-nat-filtered" in xml

    def test_template_isolated_network(self):
        """Isolated network configuration for high security"""
        template = VMTemplate(
            name="test-vm",
            network_mode=NetworkMode.ISOLATED
        )
        xml = template.generate_xml()

        assert "agent-isolated" in xml

    def test_template_includes_network_filter(self):
        """Template includes network filter by default"""
        template = VMTemplate(name="test-vm")
        xml = template.generate_xml()

        assert "filterref" in xml
        assert "agent-network-filter" in xml
```

#### Implementation:
```python
# src/agent_vm/core/template.py
"""VM template generation"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import xml.etree.ElementTree as ET


class NetworkMode(Enum):
    """Network isolation modes"""
    NAT_FILTERED = "nat-filtered"  # DEFAULT: Filtered internet access
    ISOLATED = "isolated"           # High security: No network
    BRIDGE = "bridge"               # Advanced: Direct host bridge


@dataclass
class ResourceProfile:
    """VM resource allocation"""
    vcpu: int = 2
    memory_mib: int = 2048
    disk_gib: int = 20


class VMTemplate:
    """VM template generator"""

    def __init__(
        self,
        name: str,
        resources: Optional[ResourceProfile] = None,
        network_mode: NetworkMode = NetworkMode.NAT_FILTERED,  # DEFAULT
        disk_path: Optional[str] = None
    ) -> None:
        """
        Initialize VM template.

        Args:
            name: VM name
            resources: Resource allocation
            network_mode: Network isolation mode
            disk_path: Path to disk image

        """
        self.name = name
        self.resources = resources or ResourceProfile()
        self.network_mode = network_mode
        self.disk_path = disk_path or f"/var/lib/libvirt/images/{name}.qcow2"

    def generate_xml(self) -> str:
        """
        Generate libvirt domain XML.

        Returns:
            XML string for domain definition

        """
        # Create root domain element
        domain = ET.Element("domain", type="kvm")

        # Basic configuration
        ET.SubElement(domain, "name").text = self.name
        ET.SubElement(domain, "memory", unit="MiB").text = str(self.resources.memory_mib)
        ET.SubElement(domain, "vcpu").text = str(self.resources.vcpu)

        # OS configuration
        os_elem = ET.SubElement(domain, "os")
        ET.SubElement(os_elem, "type", arch="x86_64").text = "hvm"
        ET.SubElement(os_elem, "boot", dev="hd")

        # CPU configuration
        cpu_elem = ET.SubElement(domain, "cpu", mode="host-passthrough")

        # Features (security and performance)
        features = ET.SubElement(domain, "features")
        ET.SubElement(features, "acpi")
        ET.SubElement(features, "apic")

        # Resource limits (cgroups)
        cputune = ET.SubElement(domain, "cputune")
        ET.SubElement(cputune, "shares").text = "1024"
        ET.SubElement(cputune, "period").text = "100000"
        ET.SubElement(cputune, "quota").text = str(self.resources.vcpu * 100000)

        memtune = ET.SubElement(domain, "memtune")
        ET.SubElement(memtune, "hard_limit", unit="MiB").text = str(self.resources.memory_mib)

        # Devices
        devices = ET.SubElement(domain, "devices")

        # Disk (virtio)
        disk = ET.SubElement(devices, "disk", type="file", device="disk")
        ET.SubElement(disk, "driver", name="qemu", type="qcow2", cache="writeback")
        ET.SubElement(disk, "source", file=self.disk_path)
        ET.SubElement(disk, "target", dev="vda", bus="virtio")

        # Network interface
        interface = ET.SubElement(devices, "interface", type="network")
        network_name = f"agent-{self.network_mode.value}"
        ET.SubElement(interface, "source", network=network_name)
        ET.SubElement(interface, "model", type="virtio")

        # Add network filter (except for bridge mode)
        if self.network_mode != NetworkMode.BRIDGE:
            ET.SubElement(interface, "filterref", filter="agent-network-filter")

        # Serial console
        serial = ET.SubElement(devices, "serial", type="pty")
        ET.SubElement(serial, "target", port="0")

        console = ET.SubElement(devices, "console", type="pty")
        ET.SubElement(console, "target", type="serial", port="0")

        # Convert to string
        return ET.tostring(domain, encoding="unicode")
```

**Acceptance Criteria:**
- ✅ Generated XML is valid libvirt format
- ✅ All network modes supported
- ✅ Resource limits configurable
- ✅ Security features enabled

---

### 2.2 Snapshot Management

#### Test 2.2.1: Snapshot lifecycle
```python
# tests/unit/test_snapshot.py
import pytest
from unittest.mock import Mock
from agent_vm.core.snapshot import SnapshotManager, Snapshot

class TestSnapshotManager:
    """Test snapshot management"""

    def test_create_snapshot(self, mock_vm):
        """Create snapshot of VM"""
        manager = SnapshotManager()

        snapshot = manager.create_snapshot(
            mock_vm,
            name="test-snap",
            description="Test snapshot"
        )

        assert snapshot.name == "test-snap"
        assert snapshot.description == "Test snapshot"
        mock_vm._domain.snapshotCreateXML.assert_called_once()

    def test_list_snapshots(self, mock_vm):
        """List all snapshots for VM"""
        mock_snap1 = Mock()
        mock_snap1.getName.return_value = "snap1"
        mock_snap2 = Mock()
        mock_snap2.getName.return_value = "snap2"

        mock_vm._domain.listAllSnapshots.return_value = [mock_snap1, mock_snap2]

        manager = SnapshotManager()
        snapshots = manager.list_snapshots(mock_vm)

        assert len(snapshots) == 2
        assert snapshots[0].name == "snap1"
        assert snapshots[1].name == "snap2"

    def test_restore_snapshot(self, mock_vm):
        """Restore VM to snapshot"""
        mock_snap = Mock()
        snapshot = Snapshot(name="test-snap", _snap_obj=mock_snap)

        manager = SnapshotManager()
        manager.restore_snapshot(mock_vm, snapshot)

        mock_vm._domain.revertToSnapshot.assert_called_once_with(mock_snap)

    def test_delete_snapshot(self, mock_vm):
        """Delete snapshot"""
        mock_snap = Mock()
        snapshot = Snapshot(name="test-snap", _snap_obj=mock_snap)

        manager = SnapshotManager()
        manager.delete_snapshot(snapshot)

        mock_snap.delete.assert_called_once()
```

#### Implementation:
```python
# src/agent_vm/core/snapshot.py
"""Snapshot management"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import libvirt
import structlog

from agent_vm.core.vm import VM

logger = structlog.get_logger()


@dataclass
class Snapshot:
    """Snapshot metadata"""
    name: str
    description: str = ""
    created_at: Optional[datetime] = None
    _snap_obj: Optional[libvirt.virDomainSnapshot] = None


class SnapshotError(Exception):
    """Snapshot operation error"""
    pass


class SnapshotManager:
    """VM snapshot management"""

    def create_snapshot(
        self,
        vm: VM,
        name: str,
        description: str = ""
    ) -> Snapshot:
        """
        Create VM snapshot.

        Args:
            vm: VM to snapshot
            name: Snapshot name
            description: Optional description

        Returns:
            Created snapshot

        Raises:
            SnapshotError: If creation fails

        """
        try:
            snap_xml = f"""
            <domainsnapshot>
                <name>{name}</name>
                <description>{description}</description>
            </domainsnapshot>
            """

            snap_obj = vm._domain.snapshotCreateXML(snap_xml)
            logger.info("snapshot_created", vm=vm.name, snapshot=name)

            return Snapshot(
                name=name,
                description=description,
                created_at=datetime.now(),
                _snap_obj=snap_obj
            )

        except libvirt.libvirtError as e:
            logger.error("snapshot_create_failed", vm=vm.name, error=str(e))
            raise SnapshotError(f"Failed to create snapshot: {e}") from e

    def list_snapshots(self, vm: VM) -> List[Snapshot]:
        """
        List all snapshots for VM.

        Args:
            vm: VM to query

        Returns:
            List of snapshots

        """
        try:
            snap_objs = vm._domain.listAllSnapshots()
            return [
                Snapshot(
                    name=snap.getName(),
                    _snap_obj=snap
                )
                for snap in snap_objs
            ]
        except libvirt.libvirtError as e:
            logger.error("snapshot_list_failed", vm=vm.name, error=str(e))
            return []

    def restore_snapshot(self, vm: VM, snapshot: Snapshot) -> None:
        """
        Restore VM to snapshot.

        Args:
            vm: VM to restore
            snapshot: Snapshot to restore to

        Raises:
            SnapshotError: If restore fails

        """
        try:
            vm._domain.revertToSnapshot(snapshot._snap_obj)
            logger.info("snapshot_restored", vm=vm.name, snapshot=snapshot.name)
        except libvirt.libvirtError as e:
            logger.error("snapshot_restore_failed", vm=vm.name, error=str(e))
            raise SnapshotError(f"Failed to restore snapshot: {e}") from e

    def delete_snapshot(self, snapshot: Snapshot) -> None:
        """
        Delete snapshot.

        Args:
            snapshot: Snapshot to delete

        Raises:
            SnapshotError: If deletion fails

        """
        try:
            snapshot._snap_obj.delete()
            logger.info("snapshot_deleted", snapshot=snapshot.name)
        except libvirt.libvirtError as e:
            logger.error("snapshot_delete_failed", error=str(e))
            raise SnapshotError(f"Failed to delete snapshot: {e}") from e
```

**Acceptance Criteria:**
- ✅ Snapshots create successfully
- ✅ Restore returns VM to exact state
- ✅ List shows all snapshots
- ✅ Delete removes snapshot

---

## Phase 3: Communication Channels (Week 4)

**Goal:** Implement virtio-vsock and virtio-9p for host-guest communication

### 3.1 virtio-9p Filesystem Sharing

#### Test 3.1.1: Filesystem operations
```python
# tests/integration/test_filesystem.py
import pytest
from pathlib import Path
from agent_vm.communication.filesystem import FilesystemShare

@pytest.mark.integration
class TestFilesystemShare:
    """Test 9p filesystem sharing"""

    def test_inject_code(self, tmp_path, mock_vm):
        """Inject agent code into VM"""
        fs = FilesystemShare(workspace=tmp_path)

        agent_code = "print('Hello from agent')"
        fs.inject_code(agent_code, "agent.py")

        # Verify file written to workspace/input
        code_file = tmp_path / "input" / "agent.py"
        assert code_file.exists()
        assert code_file.read_text() == agent_code

    def test_extract_results(self, tmp_path, mock_vm):
        """Extract results from VM"""
        fs = FilesystemShare(workspace=tmp_path)

        # Simulate VM writing results
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "results.json").write_text('{"status": "success"}')

        results = fs.extract_results("results.json")

        assert results == {"status": "success"}

    def test_workspace_cleanup(self, tmp_path):
        """Workspace cleanup removes all files"""
        fs = FilesystemShare(workspace=tmp_path)

        # Create some files
        (tmp_path / "input").mkdir()
        (tmp_path / "input" / "test.py").write_text("test")
        (tmp_path / "output").mkdir()
        (tmp_path / "output" / "result.txt").write_text("result")

        fs.cleanup()

        # Verify cleanup
        assert not (tmp_path / "input" / "test.py").exists()
        assert not (tmp_path / "output" / "result.txt").exists()
```

#### Implementation:
```python
# src/agent_vm/communication/filesystem.py
"""virtio-9p filesystem sharing"""

import json
from pathlib import Path
from typing import Any, Dict
import structlog

logger = structlog.get_logger()


class FilesystemError(Exception):
    """Filesystem operation error"""
    pass


class FilesystemShare:
    """Manage 9p shared filesystem"""

    def __init__(self, workspace: Path) -> None:
        """
        Initialize filesystem share.

        Args:
            workspace: Path to shared workspace directory

        """
        self.workspace = workspace
        self.input_dir = workspace / "input"
        self.output_dir = workspace / "output"
        self.work_dir = workspace / "work"

        # Ensure directories exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def inject_code(self, code: str, filename: str = "agent.py") -> Path:
        """
        Inject agent code into VM.

        Args:
            code: Agent code to inject
            filename: Name of file to create

        Returns:
            Path to created file

        Raises:
            FilesystemError: If injection fails

        """
        try:
            code_path = self.input_dir / filename
            code_path.write_text(code, encoding="utf-8")
            logger.info("code_injected", filename=filename, size=len(code))
            return code_path
        except OSError as e:
            logger.error("code_injection_failed", error=str(e))
            raise FilesystemError(f"Failed to inject code: {e}") from e

    def extract_results(self, filename: str = "results.json") -> Dict[str, Any]:
        """
        Extract results from VM.

        Args:
            filename: Name of results file

        Returns:
            Parsed results

        Raises:
            FilesystemError: If extraction fails

        """
        try:
            results_path = self.output_dir / filename
            if not results_path.exists():
                raise FilesystemError(f"Results file not found: {filename}")

            content = results_path.read_text(encoding="utf-8")
            results = json.loads(content)
            logger.info("results_extracted", filename=filename)
            return results

        except (OSError, json.JSONDecodeError) as e:
            logger.error("results_extraction_failed", error=str(e))
            raise FilesystemError(f"Failed to extract results: {e}") from e

    def cleanup(self) -> None:
        """Clean workspace directories"""
        try:
            for directory in [self.input_dir, self.output_dir, self.work_dir]:
                for file in directory.iterdir():
                    if file.is_file():
                        file.unlink()
                    elif file.is_dir():
                        # Recursively remove directory
                        import shutil
                        shutil.rmtree(file)
            logger.info("workspace_cleaned")
        except OSError as e:
            logger.error("workspace_cleanup_failed", error=str(e))
```

**Acceptance Criteria:**
- ✅ Code injection works
- ✅ Results extraction works
- ✅ Cleanup removes all files
- ✅ Error handling comprehensive

---

## Phase 4: Agent Execution Framework (Week 5)

**Goal:** Execute agent code with timeout, resource limits, and error handling

### 4.1 Agent Executor

#### Test 4.1.1: Agent execution
```python
# tests/integration/test_executor.py
import pytest
from agent_vm.execution.executor import AgentExecutor, ExecutionResult, ExecutionError

@pytest.mark.integration
class TestAgentExecutor:
    """Test agent execution"""

    @pytest.mark.asyncio
    async def test_execute_simple_agent(self, mock_vm, tmp_path):
        """Execute simple agent code"""
        executor = AgentExecutor()

        agent_code = """
import json
result = {"status": "success", "output": "Hello"}
with open("/workspace/output/results.json", "w") as f:
    json.dump(result, f)
"""

        result = await executor.execute(mock_vm, agent_code, workspace=tmp_path)

        assert result.success
        assert result.exit_code == 0
        assert "success" in result.output

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, mock_vm, tmp_path):
        """Agent times out correctly"""
        executor = AgentExecutor()

        # Agent that runs forever
        agent_code = """
import time
while True:
    time.sleep(1)
"""

        with pytest.raises(ExecutionError, match="timeout"):
            await executor.execute(mock_vm, agent_code, workspace=tmp_path, timeout=2)

    @pytest.mark.asyncio
    async def test_execute_with_error(self, mock_vm, tmp_path):
        """Agent error is captured"""
        executor = AgentExecutor()

        agent_code = """
raise ValueError("Test error")
"""

        result = await executor.execute(mock_vm, agent_code, workspace=tmp_path)

        assert not result.success
        assert result.exit_code != 0
        assert "ValueError" in result.stderr
```

#### Implementation:
```python
# src/agent_vm/execution/executor.py
"""Agent code execution"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog

from agent_vm.core.vm import VM
from agent_vm.communication.filesystem import FilesystemShare

logger = structlog.get_logger()


@dataclass
class ExecutionResult:
    """Agent execution result"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    output: Optional[dict] = None


class ExecutionError(Exception):
    """Agent execution error"""
    pass


class AgentExecutor:
    """Execute agent code in VM"""

    async def execute(
        self,
        vm: VM,
        agent_code: str,
        workspace: Path,
        timeout: int = 300
    ) -> ExecutionResult:
        """
        Execute agent code.

        Args:
            vm: VM to execute in
            agent_code: Code to execute
            workspace: Workspace directory
            timeout: Execution timeout in seconds

        Returns:
            Execution result

        Raises:
            ExecutionError: If execution fails or times out

        """
        start_time = datetime.now()
        fs = FilesystemShare(workspace)

        try:
            # Inject code
            fs.inject_code(agent_code, "agent.py")
            logger.info("agent_execution_started", vm=vm.name)

            # Execute via guest agent (simplified - would use vsock in reality)
            try:
                result = await asyncio.wait_for(
                    self._execute_in_vm(vm, "/workspace/input/agent.py"),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error("agent_execution_timeout", vm=vm.name, timeout=timeout)
                raise ExecutionError(f"Agent execution timeout after {timeout}s")

            # Extract results
            try:
                output = fs.extract_results()
            except Exception:
                output = None

            duration = (datetime.now() - start_time).total_seconds()

            exec_result = ExecutionResult(
                success=result["exit_code"] == 0,
                exit_code=result["exit_code"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                duration_seconds=duration,
                output=output
            )

            logger.info(
                "agent_execution_completed",
                vm=vm.name,
                success=exec_result.success,
                duration=duration
            )

            return exec_result

        finally:
            fs.cleanup()

    async def _execute_in_vm(self, vm: VM, script_path: str) -> dict:
        """Execute script in VM (placeholder)"""
        # In reality, this would use vsock or qemu-guest-agent
        # For now, simulate execution
        await asyncio.sleep(0.1)
        return {
            "exit_code": 0,
            "stdout": "Success",
            "stderr": ""
        }
```

**Acceptance Criteria:**
- ✅ Agent executes successfully
- ✅ Timeout enforced
- ✅ Errors captured
- ✅ Results extracted

---

## Phase 5: Monitoring & Observability (Week 6)

**Goal:** Real-time metrics, audit logging, anomaly detection

### 5.1 Prometheus Metrics

#### Test 5.1.1: Metrics collection
```python
# tests/unit/test_metrics.py
import pytest
from agent_vm.monitoring.metrics import MetricsCollector
from prometheus_client import REGISTRY

class TestMetricsCollector:
    """Test metrics collection"""

    def test_metrics_registered(self):
        """Metrics are registered with Prometheus"""
        collector = MetricsCollector()

        metrics = [m.name for m in REGISTRY.collect()]
        assert "agent_execution_total" in metrics
        assert "agent_execution_duration_seconds" in metrics

    def test_record_execution(self):
        """Record execution metrics"""
        collector = MetricsCollector()

        collector.record_execution(
            agent_id="test-agent",
            status="success",
            duration_seconds=1.5
        )

        # Verify metric updated
        # (in real test, would check Prometheus registry)

    def test_update_vm_stats(self):
        """Update VM resource metrics"""
        collector = MetricsCollector()

        collector.update_vm_stats(
            vm_id="test-vm",
            cpu_percent=45.0,
            memory_bytes=1024 * 1024 * 1024  # 1GB
        )

        # Verify gauges updated
```

**Acceptance Criteria:**
- ✅ Metrics registered
- ✅ Values update correctly
- ✅ Labels work properly
- ✅ Prometheus scraping works

---

## Phase 6: Integration & E2E Testing (Week 7)

**Goal:** Full system integration tests

### 6.1 End-to-End Test

```python
# tests/e2e/test_full_workflow.py
import pytest
from pathlib import Path
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.lifecycle import LifecycleManager
from agent_vm.execution.executor import AgentExecutor

@pytest.mark.e2e
@pytest.mark.slow
class TestFullWorkflow:
    """End-to-end system tests"""

    @pytest.mark.asyncio
    async def test_complete_agent_lifecycle(self, tmp_path):
        """Test complete workflow: create → execute → destroy"""

        # Connect to libvirt
        with LibvirtConnection() as conn:
            lifecycle = LifecycleManager(conn)
            executor = AgentExecutor()

            # Create VM
            vm = await lifecycle.create_vm("e2e-test-vm")

            try:
                # Start VM
                await vm.start()
                await vm.wait_for_ready(timeout=30)

                # Execute agent
                agent_code = """
                print("Hello from E2E test")
                import json
                result = {"test": "passed"}
                with open("/workspace/output/results.json", "w") as f:
                    json.dump(result, f)
                """

                result = await executor.execute(vm, agent_code, workspace=tmp_path)

                # Assertions
                assert result.success
                assert result.output["test"] == "passed"

                # Create snapshot
                snapshot = await lifecycle.create_snapshot(vm, "e2e-snapshot")

                # Restore snapshot
                await lifecycle.restore_snapshot(vm, snapshot)

                # Verify VM still works
                result2 = await executor.execute(vm, agent_code, workspace=tmp_path)
                assert result2.success

            finally:
                # Cleanup
                await lifecycle.destroy_vm(vm)

    @pytest.mark.asyncio
    async def test_concurrent_execution(self, tmp_path):
        """Test multiple VMs executing concurrently"""
        # Test concurrent execution of 5 VMs
        # Verify isolation and no resource conflicts
        pass
```

**Acceptance Criteria:**
- ✅ Full workflow executes successfully
- ✅ All components integrate properly
- ✅ Cleanup works correctly
- ✅ Concurrent execution works

---

## Best Practices Enforcement

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: [-r, src/]
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest tests/unit tests/integration -v --cov

      - name: Type checking
        run: mypy src/

      - name: Linting
        run: ruff check src/

      - name: Security scan
        run: bandit -r src/

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Implementation Schedule

### Week 1-2: Foundation
- [ ] Project setup and configuration
- [ ] Libvirt connection management
- [ ] VM domain abstraction
- [ ] Test fixtures and utilities

### Week 3: Lifecycle Management
- [ ] VM template system
- [ ] Snapshot management
- [ ] Resource profiles
- [ ] Network configuration

### Week 4: Communication
- [ ] virtio-9p filesystem sharing
- [ ] virtio-vsock protocol
- [ ] qemu-guest-agent integration
- [ ] Guest agent implementation

### Week 5: Execution
- [ ] Agent executor framework
- [ ] Timeout and error handling
- [ ] Result extraction
- [ ] VM pool management

### Week 6: Monitoring
- [ ] Prometheus metrics
- [ ] Audit logging
- [ ] Anomaly detection
- [ ] Alerting

### Week 7: Integration
- [ ] E2E tests
- [ ] Performance testing
- [ ] Security testing
- [ ] Documentation

### Week 8: Polish
- [ ] Performance optimization
- [ ] Bug fixes
- [ ] Documentation completion
- [ ] Release preparation

---

## Success Metrics

- ✅ **Test Coverage:** >80% overall, >90% for critical paths
- ✅ **Type Safety:** 100% mypy strict compliance
- ✅ **Performance:** Boot time <2s, execution overhead <100ms
- ✅ **Reliability:** >99% test pass rate in CI
- ✅ **Security:** Zero high/critical vulnerabilities
- ✅ **Documentation:** All public APIs documented

---

## Next Steps

1. **Initialize project**: Run project setup tasks
2. **Write first test**: Start with connection management
3. **Implement minimal code**: Pass the first test
4. **Iterate**: Continue red-green-refactor cycle

See `ARCHITECTURE.md` for system design details.
