---
layout: page.njk
title: "API Reference"
description:
  "Complete reference for dev-box CLI commands, configuration options, and
  programmatic interfaces"
eleventyNavigation:
  key: API Reference
  order: 3
---

# API Reference

Complete reference documentation for the dev-box platform's CLI commands,
configuration options, and programmatic interfaces.

## Quick Reference

### Essential Commands

```bash
# VM Management
vagrant up                    # Start VM
vagrant halt                  # Stop VM
vagrant destroy               # Delete VM
vagrant reload                # Restart VM
vagrant ssh                   # Connect to VM

# Snapshots
vagrant snapshot push         # Create snapshot
vagrant snapshot pop          # Restore latest snapshot
vagrant snapshot list         # List snapshots

# Status and Information
vagrant status                # VM status
vagrant global-status         # All VMs status
```

## CLI Commands

### Core Vagrant Commands

#### `vagrant up`

Start and provision the virtual machine.

**Usage:**

```bash
vagrant up [options] [name|id]
```

**Options:**

- `--provider=PROVIDER` - Specify provider (virtualbox, libvirt)
- `--provision` - Force provisioning
- `--no-provision` - Skip provisioning
- `--parallel` - Start multiple VMs in parallel

**Examples:**

```bash
# Start with VirtualBox (default)
vagrant up

# Start with Libvirt provider
vagrant up --provider=libvirt

# Start without running provisioning scripts
vagrant up --no-provision
```

#### `vagrant halt`

Stop the virtual machine.

**Usage:**

```bash
vagrant halt [options] [name|id]
```

**Options:**

- `--force` - Force shutdown (equivalent to pulling power)

**Examples:**

```bash
# Graceful shutdown
vagrant halt

# Force shutdown
vagrant halt --force
```

#### `vagrant destroy`

Delete the virtual machine.

**Usage:**

```bash
vagrant destroy [options] [name|id]
```

**Options:**

- `--force` - Don't ask for confirmation
- `--graceful` - Attempt graceful shutdown first

**Examples:**

```bash
# Destroy with confirmation
vagrant destroy

# Destroy without confirmation
vagrant destroy --force
```

#### `vagrant reload`

Restart the virtual machine and re-apply configuration.

**Usage:**

```bash
vagrant reload [options] [name|id]
```

**Options:**

- `--provision` - Force provisioning
- `--no-provision` - Skip provisioning

#### `vagrant ssh`

Connect to the virtual machine via SSH.

**Usage:**

```bash
vagrant ssh [options] [name|id] [-- extra_ssh_args]
```

**Options:**

- `-c, --command` - Execute a single command
- `-p, --plain` - Plain SSH without authentication setup

**Examples:**

```bash
# Interactive SSH session
vagrant ssh

# Execute single command
vagrant ssh -c "ls -la"

# SSH with additional arguments
vagrant ssh -- -L 8080:localhost:8080
```

### Snapshot Management

#### `vagrant snapshot push`

Create a new snapshot.

**Usage:**

```bash
vagrant snapshot push [options] [vm-name]
```

**Options:**

- `--name=NAME` - Name for the snapshot

**Examples:**

```bash
# Create unnamed snapshot
vagrant snapshot push

# Create named snapshot
vagrant snapshot push --name "before-changes"
```

#### `vagrant snapshot pop`

Restore and delete the most recent snapshot.

**Usage:**

```bash
vagrant snapshot pop [options] [vm-name]
```

**Options:**

- `--no-delete` - Restore without deleting snapshot
- `--no-start` - Don't start VM after restore

#### `vagrant snapshot save`

Save a named snapshot.

**Usage:**

```bash
vagrant snapshot save [vm-name] snapshot_name
```

#### `vagrant snapshot restore`

Restore a named snapshot.

**Usage:**

```bash
vagrant snapshot restore [vm-name] snapshot_name
```

#### `vagrant snapshot list`

List all snapshots.

**Usage:**

```bash
vagrant snapshot list [vm-name]
```

#### `vagrant snapshot delete`

Delete a named snapshot.

**Usage:**

```bash
vagrant snapshot delete [vm-name] snapshot_name
```

### Information Commands

#### `vagrant status`

Show status of the virtual machine.

**Usage:**

```bash
vagrant status [name|id]
```

**Output States:**

- `not created` - VM doesn't exist
- `running` - VM is running
- `poweroff` - VM is stopped
- `saved` - VM is suspended
- `aborted` - VM was aborted

#### `vagrant global-status`

Show status of all Vagrant environments.

**Usage:**

```bash
vagrant global-status [options]
```

**Options:**

- `--prune` - Remove invalid entries

#### `vagrant ssh-config`

Show SSH configuration for connecting to VM.

**Usage:**

```bash
vagrant ssh-config [name|id]
```

#### `vagrant port`

Display guest port mappings.

**Usage:**

```bash
vagrant port [name|id]
```

### Box Management

#### `vagrant box list`

List installed boxes.

**Usage:**

```bash
vagrant box list
```

#### `vagrant box add`

Add a new box.

**Usage:**

```bash
vagrant box add name url
```

#### `vagrant box update`

Update boxes to latest version.

**Usage:**

```bash
vagrant box update [options]
```

#### `vagrant box remove`

Remove a box.

**Usage:**

```bash
vagrant box remove name
```

### Provisioning

#### `vagrant provision`

Run provisioning scripts.

**Usage:**

```bash
vagrant provision [vm-name] [options]
```

**Options:**

- `--provision-with` - Run specific provisioner

#### `vagrant reload --provision`

Restart VM and run provisioning.

**Usage:**

```bash
vagrant reload --provision
```

## Configuration Reference

### Vagrantfile Configuration

The `Vagrantfile` is a Ruby file that defines your VM configuration.

#### Basic Structure

```ruby
Vagrant.configure("2") do |config|
  # Configuration goes here
end
```

#### Box Configuration

```ruby
config.vm.box = "hashicorp-education/ubuntu-24-04"
config.vm.box_version = ">= 1.0.0"
config.vm.box_check_update = false
```

#### VM Settings

```ruby
config.vm.hostname = "dev-box"
config.vm.define "main" do |main|
  # VM-specific configuration
end
```

#### Network Configuration

```ruby
# Port forwarding
config.vm.network "forwarded_port", guest: 80, host: 8080

# Private network with DHCP
config.vm.network "private_network", type: "dhcp"

# Private network with static IP
config.vm.network "private_network", ip: "192.168.56.10"

# Public network (bridged)
config.vm.network "public_network"
```

#### Shared Folders

```ruby
# Basic shared folder
config.vm.synced_folder ".", "/vagrant"

# Disabled shared folder
config.vm.synced_folder ".", "/vagrant", disabled: true

# Custom shared folder
config.vm.synced_folder "src/", "/home/vagrant/src"

# NFS shared folder (better performance)
config.vm.synced_folder ".", "/vagrant", type: "nfs"
```

#### Provider Configuration

**VirtualBox:**

```ruby
config.vm.provider "virtualbox" do |vb|
  vb.name = "dev-box-vm"
  vb.memory = "2048"
  vb.cpus = 2
  vb.gui = false

  # VirtualBox-specific settings
  vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
  vb.customize ["modifyvm", :id, "--natdnsproxy1", "on"]
  vb.customize ["modifyvm", :id, "--ioapic", "on"]
  vb.customize ["modifyvm", :id, "--vram", "16"]
end
```

**Libvirt:**

```ruby
config.vm.provider "libvirt" do |libvirt|
  libvirt.memory = 2048
  libvirt.cpus = 2
  libvirt.driver = "kvm"
  libvirt.video_type = "virtio"
  libvirt.sound_type = nil
  libvirt.nic_model_type = "virtio"
  libvirt.disk_bus = "virtio"
  libvirt.volume_cache = "writeback"

  # Storage configuration
  libvirt.storage :file, :size => '40G', :type => 'qcow2'
end
```

#### Provisioning Configuration

```ruby
# Shell provisioning
config.vm.provision "shell", inline: <<-SHELL
  apt update
  apt install -y nginx
SHELL

# Shell script provisioning
config.vm.provision "shell", path: "scripts/setup.sh"

# Shell provisioning with arguments
config.vm.provision "shell", path: "scripts/setup.sh", args: ["arg1", "arg2"]

# Privileged vs non-privileged
config.vm.provision "shell", path: "scripts/setup.sh", privileged: false

# Run only once
config.vm.provision "shell", path: "scripts/setup.sh", run: "once"

# Run on every provision
config.vm.provision "shell", path: "scripts/setup.sh", run: "always"
```

### Environment Variables

#### Vagrant Environment Variables

```bash
# Enable debug logging
export VAGRANT_LOG=info
export VAGRANT_LOG=debug

# Set default provider
export VAGRANT_DEFAULT_PROVIDER=libvirt

# Disable box update checks
export VAGRANT_BOX_UPDATE_CHECK_DISABLE=1

# Custom Vagrant home directory
export VAGRANT_HOME=/custom/path

# Disable color output
export VAGRANT_NO_COLOR=1

# Set parallel execution limit
export VAGRANT_MAX_THREADS=4
```

#### Provider-specific Variables

```bash
# VirtualBox
export VBOX_USER_HOME=/custom/virtualbox/path

# Libvirt
export LIBVIRT_DEFAULT_URI=qemu:///system
```

## Script Reference

### KVM Management Scripts

#### `kvm-unload.sh`

Safely unload KVM kernel modules.

**Usage:**

```bash
sudo ./scripts/kvm-unload.sh [options]
```

**Options:**

- `--dry-run` - Show what would be done without executing
- `--force` - Force unload even if VMs are running (DANGEROUS)
- `--permanent` - Create permanent blacklist to prevent loading on boot
- `--rollback` - Restore previous state from backup
- `--verbose` - Enable verbose output
- `--help` - Show help message

**Examples:**

```bash
# Safe dry run
sudo ./scripts/kvm-unload.sh --dry-run

# Normal unload (will fail if VMs running)
sudo ./scripts/kvm-unload.sh

# Force unload (dangerous - can cause data loss)
sudo ./scripts/kvm-unload.sh --force

# Permanent disable for nested virtualization
sudo ./scripts/kvm-unload.sh --permanent

# Rollback previous operation
sudo ./scripts/kvm-unload.sh --rollback
```

**Exit Codes:**

- `0` - Success
- `1` - General error
- `2` - VMs running (when not in force mode)

#### `test-kvm-unload.sh`

Test the KVM unload script functionality.

**Usage:**

```bash
./scripts/test-kvm-unload.sh [options]
```

**Options:**

- `--safe-only` - Run only tests that don't require root
- `--root-tests` - Run tests that require root privileges
- `--all` - Run all tests (requires root)

### Provisioning Scripts

#### `provision-dev-toolchain.sh`

Install development tools and environments.

**Usage:**

```bash
./scripts/provision-dev-toolchain.sh [options]
```

**Installed Tools:**

- Node.js (LTS) with npm
- Python 3 with pip and development packages
- Docker and docker-compose
- Git with common configuration
- Build tools (gcc, make, etc.)
- Text editors (vim, nano)

#### VM Test Scripts

#### `execute-fresh-vm-test.sh`

Execute a fresh VM test with comprehensive validation.

**Usage:**

```bash
./scripts/execute-fresh-vm-test.sh [provider]
```

**Parameters:**

- `provider` - Optional: `virtualbox` or `libvirt` (default: virtualbox)

#### `execute-libvirt-vm-test.sh`

Execute Libvirt-specific VM testing.

**Usage:**

```bash
./scripts/execute-libvirt-vm-test.sh
```

## Configuration Files

### Default Configuration (`config/default.yaml`)

```yaml
# VM Configuration
vm:
  memory: 2048
  cpus: 2
  name: "dev-box"

# Network Configuration
network:
  private_ip: "192.168.56.10"
  port_forwards:
    - guest: 3000, host: 3000  # Node.js
    - guest: 8000, host: 8000  # Python
    - guest: 5000, host: 5000  # Flask

# Provisioning
provision:
  update_packages: true
  install_docker: true
  install_nodejs: true
  install_python_dev: true

# Shared Folders
shared_folders:
  - host: ".", guest: "/vagrant"
  - host: "~/Projects", guest: "/home/vagrant/projects"
```

### Box Configuration

```yaml
# Supported base boxes
boxes:
  primary: "hashicorp-education/ubuntu-24-04"
  fallback: "bento/ubuntu-24.04"
  version: ">= 1.0.0"

# Box management
auto_update: false
check_update: true
```

## Error Codes

### Common Exit Codes

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Network error
- `4` - Provider error
- `5` - Box error

### Vagrant-specific Codes

- `126` - Command not found
- `127` - Permission denied
- `130` - Interrupted (Ctrl+C)

## Advanced Usage

### Multi-Machine Configuration

```ruby
Vagrant.configure("2") do |config|
  config.vm.define "web" do |web|
    web.vm.box = "hashicorp-education/ubuntu-24-04"
    web.vm.network "private_network", ip: "192.168.56.10"
  end

  config.vm.define "db" do |db|
    db.vm.box = "hashicorp-education/ubuntu-24-04"
    db.vm.network "private_network", ip: "192.168.56.11"
  end
end
```

### Conditional Configuration

```ruby
Vagrant.configure("2") do |config|
  # OS-specific configuration
  if Vagrant::Util::Platform.windows?
    config.vm.synced_folder ".", "/vagrant", type: "smb"
  else
    config.vm.synced_folder ".", "/vagrant", type: "nfs"
  end

  # Provider-specific configuration
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
  end

  config.vm.provider "libvirt" do |libvirt|
    libvirt.memory = 2048
  end
end
```

### Plugin Integration

```ruby
# Required plugins
required_plugins = %w[vagrant-libvirt vagrant-hostmanager]
plugins_to_install = required_plugins.select { |plugin| not Vagrant.has_plugin? plugin }
if not plugins_to_install.empty?
  puts "Installing plugins: #{plugins_to_install.join(' ')}"
  if system "vagrant plugin install #{plugins_to_install.join(' ')}"
    exec "vagrant #{ARGV.join(' ')}"
  else
    abort "Installation of one or more plugins has failed. Aborting."
  end
end
```

## Performance Tuning

### Resource Optimization

```ruby
config.vm.provider "virtualbox" do |vb|
  # Optimize CPU
  vb.cpus = [2, ([1, Etc.nprocessors].max * 0.5).floor].max

  # Optimize memory
  host_memory = `wmic computersystem get TotalPhysicalMemory`.split[1].to_i / 1024 / 1024
  vb.memory = [2048, (host_memory * 0.25).floor].max

  # Performance settings
  vb.customize ["modifyvm", :id, "--hwvirtex", "on"]
  vb.customize ["modifyvm", :id, "--nestedpaging", "on"]
  vb.customize ["modifyvm", :id, "--largepages", "on"]
  vb.customize ["modifyvm", :id, "--ioapic", "on"]
  vb.customize ["modifyvm", :id, "--pae", "on"]
end
```

---

**Need more specific information?** Check our
[troubleshooting guide](/troubleshooting/) or browse the [user guides](/guides/)
for detailed workflows and examples.
