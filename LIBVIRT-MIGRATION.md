# Libvirt Migration Guide

This guide helps you migrate from VirtualBox to libvirt/KVM for better Ubuntu
24.04 compatibility.

## 🚨 Why Migrate to Libvirt?

Ubuntu 24.04 has known issues with VirtualBox guest additions and kernel module
compatibility. Libvirt/KVM provides:

- Native Linux virtualization with better performance
- Full Ubuntu 24.04 compatibility without kernel module issues
- Better resource management and CPU passthrough
- Native integration with Linux development workflows

## 📋 Migration Steps

### 1. Clean Stale State

If you previously used VirtualBox, remove the old state:

```bash
rm -rf .vagrant/
```

### 2. Install System Dependencies

Install the required packages for vagrant-libvirt:

```bash
sudo apt-get update
sudo apt-get install -y \
  libvirt-dev \
  ruby-dev \
  libxml2-dev \
  libxslt-dev \
  libssl-dev \
  pkg-config \
  build-essential \
  qemu-kvm \
  libvirt-daemon-system \
  libvirt-clients \
  virtinst \
  bridge-utils
```

### 3. Install vagrant-libvirt Plugin

```bash
vagrant plugin install vagrant-libvirt
```

### 4. Get the Libvirt Box

You have three options:

#### Option A: Use Pre-built Box from GitHub Releases (Recommended)

Check the latest release at https://github.com/williamzujkowski/dev-box/releases
for a pre-built box:

```bash
# Download the box from the release
wget https://github.com/williamzujkowski/dev-box/releases/download/v1.1.5/ubuntu-24.04-dev-libvirt.box

# Add it to Vagrant
vagrant box add local/ubuntu-24.04-libvirt ubuntu-24.04-dev-libvirt.box
```

#### Option B: Build Locally with Packer

If you want to build the box yourself:

```bash
cd packer
./build-box.sh
vagrant box add local/ubuntu-24.04-libvirt output/ubuntu-24.04-dev-libvirt.box
```

#### Option C: Use GitHub Actions Artifact

If a recent build is available as an artifact:

1. Go to https://github.com/williamzujkowski/dev-box/actions
2. Find the latest successful "Build and Test Vagrant Libvirt Box" workflow
3. Download the `vagrant-box-amd64` artifact
4. Add it:
   `vagrant box add local/ubuntu-24.04-libvirt path/to/ubuntu-24.04-dev-libvirt.box`

### 5. Start the VM

```bash
vagrant up --provider=libvirt
# Or simply (libvirt is now the default):
vagrant up
```

## 🔧 Troubleshooting

### Permission Denied Errors

If you get permission errors with libvirt:

```bash
# Add your user to the libvirt group
sudo usermod -a -G libvirt $USER

# Log out and back in, or run:
newgrp libvirt
```

### Network Issues

If the private network doesn't work:

```bash
# Start the default libvirt network
sudo virsh net-start default
sudo virsh net-autostart default
```

### Box Not Found

If Vagrant can't find the box:

```bash
# List your boxes
vagrant box list

# The box should be named exactly: local/ubuntu-24.04-libvirt
# If it has a different name, update the Vagrantfile accordingly
```

## 🚀 Helper Scripts

We provide several helper scripts in the `scripts/` directory:

- `complete-libvirt-migration.sh` - Interactive migration helper that checks
  your system status
- `install-libvirt-dependencies.sh` - Shows the exact commands to install
  dependencies
- `clean-vagrant-state.sh` - Cleans up old Vagrant state
- `setup-libvirt-box.sh` - Helps set up the libvirt box

Run the migration helper to check your current status:

```bash
./scripts/complete-libvirt-migration.sh
```

## ✅ Verification

After successful migration, verify everything works:

```bash
# Check VM status
vagrant status

# SSH into the VM
vagrant ssh

# Inside the VM, verify the hypervisor
systemd-detect-virt  # Should show "kvm"

# Check that development tools are installed
which git
which docker
which claude
```

## 📝 Notes

- The Vagrantfile is already configured to use libvirt as the default provider
- NFS is used for synced folders for better performance
- The VM includes QEMU guest agent for better host-guest integration
- CPU passthrough is enabled for optimal performance

## 🔄 Rolling Back

If you need to switch back to VirtualBox:

1. Destroy the libvirt VM: `vagrant destroy`
2. Remove the libvirt box: `vagrant box remove local/ubuntu-24.04-libvirt`
3. Comment out the `ENV['VAGRANT_DEFAULT_PROVIDER']` line in Vagrantfile
4. Use a VirtualBox-compatible box

However, we strongly recommend staying with libvirt for Ubuntu 24.04
compatibility.
