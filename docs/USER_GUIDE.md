# User Guide: KVM Agent Isolation System

**Version:** 1.0.0
**Status:** Phase 5 Complete (424/436 tests passing, 92.04% coverage)

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Usage Examples](#usage-examples)
6. [Network Modes](#network-modes)
7. [Resource Profiles](#resource-profiles)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Introduction

The KVM Agent Isolation System provides hardware-level isolation for safely testing CLI coding agents (like Claude Code, GitHub Copilot, Aider) using KVM/libvirt virtualization.

### Key Features

- **Hardware Isolation**: True KVM virtualization prevents VM escape attacks
- **Network Access**: NAT-filtered internet for APIs, git, package managers
- **Fast Iteration**: <5s snapshot-based reset cycles
- **VM Pool**: Pre-warmed VMs with <100ms acquisition time
- **Monitoring**: Prometheus metrics and structured audit logs
- **Type Safety**: Python 3.12+ with mypy strict mode
- **High Test Coverage**: 92.04% coverage with 424/436 tests passing

### Use Cases

- **Safe Agent Testing**: Test CLI coding agents in isolated VMs
- **Behavioral Analysis**: Monitor agent resource usage and network activity
- **Regression Testing**: Snapshot-based testing for consistent environments
- **Concurrent Execution**: Run multiple agents in parallel with resource limits

---

## Installation

### System Requirements

- **Operating System**: Ubuntu 24.04 LTS (or compatible)
- **CPU**: x86_64 with virtualization support (Intel VT-x or AMD-V)
- **Memory**: 8 GB minimum (16 GB recommended for multiple VMs)
- **Disk**: 50 GB available space
- **Python**: 3.12 or higher

### Prerequisites

#### 1. Verify KVM Support

```bash
# Check CPU virtualization support
egrep -c '(vmx|svm)' /proc/cpuinfo
# Output should be > 0
```

#### 2. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install KVM and libvirt
sudo apt install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils \
    python3-libvirt \
    python3.12 \
    python3.12-venv

# Verify installation
virsh version
```

#### 3. Configure User Permissions

```bash
# Add user to libvirt group
sudo usermod -a -G libvirt $USER

# Apply group changes (or log out and back in)
newgrp libvirt

# Verify permissions
virsh -c qemu:///system list --all
```

### Python Package Installation

#### Option 1: Install from Source (Recommended for Development)

```bash
# Clone repository
git clone <repository-url>
cd dev-box
git checkout kvm_switch

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

#### Option 2: Install from PyPI (Future)

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install package
pip install agent-vm
```

### Verify Installation

```bash
# Check Python package
python -c "import agent_vm; print(agent_vm.__version__)"

# Check libvirt connection
python -c "from agent_vm.core.connection import LibvirtConnection; \
           conn = LibvirtConnection(); conn.open()"

# Run test suite
pytest tests/unit/ -v
```

---

## Quick Start

### 1. Set Up Networks

Before running VMs, configure the required libvirt networks:

```bash
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
  <!-- Allow DNS -->
  <rule action='accept' direction='out'>
    <udp dstportstart='53' dstportend='53'/>
  </rule>
  <!-- Allow HTTP/HTTPS -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='80' dstportend='80'/>
  </rule>
  <rule action='accept' direction='out'>
    <tcp dstportstart='443' dstportend='443'/>
  </rule>
  <!-- Allow SSH (git) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='22' dstportend='22'/>
  </rule>
  <!-- Allow responses only -->
  <rule action='accept' direction='in'>
    <all state='ESTABLISHED,RELATED'/>
  </rule>
  <!-- Block everything else -->
  <rule action='drop' direction='in' priority='1000'>
    <all state='NEW'/>
  </rule>
  <rule action='drop' direction='out' priority='1000'>
    <all/>
  </rule>
</filter>
EOF

sudo virsh nwfilter-define /tmp/agent-network-filter.xml

# Verify
virsh net-list --all
virsh nwfilter-list
```

### 2. Create Your First VM

```python
import asyncio
from pathlib import Path
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.template import VMTemplate, ResourceProfile
from agent_vm.core.vm import VM, VMState

async def create_and_run_vm():
    # Connect to libvirt
    conn = LibvirtConnection()
    conn.open()

    try:
        # Create VM template with standard resources
        template = VMTemplate(
            name="my-first-vm",
            resources=ResourceProfile(vcpu=2, memory_mib=2048)
        )

        # Define VM
        xml = template.generate_xml()
        domain = conn.connection.defineXML(xml)
        vm = VM(domain)

        print(f"VM created: {vm.name} (UUID: {vm.uuid})")

        # Start VM
        vm.start()
        print(f"VM state: {vm.get_state()}")

        # Wait for VM to be ready
        await vm.wait_for_state(VMState.RUNNING, timeout=30)
        print("VM is running!")

        # Stop VM
        vm.stop(graceful=True)
        await vm.wait_for_state(VMState.SHUTOFF, timeout=10)
        print("VM stopped")

    finally:
        # Cleanup
        if domain.isActive():
            domain.destroy()
        domain.undefine()
        conn.close()

# Run example
asyncio.run(create_and_run_vm())
```

### 3. Execute Agent Code

```python
import asyncio
from agent_vm.execution.executor import AgentExecutor
from agent_vm.execution.pool import VMPool

async def execute_agent():
    # Initialize VM pool
    pool = VMPool(min_size=2, max_size=10)
    await pool.initialize()

    # Create executor
    executor = AgentExecutor()

    try:
        # Acquire VM from pool
        vm = await pool.acquire(timeout=10)

        # Agent code to execute
        agent_code = """
import sys
print("Hello from isolated VM!")
print(f"Python version: {sys.version}")
"""

        # Execute agent code
        result = await executor.execute(
            vm,
            agent_code,
            timeout=60
        )

        # Check results
        print(f"Success: {result.success}")
        print(f"Exit code: {result.exit_code}")
        print(f"Output:\n{result.stdout}")

    finally:
        # Return VM to pool
        await pool.release(vm)
        await pool.shutdown()

# Run example
asyncio.run(execute_agent())
```

---

## Configuration

### Environment Variables

```bash
# libvirt connection URI (default: qemu:///system)
export LIBVIRT_DEFAULT_URI="qemu:///system"

# Default network mode (default: nat_filtered)
export AGENT_VM_NETWORK_MODE="nat_filtered"

# VM pool configuration
export AGENT_VM_POOL_MIN_SIZE="5"
export AGENT_VM_POOL_MAX_SIZE="20"

# Execution timeout (seconds)
export AGENT_VM_EXEC_TIMEOUT="300"

# Metrics export
export AGENT_VM_METRICS_PORT="9090"
```

### Configuration File

Create `~/.config/agent-vm/config.yaml`:

```yaml
# libvirt connection
libvirt:
  uri: "qemu:///system"
  connection_timeout: 30

# Default VM settings
vm:
  network_mode: "nat_filtered"
  default_profile: "standard"
  snapshot_format: "internal"

# VM pool configuration
pool:
  min_size: 5
  max_size: 20
  ttl_seconds: 3600
  health_check_interval: 60

# Execution settings
execution:
  default_timeout: 300
  max_timeout: 3600
  workspace_path: "/var/lib/agent-vm/workspace"

# Monitoring
monitoring:
  metrics_enabled: true
  metrics_port: 9090
  audit_log_path: "/var/log/agent-vm/audit.log"
  anomaly_detection: true

# Security
security:
  resource_limits:
    cpu_shares: 1024
    memory_hard_limit_mib: 2048
  network_filter: "agent-network-filter"
```

---

## Usage Examples

### Example 1: Basic VM Lifecycle

```python
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.template import VMTemplate
from agent_vm.core.vm import VM

# Connect to libvirt
conn = LibvirtConnection()
conn.open()

# Create VM
template = VMTemplate(name="example-vm")
domain = conn.connection.defineXML(template.generate_xml())
vm = VM(domain)

# Start VM
vm.start()
print(f"VM {vm.name} is {vm.get_state()}")

# Stop VM
vm.stop()

# Cleanup
domain.undefine()
conn.close()
```

### Example 2: Snapshot Management

```python
from agent_vm.core.snapshot import SnapshotManager

# Create snapshot manager
manager = SnapshotManager()

# Create snapshot
snapshot = manager.create_snapshot(
    vm,
    name="golden-state",
    description="Clean initial state"
)
print(f"Created snapshot: {snapshot.name}")

# Do some work in VM
# ...

# Restore to snapshot
manager.restore_snapshot(vm, snapshot)
print("Restored to golden state")

# List all snapshots
snapshots = manager.list_snapshots(vm)
for snap in snapshots:
    print(f"- {snap.name}: {snap.description}")

# Delete snapshot
manager.delete_snapshot(vm, snapshot)
```

### Example 3: Agent Execution with Timeout

```python
import asyncio
from agent_vm.execution.executor import AgentExecutor, ExecutionConfig

async def execute_with_timeout():
    executor = AgentExecutor()

    # Long-running agent code
    agent_code = """
import time
time.sleep(100)  # This will timeout
"""

    # Execute with 10 second timeout
    config = ExecutionConfig(timeout=10)
    result = await executor.execute(vm, agent_code, config=config)

    if result.timeout:
        print("Execution timed out (expected)")

asyncio.run(execute_with_timeout())
```

### Example 4: VM Pool Usage

```python
import asyncio
from agent_vm.execution.pool import VMPool

async def use_vm_pool():
    # Create pool
    pool = VMPool(min_size=3, max_size=10)
    await pool.initialize()

    # Acquire multiple VMs concurrently
    vms = []
    for i in range(5):
        vm = await pool.acquire(timeout=10)
        vms.append(vm)
        print(f"Acquired VM {i+1}: {vm.name}")

    # Use VMs
    # ...

    # Release VMs back to pool
    for vm in vms:
        await pool.release(vm)

    # Shutdown pool
    await pool.shutdown()

asyncio.run(use_vm_pool())
```

---

## Network Modes

### NAT-Filtered Mode (DEFAULT)

**Use Case**: Standard agent operations requiring internet access

**What's Allowed**:
- DNS (UDP 53)
- HTTP/HTTPS (TCP 80, 443)
- SSH (TCP 22) for git operations
- Git protocol (TCP 9418)

**What's Blocked**:
- Unsolicited incoming connections
- Arbitrary outgoing ports
- VM-to-host communication (except control channels)
- VM-to-VM communication

**Example**:
```python
from agent_vm.core.template import VMTemplate, NetworkMode

template = VMTemplate(
    name="agent-vm",
    network_mode=NetworkMode.NAT_FILTERED  # Default
)
```

### Isolated Mode

**Use Case**: Testing untrusted code with no network access

**Security**: Maximum isolation, no external connectivity

**Example**:
```python
template = VMTemplate(
    name="untrusted-vm",
    network_mode=NetworkMode.ISOLATED
)
```

### Checking Network Configuration

```bash
# Verify network is active
virsh net-list

# Check network filter
virsh nwfilter-list
virsh nwfilter-dumpxml agent-network-filter

# Test from inside VM
ping -c 1 google.com  # Should work (NAT-filtered)
curl https://httpbin.org/get  # Should work (HTTPS allowed)
curl http://example.com:8080  # Should fail (port blocked)
```

---

## Resource Profiles

### Standard Profile (DEFAULT)

```python
from agent_vm.core.template import ResourceProfile

profile = ResourceProfile(
    vcpu=2,
    memory_mib=2048,
    disk_gib=20
)
```

**Use Case**: Normal CLI agent operations

### Light Profile

```python
profile = ResourceProfile(
    vcpu=1,
    memory_mib=1024,
    disk_gib=10
)
```

**Use Case**: Simple scripts, quick tests

### Intensive Profile

```python
profile = ResourceProfile(
    vcpu=4,
    memory_mib=4096,
    disk_gib=40
)
```

**Use Case**: Large codebases, complex builds

### Custom Profile

```python
profile = ResourceProfile(
    vcpu=8,
    memory_mib=8192,
    disk_gib=100,
    cpu_shares=2048  # Higher priority
)
```

---

## Monitoring

### Prometheus Metrics

Start metrics server:

```python
from agent_vm.monitoring.metrics import MetricsCollector

# Create collector
collector = MetricsCollector()

# Start metrics server on port 9090
collector.start_server(port=9090)

# Metrics are now available at http://localhost:9090/metrics
```

Available metrics:

```
# VM lifecycle
agent_vm_boot_duration_seconds{vm_id}
agent_vm_pool_size{pool_id}
agent_vm_pool_acquire_duration_seconds{pool_id}

# Resource usage
agent_vm_cpu_usage_percent{vm_id}
agent_vm_memory_usage_bytes{vm_id}
agent_vm_disk_read_bytes_total{vm_id}
agent_vm_disk_write_bytes_total{vm_id}

# Execution
agent_execution_total{status}
agent_execution_duration_seconds
agent_execution_timeout_total
```

### Audit Logging

Enable structured audit logs:

```python
from agent_vm.monitoring.audit import AuditLogger

logger = AuditLogger(log_path="/var/log/agent-vm/audit.log")

# Logs are written in JSON format
# {
#   "timestamp": "2025-10-20T12:00:00Z",
#   "event_type": "vm_created",
#   "vm_id": "vm-123",
#   "details": {...}
# }
```

### Anomaly Detection

Enable behavioral monitoring:

```python
from agent_vm.monitoring.anomaly import AnomalyDetector

detector = AnomalyDetector()

# Analyze VM behavior
anomalies = await detector.analyze(vm)

for anomaly in anomalies:
    print(f"Anomaly detected: {anomaly.type}")
    print(f"Severity: {anomaly.severity}")
    print(f"Details: {anomaly.details}")
```

---

## Troubleshooting

### Issue: Cannot Connect to libvirt

**Symptoms**:
```
libvirt.libvirtError: Failed to connect to the hypervisor
```

**Solutions**:
```bash
# Check libvirtd service
sudo systemctl status libvirtd

# Start if not running
sudo systemctl start libvirtd

# Verify user permissions
groups | grep libvirt

# If not in group, add user
sudo usermod -a -G libvirt $USER
newgrp libvirt
```

### Issue: Network Not Found

**Symptoms**:
```
libvirt.libvirtError: Network not found: no network with matching name 'agent-nat-filtered'
```

**Solutions**:
```bash
# List networks
virsh net-list --all

# If missing, create network
virsh net-define /path/to/agent-nat-filtered.xml
virsh net-start agent-nat-filtered
virsh net-autostart agent-nat-filtered
```

### Issue: VM Boot Timeout

**Symptoms**:
```
VMError: Timeout waiting for VMState.RUNNING
```

**Solutions**:
```bash
# Check VM status
virsh list --all

# View VM console
virsh console <vm-name>

# Check logs
sudo journalctl -u libvirtd -f

# Increase timeout
await vm.wait_for_state(VMState.RUNNING, timeout=60)  # 60 seconds
```

### Issue: Pool Acquisition Timeout

**Symptoms**:
```
TimeoutError: No VM available in pool within 10 seconds
```

**Solutions**:
```python
# Increase pool size
pool = VMPool(min_size=10, max_size=30)

# Increase acquisition timeout
vm = await pool.acquire(timeout=30)

# Check pool health
status = await pool.get_status()
print(f"Available VMs: {status.available}")
```

### Issue: Execution Timeout

**Symptoms**:
```
ExecutionResult(success=False, timeout=True)
```

**Solutions**:
```python
# Increase execution timeout
config = ExecutionConfig(timeout=600)  # 10 minutes
result = await executor.execute(vm, code, config=config)

# Check agent code for infinite loops
# Add progress logging to agent code
```

---

## Best Practices

### 1. Use VM Pools for Performance

```python
# ✅ Good: Pre-warmed pool
pool = VMPool(min_size=5, max_size=20)
await pool.initialize()
vm = await pool.acquire()  # <100ms

# ❌ Bad: Create VM on demand
template = VMTemplate(name="vm")
domain = conn.connection.defineXML(template.generate_xml())
vm = VM(domain)
vm.start()  # ~2 seconds
```

### 2. Always Use Context Managers

```python
# ✅ Good: Automatic cleanup
with LibvirtConnection() as conn:
    # Use connection
    pass  # Automatically closed

# ❌ Bad: Manual cleanup
conn = LibvirtConnection()
conn.open()
# ... might forget to close
conn.close()
```

### 3. Set Appropriate Timeouts

```python
# ✅ Good: Reasonable timeouts
result = await executor.execute(
    vm,
    code,
    timeout=300  # 5 minutes
)

# ❌ Bad: No timeout or too long
result = await executor.execute(vm, code)  # Uses default, might be too short
result = await executor.execute(vm, code, timeout=3600)  # 1 hour is too long
```

### 4. Monitor Resource Usage

```python
# ✅ Good: Enable monitoring
collector = MetricsCollector()
collector.start_server()

detector = AnomalyDetector()
anomalies = await detector.analyze(vm)

# ❌ Bad: No monitoring
# Agents might consume excessive resources
```

### 5. Use Golden Snapshots

```python
# ✅ Good: Snapshot-based testing
golden = manager.create_snapshot(vm, "golden")
# Test agent
manager.restore_snapshot(vm, golden)
# Clean state restored

# ❌ Bad: Recreate VM each time
vm.destroy()
vm = create_new_vm()  # Slower
```

### 6. Choose Appropriate Network Mode

```python
# ✅ Good: Use NAT-filtered for agents needing internet
template = VMTemplate(
    name="agent-vm",
    network_mode=NetworkMode.NAT_FILTERED
)

# ✅ Good: Use isolated for untrusted code
template = VMTemplate(
    name="untrusted-vm",
    network_mode=NetworkMode.ISOLATED
)

# ❌ Bad: Always using isolated when agents need network
# Agents will fail when trying to access APIs
```

### 7. Handle Errors Gracefully

```python
# ✅ Good: Error handling
try:
    result = await executor.execute(vm, code)
    if not result.success:
        logger.error("Execution failed", error=result.stderr)
except VMError as e:
    logger.error("VM error", error=str(e))
finally:
    await pool.release(vm)

# ❌ Bad: No error handling
result = await executor.execute(vm, code)  # Might raise exception
```

### 8. Clean Up Resources

```python
# ✅ Good: Proper cleanup
try:
    vm = await pool.acquire()
    result = await executor.execute(vm, code)
finally:
    await pool.release(vm)  # Always release

# ❌ Bad: Resource leak
vm = await pool.acquire()
result = await executor.execute(vm, code)
# Forgot to release VM
```

---

## Additional Resources

- **Architecture Documentation**: See `ARCHITECTURE.md` for system design details
- **API Documentation**: See `docs/api/` for detailed API reference
- **Developer Guide**: See `docs/DEVELOPER_GUIDE.md` for development information
- **libvirt Documentation**: https://libvirt.org/docs.html
- **Python libvirt**: https://libvirt.org/python.html

---

**Need Help?**

- Check the [Troubleshooting](#troubleshooting) section
- Review example code in `examples/` directory
- Read the API documentation in `docs/api/`
- Check existing test files in `tests/` for usage patterns
