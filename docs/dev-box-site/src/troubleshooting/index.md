---
layout: page.njk
title: "Troubleshooting"
description:
  "Solutions to common issues, recovery procedures, and debugging techniques for
  dev-box environments"
eleventyNavigation:
  key: Troubleshooting
  order: 4
---

# Troubleshooting Guide

This comprehensive troubleshooting guide covers common issues, recovery
procedures, and debugging techniques for dev-box environments.

## Quick Problem Resolution

### Most Common Issues

1. **[VM Won't Start](#vm-startup-issues)** - Boot failures, provider errors
2. **[SSH Connection Failed](#ssh-connection-issues)** - Cannot connect to VM
3. **[Slow Performance](#performance-issues)** - VM running slowly
4. **[Network Problems](#network-issues)** - Port forwarding, connectivity
   issues
5. **[KVM Module Issues](#kvm-issues)** - Libvirt/KVM specific problems

### Emergency Recovery

If you're in a critical situation and need immediate help:

```bash
# Stop any problematic VMs
vagrant halt --force

# Check system status
vagrant global-status

# For corrupted VMs, destroy and recreate
vagrant destroy
vagrant up
```

## VM Startup Issues

### VM Won't Boot

**Symptoms:**

- `vagrant up` fails with timeout errors
- VirtualBox/Libvirt errors during startup
- VM starts but doesn't respond

**Common Solutions:**

1. **Check available resources:**

   ```bash
   # Check RAM availability
   free -h

   # Check disk space
   df -h

   # Check CPU load
   top
   ```

2. **Verify virtualization support:**

   ```bash
   # Check if virtualization is enabled
   egrep -c '(vmx|svm)' /proc/cpuinfo

   # Should return a number > 0
   # If 0, enable VT-x/AMD-V in BIOS
   ```

3. **Provider-specific checks:**

   **VirtualBox:**

   ```bash
   # Check VirtualBox installation
   VBoxManage --version

   # List running VMs
   VBoxManage list runningvms

   # Check for conflicting VMs
   VBoxManage list vms
   ```

   **Libvirt:**

   ```bash
   # Check libvirt service
   sudo systemctl status libvirtd

   # Verify KVM modules
   lsmod | grep kvm

   # Check user permissions
   groups $USER | grep libvirt
   ```

### Provider Configuration Issues

**VirtualBox Provider Issues:**

```bash
# Reinstall VirtualBox if corrupted
sudo apt remove --purge virtualbox*
sudo apt autoremove
# Follow installation guide to reinstall

# Reset VirtualBox configuration
rm -rf ~/.config/VirtualBox
```

**Libvirt Provider Issues:**

```bash
# Restart libvirt service
sudo systemctl restart libvirtd

# Check libvirt connection
virsh -c qemu:///system list --all

# Reset libvirt networks
sudo virsh net-destroy default
sudo virsh net-start default
```

## SSH Connection Issues

### Cannot SSH into VM

**Symptoms:**

- `vagrant ssh` hangs or times out
- Connection refused errors
- Authentication failures

**Diagnostic Steps:**

1. **Check VM status:**

   ```bash
   vagrant status

   # Should show "running"
   # If not, try: vagrant up
   ```

2. **Verify SSH configuration:**

   ```bash
   vagrant ssh-config

   # This shows the SSH connection details
   # Note the port and key file
   ```

3. **Test direct SSH connection:**
   ```bash
   # Use output from ssh-config
   ssh -i ~/.vagrant.d/insecure_private_key -p 2222 vagrant@127.0.0.1
   ```

**Common Solutions:**

1. **Reload the VM:**

   ```bash
   vagrant reload
   ```

2. **Reset SSH configuration:**

   ```bash
   vagrant destroy
   vagrant up
   ```

3. **Manual SSH troubleshooting:**

   ```bash
   # Check if VM is listening on SSH port
   netstat -an | grep :2222

   # Try connecting with verbose output
   ssh -v -i ~/.vagrant.d/insecure_private_key -p 2222 vagrant@127.0.0.1
   ```

### SSH Key Issues

**Regenerate SSH keys:**

```bash
# Remove old keys
rm -f ~/.vagrant.d/insecure_private_key
rm -f ~/.vagrant.d/insecure_private_key.pub

# Vagrant will regenerate on next up
vagrant up
```

## Performance Issues

### Slow VM Performance

**Symptoms:**

- VM takes a long time to boot
- Applications run slowly inside VM
- High CPU usage on host

**Performance Optimization:**

1. **Increase VM resources:**

   Edit your `Vagrantfile`:

   ```ruby
   config.vm.provider "virtualbox" do |vb|
     vb.memory = "4096"  # Increase from 2048
     vb.cpus = 4         # Increase from 2

     # Enable hardware virtualization passthrough
     vb.customize ["modifyvm", :id, "--hwvirtex", "on"]
     vb.customize ["modifyvm", :id, "--nestedpaging", "on"]
   end
   ```

2. **Optimize host system:**

   ```bash
   # Close unnecessary applications
   # Disable Windows Defender real-time scanning for VM directory
   # Use SSD storage for better I/O performance

   # Linux: Disable swap if you have sufficient RAM
   sudo swapoff -a
   ```

3. **Switch to Libvirt (Linux only):**
   ```bash
   # Libvirt/KVM typically performs better than VirtualBox
   cd libvirt-enhanced
   vagrant up --provider=libvirt
   ```

### Disk I/O Performance

**Optimize storage configuration:**

**VirtualBox:**

```ruby
config.vm.provider "virtualbox" do |vb|
  # Use host I/O cache
  vb.customize ["modifyvm", :id, "--ioapic", "on"]
  vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
  vb.customize ["modifyvm", :id, "--natdnsproxy1", "on"]
end
```

**Libvirt:**

```ruby
config.vm.provider "libvirt" do |libvirt|
  libvirt.volume_cache = "writeback"
  libvirt.storage :file, :size => '40G', :type => 'qcow2'
end
```

## Network Issues

### Port Forwarding Problems

**Symptoms:**

- Cannot access services running in VM from host
- Port conflicts
- Network timeouts

**Diagnostic Steps:**

1. **Check port forwarding configuration:**

   ```bash
   vagrant ssh-config

   # Look for forwarded ports
   # Default SSH is usually 127.0.0.1:2222 -> guest:22
   ```

2. **Test connectivity from within VM:**

   ```bash
   vagrant ssh

   # Test service is running
   netstat -tlnp | grep :3000

   # Test service responds locally
   curl http://localhost:3000
   ```

**Common Solutions:**

1. **Add explicit port forwarding:**

   In your `Vagrantfile`:

   ```ruby
   # Forward port 3000 for Node.js apps
   config.vm.network "forwarded_port", guest: 3000, host: 3000

   # Forward port 8000 for Python apps
   config.vm.network "forwarded_port", guest: 8000, host: 8000
   ```

2. **Use private network:**

   ```ruby
   # Set static IP for direct access
   config.vm.network "private_network", ip: "192.168.56.10"

   # Then access via: http://192.168.56.10:3000
   ```

3. **Fix port conflicts:**

   ```bash
   # Check what's using the port on host
   lsof -i :3000

   # Kill conflicting process or use different port
   config.vm.network "forwarded_port", guest: 3000, host: 3001
   ```

### DNS Resolution Issues

**Fix DNS problems:**

```bash
# In VM, edit /etc/systemd/resolved.conf
sudo vim /etc/systemd/resolved.conf

# Add:
# DNS=8.8.8.8 8.8.4.4
# FallbackDNS=1.1.1.1 1.0.0.1

sudo systemctl restart systemd-resolved
```

## KVM Issues

### KVM Module Management

**Symptoms:**

- Cannot start Libvirt VMs
- "KVM is not available" errors
- Performance issues with nested virtualization

**Check KVM status:**

```bash
# Check if KVM modules are loaded
lsmod | grep kvm

# Check KVM device access
ls -la /dev/kvm

# Verify user permissions
groups $USER | grep kvm
```

**KVM Module Issues:**

If you need to unload KVM modules (for nested virtualization or
troubleshooting):

```bash
# Use our KVM management script
cd scripts
sudo ./kvm-unload.sh --dry-run

# If dry run looks good, execute
sudo ./kvm-unload.sh

# To reload KVM later
sudo modprobe kvm_intel  # or kvm_amd for AMD
```

**Permanent KVM disable (if needed):**

```bash
# Create blacklist file
sudo ./kvm-unload.sh --permanent

# This prevents KVM from loading on boot
# Useful for nested virtualization setups
```

### Libvirt Service Issues

**Service management:**

```bash
# Check libvirt status
sudo systemctl status libvirtd

# Restart if needed
sudo systemctl restart libvirtd

# Enable on boot
sudo systemctl enable libvirtd
```

**Network issues:**

```bash
# Reset default network
sudo virsh net-destroy default
sudo virsh net-start default

# Check network status
sudo virsh net-list --all
```

## Recovery Procedures

### VM Corruption Recovery

**If VM becomes corrupted or unresponsive:**

1. **Try graceful recovery:**

   ```bash
   vagrant halt
   vagrant up
   ```

2. **Force stop and restart:**

   ```bash
   vagrant halt --force
   vagrant up
   ```

3. **Restore from snapshot:**

   ```bash
   vagrant snapshot list
   vagrant snapshot restore <snapshot-name>
   ```

4. **Complete rebuild:**
   ```bash
   vagrant destroy --force
   vagrant up
   ```

### Data Recovery

**Recover files from corrupted VM:**

1. **Mount VM disk (VirtualBox):**

   ```bash
   # Find VM directory
   VBoxManage list vms

   # Mount VDI file using tools like:
   # - VirtualBox VM with the disk attached
   # - qemu-nbd on Linux
   # - VBoxManage convertfromraw for extraction
   ```

2. **Access via shared folders:**
   ```bash
   # If shared folders are still working
   vagrant ssh
   cp important_files /vagrant/backup/
   ```

### Host System Recovery

**If host system becomes unstable:**

1. **Stop all VMs:**

   ```bash
   vagrant global-status
   vagrant halt --id <vm-id>  # For each running VM
   ```

2. **Reset VirtualBox/Libvirt:**

   ```bash
   # VirtualBox
   sudo systemctl restart virtualbox

   # Libvirt
   sudo systemctl restart libvirtd
   ```

## Advanced Debugging

### Enable Debug Logging

**Vagrant debug mode:**

```bash
VAGRANT_LOG=info vagrant up
VAGRANT_LOG=debug vagrant up  # Very verbose
```

**VirtualBox debug mode:**

```bash
VBoxManage setextradata global VBoxInternal/Logging/Enabled 1
VBoxManage setextradata global VBoxInternal/Logging/Flags "all"
```

### System Diagnostics

**Comprehensive system check:**

```bash
# Create diagnostic script
cat > diagnose.sh << 'EOF'
#!/bin/bash
echo "=== System Information ==="
uname -a
free -h
df -h

echo "=== Virtualization Support ==="
egrep -c '(vmx|svm)' /proc/cpuinfo

echo "=== VirtualBox Status ==="
VBoxManage --version 2>/dev/null || echo "VirtualBox not found"

echo "=== Libvirt Status ==="
systemctl is-active libvirtd 2>/dev/null || echo "Libvirt not active"

echo "=== Vagrant Status ==="
vagrant --version
vagrant global-status

echo "=== Network Interfaces ==="
ip addr show
EOF

chmod +x diagnose.sh
./diagnose.sh
```

## Getting Help

If these troubleshooting steps don't resolve your issue:

1. **Search existing issues:**
   [GitHub Issues](https://github.com/dev-box/dev-box/issues)
2. **Ask in Discord:** [dev-box Community](https://discord.gg/devbox)
3. **Create detailed issue report** with:
   - Your operating system and version
   - Vagrant and provider versions
   - Full error messages
   - Steps to reproduce
   - Output of the diagnostic script above

## Prevention Tips

### Regular Maintenance

1. **Create regular snapshots:**

   ```bash
   vagrant snapshot push --name "daily-$(date +%Y%m%d)"
   ```

2. **Update base boxes periodically:**

   ```bash
   vagrant box update
   ```

3. **Monitor system resources:**

   ```bash
   # Set up monitoring for disk space, RAM usage
   df -h
   free -h
   ```

4. **Keep logs organized:**
   ```bash
   # Regular log cleanup
   find ~/.vagrant.d/logs -name "*.log" -mtime +30 -delete
   ```

### Best Practices

- Always test configuration changes in a snapshot
- Keep important data in shared folders or version control
- Document custom configurations
- Regular backups of Vagrantfile and provisioning scripts
- Monitor resource usage to prevent host system issues

---

**Still having issues?** Check our [FAQ](/troubleshooting/faq/) or reach out to
the community for help!
