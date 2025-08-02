#!/bin/bash
# Script to clean up stale Vagrant state and ensure libvirt provider

set -e

echo "🧹 Cleaning up Vagrant state for libvirt migration..."

# Function to print colored output
print_status() {
  echo -e "\033[1;34m➜\033[0m $1"
}

print_success() {
  echo -e "\033[1;32m✓\033[0m $1"
}

print_error() {
  echo -e "\033[1;31m✗\033[0m $1"
}

# Clean up stale Vagrant state
if [ -d ".vagrant" ]; then
  print_status "Removing stale .vagrant directory..."
  rm -rf .vagrant/
  print_success "Vagrant state cleaned"
else
  print_status "No .vagrant directory found (already clean)"
fi

# Clean up any running VMs
print_status "Checking for running VMs..."
if vagrant global-status --prune | grep -q "running"; then
  print_status "Found running VMs, destroying..."
  vagrant destroy -f 2>/dev/null || true
  print_success "VMs destroyed"
else
  print_success "No running VMs found"
fi

# Check if vagrant-libvirt plugin is installed
print_status "Checking vagrant-libvirt plugin..."
if ! vagrant plugin list | grep -q vagrant-libvirt; then
  print_error "vagrant-libvirt plugin not installed!"
  echo "Please install with: vagrant plugin install vagrant-libvirt"
  exit 1
else
  print_success "vagrant-libvirt plugin installed"
fi

# Check if libvirt is running
print_status "Checking libvirt service..."
if ! systemctl is-active --quiet libvirtd; then
  print_error "libvirtd service is not running!"
  echo "Please start with: sudo systemctl start libvirtd"
  exit 1
else
  print_success "libvirtd service is running"
fi

# Check KVM support
print_status "Checking KVM support..."
if ! [ -e /dev/kvm ]; then
  print_error "KVM not available on this system"
  echo "Vagrant will use QEMU emulation (slower performance)"
else
  print_success "KVM hardware acceleration available"
fi

# List current boxes
print_status "Current Vagrant boxes:"
vagrant box list || echo "No boxes installed"

# Check if our custom box exists
if ! vagrant box list | grep -q "local/ubuntu-24.04-libvirt.*libvirt"; then
  print_error "Custom libvirt box not found!"
  echo ""
  echo "To add the box, run:"
  echo "  cd packer/"
  echo "  ./build-box.sh"
  echo "  vagrant box add local/ubuntu-24.04-libvirt output/ubuntu-24.04-dev-libvirt.box"
else
  print_success "Custom libvirt box found"
fi

echo ""
print_success "Vagrant state cleaned and ready for libvirt!"
echo ""
echo "Next steps:"
echo "1. Ensure your custom box is added (see above if missing)"
echo "2. Run: vagrant up --provider=libvirt"
echo "3. Or simply: vagrant up (libvirt is now the default)"
