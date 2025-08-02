# CI/CD Pipeline Troubleshooting Guide

## Common Issues and Solutions

### Build Failures

#### 1. Packer Build Timeout

**Symptoms:**
```
Error: timeout while waiting for guest to boot
```

**Causes:**
- Insufficient VM resources
- KVM acceleration not available
- Network connectivity issues
- ISO download failures

**Solutions:**

1. **Check KVM Support:**
```bash
# In workflow, add diagnostic step
- name: Check KVM support
  run: |
    kvm-ok || echo "KVM not available"
    ls -la /dev/kvm
    lscpu | grep Virtualization
```

2. **Increase VM Resources:**
```hcl
# In Packer configuration
memory = 4096  # Increase from 2048
cpus = 4       # Increase from 2
```

3. **Add Retries:**
```yaml
# In workflow
- name: Build with retries
  run: |
    for i in {1..3}; do
      if packer build ubuntu-24.04-libvirt.pkr.hcl; then
        break
      fi
      echo "Build attempt $i failed, retrying..."
      sleep 30
    done
```

#### 2. Libvirt Connection Failed

**Symptoms:**
```
Error: failed to connect to libvirt
```

**Causes:**
- Libvirt service not running
- Permission issues
- Socket connection problems

**Solutions:**

1. **Verify Service Status:**
```bash
- name: Debug libvirt
  run: |
    sudo systemctl status libvirtd
    sudo virsh list --all
    groups $USER
    ls -la /var/run/libvirt/
```

2. **Fix Permissions:**
```bash
# Add to setup step
sudo usermod -aG libvirt $USER
sudo usermod -aG kvm $USER
newgrp libvirt  # Refresh group membership
```

3. **Restart Services:**
```bash
sudo systemctl restart libvirtd
sudo systemctl restart virtlogd
```

### Validation Failures

#### 1. VM Won't Start During Testing

**Symptoms:**
```
The provider 'libvirt' could not be found
```

**Causes:**
- vagrant-libvirt plugin not installed
- Incompatible Vagrant/plugin versions
- Missing dependencies

**Solutions:**

1. **Verify Plugin Installation:**
```bash
- name: Debug Vagrant setup
  run: |
    vagrant version
    vagrant plugin list
    vagrant plugin install vagrant-libvirt --plugin-version 0.12.2
```

2. **Check Dependencies:**
```bash
sudo apt-get install -y \
  ruby-dev \
  libvirt-dev \
  qemu-utils \
  libguestfs-tools
```

#### 2. SSH Connection Timeout

**Symptoms:**
```
Timed out while waiting for the machine to boot
```

**Causes:**
- VM not fully booted
- SSH service not running
- Network configuration issues
- Firewall blocking connections

**Solutions:**

1. **Increase Timeouts:**
```ruby
# In Vagrantfile
config.vm.boot_timeout = 600  # 10 minutes
config.ssh.connect_timeout = 300  # 5 minutes
```

2. **Debug VM State:**
```bash
- name: Debug VM state
  run: |
    sudo virsh list --all
    sudo virsh dominfo <vm-name>
    sudo virsh console <vm-name> --force
```

3. **Check Network:**
```bash
- name: Debug networking
  run: |
    sudo virsh net-list --all
    sudo virsh net-info default
    ip route show
```

### Cache Issues

#### 1. Cache Not Working

**Symptoms:**
- Build always runs from scratch
- Cache hit rate 0%

**Causes:**
- Incorrect cache keys
- Cache size limits exceeded
- Permission issues

**Solutions:**

1. **Debug Cache Keys:**
```bash
- name: Debug cache
  run: |
    echo "Cache key components:"
    echo "Packer hash: $(find packer -name "*.pkr.hcl" -exec cat {} \; | sha256sum)"
    echo "Scripts hash: $(find scripts -name "*.sh" -exec cat {} \; | sha256sum)"
    echo "Generated key: ${{ steps.cache-key.outputs.key }}"
```

2. **Verify Cache Size:**
```bash
- name: Check cache usage
  run: |
    du -sh ~/.cache/packer/
    du -sh packer/packer_cache/
```

3. **Reset Cache:**
```yaml
# Use new cache key version
env:
  CACHE_VERSION: 'v3'  # Increment to reset
```

#### 2. Partial Cache Corruption

**Symptoms:**
- Build fails with cached data
- Inconsistent results

**Solutions:**

1. **Implement Cache Validation:**
```bash
- name: Validate cache
  run: |
    if [[ -d "packer/packer_cache" ]]; then
      find packer/packer_cache -name "*.iso" -exec file {} \;
      find packer/packer_cache -name "*.iso" -exec du -h {} \;
    fi
```

2. **Add Fallback Strategy:**
```yaml
- name: Restore cache with fallback
  uses: actions/cache@v4
  with:
    path: packer/packer_cache
    key: ${{ steps.cache-key.outputs.key }}
    restore-keys: |
      ${{ env.CACHE_KEY_PREFIX }}-
      fallback-cache-v1
```

### Performance Issues

#### 1. Slow Build Times

**Symptoms:**
- Build takes >45 minutes
- Frequent timeouts

**Causes:**
- Network bandwidth limitations
- Inefficient VM configuration
- Large artifact sizes

**Solutions:**

1. **Optimize VM Configuration:**
```hcl
# Packer optimization
memory = 2048
cpus = 2
disk_size = "10240"  # Smaller disk
accelerator = "kvm"
cpu_type = "host"
```

2. **Parallel Processing:**
```yaml
# Use job matrix for parallel execution
strategy:
  matrix:
    component: [build, validate, test]
  max-parallel: 3
```

3. **Network Optimization:**
```bash
# Use mirrors and CDNs
echo "deb http://us.archive.ubuntu.com/ubuntu/ jammy main" > sources.list
```

#### 2. Resource Exhaustion

**Symptoms:**
```
Error: No space left on device
```

**Solutions:**

1. **Monitor Disk Usage:**
```bash
- name: Check disk space
  run: |
    df -h
    du -sh /tmp/
    du -sh ~/.cache/
```

2. **Cleanup Strategy:**
```bash
- name: Cleanup before build
  run: |
    docker system prune -af || true
    sudo apt-get clean
    sudo rm -rf /var/cache/apt/archives/*
```

3. **Optimize Artifacts:**
```bash
# Compress artifacts
find output -name "*.box" -exec gzip {} \;
```

### Environment Issues

#### 1. Missing Dependencies

**Symptoms:**
```
Command not found: packer
```

**Solutions:**

1. **Verify Installation:**
```bash
- name: Verify dependencies
  run: |
    which packer || echo "Packer not found"
    which vagrant || echo "Vagrant not found"
    which qemu-system-x86_64 || echo "QEMU not found"
```

2. **Install from Source:**
```bash
# Fallback installation
PACKER_VERSION="1.10.0"
wget https://releases.hashicorp.com/packer/${PACKER_VERSION}/packer_${PACKER_VERSION}_linux_amd64.zip
unzip packer_${PACKER_VERSION}_linux_amd64.zip
sudo mv packer /usr/local/bin/
```

#### 2. Version Incompatibilities

**Symptoms:**
- Plugin installation failures
- API compatibility errors

**Solutions:**

1. **Pin Specific Versions:**
```yaml
env:
  PACKER_VERSION: '1.10.0'
  VAGRANT_VERSION: '2.4.1'
  VAGRANT_LIBVIRT_VERSION: '0.12.2'
```

2. **Version Compatibility Matrix:**
```bash
# Test compatibility
vagrant plugin install vagrant-libvirt --plugin-version $VAGRANT_LIBVIRT_VERSION
vagrant plugin list | grep libvirt
```

## Debugging Strategies

### 1. Enable Debug Logging

```yaml
env:
  PACKER_LOG: 1
  PACKER_LOG_PATH: packer-debug.log
  VAGRANT_LOG: debug
```

### 2. Add Diagnostic Steps

```yaml
- name: System diagnostics
  run: |
    echo "=== System Information ==="
    uname -a
    lscpu
    free -h
    df -h
    
    echo "=== Virtualization Support ==="
    kvm-ok || true
    ls -la /dev/kvm
    
    echo "=== Libvirt Status ==="
    sudo systemctl status libvirtd --no-pager
    sudo virsh list --all
    
    echo "=== Network Configuration ==="
    ip addr show
    sudo virsh net-list --all
```

### 3. Capture Artifacts

```yaml
- name: Upload debug artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: debug-logs
    path: |
      packer-debug.log
      /var/log/libvirt/
      ~/.vagrant.d/logs/
```

## Recovery Procedures

### 1. Failed Build Recovery

```bash
# Clean state and retry
vagrant destroy -f
vagrant box remove <box-name> --all
rm -rf .vagrant/
rm -rf packer/output/
packer build ubuntu-24.04-libvirt.pkr.hcl
```

### 2. Cache Reset

```bash
# Clear all caches
rm -rf ~/.packer.d/
rm -rf ~/.vagrant.d/boxes/
rm -rf packer/packer_cache/
# Update cache version in workflow
```

### 3. Environment Reset

```bash
# Reset libvirt
sudo systemctl stop libvirtd
sudo systemctl stop virtlogd
sudo rm -rf /var/lib/libvirt/qemu/
sudo rm -rf /etc/libvirt/qemu/networks/autostart/
sudo systemctl start libvirtd
sudo systemctl start virtlogd
```

## Monitoring and Alerting

### 1. Performance Monitoring

```yaml
- name: Performance monitoring
  run: |
    # Track build metrics
    echo "BUILD_START=$(date +%s)" >> $GITHUB_ENV
    
    # Your build steps here
    
    BUILD_END=$(date +%s)
    BUILD_DURATION=$((BUILD_END - BUILD_START))
    echo "Build duration: ${BUILD_DURATION} seconds"
    
    # Alert if build is slow
    if [[ $BUILD_DURATION -gt 2700 ]]; then  # 45 minutes
      echo "::warning::Build took longer than expected: ${BUILD_DURATION}s"
    fi
```

### 2. Success Rate Tracking

```yaml
- name: Track success rate
  if: always()
  run: |
    if [[ "${{ job.status }}" == "success" ]]; then
      echo "BUILD_SUCCESS=1" >> metrics.env
    else
      echo "BUILD_SUCCESS=0" >> metrics.env
    fi
```

## Performance Optimization

### 1. Build Optimization

```hcl
# Optimized Packer configuration
source "qemu" "ubuntu" {
  # Use smaller ISO
  iso_url = "http://cloud-images.ubuntu.com/minimal/releases/jammy/release/ubuntu-22.04-minimal-cloudimg-amd64.img"
  
  # Optimize VM settings
  memory = 2048
  cpus = 2
  disk_size = "8192"
  
  # Enable KVM acceleration
  accelerator = "kvm"
  cpu_type = "host"
  machine_type = "q35"
  
  # Network optimization
  net_device = "virtio-net"
  disk_interface = "virtio"
  
  # Reduce boot time
  boot_wait = "10s"
}
```

### 2. Caching Optimization

```yaml
# Intelligent cache key generation
- name: Generate optimized cache key
  id: cache-key
  run: |
    # Include only relevant files in hash
    PACKER_HASH=$(find packer -name "*.pkr.hcl" -o -name "*.pkrvars.hcl" | sort | xargs cat | sha256sum | cut -d' ' -f1)
    SCRIPTS_HASH=$(find scripts -name "*.sh" | sort | xargs cat | sha256sum | cut -d' ' -f1)
    
    # Add date component for time-based invalidation
    DATE_COMPONENT=$(date +%Y%m%d)
    
    CACHE_KEY="v2-${PACKER_HASH}-${SCRIPTS_HASH}-${DATE_COMPONENT}"
    echo "key=${CACHE_KEY}" >> $GITHUB_OUTPUT
```

### 3. Parallel Execution

```yaml
# Parallel validation jobs
strategy:
  matrix:
    test-type: [connectivity, provisioning, tools, performance]
  max-parallel: 4
  fail-fast: false
```

## Best Practices

### 1. Error Handling

```bash
# Robust error handling
set -euo pipefail

cleanup() {
  echo "Cleaning up..."
  vagrant destroy -f || true
  sudo virsh list --all --name | xargs -r sudo virsh destroy || true
}

trap cleanup EXIT
```

### 2. Resource Management

```yaml
# Always cleanup resources
- name: Cleanup
  if: always()
  run: |
    vagrant global-status --prune
    vagrant box list | grep test- | cut -d' ' -f1 | xargs -r vagrant box remove
    sudo virsh list --all --name | xargs -r sudo virsh destroy
```

### 3. Timeout Management

```yaml
# Appropriate timeouts
timeout-minutes: 30  # For validation jobs
timeout-minutes: 60  # For build jobs
timeout-minutes: 120 # For comprehensive tests
```

## Getting Help

### 1. Log Analysis

```bash
# Comprehensive log collection
mkdir -p debug-info
cp -r /var/log/libvirt/ debug-info/ || true
cp ~/.vagrant.d/logs/* debug-info/ || true
journalctl -u libvirtd --no-pager > debug-info/libvirtd.log
dmesg | grep -i kvm > debug-info/kvm.log
```

### 2. Community Resources

- [GitHub Actions Community](https://github.community/)
- [Vagrant Community](https://discuss.hashicorp.com/c/vagrant/)
- [Packer Community](https://discuss.hashicorp.com/c/packer/)
- [Libvirt Mailing Lists](https://libvirt.org/contact.html)

### 3. Issue Reporting

When reporting issues, include:
- Complete error messages
- Workflow run logs
- System information
- Reproduction steps
- Environment details

## Prevention

### 1. Regular Maintenance

```yaml
# Weekly health check
- name: Health check
  if: github.event_name == 'schedule'
  run: |
    # Check for outdated dependencies
    packer version
    vagrant version
    vagrant plugin outdated
    
    # Check system resources
    df -h
    free -h
    
    # Test basic functionality
    vagrant box list
    sudo virsh list --all
```

### 2. Proactive Monitoring

```yaml
# Performance trending
- name: Performance trend analysis
  run: |
    BUILD_TIME=$(date +%s)
    echo "build_timestamp=${BUILD_TIME}" >> metrics.json
    
    # Compare with historical data
    if [[ -f historical-metrics.json ]]; then
      python3 -c "
import json
with open('historical-metrics.json') as f:
    historical = json.load(f)
current_time = ${BUILD_TIME}
avg_time = sum(historical.get('build_times', [])) / len(historical.get('build_times', [1]))
if current_time > avg_time * 1.5:
    print('::warning::Build time significantly higher than average')
"
    fi
```