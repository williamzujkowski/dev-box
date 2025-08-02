# Ubuntu 24.04 Libvirt Box Builder

This directory contains Packer configurations to build Ubuntu 24.04 LTS Vagrant boxes optimized for libvirt/KVM with a complete development toolchain.

## Features

- **Ubuntu 24.04 LTS** base system with latest updates
- **Libvirt/KVM optimized** with virtio drivers and QEMU guest agent
- **Development toolchain** including:
  - Claude CLI
  - GitHub CLI (gh)
  - UV Python package manager
  - Ruff Python linter/formatter
  - Terraform and tfsec
  - Docker and Docker Compose
  - Node.js LTS with npm
  - Rust toolchain
  - Go programming language
  - Visual Studio Code
  - Git and development utilities
- **Cloud-init autoinstall** (modern, not legacy preseed)
- **Vagrant-ready** with insecure key and passwordless sudo
- **Optimized for performance** with libvirt-specific tuning

## Quick Start

1. **Build the box:**
   ```bash
   ./build-box.sh
   ```

2. **Validate the box:**
   ```bash
   ./validate-box.sh
   ```

3. **Use the box:**
   ```bash
   vagrant box add ubuntu-2404-dev output/ubuntu-24.04-dev-libvirt.box
   vagrant init ubuntu-2404-dev
   vagrant up --provider=libvirt
   ```

## Requirements

- **Packer** 1.10.0 or later
- **KVM/QEMU** with hardware acceleration
- **Libvirt** and related tools
- **Vagrant** with vagrant-libvirt plugin
- At least **4GB RAM** and **25GB disk** space for building

### Installing Requirements (Ubuntu/Debian)

```bash
# Install Packer
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install packer

# Install libvirt and KVM
sudo apt install qemu-kvm libvirt-daemon-system libvirt-clients virtinst virt-manager
sudo usermod -aG libvirt $USER

# Install Vagrant
sudo apt install vagrant

# Install vagrant-libvirt plugin
vagrant plugin install vagrant-libvirt
```

## Configuration Files

### Main Files

- **`ubuntu-24.04-libvirt.pkr.hcl`** - Main Packer configuration
- **`variables.pkrvars.hcl`** - Build variables and customization
- **`cloud-init/user-data`** - Cloud-init autoinstall configuration
- **`cloud-init/meta-data`** - Cloud-init instance metadata

### Scripts

- **`scripts/install-dev-tools.sh`** - Development toolchain installation
- **`scripts/configure-vagrant.sh`** - Vagrant user and SSH setup
- **`scripts/libvirt-optimizations.sh`** - Libvirt-specific optimizations
- **`scripts/cleanup.sh`** - Final cleanup and box preparation

### Build Scripts

- **`build-box.sh`** - Automated build script
- **`validate-box.sh`** - Box validation and testing script

## Customization

### Modifying Resources

Edit `variables.pkrvars.hcl` to adjust:

```hcl
cpus       = "4"        # Number of CPUs
memory     = "4096"     # RAM in MB
disk_size  = "25G"      # Disk size
vm_name    = "ubuntu-24.04-dev-libvirt"
```

### Adding Development Tools

Edit `scripts/install-dev-tools.sh` to add more tools:

```bash
# Add your custom tool installation here
echo "Installing custom tool..."
sudo apt-get install -y custom-tool
```

### Modifying Cloud-Init

Edit `cloud-init/user-data` to customize:
- Package installations
- User configuration
- System settings
- Network configuration

## Build Process

The build process follows these steps:

1. **Download** Ubuntu 24.04 ISO
2. **Boot** VM with cloud-init autoinstall
3. **Install** base system with packages
4. **Configure** vagrant user and SSH
5. **Install** development toolchain
6. **Apply** libvirt optimizations
7. **Clean up** and minimize disk usage
8. **Package** as Vagrant box

## Build Options

### Basic Build
```bash
./build-box.sh
```

### Validation Only
```bash
./build-box.sh --validate-only
```

### Clean Build
```bash
./build-box.sh --clean
```

### Custom Variables
```bash
packer build -var 'cpus=8' -var 'memory=8192' ubuntu-24.04-libvirt.pkr.hcl
```

## Validation

The validation script tests:

- Box file structure
- VM boot and SSH connectivity
- Development tools functionality
- Vagrant user configuration
- System optimizations
- Performance metrics

```bash
# Full validation
./validate-box.sh

# Quick structure check only
./validate-box.sh --quick

# Skip boot test (faster)
./validate-box.sh --skip-boot

# Test specific box file
./validate-box.sh --box-file /path/to/box.box
```

## Output

After successful build, you'll find:

- **`output/*.box`** - Vagrant box file
- **`output/*.qcow2`** - Raw QCOW2 image
- **`build.log`** - Detailed build log
- **`validation-report-*.txt`** - Validation results

## Vagrant Cloud Upload

To upload to Vagrant Cloud, set environment variables:

```bash
export VAGRANT_CLOUD_TOKEN="your-token"
export VAGRANT_CLOUD_USERNAME="your-username"
./build-box.sh
```

## Troubleshooting

### Common Issues

1. **KVM not available:**
   ```bash
   # Check KVM support
   kvm-ok
   
   # Enable virtualization in BIOS/UEFI
   # Add user to kvm group
   sudo usermod -aG kvm $USER
   ```

2. **Build fails with network timeout:**
   - Check internet connection
   - Try different Ubuntu mirror
   - Increase timeout values in HCL file

3. **SSH connection fails:**
   - Check cloud-init configuration
   - Verify SSH key is properly installed
   - Check VM network configuration

4. **Box too large:**
   - Enable cleanup script optimizations
   - Remove unnecessary packages
   - Zero out free space more aggressively

### Debug Mode

Enable verbose logging:

```bash
export PACKER_LOG=1
./build-box.sh
```

## Development

### File Structure
```
packer/
├── ubuntu-24.04-libvirt.pkr.hcl    # Main config
├── variables.pkrvars.hcl            # Variables
├── cloud-init/
│   ├── user-data                    # Autoinstall config
│   └── meta-data                    # Instance metadata
├── scripts/
│   ├── install-dev-tools.sh         # Development tools
│   ├── configure-vagrant.sh         # Vagrant setup
│   ├── libvirt-optimizations.sh     # Libvirt tuning
│   └── cleanup.sh                   # Final cleanup
├── build-box.sh                     # Build script
├── validate-box.sh                  # Validation script
└── output/                          # Build outputs
```

### Testing Changes

1. Validate configuration:
   ```bash
   packer validate -var-file=variables.pkrvars.hcl ubuntu-24.04-libvirt.pkr.hcl
   ```

2. Test cloud-init syntax:
   ```bash
   cloud-init devel schema --config-file cloud-init/user-data
   ```

3. Build and validate:
   ```bash
   ./build-box.sh && ./validate-box.sh
   ```

## License

This configuration is based on the hashicorp-education Packer template and is provided under the same terms.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request

For issues and feature requests, please use the GitHub issue tracker.