# Libvirt Migration Guide

## Overview

This guide documents the migration from VirtualBox to libvirt/KVM as the primary virtualization provider for dev-box. This change resolves Ubuntu 24.04 compatibility issues and provides better performance through native KVM integration.

## Why the Migration?

### Issues with VirtualBox
- **Ubuntu 24.04 Support**: Canonical discontinued official VirtualBox support for Ubuntu 24.04
- **Box Availability**: `hashicorp-education/ubuntu-24-04` only supports VirtualBox provider
- **Performance**: VirtualBox has overhead compared to native KVM virtualization
- **Compatibility**: Modern Linux distributions favor KVM/libvirt over VirtualBox

### Benefits of Libvirt/KVM
- **Native Virtualization**: Direct hardware virtualization support
- **Better Performance**: Lower overhead and faster I/O
- **Modern Ecosystem**: Better integration with cloud and container technologies
- **Flexibility**: Support for various hypervisors (KVM, QEMU, Xen)

## Migration Changes

### 1. Packer Configuration
- **Created**: Custom Packer builds for Ubuntu 24.04 libvirt boxes
- **Location**: `packer/` directory with complete build system
- **Features**: Cloud-init autoinstall, development toolchain, libvirt optimizations

### 2. Vagrantfile Updates
- **Box Source**: Changed from `hashicorp-education/ubuntu-24-04` to `local/ubuntu-24.04-libvirt`
- **Provider**: Forced libvirt provider with KVM optimizations
- **Configuration**: Added libvirt-specific settings for performance

### 3. CI/CD Pipeline
- **Added**: Automated Vagrant box building with Packer
- **Testing**: Comprehensive libvirt compatibility testing
- **Artifacts**: Automatic box uploads for releases

### 4. Documentation
- **Updated**: All references to use libvirt instead of VirtualBox
- **Added**: Complete build and setup guides
- **Included**: Troubleshooting for common libvirt issues

## Quick Start

### Prerequisites
```bash
# Install libvirt and KVM
sudo apt-get install qemu-kvm libvirt-daemon-system libvirt-clients virtinst

# Install Vagrant
curl -fsSL https://releases.hashicorp.com/vagrant/2.4.1/vagrant_2.4.1-1_amd64.deb -o vagrant.deb
sudo dpkg -i vagrant.deb

# Install vagrant-libvirt plugin
sudo apt-get install ruby-dev libvirt-dev
vagrant plugin install vagrant-libvirt

# Add user to libvirt group
sudo usermod -a -G libvirt $USER
# Log out and back in for group changes to take effect
```

### Building Your Box
```bash
# Navigate to packer directory
cd packer/

# Build the box (takes 20-30 minutes)
./build-box.sh

# Add to Vagrant
vagrant box add ubuntu-2404-dev output/ubuntu-24.04-dev-libvirt.box
```

### Using the Environment
```bash
# Start the development environment
vagrant up --provider=libvirt

# SSH into the VM
vagrant ssh

# Test development tools
claude --version
gh --version
```

## Box Features

### Development Toolchain
- **Claude CLI**: Latest version for AI assistance
- **GitHub CLI**: Repository management
- **UV**: Modern Python package manager
- **Ruff**: Fast Python linter/formatter
- **Terraform**: Infrastructure as code
- **Docker**: Containerization platform
- **Node.js LTS**: JavaScript runtime
- **Rust**: Systems programming language

### Libvirt Optimizations
- **Virtio Drivers**: High-performance paravirtualized drivers
- **QEMU Guest Agent**: Better host-guest integration
- **CPU Passthrough**: Direct CPU feature access
- **Optimized Storage**: QCOW2 format with writeback caching
- **Network Performance**: Virtio networking

### Security Features
- **Vagrant User**: Preconfigured with insecure key (for development)
- **SSH Hardening**: Secure SSH configuration
- **Firewall**: UFW configured for development use
- **Package Updates**: Latest security updates installed

## Configuration Options

### VM Resources
```ruby
config.vm.provider :libvirt do |libvirt|
  libvirt.memory = 4096      # RAM in MB
  libvirt.cpus = 4           # Number of CPUs
  libvirt.nested = true      # Enable nested virtualization
  libvirt.cpu_mode = "host-passthrough"  # CPU performance
end
```

### Storage Configuration
```ruby
libvirt.storage :file, :size => '40G', :type => 'qcow2'
libvirt.volume_cache = "writeback"
libvirt.disk_bus = "virtio"
```

### Network Settings
```ruby
config.vm.network "private_network", type: "dhcp"
config.vm.network "forwarded_port", guest: 3000, host: 3000
```

## Troubleshooting

### Common Issues

#### Permission Denied
```bash
# Check libvirt group membership
groups $USER

# If libvirt group is missing, add user and restart
sudo usermod -a -G libvirt $USER
# Log out and back in
```

#### KVM Not Available
```bash
# Check KVM support
sudo kvm-ok

# If KVM not supported, Vagrant will use QEMU emulation
# Performance will be slower but functional
```

#### Network Issues
```bash
# Restart libvirt networking
sudo systemctl restart libvirtd

# Check default network
sudo virsh net-list --all
sudo virsh net-start default
```

#### Box Build Failures
```bash
# Check Packer logs
cd packer/
packer build -debug ubuntu-24.04-libvirt.pkr.hcl

# Common issues:
# - Insufficient disk space (need 10GB+ free)
# - Network timeouts (check internet connection)
# - KVM permissions (check libvirt group)
```

### Performance Tuning

#### Host System
```bash
# Enable CPU governor performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase vm.swappiness for better performance
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

#### Guest System
```ruby
# In Vagrantfile
config.vm.provider :libvirt do |libvirt|
  # Use all available CPU cores
  libvirt.cpus = `nproc`.to_i
  
  # Optimize memory allocation
  libvirt.memory = (`free -m | grep '^Mem' | awk '{print $2}'`.to_i * 0.5).to_i
  
  # CPU topology optimization
  libvirt.numa_nodes = [
    { :cpus => "0-#{`nproc`.to_i - 1}", :memory => libvirt.memory }
  ]
end
```

## Migration Checklist

- [ ] Install libvirt and KVM
- [ ] Install Vagrant with libvirt plugin
- [ ] Add user to libvirt group
- [ ] Build custom Ubuntu 24.04 box
- [ ] Test basic Vagrant operations
- [ ] Update project Vagrantfile
- [ ] Test development workflow
- [ ] Update documentation
- [ ] Remove VirtualBox dependencies

## Support

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check docs/ directory for detailed guides
- **Community**: Join discussions in GitHub Discussions

### Contributing
- **Box Improvements**: Submit PRs for Packer configuration
- **Documentation**: Help improve setup guides
- **Testing**: Report compatibility issues across different systems

## References

- [Vagrant Libvirt Documentation](https://vagrant-libvirt.github.io/vagrant-libvirt/)
- [KVM/QEMU Documentation](https://www.qemu.org/documentation/)
- [Packer QEMU Builder](https://www.packer.io/docs/builders/qemu)
- [Ubuntu Cloud Images](https://cloud-images.ubuntu.com/)