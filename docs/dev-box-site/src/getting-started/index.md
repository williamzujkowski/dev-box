---
layout: guide.njk
title: "Getting Started with dev-box"
description:
  "Complete installation and setup guide for the dev-box development environment
  platform"
eleventyNavigation:
  key: Getting Started
  order: 1
toc: true
---

# Getting Started with dev-box

Welcome to dev-box! This guide will help you set up isolated Ubuntu 24.04
development environments using Vagrant and VirtualBox or Libvirt/KVM.

## What is dev-box?

dev-box is a comprehensive development environment platform that provides:

- **Isolated Ubuntu 24.04 LTS environments** for safe development and testing
- **Vagrant-based VM management** with VirtualBox and Libvirt/KVM support
- **Pre-configured development tools** including Node.js, Python, Docker, and
  more
- **Snapshot and rollback capabilities** for safe experimentation
- **KVM module management** for optimal virtualization performance
- **Comprehensive safety features** with monitoring and resource management

## Quick Start

If you're already familiar with Vagrant and have the prerequisites installed,
here's the fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/dev-box/dev-box.git
cd dev-box

# Start your first VM
vagrant up

# SSH into the environment
vagrant ssh

# Create a snapshot before making changes
vagrant snapshot push
```

## Detailed Installation

### Step 1: Install Prerequisites

#### VirtualBox (Recommended for beginners)

**Ubuntu/Debian:**

```bash
# Add Oracle VirtualBox repository
sudo apt update
sudo apt install -y wget gnupg
wget -O- https://www.virtualbox.org/download/oracle_vbox_2016.asc | \
  sudo gpg --dearmor --yes --output /usr/share/keyrings/oracle-virtualbox-2016.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/oracle-virtualbox-2016.gpg] https://download.virtualbox.org/virtualbox/debian $(lsb_release -cs) contrib" | \
  sudo tee /etc/apt/sources.list.d/virtualbox.list

sudo apt update
sudo apt install -y virtualbox-7.1

# Add your user to vboxusers group
sudo usermod -aG vboxusers $USER
```

**macOS:**

```bash
# Using Homebrew
brew install --cask virtualbox
```

**Windows:** Download and install from
[VirtualBox Downloads](https://www.virtualbox.org/wiki/Downloads)

#### Vagrant

**Ubuntu/Debian:**

```bash
# Add HashiCorp repository
wget -O- https://apt.releases.hashicorp.com/gpg | \
  gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update
sudo apt install -y vagrant
```

**macOS:**

```bash
# Using Homebrew
brew install vagrant
```

**Windows:** Download and install from
[Vagrant Downloads](https://www.vagrantup.com/downloads)

#### Libvirt/KVM (Optional - Advanced users)

For better performance on Linux systems:

```bash
# Install KVM and libvirt
sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils

# Add user to libvirt group
sudo usermod -aG libvirt $USER

# Install vagrant-libvirt plugin
vagrant plugin install vagrant-libvirt
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/dev-box/dev-box.git
cd dev-box
```

### Step 3: Choose Your Provider

#### Option A: VirtualBox (Default)

```bash
# Use the default Vagrantfile (VirtualBox provider)
vagrant up
```

#### Option B: Libvirt/KVM

```bash
# Use the enhanced Libvirt configuration
cd libvirt-enhanced
vagrant up --provider=libvirt
```

### Step 4: First Boot and SSH

```bash
# Wait for the VM to boot (this may take 5-10 minutes on first run)
vagrant up

# SSH into your new development environment
vagrant ssh

# Verify the installation
uname -a
echo "Welcome to your dev-box environment!"
```

## Your First Development Session

Once you're SSH'd into your dev-box environment:

### 1. Explore the Environment

```bash
# Check installed tools
node --version
npm --version
python3 --version
docker --version

# View the workspace
ls -la /home/vagrant/
```

### 2. Create a Test Project

```bash
# Create a new project directory
mkdir ~/my-first-project
cd ~/my-first-project

# Initialize a Node.js project
npm init -y
npm install express

# Create a simple server
cat > server.js << 'EOF'
const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.send('Hello from dev-box!');
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Server running at http://localhost:${port}`);
});
EOF

# Start the server
node server.js
```

### 3. Access Your Application

The VM is configured with port forwarding, so you can access your application
from your host machine:

- Open your browser and navigate to `http://localhost:3000`
- You should see "Hello from dev-box!"

### 4. Create Your First Snapshot

Before making any significant changes, create a snapshot:

```bash
# Exit the SSH session
exit

# Create a snapshot from the host
vagrant snapshot push --name "clean-state"

# View available snapshots
vagrant snapshot list
```

## What's Next?

Now that you have dev-box up and running, explore these topics:

1. **[Vagrant Workflow Guide](/guides/vagrant-workflow/)** - Learn daily
   workflows and best practices
2. **[Provisioning Guide](/guides/provisioning/)** - Customize your environment
   with additional tools
3. **[Libvirt Setup](/guides/libvirt-setup/)** - Switch to KVM for better
   performance
4. **[Troubleshooting](/troubleshooting/)** - Solutions to common issues

## Common First-Time Issues

### VM Won't Start

**Check VirtualBox installation:**

```bash
VBoxManage --version
```

**Verify sufficient resources:**

```bash
free -h  # Check available RAM
df -h    # Check disk space
```

### SSH Connection Issues

**Check VM status:**

```bash
vagrant status
```

**Try reloading the VM:**

```bash
vagrant reload
```

### Slow Performance

1. **Increase VM resources** in the Vagrantfile:

   ```ruby
   config.vm.provider "virtualbox" do |vb|
     vb.memory = "4096"  # Increase from default 2048
     vb.cpus = 4         # Increase from default 2
   end
   ```

2. **Enable hardware virtualization** in your computer's BIOS/UEFI settings

3. **Consider switching to Libvirt/KVM** for better Linux performance

## Getting Help

- **Documentation:** Browse our comprehensive [guides](/guides/)
- **Troubleshooting:** Check the [troubleshooting section](/troubleshooting/)
- **Community:** Join our [Discord server](https://discord.gg/devbox)
- **Issues:** Report bugs on [GitHub](https://github.com/dev-box/dev-box/issues)

## System Requirements

### Minimum Requirements

- **RAM:** 8GB (4GB for VM + 4GB for host)
- **Disk:** 20GB available space
- **CPU:** Dual-core with virtualization support
- **OS:** Windows 10+, macOS 10.14+, or Linux

### Recommended Requirements

- **RAM:** 16GB or more
- **Disk:** 50GB+ available space (SSD preferred)
- **CPU:** Quad-core with VT-x/AMD-V support
- **OS:** Recent Linux distribution for best performance

Ready to dive deeper? Check out our [comprehensive guides](/guides/) or start
with the [Vagrant workflow guide](/guides/vagrant-workflow/)!
