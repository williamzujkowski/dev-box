---
layout: guide.njk
title: "Vagrant Workflow Guide"
description:
  "Master the essential Vagrant commands and workflows for daily development
  tasks with dev-box"
eleventyNavigation:
  key: Vagrant Workflow
  parent: Guides
  order: 1
difficulty: beginner
estimatedTime: "30 minutes"
toc: true
---

# Vagrant Workflow Guide

This guide covers the essential Vagrant workflows you'll use daily with dev-box.
Master these commands and patterns to become productive with your isolated
development environments.

## Daily Workflow Overview

A typical dev-box workflow follows this pattern:

1. **Start** your VM when beginning work
2. **Snapshot** before making significant changes
3. **Develop** within the isolated environment
4. **Test** your changes safely
5. **Snapshot** successful states
6. **Stop** the VM when finished

## Basic VM Lifecycle

### Starting Your Environment

```bash
# Navigate to your dev-box directory
cd dev-box

# Start the VM (first time may take 5-10 minutes)
vagrant up

# Check status
vagrant status
```

**What happens during `vagrant up`:**

- Downloads the Ubuntu 24.04 base box (first time only)
- Creates the virtual machine
- Configures network and shared folders
- Runs provisioning scripts
- Installs development tools

### Connecting to Your VM

```bash
# SSH into the running VM
vagrant ssh

# You're now in the Ubuntu environment
vagrant@dev-box:~$
```

**Inside the VM:**

```bash
# Check the environment
pwd                    # /home/vagrant
uname -a              # Ubuntu 24.04 details
ls /vagrant           # Your host project files

# Check installed tools
node --version        # Node.js LTS
python3 --version     # Python 3.12+
docker --version      # Docker CE
```

### Stopping Your Environment

```bash
# Graceful shutdown (recommended)
vagrant halt

# Force shutdown (if VM is unresponsive)
vagrant halt --force

# Verify it's stopped
vagrant status
```

## Working with Files

### Understanding Shared Folders

The dev-box automatically shares your project directory:

```bash
# On your host machine
echo "Hello from host" > test.txt

# In the VM
vagrant ssh
cat /vagrant/test.txt   # Shows: Hello from host

# Changes are bidirectional
echo "Hello from VM" > /vagrant/vm-file.txt
exit

# Back on host
cat vm-file.txt        # Shows: Hello from VM
```

### File Editing Strategies

**Option 1: Edit on host, run in VM (Recommended)**

```bash
# Edit files with your favorite host editor
code .                 # VS Code
vim src/app.js        # Vim
subl .                # Sublime Text

# Run and test in VM
vagrant ssh
cd /vagrant
npm start
```

**Option 2: Edit directly in VM**

```bash
vagrant ssh
vim /vagrant/src/app.js    # Edit directly in VM
nano /vagrant/README.md    # Or use nano
```

## Snapshot Management

Snapshots are your safety net - use them liberally!

### Creating Snapshots

```bash
# Quick unnamed snapshot
vagrant snapshot push

# Named snapshot (recommended)
vagrant snapshot push --name "initial-setup"

# Before making risky changes
vagrant snapshot push --name "before-database-migration"
```

### Managing Snapshots

```bash
# List all snapshots
vagrant snapshot list

# Restore the latest snapshot
vagrant snapshot pop

# Restore a specific snapshot
vagrant snapshot restore "initial-setup"

# Delete a snapshot
vagrant snapshot delete "old-snapshot"
```

### Snapshot Strategies

**Daily snapshots:**

```bash
# Create dated snapshots
vagrant snapshot push --name "daily-$(date +%Y%m%d)"
```

**Feature-based snapshots:**

```bash
# Before starting new features
vagrant snapshot push --name "before-user-auth"

# After completing features
vagrant snapshot push --name "user-auth-complete"
```

**Experimental snapshots:**

```bash
# Before trying something risky
vagrant snapshot push --name "before-experiment"

# If it fails, restore quickly
vagrant snapshot restore "before-experiment"
```

## Development Workflows

### Node.js Development Workflow

```bash
# Start VM and connect
vagrant up && vagrant ssh

# Navigate to your project
cd /vagrant

# Initialize project (if new)
npm init -y
npm install express

# Create a simple app
cat > app.js << 'EOF'
const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.json({ message: 'Hello from dev-box!', timestamp: new Date() });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Server running at http://localhost:${port}`);
});
EOF

# Start the application
node app.js
```

**Access from host browser:** `http://localhost:3000`

### Python Development Workflow

```bash
vagrant ssh
cd /vagrant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask

# Create Flask app
cat > app.py << 'EOF'
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        'message': 'Hello from Flask in dev-box!',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
EOF

# Run Flask app
python app.py
```

**Access from host browser:** `http://localhost:5000`

### Docker Development Workflow

```bash
vagrant ssh
cd /vagrant

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "app.js"]
EOF

# Build and run container
docker build -t my-app .
docker run -d -p 3000:3000 --name my-app-container my-app

# Check running containers
docker ps

# View logs
docker logs my-app-container
```

## Multi-VM Workflows

### Creating Multiple Environments

Edit your `Vagrantfile` for multiple VMs:

```ruby
Vagrant.configure("2") do |config|
  # Development VM
  config.vm.define "dev" do |dev|
    dev.vm.box = "hashicorp-education/ubuntu-24-04"
    dev.vm.network "private_network", ip: "192.168.56.10"
    dev.vm.network "forwarded_port", guest: 3000, host: 3000
  end

  # Testing VM
  config.vm.define "test" do |test|
    test.vm.box = "hashicorp-education/ubuntu-24-04"
    test.vm.network "private_network", ip: "192.168.56.11"
    test.vm.network "forwarded_port", guest: 3000, host: 3001
  end
end
```

### Managing Multiple VMs

```bash
# Start specific VM
vagrant up dev

# Start all VMs
vagrant up

# SSH to specific VM
vagrant ssh dev
vagrant ssh test

# Check status of all VMs
vagrant status

# Global status (all Vagrant VMs on system)
vagrant global-status
```

## Network Configuration

### Port Forwarding

Access services running in your VM from your host:

```ruby
# In Vagrantfile
config.vm.network "forwarded_port", guest: 3000, host: 3000  # Node.js
config.vm.network "forwarded_port", guest: 8000, host: 8000  # Python
config.vm.network "forwarded_port", guest: 5432, host: 5432  # PostgreSQL
config.vm.network "forwarded_port", guest: 6379, host: 6379  # Redis
```

### Private Networks

Create isolated networks between VMs:

```ruby
# Static IP
config.vm.network "private_network", ip: "192.168.56.10"

# DHCP
config.vm.network "private_network", type: "dhcp"
```

### Testing Network Connectivity

```bash
# From VM, test external connectivity
vagrant ssh
ping google.com
curl -I https://httpbin.org/get

# From host, test VM services
curl http://localhost:3000
nc -zv localhost 3000
```

## Provisioning Workflows

### Custom Provisioning Scripts

Create `scripts/setup.sh`:

```bash
#!/bin/bash
set -euo pipefail

echo "Installing custom tools..."

# Install additional packages
apt-get update
apt-get install -y htop tree jq

# Install global npm packages
npm install -g nodemon pm2 typescript

# Configure git (customize these)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

echo "Custom setup complete!"
```

Add to your `Vagrantfile`:

```ruby
config.vm.provision "shell", path: "scripts/setup.sh"
```

### Running Provisioning

```bash
# Re-run provisioning on existing VM
vagrant provision

# Force provisioning during startup
vagrant up --provision

# Skip provisioning during startup
vagrant up --no-provision
```

## Troubleshooting Workflows

### Common Issues and Solutions

**VM won't start:**

```bash
# Check available resources
free -h && df -h

# Check VirtualBox status
VBoxManage --version
VBoxManage list runningvms

# Try with more verbose output
VAGRANT_LOG=info vagrant up
```

**SSH connection issues:**

```bash
# Check SSH config
vagrant ssh-config

# Try reloading
vagrant reload

# Force stop and restart
vagrant halt --force
vagrant up
```

**Performance issues:**

```bash
# Increase VM resources in Vagrantfile
config.vm.provider "virtualbox" do |vb|
  vb.memory = "4096"  # Increase from 2048
  vb.cpus = 4         # Increase from 2
end

# Then reload
vagrant reload
```

### Recovery Procedures

**Corrupted VM:**

```bash
# Try recovery with snapshots
vagrant snapshot list
vagrant snapshot restore "last-good-state"

# If no snapshots, rebuild
vagrant destroy --force
vagrant up
```

**Lost work recovery:**

```bash
# Check shared folders
ls -la /vagrant  # In VM

# Files should be on host in project directory
ls -la .         # On host
```

## Performance Optimization

### Resource Allocation

```ruby
# Optimize based on host system
config.vm.provider "virtualbox" do |vb|
  # Use 50% of host cores, minimum 2
  vb.cpus = [2, (Etc.nprocessors * 0.5).floor].max

  # Use 25% of host RAM, minimum 2GB
  host_memory_mb = `wmic computersystem get TotalPhysicalMemory`.split[1].to_i / 1024 / 1024
  vb.memory = [2048, (host_memory_mb * 0.25).floor].max

  # Enable hardware acceleration
  vb.customize ["modifyvm", :id, "--hwvirtex", "on"]
  vb.customize ["modifyvm", :id, "--nestedpaging", "on"]
end
```

### Storage Optimization

```bash
# Clean up disk space regularly
vagrant ssh

# Clean package cache
sudo apt clean
sudo apt autoremove

# Clean Docker if used
docker system prune -f

# Clean npm cache
npm cache clean --force
```

## Best Practices

### Directory Structure

Organize your projects for easy VM management:

```
~/Development/
├── project1/
│   ├── Vagrantfile
│   ├── src/
│   └── scripts/
├── project2/
│   ├── Vagrantfile
│   ├── app/
│   └── docs/
└── shared-scripts/
    ├── common-setup.sh
    └── dev-tools.sh
```

### Naming Conventions

Use consistent naming for VMs and snapshots:

```bash
# VM names
vagrant up web-frontend
vagrant up api-backend
vagrant up database

# Snapshot names
vagrant snapshot push --name "feature-start-$(date +%Y%m%d)"
vagrant snapshot push --name "before-migration"
vagrant snapshot push --name "stable-$(git rev-parse --short HEAD)"
```

### Version Control

Track your Vagrant configuration:

```bash
# Add to git
git add Vagrantfile
git add scripts/
git commit -m "Add Vagrant configuration"

# Ignore VM-specific files
echo ".vagrant/" >> .gitignore
echo "*.log" >> .gitignore
```

## Advanced Workflows

### Automated Testing

```bash
# Create test script
cat > test.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting automated tests..."

# Start VM
vagrant up

# Run tests in VM
vagrant ssh -c "cd /vagrant && npm test"

# Create snapshot if tests pass
vagrant snapshot push --name "tests-passed-$(date +%Y%m%d-%H%M)"

echo "Tests completed successfully!"
EOF

chmod +x test.sh
```

### CI Integration

```yaml
# .github/workflows/vagrant.yml
name: Vagrant Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Vagrant tests
        run: |
          vagrant up
          vagrant ssh -c "cd /vagrant && npm test"
          vagrant destroy --force
```

## Summary

You now have the essential Vagrant workflows for productive dev-box usage:

- **VM lifecycle management** (up, halt, destroy, reload)
- **File sharing** between host and VM
- **Snapshot strategies** for safe experimentation
- **Development workflows** for different languages
- **Network configuration** for service access
- **Troubleshooting techniques** for common issues

### Next Steps

- Explore [Libvirt setup](/guides/libvirt-setup/) for better performance
- Learn about [custom provisioning](/guides/provisioning/) to customize your
  environment
- Check out [Docker development](/guides/docker-development/) workflows
- Review [performance tuning](/guides/performance/) techniques

### Quick Reference Card

```bash
# Essential commands
vagrant up          # Start VM
vagrant ssh         # Connect to VM
vagrant halt        # Stop VM
vagrant status      # Check status

# Snapshots
vagrant snapshot push --name "backup"
vagrant snapshot list
vagrant snapshot restore "backup"

# Troubleshooting
vagrant reload      # Restart VM
vagrant provision   # Re-run setup scripts
vagrant destroy     # Delete and rebuild
```

Happy developing with dev-box!
