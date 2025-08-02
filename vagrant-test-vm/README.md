# Vagrant Ubuntu 24.04 Test VM

This directory contains a complete Vagrant testing environment for Ubuntu 24.04
LTS with VirtualBox Guest Additions and development tools.

## Quick Start

```bash
# Navigate to the project directory
cd vagrant-test-vm

# Start the VM
vagrant up

# SSH into the VM
vagrant ssh

# Run integration tests
./tests/integration/vm-integration-test.sh

# Stop the VM
vagrant halt

# Destroy the VM (cleanup)
./scripts/cleanup/destroy-vm.sh
```

## Directory Structure

```
vagrant-test-vm/
├── Vagrantfile                           # Main Vagrant configuration
├── README.md                            # This file
├── scripts/                             # Provisioning and utility scripts
│   ├── provisioning/
│   │   ├── base-setup.sh               # Base system configuration
│   │   ├── guest-additions.sh          # VirtualBox Guest Additions
│   │   └── development-tools.sh        # Development environment setup
│   └── cleanup/
│       └── destroy-vm.sh                # VM cleanup script
└── tests/                               # Testing and validation
    ├── validation/
    │   └── vm-test-checklist.md        # Manual testing checklist
    └── integration/
        └── vm-integration-test.sh       # Automated integration tests
```

## VM Configuration

### Base Configuration

- **OS**: Ubuntu 24.04 LTS (Noble Numbat)
- **Box**: bento/ubuntu-24.04 (latest stable)
- **Memory**: 2048 MB
- **CPUs**: 2 cores
- **Hostname**: ubuntu-test-vm

### Network Configuration

- **Private Network**: DHCP
- **Port Forwarding**:
  - SSH: Host 2222 → Guest 22
  - HTTP: Host 8080 → Guest 80
  - HTTPS: Host 8443 → Guest 443

### Shared Folders

- Project root → `/vagrant`
- Test files → `/home/vagrant/tests`
- Scripts → `/home/vagrant/scripts`

## Included Software

### System Tools

- curl, wget, git, vim, htop, tree
- build-essential, dkms
- UFW firewall (configured)

### Development Tools

- **Node.js** (LTS) with npm
- **Python 3** with pip and venv
- **Docker** with docker-compose
- **VS Code** repository (ready for installation)

### Global Packages

- **npm**: typescript, nodemon, pm2, @angular/cli, create-react-app
- **Python**: requests, flask, fastapi, pytest, black, jupyter

## Provisioning Scripts

### 1. base-setup.sh

- Updates system packages
- Installs essential tools
- Configures timezone (UTC) and locale
- Sets up firewall and SSH security
- Creates workspace directories

### 2. guest-additions.sh

- Installs VirtualBox Guest Additions
- Handles different installation methods
- Verifies installation success
- Configures shared folder access

### 3. development-tools.sh

- Installs Node.js, Python, Docker
- Sets up development workspace
- Installs global packages
- Configures shell aliases and git

## Testing

### Automated Integration Tests

Run the comprehensive test suite:

```bash
./tests/integration/vm-integration-test.sh
```

Test categories:

- VM status and connectivity
- VirtualBox Guest Additions
- Shared folders and port forwarding
- System packages and tools
- Docker functionality
- Network connectivity
- Resource allocation
- Performance benchmarks

### Manual Testing Checklist

Use the detailed checklist for thorough validation:

- **File**: `tests/validation/vm-test-checklist.md`
- **85 test items** covering all aspects
- Organized by category with pass/fail tracking

## Usage Examples

### Basic Development Workflow

```bash
# Start VM
vagrant up

# SSH into VM
vagrant ssh

# Navigate to shared workspace
cd /home/vagrant/workspace

# Create a new project
mkdir my-project && cd my-project

# Initialize git repository
git init

# Install dependencies
npm init -y
npm install express

# Edit files (available in host at ./vagrant-test-vm/)
vim server.js
```

### Docker Development

```bash
# SSH into VM
vagrant ssh

# Run a container
docker run -d -p 3000:3000 --name web-app node:alpine

# Check running containers
docker ps

# Access logs
docker logs web-app
```

### Testing Web Applications

```bash
# Start development server in VM
cd /home/vagrant/workspace/my-app
npm start  # Runs on port 3000 in VM

# Access from host browser
# http://localhost:8080 (if app runs on port 80)
# Or configure port forwarding in Vagrantfile
```

## Performance Considerations

### Resource Requirements

- **Host RAM**: Minimum 4GB (6GB+ recommended)
- **Host Disk**: 20GB+ available space
- **CPU**: Virtualization support enabled

### Optimization Tips

1. **Enable VT-x/AMD-V** in BIOS for better performance
2. **Allocate sufficient RAM** to avoid swapping
3. **Use SSD storage** for faster I/O operations
4. **Close unnecessary host applications** during VM usage

## Troubleshooting

### Common Issues

**VM won't start:**

```bash
# Check VirtualBox installation
VBoxManage --version

# Verify sufficient resources
free -h && df -h
```

**Guest Additions not working:**

```bash
# Re-run guest additions script
vagrant ssh -c "sudo /home/vagrant/scripts/guest-additions.sh"

# Or re-provision
vagrant provision
```

**Network connectivity issues:**

```bash
# Check VM network status
vagrant ssh -c "ip addr show"

# Test DNS resolution
vagrant ssh -c "nslookup google.com"
```

**Shared folders not accessible:**

```bash
# Check mount status
vagrant ssh -c "mount | grep vboxsf"

# Verify user permissions
vagrant ssh -c "groups vagrant"
```

### Getting Help

1. **Check logs**: Vagrant and VirtualBox logs contain detailed error
   information
2. **Run tests**: Use integration tests to identify specific issues
3. **Verify checklist**: Manual checklist helps isolate problems
4. **Guest Additions**: Most issues relate to Guest Additions installation

## Cleanup

### Temporary Cleanup

```bash
# Stop VM but keep it available
vagrant halt
```

### Complete Cleanup

```bash
# Destroy VM and all associated files
./scripts/cleanup/destroy-vm.sh

# Or manually
vagrant destroy -f
```

## Advanced Configuration

### Customizing the Vagrantfile

- **Memory/CPU**: Modify `vb.memory` and `vb.cpus`
- **Port forwarding**: Add more `config.vm.network` entries
- **Shared folders**: Add `config.vm.synced_folder` entries
- **Provisioning**: Add custom shell scripts

### Adding Software

- **Modify provisioning scripts** for permanent changes
- **Use `vagrant provision`** to re-run provisioning
- **Install manually** for temporary changes

### Multiple VMs

- **Copy project directory** for isolated environments
- **Modify hostname and ports** to avoid conflicts
- **Use `vagrant global-status`** to manage multiple VMs

## Security Notes

- SSH root login is **disabled**
- UFW firewall is **enabled** with restrictive rules
- Only necessary ports are **forwarded**
- Guest Additions provide **secure shared folders**
- VM is **isolated** from host network by default

## Version Information

- **Ubuntu**: 24.04 LTS (Noble Numbat)
- **Vagrant Box**: bento/ubuntu-24.04 (>= 202404.23.0)
- **VirtualBox**: Compatible with latest versions
- **Vagrant**: Compatible with 2.3+

---

## Quick Reference Commands

```bash
# VM Lifecycle
vagrant up                    # Start VM
vagrant halt                  # Stop VM
vagrant reload                # Restart VM
vagrant destroy               # Delete VM
vagrant ssh                   # Connect to VM

# Status and Information
vagrant status                # VM status
vagrant global-status         # All VMs status
vagrant box list              # Available boxes

# Provisioning
vagrant provision             # Re-run provisioning
vagrant reload --provision    # Restart and provision

# Debugging
vagrant up --debug            # Verbose startup
VAGRANT_LOG=info vagrant up   # Detailed logging
```
