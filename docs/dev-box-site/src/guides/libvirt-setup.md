---
layout: guide.njk
title: "Libvirt/KVM Setup Guide"
description:
  "Switch from VirtualBox to Libvirt/KVM for better performance on Linux systems
  with dev-box"
eleventyNavigation:
  key: Libvirt Setup
  parent: Guides
  order: 2
difficulty: intermediate
estimatedTime: "45 minutes"
toc: true
---

# Libvirt/KVM Setup Guide

This guide helps you switch from VirtualBox to Libvirt/KVM for significantly
better performance on Linux systems. Libvirt with KVM provides native
virtualization capabilities that can dramatically improve your dev-box
experience.

{% alert "info" %} **Performance Benefits**: Users typically see 2-3x better
performance with Libvirt/KVM compared to VirtualBox on Linux systems.
{% endalert %}

## Why Choose Libvirt/KVM?

### Performance Advantages

- **Native virtualization** using hardware acceleration
- **Better memory management** with lower overhead
- **Improved I/O performance** for disk and network operations
- **Lower CPU usage** on the host system
- **Better integration** with Linux kernel

### Feature Benefits

- **Snapshots with overlay support** for efficient storage
- **Advanced networking** with bridge and NAT configurations
- **Better resource isolation** and security
- **Professional-grade** virtualization platform

## Prerequisites

### System Requirements

**Minimum Requirements:**

- Linux distribution (Ubuntu 20.04+, CentOS 8+, etc.)
- CPU with virtualization support (Intel VT-x or AMD-V)
- 8GB RAM (recommended: 16GB+)
- 20GB+ available disk space

**Check Virtualization Support:**

```bash
# Check if your CPU supports virtualization
egrep -c '(vmx|svm)' /proc/cpuinfo

# Should return a number > 0
# If 0, enable VT-x/AMD-V in BIOS/UEFI
```

**Verify KVM Support:**

```bash
# Check if KVM is supported
kvm-ok 2>/dev/null || echo "kvm-ok not installed"

# Alternative check
ls -la /dev/kvm 2>/dev/null || echo "KVM device not available"
```

## Installation

### Step 1: Install KVM and Libvirt

**Ubuntu/Debian:**

```bash
# Update package list
sudo apt update

# Install KVM and libvirt packages
sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils

# Install additional useful tools
sudo apt install -y virt-manager libvirt-daemon virtinst libvirt-daemon-driver-qemu

# Verify installation
sudo systemctl status libvirtd
```

**CentOS/RHEL/Fedora:**

```bash
# CentOS/RHEL 8+
sudo dnf install -y qemu-kvm libvirt libvirt-python3 virt-install virt-viewer bridge-utils

# Fedora
sudo dnf install -y @virtualization

# Start and enable libvirt
sudo systemctl start libvirtd
sudo systemctl enable libvirtd
```

### Step 2: Configure User Permissions

```bash
# Add your user to libvirt and kvm groups
sudo usermod -aG libvirt $USER
sudo usermod -aG kvm $USER

# Apply group changes (logout/login or use newgrp)
newgrp libvirt

# Verify group membership
groups $USER | grep -E "(libvirt|kvm)"
```

### Step 3: Install Vagrant Libvirt Plugin

```bash
# Install the vagrant-libvirt plugin
vagrant plugin install vagrant-libvirt

# Verify installation
vagrant plugin list | grep libvirt
```

**Common Installation Issues:**

If plugin installation fails:

```bash
# Install development packages first
sudo apt install -y libvirt-dev ruby-dev gcc pkg-config

# Try installing again
vagrant plugin install vagrant-libvirt

# For specific Ruby versions
sudo apt install -y ruby-libvirt
```

## Configuration

### Using the Enhanced Libvirt Configuration

dev-box includes a pre-configured Libvirt setup:

```bash
# Navigate to the libvirt-enhanced directory
cd dev-box/libvirt-enhanced

# Review the configuration
cat Vagrantfile
```

### Enhanced Vagrantfile Features

The `libvirt-enhanced/Vagrantfile` includes:

```ruby
# Optimized for performance
config.vm.provider "libvirt" do |libvirt|
  libvirt.memory = 2048
  libvirt.cpus = 2
  libvirt.driver = "kvm"

  # Performance optimizations
  libvirt.cpu_mode = "host-passthrough"
  libvirt.nested = true
  libvirt.video_type = "virtio"
  libvirt.sound_type = nil

  # Network optimization
  libvirt.nic_model_type = "virtio"

  # Storage optimization
  libvirt.disk_bus = "virtio"
  libvirt.volume_cache = "writeback"

  # Storage configuration
  libvirt.storage :file, :size => '40G', :type => 'qcow2'
end
```

### Network Configuration

The enhanced configuration includes development-friendly networking:

```ruby
# Private network for VM access
config.vm.network "private_network", ip: "192.168.56.100"

# Port forwarding for development services
config.vm.network "forwarded_port", guest: 3000, host: 3000  # React/Node.js
config.vm.network "forwarded_port", guest: 8000, host: 8000  # Python/Django
config.vm.network "forwarded_port", guest: 8080, host: 8080  # General web
config.vm.network "forwarded_port", guest: 5000, host: 5000  # Flask/API
```

## Starting Your First Libvirt VM

### Step 1: Start the VM

```bash
# Navigate to libvirt-enhanced directory
cd dev-box/libvirt-enhanced

# Start VM with libvirt provider
vagrant up --provider=libvirt

# This will:
# - Download Ubuntu 24.04 box (if needed)
# - Create KVM virtual machine
# - Configure networking and storage
# - Run provisioning scripts
```

### Step 2: Verify the Installation

```bash
# Check VM status
vagrant status

# SSH into the VM
vagrant ssh

# Check virtualization inside VM
vagrant@dev-box:~$ lscpu | grep Virtualization
vagrant@dev-box:~$ cat /proc/cpuinfo | grep -E "(vmx|svm)"
```

### Step 3: Performance Testing

Compare performance between providers:

```bash
# Test boot time
time vagrant up --provider=libvirt
time vagrant up --provider=virtualbox

# Test file I/O (inside VM)
vagrant ssh
dd if=/dev/zero of=/tmp/test bs=1M count=1000 oflag=direct

# Test network performance
vagrant ssh
curl -w "@curl-format.txt" -o /dev/null -s "http://httpbin.org/bytes/10485760"
```

## KVM Module Management

### Understanding KVM Modules

KVM uses kernel modules that sometimes need management:

```bash
# Check loaded KVM modules
lsmod | grep kvm

# Typical output:
# kvm_intel    245760  0    (for Intel CPUs)
# kvm          745472  1 kvm_intel
```

### Using KVM Management Scripts

dev-box includes scripts for KVM module management:

```bash
# Navigate to scripts directory
cd dev-box/scripts

# Check what the script would do
sudo ./kvm-unload.sh --dry-run

# Test the KVM management system
./test-kvm-unload.sh --safe-only
```

### When to Unload KVM Modules

You might need to unload KVM modules for:

1. **Nested Virtualization Setup**
2. **Troubleshooting Hardware Issues**
3. **Switching Between Hypervisors**
4. **System Debugging**

**Safe KVM Unload:**

```bash
# Ensure no VMs are running
vagrant global-status
virsh list --all

# Unload KVM modules safely
sudo ./scripts/kvm-unload.sh

# Reload when needed
sudo modprobe kvm_intel  # or kvm_amd
```

## Advanced Configuration

### Custom Network Setup

Create custom networks for complex scenarios:

```ruby
# Custom bridge network
config.vm.provider "libvirt" do |libvirt|
  libvirt.management_network_name = "dev-network"
  libvirt.management_network_address = "192.168.100.0/24"
end
```

### Storage Optimization

Configure storage for better performance:

```ruby
config.vm.provider "libvirt" do |libvirt|
  # Use host file system for better performance
  libvirt.storage_pool_name = "default"

  # Optimize cache settings
  libvirt.volume_cache = "writeback"

  # Use virtio for better I/O
  libvirt.disk_bus = "virtio"

  # Additional storage
  libvirt.storage :file, :size => '20G', :path => 'extra-disk.qcow2'
end
```

### CPU and Memory Tuning

```ruby
config.vm.provider "libvirt" do |libvirt|
  # CPU configuration
  libvirt.cpus = 4
  libvirt.cpu_mode = "host-passthrough"  # Better performance
  libvirt.nested = true                  # Enable nested virtualization

  # Memory configuration
  libvirt.memory = 4096
  libvirt.hugepages = "1048576"          # Use hugepages for performance
end
```

## Migration from VirtualBox

### Backing Up VirtualBox VMs

Before switching, backup your existing work:

```bash
# Create snapshots of important VMs
vagrant snapshot push --name "before-libvirt-migration"

# Export shared folder contents
rsync -av /path/to/project/ /backup/project-backup/
```

### Step-by-Step Migration

1. **Prepare new environment:**

   ```bash
   # Create new directory for libvirt setup
   cp -r dev-box/libvirt-enhanced /path/to/new-project-libvirt
   cd /path/to/new-project-libvirt
   ```

2. **Copy project files:**

   ```bash
   # Copy your project files
   rsync -av /path/to/old-project/ ./ --exclude='.vagrant'
   ```

3. **Start with libvirt:**

   ```bash
   vagrant up --provider=libvirt
   ```

4. **Verify everything works:**

   ```bash
   vagrant ssh
   # Test your applications
   # Verify file sharing
   # Check network connectivity
   ```

5. **Clean up old VMs:**
   ```bash
   cd /path/to/old-project
   vagrant destroy
   ```

## Troubleshooting

### Common Issues

**VM won't start:**

```bash
# Check libvirt service
sudo systemctl status libvirtd

# Check user permissions
groups $USER | grep libvirt

# Check for conflicts
virsh list --all
```

**Network issues:**

```bash
# Check libvirt networks
virsh net-list --all

# Restart default network
sudo virsh net-destroy default
sudo virsh net-start default

# Check firewall
sudo ufw status
sudo iptables -L
```

**Performance issues:**

```bash
# Check KVM acceleration
cat /sys/module/kvm_intel/parameters/nested  # Should show 'Y'

# Check CPU flags
lscpu | grep -E "(vmx|svm)"

# Monitor VM performance
virsh domstats <vm-name>
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Vagrant debug mode
VAGRANT_LOG=debug vagrant up --provider=libvirt

# Libvirt debug
export LIBVIRT_DEBUG=1
vagrant up --provider=libvirt
```

### Recovery Procedures

**Reset libvirt configuration:**

```bash
# Stop all VMs
vagrant halt

# Restart libvirt
sudo systemctl restart libvirtd

# Reset networks
sudo virsh net-destroy default
sudo virsh net-start default
```

**KVM module recovery:**

```bash
# Unload and reload KVM modules
sudo ./scripts/kvm-unload.sh
sudo modprobe kvm_intel  # or kvm_amd

# Restart libvirt
sudo systemctl restart libvirtd
```

## Performance Optimization

### Host System Optimization

```bash
# Disable swap for better performance (if you have enough RAM)
sudo swapoff -a

# Enable KVM features in kernel
echo 'options kvm_intel nested=1' | sudo tee /etc/modprobe.d/kvm-intel.conf

# Reload KVM module
sudo modprobe -r kvm_intel
sudo modprobe kvm_intel
```

### VM-Specific Optimizations

```ruby
config.vm.provider "libvirt" do |libvirt|
  # Enable all performance features
  libvirt.cpu_mode = "host-passthrough"
  libvirt.nested = true
  libvirt.volume_cache = "writeback"
  libvirt.disk_bus = "virtio"
  libvirt.nic_model_type = "virtio"
  libvirt.video_type = "virtio"

  # Disable unnecessary features
  libvirt.sound_type = nil
  libvirt.graphics_type = "none"
end
```

### Monitoring Performance

```bash
# Monitor VM resource usage
virsh domstats <vm-name>

# Monitor host system
htop
iotop
nethogs

# VM network statistics
virsh domifstat <vm-name> <interface>
```

## Best Practices

### Resource Management

1. **Allocate appropriate resources:**

   ```ruby
   # Don't over-allocate
   libvirt.memory = [host_memory * 0.5, 8192].min
   libvirt.cpus = [host_cpus * 0.75, 8].min
   ```

2. **Use storage efficiently:**

   ```bash
   # Monitor disk usage
   virsh pool-info default
   virsh vol-list default
   ```

3. **Network optimization:**
   ```ruby
   # Use virtio for better performance
   libvirt.nic_model_type = "virtio"
   ```

### Security Considerations

1. **Isolate VMs properly:**

   ```ruby
   # Use private networks
   config.vm.network "private_network", type: "dhcp"
   ```

2. **Regular updates:**

   ```bash
   # Keep libvirt updated
   sudo apt update && sudo apt upgrade libvirt*
   ```

3. **Monitor access:**
   ```bash
   # Check who can access VMs
   getfacl /var/lib/libvirt/images/
   ```

## Integration with dev-box Features

### Snapshot Management

Libvirt snapshots are more efficient:

```bash
# Create snapshots (faster with qcow2)
vagrant snapshot push --name "feature-complete"

# List snapshots
vagrant snapshot list

# Restore snapshots (very fast)
vagrant snapshot restore "feature-complete"
```

### Shared Folder Performance

Optimize shared folders:

```ruby
# Better performance with libvirt
config.vm.synced_folder ".", "/vagrant",
  type: "nfs",
  nfs_udp: false,
  nfs_version: 4
```

### Development Workflow

Libvirt integrates seamlessly with dev-box workflows:

```bash
# Standard workflows work the same
vagrant up --provider=libvirt
vagrant ssh
vagrant halt
vagrant destroy
```

## Summary

You've successfully set up Libvirt/KVM with dev-box! Key benefits you'll
experience:

- **2-3x better performance** compared to VirtualBox
- **Lower host system resource usage**
- **Faster snapshots and VM operations**
- **Better development experience**

### Next Steps

- Explore [performance tuning](/guides/performance/) for even better results
- Learn about [advanced networking](/guides/networking/) configurations
- Check out [Docker development](/guides/docker-development/) with Libvirt
- Review [team workflows](/guides/team-workflows/) for sharing configurations

### Quick Reference

```bash
# Essential libvirt commands
vagrant up --provider=libvirt     # Start with libvirt
virsh list --all                  # List all VMs
virsh domstats <vm>               # VM statistics
sudo systemctl restart libvirtd   # Restart service

# KVM module management
sudo ./scripts/kvm-unload.sh      # Unload KVM modules
sudo modprobe kvm_intel           # Reload KVM modules
lsmod | grep kvm                  # Check KVM modules
```

{% alert "success" %} **Congratulations!** You're now using professional-grade
virtualization with dev-box. Enjoy the improved performance and capabilities!
{% endalert %}
