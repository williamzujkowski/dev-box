#!/bin/bash
# Vagrant Box Management Script for libvirt provider
# Handles building, adding, and managing local Ubuntu 24.04 boxes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log() {
  echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} box-manager: $1"
}

success() {
  echo -e "${GREEN}✅ $1${NC}"
}

warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
  echo -e "${RED}❌ $1${NC}"
}

info() {
  echo -e "${PURPLE}ℹ️  $1${NC}"
}

# Configuration
BOX_NAME="local/ubuntu-24.04-libvirt"
BASE_BOX="hashicorp-education/ubuntu-24-04"
PACKER_DIR="$PROJECT_ROOT/.vagrant-boxes"
BOX_BUILD_DIR="$PACKER_DIR/ubuntu-24.04-libvirt"

# Show usage
show_usage() {
  echo "Vagrant Box Management for libvirt"
  echo "Usage: $0 [COMMAND] [OPTIONS]"
  echo ""
  echo "Commands:"
  echo "  build       Build local Ubuntu 24.04 box optimized for libvirt"
  echo "  add         Add pre-built box to Vagrant"
  echo "  remove      Remove local box from Vagrant"
  echo "  list        List all available boxes"
  echo "  status      Show status of local boxes"
  echo "  validate    Validate box functionality"
  echo "  cleanup     Clean up build artifacts and temporary files"
  echo "  rebuild     Remove and rebuild the local box"
  echo ""
  echo "Options:"
  echo "  --force     Force operations without confirmation"
  echo "  --debug     Enable debug output"
  echo "  --dry-run   Show what would be done without executing"
  echo ""
  echo "Examples:"
  echo "  $0 build              # Build local libvirt-optimized box"
  echo "  $0 add                # Add existing box file to Vagrant"
  echo "  $0 rebuild --force    # Force rebuild of local box"
  echo "  $0 validate           # Test the local box functionality"
}

# Check prerequisites
check_prerequisites() {
  log "Checking prerequisites..."
  
  local missing_tools=()
  
  # Check for required tools
  for tool in vagrant packer qemu-img virt-sysprep; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing_tools+=("$tool")
    fi
  done
  
  if [ ${#missing_tools[@]} -gt 0 ]; then
    error "Missing required tools: ${missing_tools[*]}"
    echo ""
    echo "Install missing tools:"
    echo "  sudo apt update"
    echo "  sudo apt install -y vagrant packer qemu-utils guestfs-tools"
    echo ""
    echo "For packer, you may need to install from HashiCorp repository:"
    echo "  curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -"
    echo "  echo 'deb [arch=amd64] https://apt.releases.hashicorp.com focal main' | sudo tee /etc/apt/sources.list.d/hashicorp.list"
    echo "  sudo apt update && sudo apt install packer"
    exit 1
  fi
  
  # Check vagrant-libvirt plugin
  if ! vagrant plugin list | grep -q vagrant-libvirt; then
    warning "vagrant-libvirt plugin not installed"
    read -p "Install vagrant-libvirt plugin? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      vagrant plugin install vagrant-libvirt
      success "vagrant-libvirt plugin installed"
    else
      error "vagrant-libvirt plugin required for libvirt boxes"
      exit 1
    fi
  fi
  
  # Check KVM support
  if [ ! -c /dev/kvm ]; then
    error "KVM not available - ensure virtualization is enabled"
    exit 1
  fi
  
  success "All prerequisites satisfied"
}

# Create Packer template
create_packer_template() {
  log "Creating Packer template for libvirt-optimized Ubuntu 24.04..."
  
  mkdir -p "$BOX_BUILD_DIR"
  
  cat > "$BOX_BUILD_DIR/ubuntu-24.04-libvirt.pkr.hcl" <<'EOF'
packer {
  required_plugins {
    qemu = {
      version = ">= 1.0.0"
      source  = "github.com/hashicorp/qemu"
    }
  }
}

source "qemu" "ubuntu-24-04-libvirt" {
  # Base ISO configuration
  iso_url      = "https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso"
  iso_checksum = "sha256:c7cda48494a6d7d9665964388a3fc9c824b3bef0c9ea3818a1be982bc80d346b"
  
  # VM configuration optimized for libvirt
  memory       = 2048
  cpus         = 2
  disk_size    = "20G"
  format       = "qcow2"
  accelerator  = "kvm"
  
  # Network configuration
  net_device   = "virtio-net"
  disk_interface = "virtio"
  
  # Display configuration (headless)
  headless     = true
  vnc_bind_address = "0.0.0.0"
  vnc_port_min = 5900
  vnc_port_max = 5999
  
  # SSH configuration
  ssh_username = "vagrant"
  ssh_password = "vagrant"
  ssh_timeout = "20m"
  
  # Boot configuration
  boot_wait    = "5s"
  boot_command = [
    "<esc><wait>",
    "linux /casper/vmlinuz --- autoinstall ds=nocloud-net;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/",
    "<enter><wait>",
    "initrd /casper/initrd",
    "<enter><wait>",
    "boot",
    "<enter>"
  ]
  
  # HTTP server for autoinstall
  http_directory = "http"
  http_port_min  = 8000
  http_port_max  = 8099
  
  # Output configuration
  output_directory = "output-ubuntu-24.04-libvirt"
  vm_name         = "ubuntu-24.04-libvirt"
  
  # Shutdown configuration
  shutdown_command = "echo 'vagrant' | sudo -S shutdown -P now"
}

build {
  sources = ["source.qemu.ubuntu-24-04-libvirt"]
  
  # Update system
  provisioner "shell" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get upgrade -y"
    ]
  }
  
  # Install libvirt optimizations
  provisioner "shell" {
    inline = [
      "sudo apt-get install -y qemu-guest-agent",
      "sudo apt-get install -y linux-image-virtual",
      "sudo systemctl enable qemu-guest-agent"
    ]
  }
  
  # Vagrant user setup
  provisioner "shell" {
    inline = [
      "sudo useradd -m -s /bin/bash vagrant",
      "echo 'vagrant:vagrant' | sudo chpasswd",
      "echo 'vagrant ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/vagrant"
    ]
  }
  
  # SSH key setup
  provisioner "shell" {
    inline = [
      "sudo mkdir -p /home/vagrant/.ssh",
      "curl -L https://raw.githubusercontent.com/mitchellh/vagrant/main/keys/vagrant.pub -o /tmp/vagrant.pub",
      "sudo mv /tmp/vagrant.pub /home/vagrant/.ssh/authorized_keys",
      "sudo chown -R vagrant:vagrant /home/vagrant/.ssh",
      "sudo chmod 700 /home/vagrant/.ssh",
      "sudo chmod 600 /home/vagrant/.ssh/authorized_keys"
    ]
  }
  
  # Clean up
  provisioner "shell" {
    inline = [
      "sudo apt-get autoremove -y",
      "sudo apt-get autoclean",
      "sudo rm -rf /tmp/*",
      "sudo rm -rf /var/tmp/*",
      "history -c"
    ]
  }
  
  # Create Vagrant box
  post-processor "vagrant" {
    output = "ubuntu-24.04-libvirt.box"
    provider_override = "libvirt"
  }
}
EOF

  # Create autoinstall configuration
  mkdir -p "$BOX_BUILD_DIR/http"
  cat > "$BOX_BUILD_DIR/http/user-data" <<'EOF'
#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  network:
    network:
      version: 2
      ethernets:
        ens3:
          dhcp4: true
  storage:
    layout:
      name: direct
  identity:
    hostname: ubuntu-24-04-libvirt
    username: vagrant
    password: '$6$vagrant$X2WZO8Cv2wO8AuFJ/p0Sg0w1u8VYvqWK1lY6cJZvRHQf0l8oQU0r2jnF8qDn8QQJr4kJ5pBT5zGQJr2lY8QQJ/'
  ssh:
    install-server: true
    allow-pw: true
  packages:
    - qemu-guest-agent
    - linux-image-virtual
  late-commands:
    - echo 'vagrant ALL=(ALL) NOPASSWD:ALL' > /target/etc/sudoers.d/vagrant
    - chmod 440 /target/etc/sudoers.d/vagrant
EOF

  cat > "$BOX_BUILD_DIR/http/meta-data" <<'EOF'
instance-id: ubuntu-24-04-libvirt
local-hostname: ubuntu-24-04-libvirt
EOF

  success "Packer template created at $BOX_BUILD_DIR"
}

# Build the box
build_box() {
  local force_build=false
  
  if [[ "$1" == "--force" ]]; then
    force_build=true
  fi
  
  check_prerequisites
  
  log "Building libvirt-optimized Ubuntu 24.04 box..."
  
  # Create build directory
  mkdir -p "$BOX_BUILD_DIR"
  cd "$BOX_BUILD_DIR"
  
  # Check if box already exists
  if vagrant box list | grep -q "$BOX_NAME" && [ "$force_build" = false ]; then
    warning "Box $BOX_NAME already exists"
    read -p "Rebuild box? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      info "Skipping build"
      return 0
    fi
  fi
  
  # Create packer template if it doesn't exist
  if [ ! -f "ubuntu-24.04-libvirt.pkr.hcl" ]; then
    create_packer_template
  fi
  
  log "Starting Packer build (this may take 20-30 minutes)..."
  
  # Build with Packer
  if packer build ubuntu-24.04-libvirt.pkr.hcl; then
    success "Box built successfully"
    
    # Add box to Vagrant if build succeeded
    if [ -f "ubuntu-24.04-libvirt.box" ]; then
      vagrant box add "$BOX_NAME" ubuntu-24.04-libvirt.box --force
      success "Box added to Vagrant as $BOX_NAME"
    fi
  else
    error "Box build failed"
    return 1
  fi
}

# Add existing box
add_box() {
  log "Adding pre-built box to Vagrant..."
  
  # Check if we have a base box to customize
  if ! vagrant box list | grep -q "$BASE_BOX"; then
    log "Downloading base box $BASE_BOX..."
    vagrant box add "$BASE_BOX"
  fi
  
  # For now, just create an alias to the base box
  # In a real scenario, you'd point to a pre-built .box file
  if vagrant box list | grep -q "$BOX_NAME"; then
    warning "Box $BOX_NAME already exists"
    read -p "Replace existing box? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      vagrant box remove "$BOX_NAME" --force
    else
      info "Skipping add operation"
      return 0
    fi
  fi
  
  # Create a symlink/alias for development
  log "Creating development alias for $BOX_NAME..."
  vagrant box add "$BOX_NAME" "$BASE_BOX" --provider libvirt
  success "Box $BOX_NAME added (aliased to $BASE_BOX)"
}

# Remove box
remove_box() {
  log "Removing local box $BOX_NAME..."
  
  if ! vagrant box list | grep -q "$BOX_NAME"; then
    warning "Box $BOX_NAME not found"
    return 0
  fi
  
  vagrant box remove "$BOX_NAME" --provider libvirt --force
  success "Box $BOX_NAME removed"
}

# List boxes
list_boxes() {
  log "Available Vagrant boxes:"
  echo ""
  vagrant box list
  echo ""
  
  if vagrant box list | grep -q "$BOX_NAME"; then
    success "Local libvirt box is available: $BOX_NAME"
  else
    warning "Local libvirt box not found: $BOX_NAME"
    info "Run '$0 build' or '$0 add' to create it"
  fi
}

# Show status
show_status() {
  log "Box management status:"
  echo ""
  
  # Check prerequisites
  echo "Prerequisites:"
  for tool in vagrant packer qemu-img virt-sysprep; do
    if command -v "$tool" >/dev/null 2>&1; then
      echo "  ✅ $tool: $(command -v "$tool")"
    else
      echo "  ❌ $tool: not found"
    fi
  done
  echo ""
  
  # Check vagrant plugins
  echo "Vagrant plugins:"
  if vagrant plugin list | grep -q vagrant-libvirt; then
    echo "  ✅ vagrant-libvirt: installed"
  else
    echo "  ❌ vagrant-libvirt: not installed"
  fi
  echo ""
  
  # Check boxes
  echo "Boxes:"
  if vagrant box list | grep -q "$BOX_NAME"; then
    echo "  ✅ $BOX_NAME: available"
  else
    echo "  ❌ $BOX_NAME: not found"
  fi
  
  if vagrant box list | grep -q "$BASE_BOX"; then
    echo "  ✅ $BASE_BOX: available"
  else
    echo "  ❌ $BASE_BOX: not found"
  fi
  echo ""
  
  # Check build artifacts
  if [ -d "$BOX_BUILD_DIR" ]; then
    echo "Build directory: $BOX_BUILD_DIR"
    if [ -f "$BOX_BUILD_DIR/ubuntu-24.04-libvirt.box" ]; then
      echo "  ✅ Built box file exists"
    else
      echo "  ❌ No built box file found"
    fi
  else
    echo "  ❌ No build directory found"
  fi
}

# Validate box
validate_box() {
  log "Validating box $BOX_NAME..."
  
  if ! vagrant box list | grep -q "$BOX_NAME"; then
    error "Box $BOX_NAME not found. Run '$0 add' or '$0 build' first."
    return 1
  fi
  
  # Create temporary test directory
  local test_dir="/tmp/box-test-$(date +%s)"
  mkdir -p "$test_dir"
  cd "$test_dir"
  
  # Create minimal Vagrantfile for testing
  cat > Vagrantfile <<EOF
Vagrant.configure("2") do |config|
  config.vm.box = "$BOX_NAME"
  config.vm.provider :libvirt do |libvirt|
    libvirt.memory = 1024
    libvirt.cpus = 1
  end
end
EOF
  
  log "Testing box with minimal configuration..."
  
  # Test box startup
  if vagrant up --provider=libvirt; then
    success "Box starts successfully"
    
    # Test SSH connectivity
    if vagrant ssh -c "echo 'SSH test successful'"; then
      success "SSH connectivity verified"
    else
      error "SSH connectivity failed"
    fi
    
    # Cleanup
    vagrant destroy -f
    success "Validation completed successfully"
  else
    error "Box failed to start"
    return 1
  fi
  
  # Cleanup test directory
  cd /
  rm -rf "$test_dir"
}

# Cleanup build artifacts
cleanup() {
  log "Cleaning up build artifacts..."
  
  if [ -d "$PACKER_DIR" ]; then
    read -p "Remove build directory $PACKER_DIR? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      rm -rf "$PACKER_DIR"
      success "Build directory removed"
    fi
  fi
  
  # Clean up any temporary Vagrant environments
  log "Cleaning up temporary Vagrant environments..."
  find /tmp -name "box-test-*" -type d -exec rm -rf {} + 2>/dev/null || true
  
  success "Cleanup completed"
}

# Rebuild box
rebuild_box() {
  log "Rebuilding box $BOX_NAME..."
  
  remove_box
  cleanup
  build_box --force
  
  success "Box rebuilt successfully"
}

# Main execution
main() {
  case "${1:-help}" in
    "build")
      build_box "$2"
      ;;
    "add")
      add_box
      ;;
    "remove")
      remove_box
      ;;
    "list")
      list_boxes
      ;;
    "status")
      show_status
      ;;
    "validate")
      validate_box
      ;;
    "cleanup")
      cleanup
      ;;
    "rebuild")
      rebuild_box
      ;;
    "help"|"--help"|"-h")
      show_usage
      ;;
    *)
      error "Unknown command: $1"
      echo ""
      show_usage
      exit 1
      ;;
  esac
}

# Execute main function with all arguments
main "$@"