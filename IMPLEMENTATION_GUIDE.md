# Implementation Guide: KVM Agent Isolation System

**Version:** 1.0.0
**Approach:** TDD with Claude-Flow Orchestration
**Target Completion:** 8 weeks

## Quick Start

### For Developers

```bash
# 1. Clone and setup
git clone <repo-url>
cd dev-box
git checkout kvm_switch

# 2. Install dependencies
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# 3. Verify setup
pytest tests/ -v
mypy src/
ruff check src/

# 4. Start development
# Follow Phase 1 below
```

### Using Claude-Flow for Implementation

This project leverages **claude-flow** MCP server for:
- Parallel task execution
- Agent swarm coordination
- Automated testing workflows
- Performance monitoring

See [Claude-Flow Integration](#claude-flow-integration) section for details.

---

## Implementation Phases

### Phase 1: Foundation (Days 1-14)

**Status:** 📋 Not Started (Planning Complete)
**Documentation:** ✅ Complete (`src/agent_vm/README.md`)
**Next Action:** Begin Day 1 - Project Bootstrap

**Objective:** Establish project structure, testing framework, and core libvirt abstractions

**Prerequisites:**
- Ubuntu 24.04 with KVM support
- libvirt 9.0+ installed
- Python 3.12+
- pytest, mypy, ruff installed

#### Day 1-2: Project Bootstrap

**Status:** ⏳ Not Started
**Estimated Time:** 4 hours

**Task 1.1: Create Project Structure**

```bash
# Test-first: Create test file
cat > tests/test_project_structure.py << 'EOF'
import pytest
from pathlib import Path
import toml

def test_project_structure_exists():
    """Project follows standard Python package structure"""
    root = Path(__file__).parent.parent
    assert (root / "src" / "agent_vm").exists()
    assert (root / "tests" / "unit").exists()
    assert (root / "tests" / "integration").exists()
    assert (root / "tests" / "e2e").exists()
    assert (root / "pyproject.toml").exists()

def test_pyproject_has_required_config():
    """pyproject.toml configured correctly"""
    root = Path(__file__).parent.parent
    config = toml.load(root / "pyproject.toml")
    assert "tool.pytest.ini_options" in config
    assert "tool.mypy" in config
    assert config["tool.pytest.ini_options"]["testpaths"] == ["tests"]
    assert config["tool.mypy"]["strict"] == True
EOF

# Run test (should fail - RED)
pytest tests/test_project_structure.py

# Implement structure (GREEN)
mkdir -p src/agent_vm/{core,network,storage,security,monitoring,execution,communication}
mkdir -p tests/{unit,integration,e2e}
touch src/agent_vm/__init__.py
touch src/agent_vm/py.typed

# Create pyproject.toml (see TDD_IMPLEMENTATION_PLAN.md for full content)

# Verify test passes (GREEN)
pytest tests/test_project_structure.py

# Commit
git add .
git commit -m "feat: initialize project structure with TDD

- Create src/ and tests/ directories
- Configure pytest, mypy, ruff
- Add pyproject.toml with dependencies

Test: test_project_structure.py"
```

**Acceptance Criteria:**
- ✅ All tests pass
- ✅ `pip install -e ".[dev]"` works
- ✅ `pytest --collect-only` finds test directories
- ✅ `mypy src/` runs without errors

**Estimated Time:** 4 hours

---

**Status:** ⏳ Not Started
**Estimated Time:** 6 hours

**Task 1.2: Libvirt Connection Management**

```bash
# Test-first: Create connection tests
cat > tests/unit/test_connection.py << 'EOF'
import pytest
from unittest.mock import Mock, patch
from agent_vm.core.connection import LibvirtConnection, ConnectionError

class TestLibvirtConnection:
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
    def test_connection_context_manager(self, mock_libvirt_open):
        """Connection works as context manager"""
        mock_conn = Mock()
        mock_libvirt_open.return_value = mock_conn

        with LibvirtConnection() as conn:
            assert conn.is_connected()

        mock_conn.close.assert_called_once()
EOF

# Run test (should fail - RED)
pytest tests/unit/test_connection.py -v

# Implement LibvirtConnection (GREEN)
# See TDD_IMPLEMENTATION_PLAN.md section 1.2 for implementation

# Verify tests pass
pytest tests/unit/test_connection.py -v

# Commit
git add src/agent_vm/core/connection.py tests/unit/test_connection.py
git commit -m "feat(core): add LibvirtConnection with context manager

- Thread-safe connection management
- Context manager support
- Comprehensive error handling
- Structured logging

Tests: 4 passing
Coverage: 95%"
```

**Acceptance Criteria:**
- ✅ All connection tests pass (4/4)
- ✅ mypy strict passes
- ✅ Coverage >90%
- ✅ Logs structured events

**Estimated Time:** 6 hours

---

**Status:** ⏳ Not Started
**Estimated Time:** 8 hours

**Task 1.3: VM Domain Abstraction**

```bash
# Test-first: Create VM tests
# See TDD_IMPLEMENTATION_PLAN.md section 1.3 for test code

pytest tests/unit/test_vm.py -v  # Should fail

# Implement VM class
# See TDD_IMPLEMENTATION_PLAN.md section 1.3 for implementation

pytest tests/unit/test_vm.py -v  # Should pass

git commit -m "feat(core): add VM domain abstraction with async support

- VM lifecycle operations (start, stop)
- State management and waiting
- Graceful and force shutdown
- Async/await support

Tests: 6 passing
Coverage: 92%"
```

**Acceptance Criteria:**
- ✅ VM lifecycle tests pass (6/6)
- ✅ Async tests work correctly
- ✅ State transitions validated
- ✅ Error handling comprehensive

**Estimated Time:** 8 hours

---

**Status:** ⏳ Not Started
**Estimated Time:** 3 hours

**Task 1.4: Test Fixtures**

```bash
# Create conftest.py with shared fixtures
# See TDD_IMPLEMENTATION_PLAN.md section 1.4

# Verify fixtures work
pytest tests/unit/ --fixtures  # Should show fixtures

git commit -m "test: add shared pytest fixtures

- Mock libvirt connection
- Mock domain and VM
- Sample VM XML
- Proper fixture scoping"
```

**Estimated Time:** 3 hours

---

#### Day 3-5: VM Template System

**Task 1.5: XML Template Generation**

```bash
# Test-first: Template tests
cat > tests/unit/test_template.py << 'EOF'
# See TDD_IMPLEMENTATION_PLAN.md section 2.1 for full test code
EOF

pytest tests/unit/test_template.py -v  # RED

# Implement VMTemplate
# See TDD_IMPLEMENTATION_PLAN.md section 2.1 for implementation

pytest tests/unit/test_template.py -v  # GREEN

git commit -m "feat(core): add VM template generation

- Dynamic XML generation
- Resource profiles (light, standard, intensive)
- Network modes (nat-filtered DEFAULT, isolated, bridge)
- Network filtering for security
- Security features (cgroups, virtio)

Tests: 6 passing (includes network filter test)
Coverage: 88%"
```

**Important:** NAT-filtered network is now the default since CLI agents (Claude CLI, etc.) require internet access. Network security is maintained through:
- Whitelist-based filtering (DNS, HTTP/S, SSH for git)
- Connection monitoring and logging
- Anomaly detection
- No unsolicited incoming connections

**Acceptance Criteria:**
- ✅ Generated XML validates with libvirt
- ✅ All network modes supported
- ✅ Resource profiles configurable
- ✅ Security features present

**Estimated Time:** 10 hours

---

#### Day 6-8: Snapshot Management

**Task 1.6: Snapshot Lifecycle**

```bash
# Test-first
# See TDD_IMPLEMENTATION_PLAN.md section 2.2

pytest tests/unit/test_snapshot.py -v  # RED

# Implement SnapshotManager
# See TDD_IMPLEMENTATION_PLAN.md section 2.2

pytest tests/unit/test_snapshot.py -v  # GREEN

git commit -m "feat(core): add snapshot management

- Create/list/restore/delete snapshots
- Metadata tracking
- Error handling
- Integration with VM class

Tests: 4 passing
Coverage: 90%"
```

**Acceptance Criteria:**
- ✅ Snapshot operations work
- ✅ Restore returns to exact state
- ✅ Metadata persists
- ✅ Cleanup removes snapshots

**Estimated Time:** 10 hours

---

#### Day 9-12: Integration Testing Setup

**Task 1.7: Integration Test Framework**

```bash
# First, set up network infrastructure
# Create NAT-filtered network (DEFAULT)
cat > /tmp/agent-nat-filtered.xml << 'EOF'
<network>
  <name>agent-nat-filtered</name>
  <forward mode='nat'>
    <nat><port start='1024' end='65535'/></nat>
  </forward>
  <ip address='192.168.101.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.101.10' end='192.168.101.254'/>
    </dhcp>
  </ip>
</network>
EOF

sudo virsh net-define /tmp/agent-nat-filtered.xml
sudo virsh net-start agent-nat-filtered
sudo virsh net-autostart agent-nat-filtered

# Create network filter
cat > /tmp/agent-network-filter.xml << 'EOF'
<filter name='agent-network-filter' chain='root'>
  <!-- DNS -->
  <rule action='accept' direction='out'>
    <udp dstportstart='53' dstportend='53'/>
  </rule>
  <!-- HTTP/HTTPS -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='80' dstportend='80'/>
  </rule>
  <rule action='accept' direction='out'>
    <tcp dstportstart='443' dstportend='443'/>
  </rule>
  <!-- SSH (git) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='22' dstportend='22'/>
  </rule>
  <!-- Established connections -->
  <rule action='accept' direction='in'>
    <all state='ESTABLISHED,RELATED'/>
  </rule>
  <!-- Block unsolicited incoming -->
  <rule action='drop' direction='in' priority='1000'>
    <all state='NEW'/>
  </rule>
  <!-- Drop other outgoing -->
  <rule action='drop' direction='out' priority='1000'>
    <all/>
  </rule>
</filter>
EOF

sudo virsh nwfilter-define /tmp/agent-network-filter.xml

# Verify networks
virsh net-list --all
virsh nwfilter-list

# Create integration test base
cat > tests/integration/conftest.py << 'EOF'
import pytest
import libvirt
from pathlib import Path

@pytest.fixture(scope="module")
def real_libvirt_connection():
    """Real libvirt connection for integration tests"""
    conn = libvirt.open('qemu:///system')
    yield conn
    conn.close()

@pytest.fixture
def test_workspace(tmp_path):
    """Temporary workspace for tests"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "input").mkdir()
    (workspace / "output").mkdir()
    (workspace / "work").mkdir()
    return workspace

@pytest.fixture
def cleanup_test_vms(real_libvirt_connection):
    """Cleanup any test VMs after tests"""
    yield
    # Cleanup code
    for domain in real_libvirt_connection.listAllDomains():
        if domain.name().startswith("test-"):
            if domain.isActive():
                domain.destroy()
            domain.undefine()
EOF

# First integration test
cat > tests/integration/test_vm_lifecycle.py << 'EOF'
import pytest
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.template import VMTemplate, ResourceProfile, NetworkMode
from agent_vm.core.vm import VM, VMState

@pytest.mark.integration
class TestVMLifecycle:
    @pytest.mark.asyncio
    async def test_create_and_start_vm(self, real_libvirt_connection, cleanup_test_vms):
        """Create and start a real VM"""
        # Generate template (uses NAT-filtered by default)
        template = VMTemplate(
            name="test-vm-integration",
            resources=ResourceProfile(vcpu=1, memory_mib=512)
            # network_mode defaults to NAT_FILTERED
        )

        # Define domain
        domain = real_libvirt_connection.defineXML(template.generate_xml())
        vm = VM(domain)

        try:
            # Start VM
            vm.start()
            await vm.wait_for_state(VMState.RUNNING, timeout=30)

            assert vm.get_state() == VMState.RUNNING

            # Stop VM
            vm.stop()
            await vm.wait_for_state(VMState.SHUTOFF, timeout=10)

            assert vm.get_state() == VMState.SHUTOFF

        finally:
            if domain.isActive():
                domain.destroy()
            domain.undefine()
EOF

# Run integration test (needs KVM access)
sudo usermod -a -G libvirt $USER
newgrp libvirt
pytest tests/integration/test_vm_lifecycle.py -v -s

git commit -m "test(integration): add VM lifecycle integration test

- Real libvirt connection fixture
- Test workspace fixture
- VM creation and lifecycle test
- Automatic cleanup"
```

**Acceptance Criteria:**
- ✅ Can create real VM
- ✅ Can start/stop VM
- ✅ State transitions work
- ✅ Cleanup removes VMs

**Estimated Time:** 12 hours

---

#### Day 13-14: Phase 1 Wrap-up

**Task 1.8: Documentation and Review**

```bash
# Create README for developers
cat > src/agent_vm/README.md << 'EOF'
# Agent VM Core Library

## Overview

Python library for managing KVM-based agent isolation environments.

## Components

- **core/**: VM and connection management
- **network/**: Network configuration
- **storage/**: Disk and snapshot management
- **security/**: Security policies
- **monitoring/**: Metrics and logging
- **execution/**: Agent execution framework
- **communication/**: Host-guest communication

## Usage

```python
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.template import VMTemplate
from agent_vm.core.vm import VM

# Connect to libvirt
with LibvirtConnection() as conn:
    # Create VM from template
    template = VMTemplate(name="my-agent-vm")
    domain = conn.connection.defineXML(template.generate_xml())
    vm = VM(domain)

    # Start VM
    vm.start()
    await vm.wait_for_ready()

    # ... use VM ...

    # Cleanup
    vm.stop()
    domain.undefine()
```

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires KVM)
pytest tests/integration/ -v

# All tests with coverage
pytest tests/ --cov
```

## Development

See `CONTRIBUTING.md` for development guidelines.
EOF

# Run full test suite
pytest tests/ -v --cov --cov-report=html

# Generate coverage report
open htmlcov/index.html

# Verify all Phase 1 acceptance criteria
echo "Phase 1 Checklist:"
echo "✅ Project structure complete"
echo "✅ LibvirtConnection implemented and tested"
echo "✅ VM abstraction implemented and tested"
echo "✅ Template generation implemented and tested"
echo "✅ Snapshot management implemented and tested"
echo "✅ Integration tests passing"
echo "✅ Test coverage >80%"
echo "✅ Type checking passes (mypy)"
echo "✅ Linting passes (ruff)"

git commit -m "docs: add developer documentation for phase 1

- Usage examples
- Component overview
- Testing instructions
- Development guidelines"

git tag v0.1.0-phase1
```

**Phase 1 Complete!**

**Metrics:**
- Test Coverage: >80%
- Passing Tests: 20+
- Integration Tests: 3+
- Documentation: Complete

**Estimated Time:** 6 hours

---

### Phase 2: Communication Channels (Days 15-21)

**Objective:** Implement virtio-9p and virtio-vsock for host-guest communication

#### Day 15-17: virtio-9p Filesystem Sharing

**Task 2.1: Filesystem Share Implementation**

```bash
# Test-first
# See TDD_IMPLEMENTATION_PLAN.md section 3.1

pytest tests/integration/test_filesystem.py -v  # RED

# Implement FilesystemShare
# See TDD_IMPLEMENTATION_PLAN.md section 3.1

pytest tests/integration/test_filesystem.py -v  # GREEN

git commit -m "feat(communication): add virtio-9p filesystem sharing

- Code injection (host → guest)
- Results extraction (guest → host)
- Workspace management
- Cleanup operations

Tests: 3 passing (integration)"
```

**Acceptance Criteria:**
- ✅ Can inject files into VM
- ✅ Can extract files from VM
- ✅ Workspace cleanup works
- ✅ Handles large files (>10MB)

**Estimated Time:** 16 hours

---

#### Day 18-19: virtio-vsock Protocol

**Task 2.2: vsock Communication Protocol**

```python
# Test-first: Protocol tests
cat > tests/unit/test_vsock_protocol.py << 'EOF'
import pytest
from agent_vm.communication.vsock import VsockProtocol, MessageType

class TestVsockProtocol:
    @pytest.mark.asyncio
    async def test_send_message(self, mock_socket):
        """Send message over vsock"""
        protocol = VsockProtocol(mock_socket)

        await protocol.send_message(
            MessageType.EXECUTE,
            b"print('hello')"
        )

        # Verify message format
        mock_socket.sendall.assert_called_once()
        data = mock_socket.sendall.call_args[0][0]
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_receive_message(self, mock_socket):
        """Receive message from vsock"""
        # Mock receiving data
        header = struct.pack("!BHI", 4, 5, 12345)  # RESULT, 5 bytes, checksum
        payload = b"hello"
        mock_socket.recv.side_effect = [header, payload]

        protocol = VsockProtocol(mock_socket)
        msg_type, data = await protocol.receive_message()

        assert msg_type == MessageType.RESULT
        assert data == b"hello"

    @pytest.mark.asyncio
    async def test_checksum_validation(self, mock_socket):
        """Reject messages with bad checksum"""
        header = struct.pack("!BHI", 4, 5, 99999)  # Bad checksum
        payload = b"hello"
        mock_socket.recv.side_effect = [header, payload]

        protocol = VsockProtocol(mock_socket)
        with pytest.raises(ProtocolError, match="checksum"):
            await protocol.receive_message()
EOF

pytest tests/unit/test_vsock_protocol.py -v  # RED

# Implement VsockProtocol
# See ARCHITECTURE.md section 4.1 for implementation

pytest tests/unit/test_vsock_protocol.py -v  # GREEN

git commit -m "feat(communication): add vsock protocol implementation

- Message framing with header
- CRC32 checksum validation
- Async send/receive
- Message type enumeration

Tests: 3 passing"
```

**Estimated Time:** 12 hours

---

#### Day 20-21: Guest Agent

**Task 2.3: Guest Agent Implementation**

```python
# Create guest agent that runs inside VM
cat > guest/agent.py << 'EOF'
"""
Guest agent runs inside VM and communicates via vsock.
Deploy this to VMs via cloud-init or Packer provisioning.
"""
import asyncio
import json
import subprocess
from pathlib import Path
from agent_vm.communication.vsock import VsockProtocol, MessageType

class GuestAgent:
    """Agent running inside VM"""

    def __init__(self, vsock_port: int = 9999):
        self.port = vsock_port
        self.workspace = Path("/workspace")

    async def run(self):
        """Main event loop"""
        # Listen on vsock
        server = await asyncio.start_server(
            self.handle_client,
            host="0.0.0.0",  # vsock uses CID, not IP
            port=self.port
        )

        print(f"Guest agent listening on vsock port {self.port}")
        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        """Handle host connection"""
        protocol = VsockProtocol(reader, writer)

        while True:
            try:
                msg_type, payload = await protocol.receive_message()

                if msg_type == MessageType.EXECUTE:
                    await self.handle_execute(protocol, payload)
                elif msg_type == MessageType.STATUS:
                    await self.handle_status(protocol)
                elif msg_type == MessageType.STOP:
                    break

            except Exception as e:
                await protocol.send_message(
                    MessageType.ERROR,
                    json.dumps({"error": str(e)}).encode()
                )

        writer.close()
        await writer.wait_closed()

    async def handle_execute(self, protocol, payload):
        """Execute agent code"""
        code = payload.decode('utf-8')

        # Write code to file
        code_path = self.workspace / "input" / "agent.py"
        code_path.write_text(code)

        # Execute
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3",
                str(code_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace / "work")
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=300
            )

            result = {
                "exit_code": proc.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }

            await protocol.send_message(
                MessageType.RESULT,
                json.dumps(result).encode()
            )

        except asyncio.TimeoutError:
            await protocol.send_message(
                MessageType.ERROR,
                b"Execution timeout"
            )

    async def handle_status(self, protocol):
        """Send status information"""
        status = {
            "status": "ready",
            "workspace": str(self.workspace)
        }

        await protocol.send_message(
            MessageType.STATUS,
            json.dumps(status).encode()
        )

if __name__ == "__main__":
    agent = GuestAgent()
    asyncio.run(agent.run())
EOF

# Create systemd unit for guest agent
cat > guest/agent-vm.service << 'EOF'
[Unit]
Description=Agent VM Guest Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/agent-vm-guest.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Test integration
pytest tests/integration/test_vsock_communication.py -v

git commit -m "feat(guest): add guest agent with vsock support

- Listens on vsock port 9999
- Handles execute, status, stop commands
- Timeout enforcement
- Error reporting
- Systemd integration

Tests: integration passing"
```

**Estimated Time:** 16 hours

---

### Phase 3: Agent Execution Framework (Days 22-28)

**Objective:** Execute agent code with timeout, resource limits, error handling

#### Day 22-25: Core Executor

**Task 3.1: Agent Executor**

```bash
# Test-first
# See TDD_IMPLEMENTATION_PLAN.md section 4.1

pytest tests/integration/test_executor.py -v  # RED

# Implement AgentExecutor
# See TDD_IMPLEMENTATION_PLAN.md section 4.1

pytest tests/integration/test_executor.py -v  # GREEN

git commit -m "feat(execution): add agent executor framework

- Execute agent code in VM
- Timeout enforcement
- Error capture
- Results extraction
- Filesystem integration

Tests: 3 passing (integration)
Coverage: 85%"
```

**Estimated Time:** 20 hours

---

#### Day 26-28: VM Pool Management

**Task 3.2: VM Pool**

```python
# Test-first: Pool tests
cat > tests/unit/test_vm_pool.py << 'EOF'
import pytest
from agent_vm.execution.pool import VMPool, VMPoolError

class TestVMPool:
    @pytest.mark.asyncio
    async def test_pool_initialization(self):
        """Pool creates initial VMs"""
        pool = VMPool(min_size=3, max_size=10)
        await pool.initialize()

        assert pool.size() >= 3

    @pytest.mark.asyncio
    async def test_acquire_from_pool(self):
        """Acquire VM from pool"""
        pool = VMPool(min_size=2)
        await pool.initialize()

        vm = await pool.acquire(timeout=5)

        assert vm is not None
        assert pool.size() == 1  # One removed

    @pytest.mark.asyncio
    async def test_release_to_pool(self):
        """Release VM back to pool"""
        pool = VMPool(min_size=2, max_size=5)
        await pool.initialize()

        vm = await pool.acquire()
        initial_size = pool.size()

        await pool.release(vm)

        assert pool.size() == initial_size + 1

    @pytest.mark.asyncio
    async def test_pool_maintenance(self):
        """Pool maintains minimum size"""
        pool = VMPool(min_size=3, max_size=10)
        await pool.initialize()

        # Acquire all VMs
        vms = [await pool.acquire() for _ in range(3)]

        # Start maintenance task
        asyncio.create_task(pool.maintain_pool())
        await asyncio.sleep(2)

        # Pool should have refilled
        assert pool.size() >= 3
EOF

pytest tests/unit/test_vm_pool.py -v  # RED

# Implement VMPool (see ARCHITECTURE.md section 1.2)

pytest tests/unit/test_vm_pool.py -v  # GREEN

git commit -m "feat(execution): add VM pool management

- Pre-warmed VM pool
- Automatic refilling
- Max size enforcement
- TTL-based eviction
- Health checking

Tests: 4 passing
Coverage: 88%"
```

**Estimated Time:** 18 hours

---

### Phase 4: Monitoring & Security (Days 29-35)

#### Day 29-31: Prometheus Metrics

**Task 4.1: Metrics Collection**

```bash
# Implementation in TDD_IMPLEMENTATION_PLAN.md section 5.1

pytest tests/unit/test_metrics.py -v

git commit -m "feat(monitoring): add Prometheus metrics

- Execution metrics
- VM resource metrics
- Pool metrics
- Prometheus exposition

Tests: 4 passing"
```

**Estimated Time:** 16 hours

---

#### Day 32-33: Audit Logging

**Task 4.2: Structured Audit Logs**

```python
# Implement audit logger
# See ARCHITECTURE.md section 2.2

pytest tests/unit/test_audit_logger.py -v

git commit -m "feat(monitoring): add structured audit logging

- JSON-formatted logs
- Event types and schema
- Syslog integration
- Log rotation

Tests: 3 passing"
```

**Estimated Time:** 12 hours

---

#### Day 34-35: Anomaly Detection

**Task 4.3: Anomaly Detection**

```python
# Implement anomaly detector
# See ARCHITECTURE.md section 2.3

pytest tests/unit/test_anomaly_detector.py -v

git commit -m "feat(monitoring): add anomaly detection

- Statistical detection (z-score)
- Rule-based patterns
- Alert generation
- Auto-response actions

Tests: 5 passing"
```

**Estimated Time:** 16 hours

---

### Phase 5: Integration & E2E (Days 36-42)

#### Day 36-40: End-to-End Tests

**Task 5.1: Full Workflow Tests**

```bash
# See TDD_IMPLEMENTATION_PLAN.md section 6.1

pytest tests/e2e/ -v -s --log-cli-level=INFO

git commit -m "test(e2e): add full workflow tests

- Complete lifecycle test
- Concurrent execution test
- Snapshot restore test
- Error recovery test

Tests: 4 passing (E2E)"
```

**Estimated Time:** 30 hours

---

#### Day 41-42: Performance Testing

**Task 5.2: Performance Benchmarks**

```python
# Create performance tests
cat > tests/performance/test_benchmarks.py << 'EOF'
import pytest
import time
from agent_vm.execution.executor import AgentExecutor

@pytest.mark.performance
class TestPerformance:
    @pytest.mark.asyncio
    async def test_vm_boot_time(self, lifecycle_manager):
        """VM boots in under 2 seconds"""
        start = time.time()

        vm = await lifecycle_manager.create_vm("perf-test")
        await vm.start()
        await vm.wait_for_ready(timeout=30)

        boot_time = time.time() - start

        assert boot_time < 2.0, f"Boot took {boot_time}s"

        await lifecycle_manager.destroy_vm(vm)

    @pytest.mark.asyncio
    async def test_pool_acquire_time(self, vm_pool):
        """Pool acquire in under 100ms"""
        start = time.time()

        vm = await vm_pool.acquire(timeout=5)

        acquire_time = time.time() - start

        assert acquire_time < 0.1, f"Acquire took {acquire_time}s"

        await vm_pool.release(vm)

    @pytest.mark.asyncio
    async def test_concurrent_execution(self, vm_pool, tmp_path):
        """Execute 10 agents concurrently"""
        executor = AgentExecutor()
        agent_code = "print('test')"

        start = time.time()

        tasks = [
            executor.execute_with_pool(vm_pool, agent_code, tmp_path)
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start

        assert all(r.success for r in results)
        assert total_time < 30, f"10 concurrent executions took {total_time}s"
EOF

pytest tests/performance/ -v

# Generate performance report
pytest tests/performance/ --benchmark-json=perf-results.json

git commit -m "test(performance): add performance benchmarks

- Boot time benchmark (<2s)
- Pool acquire benchmark (<100ms)
- Concurrent execution benchmark
- Report generation

Results: All benchmarks passing"
```

**Estimated Time:** 14 hours

---

### Phase 6: Polish & Documentation (Days 43-56)

#### Day 43-48: Documentation

**Task 6.1: Complete Documentation**

```bash
# API documentation
pdoc src/agent_vm/ -o docs/api/

# User guide
cat > docs/USER_GUIDE.md << 'EOF'
# Agent VM User Guide

## Installation
## Quick Start
## Configuration
## Examples
## Troubleshooting
EOF

# Developer guide
cat > docs/DEVELOPER_GUIDE.md << 'EOF'
# Developer Guide

## Architecture Overview
## Development Setup
## Testing Strategy
## Contributing Guidelines
EOF

git commit -m "docs: add comprehensive documentation

- API documentation (pdoc)
- User guide
- Developer guide
- Architecture diagrams"
```

**Estimated Time:** 30 hours

---

#### Day 49-52: Performance Optimization

**Task 6.2: Optimize Critical Paths**

```bash
# Profile code
python -m cProfile -o profile.stats src/agent_vm/execution/executor.py

# Analyze bottlenecks
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"

# Optimize identified bottlenecks
# - Reduce VM boot time
# - Optimize snapshot operations
# - Improve vsock communication

pytest tests/performance/ -v  # Verify improvements

git commit -m "perf: optimize critical execution paths

- Reduce VM boot time by 30%
- Optimize snapshot restore by 50%
- Improve vsock throughput

Benchmarks: All targets met"
```

**Estimated Time:** 24 hours

---

#### Day 53-56: Security Hardening

**Task 6.3: Security Audit & Fixes**

```bash
# Run security scans
bandit -r src/ -f json -o security-report.json
safety check --json

# Fix identified issues
# ... make fixes ...

# Re-scan
bandit -r src/ -f json -o security-report-final.json

# Verify no high/critical issues
cat security-report-final.json | jq '.metrics._totals.high'  # Should be 0

git commit -m "security: harden system against vulnerabilities

- Fix bandit warnings
- Update dependencies (safety)
- Add AppArmor profile
- Strengthen network filters

Security scan: Clean (0 high, 0 critical)"
```

**Estimated Time:** 24 hours

---

## Claude-Flow Integration

### Using Claude-Flow for Parallel Development

```bash
# Initialize swarm for development
/swarm-init hierarchical --max-agents=10

# Spawn specialized agents
/agent-spawn type=coder name=unit-test-writer
/agent-spawn type=coder name=integration-test-writer
/agent-spawn type=reviewer name=code-reviewer
/agent-spawn type=tester name=test-runner

# Orchestrate parallel task execution
/task-orchestrate "Implement Phase 1 components in parallel" --strategy=parallel

# Monitor progress
/swarm-monitor

# Review completed tasks
/task-results <task_id>
```

### Automated Testing Workflows

```bash
# Create workflow for TDD cycle
/workflow-create tdd-cycle << 'EOF'
steps:
  - run_tests: pytest tests/unit --tb=short
  - check_coverage: pytest --cov --cov-fail-under=80
  - type_check: mypy src/
  - lint: ruff check src/
  - security: bandit -r src/

triggers:
  - on_file_change: src/**/*.py
  - on_test_change: tests/**/*.py
EOF

# Execute workflow
/workflow-execute tdd-cycle
```

### Performance Monitoring with Claude-Flow

```bash
# Monitor system performance
/performance-report --timeframe=24h

# Detect bottlenecks
/bottleneck-analyze --component=vm_pool

# Token usage tracking
/token-usage --operation=test-execution
```

---

## Daily Workflow

### Start of Day
```bash
# 1. Sync with main
git pull origin main

# 2. Create feature branch
git checkout -b feature/task-name

# 3. Review today's tasks
cat IMPLEMENTATION_GUIDE.md | grep "Day $(date +%d)"

# 4. Activate environment
source venv/bin/activate
```

### During Development
```bash
# 1. Write test (RED)
vim tests/unit/test_feature.py
pytest tests/unit/test_feature.py -v  # Should fail

# 2. Implement feature (GREEN)
vim src/agent_vm/module/feature.py
pytest tests/unit/test_feature.py -v  # Should pass

# 3. Refactor
# Improve code without changing behavior

# 4. Verify all tests pass
pytest tests/ -v

# 5. Type check
mypy src/

# 6. Lint
ruff check src/

# 7. Commit
git add .
git commit -m "feat: description"
```

### End of Day
```bash
# 1. Run full test suite
pytest tests/ --cov

# 2. Push branch
git push origin feature/task-name

# 3. Create PR (if task complete)
gh pr create --title "Task name" --body "Description"

# 4. Update progress
# Mark tasks complete in this guide
```

---

## Success Criteria

### Phase 1 (Foundation)
- ✅ Test coverage >80%
- ✅ All unit tests passing (20+)
- ✅ Integration tests passing (3+)
- ✅ mypy strict passing
- ✅ No ruff warnings

### Phase 2 (Communication)
- ✅ virtio-9p working
- ✅ virtio-vsock working
- ✅ Guest agent deployed
- ✅ Integration tests passing

### Phase 3 (Execution)
- ✅ Agent execution working
- ✅ Timeout enforcement working
- ✅ VM pool functional
- ✅ E2E tests passing

### Phase 4 (Monitoring)
- ✅ Prometheus metrics exported
- ✅ Audit logs structured
- ✅ Anomaly detection working
- ✅ Alerts configured

### Phase 5 (Integration)
- ✅ Full workflow E2E passing
- ✅ Performance benchmarks met
- ✅ Concurrent execution working
- ✅ Error recovery working

### Phase 6 (Polish)
- ✅ Documentation complete
- ✅ Performance optimized
- ✅ Security hardened
- ✅ Ready for production

---

## Troubleshooting

### Tests Failing
```bash
# Run with verbose output
pytest tests/ -vv -s

# Run specific test
pytest tests/unit/test_connection.py::TestLibvirtConnection::test_connection_opens -vv

# Debug with pdb
pytest tests/ --pdb

# See full traceback
pytest tests/ --tb=long
```

### Type Errors
```bash
# Run mypy with verbose
mypy src/ --show-error-codes --show-error-context

# Check specific file
mypy src/agent_vm/core/connection.py
```

### Libvirt Issues
```bash
# Check libvirt service
sudo systemctl status libvirtd

# Verify connection
virsh -c qemu:///system list --all

# Check permissions
groups | grep libvirt
```

---

## Resources

- **Architecture:** `ARCHITECTURE.md`
- **TDD Plan:** `TDD_IMPLEMENTATION_PLAN.md`
- **Project README:** `README.md`
- **API Docs:** `docs/api/`
- **Claude Flow:** https://github.com/williamzujkowski/claude-flow

---

## Support

For questions or issues:
1. Check documentation first
2. Search existing issues
3. Ask in discussions
4. Create issue with reproducible example

Happy coding! 🚀
