# KVM Agent Isolation Architecture

**Version:** 1.0.0
**Status:** Design Phase
**Target:** Production-ready KVM-based CLI agent isolation for safe agent testing

## Executive Summary

This architecture implements hardware-level isolation for CLI coding agents (like Claude Code) using KVM/libvirt, providing a secure execution environment that balances safety with productivity. Unlike container-based sandboxes, this system provides true hardware isolation while maintaining fast iteration cycles through snapshot-based testing.

**Key Characteristics:**
- **Boot Time:** <500ms (target), <2s (MVP)
- **Isolation:** Hardware + 4 OS-level security layers
- **Network:** Controlled internet access (NAT with filtering) by default
- **Testing Cycle:** <5s from destroy to ready
- **Concurrency:** 20+ VMs per host (workload-dependent)
- **Monitoring:** Real-time resource tracking and anomaly detection

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE (Host System)                       │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                    Agent Management Layer                       │     │
│  │                                                                  │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │     │
│  │  │ Agent Router │  │   VM Pool    │  │  Lifecycle   │         │     │
│  │  │  (API/CLI)   │  │  Manager     │  │   Manager    │         │     │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │     │
│  │         │                  │                  │                  │     │
│  │         └──────────────────┴──────────────────┘                  │     │
│  │                            │                                      │     │
│  └────────────────────────────┼──────────────────────────────────┘     │
│                                │                                         │
│  ┌────────────────────────────┼──────────────────────────────────┐     │
│  │            Observability & Safety Layer                         │     │
│  │                            │                                      │     │
│  │  ┌──────────────┐  ┌──────┴───────┐  ┌──────────────┐         │     │
│  │  │  Metrics     │  │  Audit Log   │  │   Anomaly    │         │     │
│  │  │ (Prometheus) │  │ (Structured) │  │   Detector   │         │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │     │
│  └────────────────────────────┼──────────────────────────────────┘     │
│                                │                                         │
│  ┌────────────────────────────┼──────────────────────────────────┐     │
│  │                  Libvirt Management Layer                       │     │
│  │                            │                                      │     │
│  │  VM Lifecycle | Snapshots | Networks | Storage | Resources     │     │
│  └────────────────────────────┼──────────────────────────────────┘     │
│                                │                                         │
├────────────────────────────────┼─────────────────────────────────────────┤
│                                │      KVM/QEMU Hypervisor               │
│                                │   (Hardware Virtualization)             │
├────────────────────────────────┼─────────────────────────────────────────┤
│                                │                                         │
│  ┌────────────────────────────▼──────────────────────────────────┐     │
│  │                      AGENT VM (Isolated)                        │     │
│  │                                                                  │     │
│  │  ┌──────────────────────────────────────────────────────────┐  │     │
│  │  │                  Security Boundaries                      │  │     │
│  │  │                                                            │  │     │
│  │  │  Layer 1: KVM Hardware Isolation                         │  │     │
│  │  │  Layer 2: seccomp (syscall filtering)                    │  │     │
│  │  │  Layer 3: Namespaces (PID/Net/Mount/IPC)                 │  │     │
│  │  │  Layer 4: cgroups (resource limits)                      │  │     │
│  │  │  Layer 5: AppArmor/SELinux (mandatory access control)    │  │     │
│  │  └──────────────────────────────────────────────────────────┘  │     │
│  │                                                                  │     │
│  │  ┌──────────────────────────────────────────────────────────┐  │     │
│  │  │              Communication Channels                       │  │     │
│  │  │                                                            │  │     │
│  │  │  • virtio-vsock    : Control plane (commands, status)   │  │     │
│  │  │  • virtio-9p       : Filesystem (code in, results out)  │  │     │
│  │  │  • qemu-guest-agent: Monitoring and health checks       │  │     │
│  │  │  • virtio-serial   : Emergency console                  │  │     │
│  │  └──────────────────────────────────────────────────────────┘  │     │
│  │                                                                  │     │
│  │  ┌──────────────────────────────────────────────────────────┐  │     │
│  │  │                 Network Configuration                     │  │     │
│  │  │                                                            │  │     │
│  │  │  Mode: isolated (default) | nat (filtered) | bridge      │  │     │
│  │  │  Filter: Allow DNS, HTTP/S only (when NAT)              │  │     │
│  │  │  Monitoring: All connections logged                      │  │     │
│  │  └──────────────────────────────────────────────────────────┘  │     │
│  │                                                                  │     │
│  │  ┌──────────────────────────────────────────────────────────┐  │     │
│  │  │                Filesystem Layout                          │  │     │
│  │  │                                                            │  │     │
│  │  │  /workspace (9p, mapped, read-write)                     │  │     │
│  │  │    ├─ input/     : Agent code injection point           │  │     │
│  │  │    ├─ output/    : Results extraction point             │  │     │
│  │  │    └─ work/      : Agent working directory              │  │     │
│  │  │                                                            │  │     │
│  │  │  /tools (9p, mapped, read-only)                          │  │     │
│  │  │    └─ utilities/ : Pre-installed tool binaries          │  │     │
│  │  │                                                            │  │     │
│  │  │  / (qcow2, snapshot-backed, ephemeral)                   │  │     │
│  │  │    ├─ OS and system files                                │  │     │
│  │  │    ├─ Package caches (npm, pip, apt)                     │  │     │
│  │  │    └─ Agent execution environment                        │  │     │
│  │  └──────────────────────────────────────────────────────────┘  │     │
│  │                                                                  │     │
│  │  ┌──────────────────────────────────────────────────────────┐  │     │
│  │  │            Agent Execution Environment                    │  │     │
│  │  │                                                            │  │     │
│  │  │  • Python 3.12 (pyenv)                                   │  │     │
│  │  │  • Node.js 20 (nvm)                                      │  │     │
│  │  │  • Development tools (git, gcc, make, etc.)              │  │     │
│  │  │  • Package managers (pip, npm, apt)                      │  │     │
│  │  │  • CLI tools (gh, aws, docker client, etc.)             │  │     │
│  │  │  • Agent runner service (listens on vsock)              │  │     │
│  │  └──────────────────────────────────────────────────────────┘  │     │
│  └──────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Agent Management Layer

#### 1.1 Agent Router
**Purpose:** Entry point for all agent execution requests (API and CLI)

**Responsibilities:**
- Request validation and authentication
- Route requests to appropriate VM pool
- Result aggregation and response formatting
- Error handling and retry logic

**Interface:**
```python
class AgentRouter:
    """Main entry point for agent execution"""

    async def execute(
        self,
        agent_code: str,
        profile: AgentProfile,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute agent code with specified profile"""

    async def execute_with_snapshot(
        self,
        agent_code: str,
        snapshot_id: str
    ) -> ExecutionResult:
        """Execute from specific snapshot state"""

    async def health_check(self) -> HealthStatus:
        """System health and availability"""
```

**Configuration:**
```yaml
agent_router:
  max_concurrent_requests: 50
  request_timeout_seconds: 600
  retry_attempts: 3
  retry_backoff_seconds: 5
```

#### 1.2 VM Pool Manager
**Purpose:** Maintain pool of pre-warmed VMs for instant execution

**Responsibilities:**
- Pre-create and maintain VM pool
- Health check and refresh stale VMs
- Pool size auto-scaling based on demand
- VM acquisition and release

**Algorithm:**
```python
class VMPoolManager:
    """Manages pool of ready-to-use VMs"""

    def __init__(
        self,
        min_size: int = 5,
        max_size: int = 20,
        ttl_seconds: int = 3600
    ):
        self.pool: Queue[VM] = Queue(maxsize=max_size)
        self.min_size = min_size
        self.max_size = max_size
        self.ttl = ttl_seconds

    async def acquire(self, timeout: int = 30) -> VM:
        """Get VM from pool (creates if empty)"""
        try:
            vm = await asyncio.wait_for(
                self.pool.get(),
                timeout=timeout
            )
            if self._is_stale(vm):
                await vm.destroy()
                return await self._create_fresh_vm()
            return vm
        except asyncio.TimeoutError:
            # Pool exhausted, create on-demand
            return await self._create_fresh_vm()

    async def release(self, vm: VM):
        """Return VM to pool (or destroy if full)"""
        if self.pool.full():
            await vm.destroy()
        else:
            await vm.reset_to_golden()
            await self.pool.put(vm)

    async def maintain_pool(self):
        """Background task: maintain pool size"""
        while True:
            current_size = self.pool.qsize()
            if current_size < self.min_size:
                for _ in range(self.min_size - current_size):
                    vm = await self._create_fresh_vm()
                    await self.pool.put(vm)
            await asyncio.sleep(10)
```

**Metrics:**
- Pool size (current, min, max)
- Acquisition time (p50, p95, p99)
- Pool hits vs. misses
- VM age distribution

#### 1.3 Lifecycle Manager
**Purpose:** VM creation, destruction, snapshot management

**Responsibilities:**
- Create VMs from templates
- Snapshot creation and management
- Snapshot-based cloning
- VM destruction and cleanup
- Golden image updates

**API:**
```python
class LifecycleManager:
    """VM lifecycle operations"""

    async def create_vm(
        self,
        template: VMTemplate,
        network_mode: NetworkMode = NetworkMode.ISOLATED
    ) -> VM:
        """Create new VM from template"""

    async def create_snapshot(
        self,
        vm: VM,
        name: str,
        description: str = ""
    ) -> Snapshot:
        """Create VM snapshot"""

    async def restore_snapshot(
        self,
        vm: VM,
        snapshot: Snapshot
    ) -> None:
        """Restore VM to snapshot state"""

    async def clone_from_snapshot(
        self,
        snapshot: Snapshot,
        vm_name: str
    ) -> VM:
        """Create new VM from snapshot (COW)"""

    async def destroy_vm(self, vm: VM) -> None:
        """Destroy VM and clean up resources"""

    async def update_golden_image(
        self,
        provisioning_script: str
    ) -> Snapshot:
        """Update and snapshot golden image"""
```

**Golden Image Strategy:**
```yaml
Golden Snapshots:
  - base: Minimal OS + security hardening
  - dev-tools: base + development toolchain
  - agent-ready: dev-tools + agent runtime components

Update Schedule:
  - Weekly: Security updates
  - Monthly: Toolchain updates
  - On-demand: Critical patches

Versioning:
  - Semantic versioning (major.minor.patch)
  - Rollback capability to previous versions
  - Compatibility matrix with agent versions
```

---

### 2. Observability & Safety Layer

#### 2.1 Metrics Collector (Prometheus)
**Purpose:** Real-time resource monitoring and performance metrics

**Metrics Exposed:**
```yaml
# VM Resource Metrics
agent_vm_cpu_usage_percent{vm_id, agent_id}
agent_vm_memory_usage_bytes{vm_id, agent_id}
agent_vm_disk_read_bytes_total{vm_id, agent_id, device}
agent_vm_disk_write_bytes_total{vm_id, agent_id, device}
agent_vm_network_rx_bytes_total{vm_id, agent_id, interface}
agent_vm_network_tx_bytes_total{vm_id, agent_id, interface}

# Lifecycle Metrics
agent_vm_boot_duration_seconds{vm_id}
agent_vm_snapshot_restore_duration_seconds{vm_id}
agent_vm_pool_size{pool_id}
agent_vm_pool_acquire_duration_seconds{pool_id}

# Execution Metrics
agent_execution_duration_seconds{agent_id, status}
agent_execution_total{agent_id, status}
agent_execution_timeout_total{agent_id}

# Safety Metrics
agent_resource_limit_violations_total{vm_id, resource_type}
agent_network_connection_attempts_total{vm_id, allowed}
agent_syscall_violations_total{vm_id, syscall}
```

**Implementation:**
```python
from prometheus_client import Counter, Histogram, Gauge

class MetricsCollector:
    """Prometheus metrics collection"""

    def __init__(self):
        self.executions = Counter(
            'agent_execution_total',
            'Total agent executions',
            ['agent_id', 'status']
        )
        self.execution_duration = Histogram(
            'agent_execution_duration_seconds',
            'Agent execution duration'
        )
        self.vm_cpu = Gauge(
            'agent_vm_cpu_usage_percent',
            'VM CPU usage',
            ['vm_id']
        )

    async def collect_vm_stats(self, vm: VM):
        """Collect and update VM metrics"""
        stats = await vm.get_stats()
        self.vm_cpu.labels(vm_id=vm.id).set(stats.cpu_percent)
        # ... other metrics
```

#### 2.2 Audit Logger
**Purpose:** Structured logging of all security-relevant events

**Log Schema:**
```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "event_type": "agent_execution_started",
  "agent_id": "agent-abc123",
  "vm_id": "vm-xyz789",
  "user_id": "user-456",
  "details": {
    "code_hash": "sha256:...",
    "profile": "standard",
    "network_mode": "isolated"
  }
}
```

**Event Types:**
```yaml
Lifecycle Events:
  - vm_created
  - vm_started
  - vm_stopped
  - vm_destroyed
  - snapshot_created
  - snapshot_restored

Execution Events:
  - agent_execution_started
  - agent_execution_completed
  - agent_execution_failed
  - agent_execution_timeout

Security Events:
  - resource_limit_exceeded
  - network_connection_blocked
  - syscall_violation
  - filesystem_access_denied
  - anomaly_detected

Administrative Events:
  - golden_image_updated
  - configuration_changed
  - user_authenticated
```

**Implementation:**
```python
import structlog

class AuditLogger:
    """Structured audit logging"""

    def __init__(self):
        self.logger = structlog.get_logger()

    def log_event(
        self,
        event_type: str,
        agent_id: str,
        vm_id: str,
        details: dict
    ):
        """Log structured event"""
        self.logger.info(
            event_type,
            agent_id=agent_id,
            vm_id=vm_id,
            **details
        )
```

#### 2.3 Anomaly Detector
**Purpose:** Behavioral analysis and threat detection

**Detection Algorithms:**

1. **Statistical Anomaly Detection**
```python
class StatisticalAnomalyDetector:
    """Detect deviations from baseline using statistics"""

    def __init__(self, baseline_profile: ResourceProfile):
        self.baseline = baseline_profile
        self.z_score_threshold = 3.0

    def detect(self, current: ResourceProfile) -> List[Anomaly]:
        """Detect anomalies using z-score"""
        anomalies = []

        # CPU usage spike
        z_score = (current.cpu - self.baseline.cpu_mean) / self.baseline.cpu_stddev
        if abs(z_score) > self.z_score_threshold:
            anomalies.append(Anomaly(
                type="cpu_spike",
                severity="high" if z_score > 4 else "medium",
                details={"z_score": z_score, "current": current.cpu}
            ))

        return anomalies
```

2. **Rule-Based Detection**
```python
class RuleBasedDetector:
    """Detect known malicious patterns"""

    RULES = {
        "crypto_mining": {
            "cpu_usage": ">95% for >60s",
            "network": "connections to known mining pools"
        },
        "data_exfiltration": {
            "network_tx": ">100MB in <10s",
            "destinations": "unknown external IPs"
        },
        "fork_bomb": {
            "processes": ">1000 in <5s"
        }
    }
```

3. **Machine Learning (Future Enhancement)**
```yaml
Approach: Unsupervised learning (Isolation Forest, Autoencoders)
Training Data: Historical agent execution traces
Features:
  - Resource usage patterns
  - Syscall sequences
  - Network behavior
  - File access patterns
Deployment: Sidecar model service
```

**Response Actions:**
```python
class AnomalyResponder:
    """Respond to detected anomalies"""

    async def handle_anomaly(self, anomaly: Anomaly, vm: VM):
        """Execute response based on severity"""

        if anomaly.severity == "critical":
            # Immediate kill
            await vm.force_stop()
            await self.alert_admin(anomaly)

        elif anomaly.severity == "high":
            # Graceful stop + preserve for analysis
            await self.create_forensic_snapshot(vm)
            await vm.stop()
            await self.alert_admin(anomaly)

        elif anomaly.severity == "medium":
            # Log and continue monitoring
            await self.audit_logger.log_anomaly(anomaly)
            await self.increase_monitoring_frequency(vm)
```

---

### 3. Libvirt Management Layer

**Wrapper around libvirt API for:**
- Type-safe Python interfaces
- Async/await support
- Error handling and retries
- Resource cleanup

**Key Abstractions:**
```python
class VM:
    """High-level VM abstraction"""

    async def start(self) -> None:
        """Start VM and wait for ready"""

    async def stop(self, graceful: bool = True) -> None:
        """Stop VM (graceful or force)"""

    async def get_stats(self) -> VMStats:
        """Get current resource usage"""

    async def execute_command(
        self,
        command: str,
        timeout: int = 60
    ) -> CommandResult:
        """Execute command via guest agent"""

    async def inject_file(
        self,
        local_path: Path,
        remote_path: Path
    ) -> None:
        """Copy file into VM via 9p"""

    async def extract_file(
        self,
        remote_path: Path,
        local_path: Path
    ) -> None:
        """Copy file from VM via 9p"""
```

---

### 4. Communication Channels

#### 4.1 virtio-vsock (Control Channel)
**Purpose:** Low-latency host-guest communication for control plane

**Protocol Design:**
```python
class VsockProtocol:
    """Message protocol over vsock"""

    MESSAGE_TYPES = {
        "EXECUTE": 1,      # Execute agent code
        "STATUS": 2,       # Query status
        "STOP": 3,         # Stop execution
        "RESULT": 4,       # Return results
        "HEARTBEAT": 5,    # Health check
        "ERROR": 6,        # Error notification
    }

    async def send_message(
        self,
        msg_type: int,
        payload: bytes
    ) -> None:
        """Send message to guest"""
        header = struct.pack(
            "!BHI",
            msg_type,
            len(payload),
            crc32(payload)
        )
        await self.socket.sendall(header + payload)

    async def receive_message(self) -> Tuple[int, bytes]:
        """Receive message from guest"""
        header = await self.socket.recv(7)
        msg_type, length, checksum = struct.unpack("!BHI", header)
        payload = await self.socket.recv(length)

        if crc32(payload) != checksum:
            raise ProtocolError("Checksum mismatch")

        return msg_type, payload
```

**Guest Agent (runs in VM):**
```python
class GuestAgent:
    """Agent running inside VM, listening on vsock"""

    async def run(self):
        """Main event loop"""
        async with VsockListener(port=9999) as listener:
            while True:
                msg_type, payload = await listener.receive_message()

                if msg_type == VsockProtocol.MESSAGE_TYPES["EXECUTE"]:
                    await self.handle_execute(payload)
                elif msg_type == VsockProtocol.MESSAGE_TYPES["STATUS"]:
                    await self.handle_status()
                elif msg_type == VsockProtocol.MESSAGE_TYPES["STOP"]:
                    await self.handle_stop()

    async def handle_execute(self, payload: bytes):
        """Execute agent code"""
        agent_code = payload.decode('utf-8')

        # Write code to file
        code_path = Path("/workspace/input/agent.py")
        code_path.write_text(agent_code)

        # Execute with timeout
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3",
                str(code_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/workspace/work"
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

            await self.send_result(result)

        except asyncio.TimeoutError:
            await self.send_error("Execution timeout")
```

#### 4.2 virtio-9p (Filesystem Sharing)
**Purpose:** Secure file exchange between host and guest

**Security Model: mapped (recommended)**
```xml
<filesystem type='mount' accessmode='mapped'>
  <driver type='path' wrpolicy='immediate'/>
  <source dir='/var/lib/agent-vm/workspace'/>
  <target dir='workspace'/>
</filesystem>
```

**Directory Structure:**
```
/var/lib/agent-vm/
├── workspace/
│   ├── input/        # Code injection (host → guest)
│   │   └── agent.py
│   ├── output/       # Results extraction (guest → host)
│   │   └── results.json
│   └── work/         # Agent working directory (bidirectional)
│       ├── .git/
│       ├── src/
│       └── ...
└── tools/            # Read-only utilities
    └── bin/
```

**Usage Pattern:**
```python
# Host: Inject agent code
workspace = Path("/var/lib/agent-vm/workspace")
input_dir = workspace / "input"
(input_dir / "agent.py").write_text(agent_code)

# VM mounts at /workspace (via fstab)
# Guest: Execute agent code
# Agent writes results to /workspace/output/results.json

# Host: Extract results
output_dir = workspace / "output"
results = json.loads((output_dir / "results.json").read_text())
```

#### 4.3 qemu-guest-agent
**Purpose:** VM introspection and guest operations

**Enabled Operations:**
```python
async def introspect_vm(domain: libvirt.virDomain) -> VMInfo:
    """Get detailed VM information via guest agent"""

    # Get OS info
    os_info = json.loads(domain.qemuAgentCommand(
        '{"execute": "guest-get-osinfo"}', 5, 0
    ))

    # Get network interfaces
    interfaces = json.loads(domain.qemuAgentCommand(
        '{"execute": "guest-network-get-interfaces"}', 5, 0
    ))

    # Get running processes
    processes = json.loads(domain.qemuAgentCommand(
        '{"execute": "guest-get-processes"}', 5, 0
    ))

    return VMInfo(
        os=os_info,
        interfaces=interfaces,
        processes=processes
    )
```

---

## Security Model

### Defense-in-Depth Layers

**Layer 1: Hardware Isolation (KVM)**
- Full CPU virtualization (VT-x/AMD-V)
- Memory isolation (EPT/NPT)
- I/O MMU (VT-d/AMD-Vi)
- No shared resources between VMs

**Layer 2: seccomp (Syscall Filtering)**
```yaml
Blocked Syscalls:
  - ptrace (process debugging)
  - uselib (obsolete)
  - _sysctl (kernel parameter modification)
  - afs_syscall (obsolete)
  - create_module, delete_module (kernel module manipulation)
  - ioperm, iopl (I/O port access)
  - kexec_load (kernel loading)

Allowed: Standard libc syscalls + virtio operations
```

**Layer 3: Linux Namespaces**
```yaml
Namespaces Enabled:
  - PID: Isolated process tree
  - Network: Private network stack
  - Mount: Private filesystem mounts
  - UTS: Independent hostname
  - IPC: Isolated shared memory
  - User: UID/GID mapping (future)
```

**Layer 4: cgroups (Resource Limits)**
```yaml
Standard Profile:
  CPU:
    shares: 1024
    quota: 200000  # 2 CPUs
    period: 100000
  Memory:
    hard_limit: 2048 MB
    soft_limit: 1536 MB
    swap_limit: 512 MB
  Block I/O:
    weight: 500
    read_bps: 100 MB/s
    write_bps: 50 MB/s
  Network:
    egress_rate: 10 Mbps
```

**Layer 5: AppArmor/SELinux**
```apparmor
profile agent-vm flags=(attach_disconnected) {
  # Allow standard libc
  /lib/** mr,
  /usr/lib/** mr,

  # Allow workspace access
  /workspace/** rw,

  # Allow tools (read-only)
  /tools/** r,

  # Deny everything else
  deny /etc/shadow r,
  deny /root/** rwx,
  deny /proc/kcore r,
  deny @{PROC}/sys/kernel/** w,
  deny mount,
  deny pivot_root,
}
```

### Network Security

**NAT-Filtered Mode (DEFAULT):**
This is the default network mode since CLI agents (Claude CLI, GitHub Copilot, etc.) require internet access for API calls, package downloads, and git operations.

**Security Note:** Despite allowing network access, isolation is still maintained through:
- Network filtering (whitelist-based)
- Connection monitoring and logging
- Anomaly detection for suspicious traffic
- Rate limiting
- No access to host network or other VMs
```xml
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

<!-- Network filter applied to VM interface -->
<interface type='network'>
  <source network='agent-nat-filtered'/>
  <filterref filter='agent-network-filter'/>
</interface>
```

**Network Filter Definition (Default for Agent VMs):**
```xml
<filter name='agent-network-filter' chain='root'>
  <!-- Allow DNS (required for all internet access) -->
  <rule action='accept' direction='out'>
    <udp dstportstart='53' dstportend='53'/>
  </rule>

  <!-- Allow HTTP/HTTPS (for API calls, package managers) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='80' dstportend='80'/>
  </rule>
  <rule action='accept' direction='out'>
    <tcp dstportstart='443' dstportend='443'/>
  </rule>

  <!-- Allow SSH (for git operations) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='22' dstportend='22'/>
  </rule>

  <!-- Allow git protocol (port 9418) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='9418' dstportend='9418'/>
  </rule>

  <!-- Allow established connections (responses to outgoing requests) -->
  <rule action='accept' direction='in'>
    <all state='ESTABLISHED,RELATED'/>
  </rule>

  <!-- Block all unsolicited incoming connections -->
  <rule action='drop' direction='in' priority='1000'>
    <all state='NEW'/>
  </rule>

  <!-- Log blocked outgoing connections for monitoring -->
  <rule action='drop' direction='out' priority='1000'>
    <all/>
  </rule>
</filter>
```

**Isolated Mode (for high-security testing):**
```xml
<network>
  <name>agent-isolated</name>
  <bridge name='virbr-isolated'/>
  <forward mode='none'/>  <!-- No forwarding -->
  <ip address='192.168.100.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.100.10' end='192.168.100.254'/>
    </dhcp>
  </ip>
</network>
```
Use isolated mode only when testing agents that don't need network access or when maximum security is required.

---

## Agent Execution Profiles

### Profile: Standard (DEFAULT)
```yaml
Use Case: Normal CLI agent operations (Claude CLI, Copilot, etc.)
Resources:
  vcpu: 2
  memory: 2048 MB
  disk: 20 GB
Network: nat-filtered (DEFAULT)
  Allowed: DNS, HTTP/HTTPS, SSH (git), git protocol
  Monitoring: All connections logged
  Anomaly detection: Enabled
Timeout: 300 seconds
```

### Profile: Light
```yaml
Use Case: Simple scripts, quick tests
Resources:
  vcpu: 1
  memory: 1024 MB
  disk: 10 GB
Network: nat-filtered
  Same filters as Standard profile
Timeout: 60 seconds
```

### Profile: Intensive
```yaml
Use Case: Large codebases, complex operations, builds
Resources:
  vcpu: 4
  memory: 4096 MB
  disk: 40 GB
Network: nat-filtered
  Same filters as Standard profile
  Additional bandwidth monitoring
Timeout: 600 seconds
```

### Profile: Isolated (High Security)
```yaml
Use Case: Testing untrusted code, no network required
Resources:
  vcpu: 2
  memory: 2048 MB
  disk: 20 GB
Network: isolated (NO internet access)
  Only VM-to-VM communication blocked
  No external connectivity
Timeout: 300 seconds
Use When:
  - Testing potentially malicious code
  - Agent doesn't require network
  - Maximum security required
```

---

## Performance Targets

```yaml
Boot Time:
  MVP: < 2 seconds (optimized QEMU)
  Target: < 500 milliseconds (Cloud Hypervisor)
  Stretch: < 200 milliseconds (Firecracker)

Execution Overhead:
  VM Pool Acquire: < 100 milliseconds
  Snapshot Restore: < 1 second
  Code Injection (9p): < 10 milliseconds
  Result Extraction (9p): < 50 milliseconds (1MB)
  Control Command (vsock): < 5 milliseconds

Resource Utilization:
  Idle VM Memory: < 100 MB
  Idle VM CPU: < 5%
  Disk Overhead (COW): < 50 MB per VM
  Concurrent VMs: 20+ per host (16 GB RAM)

Reliability:
  VM Boot Success: > 99.9%
  Snapshot Restore Success: 100%
  Pool Availability: > 99.5%
  Agent Execution Success: > 99% (excluding agent errors)
```

---

## Technology Stack

### Core Infrastructure
- **Hypervisor:** QEMU/KVM 8.0+ (MVP), Cloud Hypervisor (optimization phase)
- **Management:** libvirt 9.0+
- **OS:** Ubuntu 24.04 LTS (minimal cloud image)
- **Kernel:** Custom-built microVM kernel (optimization phase)

### Host Software
- **Language:** Python 3.12+
- **Async Framework:** asyncio + aiohttp
- **libvirt Bindings:** libvirt-python 9.0+
- **Testing:** pytest + pytest-asyncio + pytest-libvirt
- **Monitoring:** Prometheus + Grafana
- **Logging:** structlog → syslog/Elasticsearch

### Guest Software
- **Python:** 3.12 (via pyenv)
- **Node.js:** 20 LTS (via nvm)
- **Guest Agent:** qemu-guest-agent + custom vsock daemon
- **Development Tools:** git, gcc, make, docker-cli, gh, aws-cli

### CI/CD
- **Packer:** 1.10+ (image building)
- **Terraform:** 1.6+ (infrastructure)
- **GitHub Actions:** CI/CD workflows
- **Trivy:** Security scanning

---

## Next: TDD Implementation Plan

This architecture document provides the foundation. The next step is to create a detailed TDD-driven implementation plan with:

1. Test specifications for each component
2. Implementation order (dependency graph)
3. Acceptance criteria
4. Performance benchmarks

See `TDD_IMPLEMENTATION_PLAN.md` for detailed implementation strategy.
