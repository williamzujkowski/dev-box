# Network Configuration Guide

## Overview

The KVM Agent Isolation System uses **NAT-filtered networking by default** to support real-world CLI agent usage while maintaining security through network filtering and monitoring.

## Why Network Access is Default

Modern CLI agents (Claude CLI, GitHub Copilot, etc.) require internet access for:
- **API calls** to cloud services (Anthropic, OpenAI, GitHub)
- **Package installation** (npm, pip, apt)
- **Git operations** (clone, push, pull via HTTPS/SSH)
- **Documentation lookup** (online docs, Stack Overflow)
- **Tool downloads** (language runtimes, utilities)

Without network access, these agents cannot function properly.

## Default Network Mode: NAT-Filtered

### Configuration

```xml
<network>
  <name>agent-nat-filtered</name>
  <forward mode='nat'>
    <nat>
      <port start='1024' end='65535'/>
    </nat>
  </forward>
  <ip address='192.168.101.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.101.10' end='192.168.101.254'/>
    </dhcp>
  </ip>
</network>
```

### Network Filter (Whitelist-Based)

```xml
<filter name='agent-network-filter' chain='root'>
  <!-- DNS (required) -->
  <rule action='accept' direction='out'>
    <udp dstportstart='53' dstportend='53'/>
  </rule>

  <!-- HTTP/HTTPS (for APIs, package managers) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='80' dstportend='80'/>
  </rule>
  <rule action='accept' direction='out'>
    <tcp dstportstart='443' dstportend='443'/>
  </rule>

  <!-- SSH (for git operations) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='22' dstportend='22'/>
  </rule>

  <!-- Git protocol (port 9418) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='9418' dstportend='9418'/>
  </rule>

  <!-- Established connections only (no unsolicited incoming) -->
  <rule action='accept' direction='in'>
    <all state='ESTABLISHED,RELATED'/>
  </rule>

  <!-- Block all unsolicited incoming -->
  <rule action='drop' direction='in' priority='1000'>
    <all state='NEW'/>
  </rule>

  <!-- Drop and log other outgoing (for monitoring) -->
  <rule action='drop' direction='out' priority='1000'>
    <all/>
  </rule>
</filter>
```

### What's Allowed

✅ **Outgoing connections to:**
- DNS servers (UDP 53)
- HTTP servers (TCP 80)
- HTTPS servers (TCP 443)
- SSH servers (TCP 22) - for git
- Git protocol (TCP 9418)

✅ **Incoming responses to above connections**

❌ **Blocked:**
- Unsolicited incoming connections
- Other outgoing protocols (FTP, SMTP, custom ports)
- VM-to-VM communication
- VM-to-host communication (except control channels)

## Security Despite Network Access

### 1. Hardware Isolation
VMs are isolated at the hypervisor level. Even with network access, they cannot:
- Access host filesystem
- Read host memory
- Access other VMs
- Escape to host

### 2. Network Filtering
Whitelist-based filtering ensures:
- Only necessary protocols allowed
- All connections logged
- Anomaly detection monitors traffic
- Rate limiting prevents abuse

### 3. Monitoring
All network activity is:
- **Logged:** Every connection attempt
- **Analyzed:** Anomaly detection for suspicious patterns
- **Alerted:** Unusual traffic triggers alerts
- **Metered:** Bandwidth limits enforced

### 4. No Incoming Access
Agents **cannot** receive unsolicited incoming connections:
- No services exposed to internet
- No listening ports accessible
- Only responses to outgoing requests
- Prevents VM from being attacked

## Alternative Network Modes

### Isolated Mode (High Security)

**Use when:**
- Testing potentially malicious code
- Agent doesn't need network
- Maximum security required
- Offline testing

```python
from agent_vm.core.template import VMTemplate, NetworkMode

template = VMTemplate(
    name="secure-vm",
    network_mode=NetworkMode.ISOLATED
)
```

**Characteristics:**
- ❌ No internet access
- ❌ No external connectivity
- ✅ Complete network isolation
- ✅ VM cannot communicate outside

**Trade-off:** Most agents won't work without network.

### Bridge Mode (Advanced)

**Use when:**
- Need direct host network access
- Custom network setup required
- Testing network services

```python
template = VMTemplate(
    name="bridge-vm",
    network_mode=NetworkMode.BRIDGE
)
```

**Characteristics:**
- ⚠️ Direct host network access
- ⚠️ VM gets IP from host network
- ⚠️ More network attack surface
- ✅ Full network functionality

**Trade-off:** Less isolation, use only when necessary.

## Setting Up Networks

### 1. Create NAT-Filtered Network (Default)

```bash
# Define network
cat > agent-nat-filtered.xml << 'EOF'
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

# Create network
virsh net-define agent-nat-filtered.xml
virsh net-start agent-nat-filtered
virsh net-autostart agent-nat-filtered
```

### 2. Create Network Filter

```bash
# Define filter
cat > agent-network-filter.xml << 'EOF'
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

  <!-- Git protocol -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='9418' dstportend='9418'/>
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

# Create filter
virsh nwfilter-define agent-network-filter.xml
```

### 3. (Optional) Create Isolated Network

```bash
cat > agent-isolated.xml << 'EOF'
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

virsh net-define agent-isolated.xml
virsh net-start agent-isolated
virsh net-autostart agent-isolated
```

## Monitoring Network Activity

### View Active Connections (Inside VM)

```bash
# SSH into VM
vagrant ssh

# Show active connections
netstat -tupn

# Show connection statistics
ss -s

# Monitor traffic
sudo tcpdump -i any -n
```

### View Libvirt Network Stats

```bash
# Network statistics
virsh domifstat <vm-name> vnet0

# Network info
virsh domiflist <vm-name>

# Filter status
virsh nwfilter-list
```

### Prometheus Metrics

The system automatically collects:
- `agent_vm_network_rx_bytes_total` - Received bytes
- `agent_vm_network_tx_bytes_total` - Transmitted bytes
- `agent_vm_network_rx_packets_total` - Received packets
- `agent_vm_network_tx_packets_total` - Transmitted packets
- `agent_network_connection_attempts_total` - Connection attempts
- `agent_network_blocked_connections_total` - Blocked connections

## Testing Network Configuration

### Test Internet Access

```python
# Inside VM
import urllib.request

# Should work (HTTPS)
response = urllib.request.urlopen('https://www.google.com')
print(response.status)  # 200

# Should work (HTTP)
response = urllib.request.urlopen('http://example.com')
print(response.status)  # 200
```

### Test Git Operations

```bash
# Inside VM
git clone https://github.com/user/repo.git  # Should work
git clone git@github.com:user/repo.git      # Should work
```

### Test Blocked Connections

```python
# Inside VM
import socket

# Should fail (arbitrary port)
try:
    s = socket.socket()
    s.connect(('example.com', 8080))
    print("Connected")  # Should not reach here
except Exception as e:
    print(f"Blocked: {e}")  # Should be blocked
```

## Customizing Network Filters

### Allow Additional Port

```bash
# Edit filter
virsh nwfilter-edit agent-network-filter

# Add rule (e.g., for PostgreSQL 5432)
<rule action='accept' direction='out'>
  <tcp dstportstart='5432' dstportend='5432'/>
</rule>

# Reload filter
virsh nwfilter-define agent-network-filter.xml
```

### Temporarily Disable Filter (Testing)

```python
# In VM template
template = VMTemplate(
    name="test-vm",
    network_mode=NetworkMode.BRIDGE  # No filter applied
)
```

⚠️ **Warning:** Only disable filters for testing. Always use filtered networks in production.

## Best Practices

### 1. Use NAT-Filtered by Default
Unless you have specific security requirements, use NAT-filtered mode:
```python
# This is the default
template = VMTemplate(name="my-vm")  # Already NAT-filtered
```

### 2. Monitor Network Activity
Always enable monitoring:
```python
from agent_vm.monitoring.metrics import MetricsCollector

collector = MetricsCollector()
collector.enable_network_monitoring(vm_id="my-vm")
```

### 3. Set Bandwidth Limits
Prevent excessive bandwidth usage:
```xml
<interface type='network'>
  <source network='agent-nat-filtered'/>
  <bandwidth>
    <inbound average='10240' peak='20480'/>  <!-- 10 Mbps avg, 20 Mbps peak -->
    <outbound average='10240' peak='20480'/>
  </bandwidth>
</interface>
```

### 4. Review Logs Regularly
Check for suspicious activity:
```bash
# View audit logs
journalctl -u libvirtd | grep network

# Check blocked connections
grep "dropped" /var/log/syslog
```

### 5. Use Isolated Mode for Untrusted Code
When testing potentially malicious code:
```python
template = VMTemplate(
    name="untrusted-vm",
    network_mode=NetworkMode.ISOLATED
)
```

## Troubleshooting

### Agent Can't Connect to API

**Problem:** Agent fails with "connection refused" or "network unreachable"

**Solution:**
1. Verify VM has network:
   ```bash
   virsh domiflist <vm-name>
   ping -c 1 8.8.8.8  # Inside VM
   ```

2. Check filter is applied:
   ```bash
   virsh domiflist <vm-name> | grep filterref
   ```

3. Test DNS:
   ```bash
   nslookup google.com  # Inside VM
   ```

### Connections Being Blocked

**Problem:** Network filter blocking necessary connections

**Solution:**
1. Check which port is needed:
   ```bash
   # Inside VM, try connection
   telnet api.example.com 8080
   ```

2. Add port to filter (if safe):
   ```bash
   virsh nwfilter-edit agent-network-filter
   ```

3. Temporarily use bridge mode for testing:
   ```python
   template = VMTemplate(name="test", network_mode=NetworkMode.BRIDGE)
   ```

### Slow Network Performance

**Problem:** Network operations are slow

**Solution:**
1. Check bandwidth limits:
   ```bash
   virsh domiftune <vm-name> vnet0
   ```

2. Verify virtio driver:
   ```bash
   # Inside VM
   ethtool -i eth0 | grep driver  # Should be virtio_net
   ```

3. Monitor network stats:
   ```bash
   virsh domifstat <vm-name> vnet0
   ```

## Security Considerations

### Network Access ≠ Insecurity

**Despite having network access, VMs are still isolated:**
- Cannot access host filesystem or memory
- Cannot communicate with other VMs
- Cannot receive unsolicited connections
- All traffic monitored and logged
- Bandwidth limited
- Anomaly detection active

### Defense in Depth

Network filtering is just one layer:
1. **KVM hardware isolation** (base layer)
2. **Network filtering** (this layer)
3. **Resource limits** (cgroups)
4. **Syscall filtering** (seccomp)
5. **Monitoring** (anomaly detection)

### When to Use Isolated Mode

Use `NetworkMode.ISOLATED` when:
- Testing potentially malicious code
- Agent doesn't need network functionality
- Compliance requires air-gapped testing
- Maximum security is more important than functionality

## Summary

**Default Configuration:**
- ✅ NAT-filtered network mode
- ✅ Whitelist-based filtering (DNS, HTTP/S, SSH, Git)
- ✅ All connections logged and monitored
- ✅ No unsolicited incoming connections
- ✅ Hardware isolation still maintained

**This provides the best balance of:**
- **Functionality:** Agents work with internet access
- **Security:** Strong isolation and filtering
- **Monitoring:** Complete visibility into network activity
- **Performance:** Near-native network speed

Use isolated mode only when network access is not needed or when maximum security overrides functionality requirements.
