# Integration Test Setup and Status

## Purpose

Integration tests verify that components work correctly with **real libvirt** and KVM virtualization. These tests require actual hardware virtualization and running libvirt daemon.

## Prerequisites

### 1. KVM Virtualization Available

```bash
# Check CPU support
egrep -c '(vmx|svm)' /proc/cpuinfo  # Should be > 0

# Check KVM modules loaded
lsmod | grep kvm
```

**Status:** ✅ KVM available (32 CPU cores with virtualization support)

### 2. Libvirt Running

```bash
# Check libvirt daemon
sudo systemctl status libvirtd

# Test connection
virsh -c qemu:///system list --all
```

**Status:** ✅ Libvirt daemon running and accessible

### 3. Python Dependencies

```bash
# Install required packages
pip install libvirt-python pytest-asyncio
```

**Status:** ✅ Dependencies installed

### 4. Required Networks

Integration tests require two libvirt networks:

#### agent-nat-filtered (DEFAULT - for CLI agents)
NAT network with filtering to allow controlled internet access.

**Required for:** Testing agents that need network (Claude CLI, etc.)

**Setup:**
```bash
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
```

**Status:** ⚠️  NOT CONFIGURED - see NETWORK_CONFIG_GUIDE.md

#### agent-isolated (for high-security testing)
Isolated network with no external connectivity.

**Required for:** Testing untrusted code without network access

**Setup:**
```bash
cat > /tmp/agent-isolated.xml << 'EOF'
<network>
  <name>agent-isolated</name>
  <bridge name='virbr-isolated'/>
  <forward mode='none'/>
  <ip address='192.168.100.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.100.10' end='192.168.100.254'/>
    </dhcp>
  </ip>
</network>
EOF

sudo virsh net-define /tmp/agent-isolated.xml
sudo virsh net-start agent-isolated
sudo virsh net-autostart agent-isolated
```

**Status:** ⚠️  NOT CONFIGURED - see NETWORK_CONFIG_GUIDE.md

#### Network Filter (for security)
Whitelist-based filtering for NAT network.

**Setup:**
```bash
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
  <!-- Allow git protocol -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='9418' dstportend='9418'/>
  </rule>
  <!-- Allow established connections -->
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
```

**Status:** ⚠️  NOT CONFIGURED

## Running Integration Tests

### Quick Start

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run excluding skipped tests
pytest tests/integration/ -v -m "not skip"

# Run specific test class
pytest tests/integration/test_vm_lifecycle.py::TestVMLifecycleBasic -v

# Run with detailed output
pytest tests/integration/ -v -s
```

### Test Organization

```
tests/integration/
├── conftest.py                    # Shared fixtures
├── test_vm_lifecycle.py          # VM lifecycle tests
├── test_filesystem.py            # virtio-9p tests (future)
├── test_snapshot.py              # Snapshot tests (future)
└── test_executor.py              # Agent execution tests (future)
```

## Current Test Status

### ✅ Passing Tests (5)

1. **test_libvirt_connection_works** - Libvirt connection and system info
2. **test_workspace_creation** - Test workspace fixture
3. **test_cleanup_fixture_available** - Cleanup fixture availability
4. **test_pytest_asyncio_available** - Async test support
5. **test_async_tests_work** - Async execution verification

### ⚠️  Skipped Tests (1)

1. **test_network_configuration_exists** - Networks not configured (EXPECTED)
   - Reason: Agent networks not yet set up
   - Action: Follow NETWORK_CONFIG_GUIDE.md to configure

### 🚧 Awaiting Implementation (3)

These tests are marked as `@pytest.mark.skip` and will be enabled as components are implemented:

1. **test_create_vm_from_template** - Requires VMTemplate class (Phase 1, Task 1.5)
2. **test_vm_start_stop_lifecycle** - Requires VM class (Phase 1, Task 1.3)
3. **test_vm_snapshot_restore** - Requires SnapshotManager (Phase 1, Task 1.6)

## Implementation Dependencies

Integration tests depend on the following components being implemented (in TDD order):

### Phase 1: Foundation (Current)

1. ✅ **LibvirtConnection** - Connection management
2. ✅ **VM** - Domain abstraction with lifecycle
3. 🚧 **VMTemplate** - XML generation (Task 1.5)
4. 🚧 **SnapshotManager** - Snapshot lifecycle (Task 1.6)

Once these are implemented, corresponding integration tests will be enabled.

## Test Fixtures Available

### `real_libvirt_connection`
- Scope: module
- Provides: Active libvirt.virConnect instance
- Usage: Real libvirt operations

### `test_workspace`
- Scope: function
- Provides: Path to temporary workspace with standard structure
- Structure: workspace/{input,output,work}/

### `cleanup_test_vms`
- Scope: function
- Provides: Automatic cleanup of test VMs
- Behavior: Destroys and undefines all VMs starting with "test-"

### `verify_kvm_available`
- Scope: session
- Provides: bool (True if KVM available)
- Behavior: Skips tests if KVM not available

### `verify_libvirt_networks`
- Scope: session
- Provides: dict of network status
- Behavior: Skips tests if required networks missing

## Troubleshooting

### "KVM virtualization not available"

**Cause:** CPU doesn't support virtualization or modules not loaded

**Fix:**
```bash
# Check CPU support
egrep -c '(vmx|svm)' /proc/cpuinfo

# Load KVM modules
sudo modprobe kvm
sudo modprobe kvm_intel  # or kvm_amd
```

### "Required networks missing"

**Cause:** agent-nat-filtered or agent-isolated networks not configured

**Fix:** Follow network setup in this README or NETWORK_CONFIG_GUIDE.md

### "Permission denied" when connecting to libvirt

**Cause:** User not in libvirt group

**Fix:**
```bash
sudo usermod -a -G libvirt $USER
newgrp libvirt  # or logout/login
```

### "Module not found: libvirt"

**Cause:** libvirt-python not installed

**Fix:**
```bash
pip install libvirt-python
```

## Next Steps

1. **Configure Networks** (REQUIRED for full testing)
   - Run network setup commands above
   - Verify with: `virsh net-list --all`

2. **Implement Core Components** (following TDD)
   - VMTemplate (Phase 1, Task 1.5)
   - SnapshotManager (Phase 1, Task 1.6)
   - Enable corresponding integration tests

3. **Add More Integration Tests**
   - Filesystem sharing (virtio-9p)
   - VM pool management
   - Agent execution

4. **Performance Benchmarks**
   - VM boot time (<2s target)
   - Snapshot restore (<1s target)
   - Pool acquire time (<100ms target)

## References

- **Implementation Guide:** ../IMPLEMENTATION_GUIDE.md (Phase 1, Day 9-12)
- **TDD Plan:** ../TDD_IMPLEMENTATION_PLAN.md (Section 1.7)
- **Architecture:** ../ARCHITECTURE.md (Section 3)
- **Network Config:** ../NETWORK_CONFIG_GUIDE.md
