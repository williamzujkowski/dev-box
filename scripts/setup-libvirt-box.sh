#!/bin/bash
# Script to build and add the libvirt box locally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PACKER_DIR="$PROJECT_ROOT/packer"
BOX_NAME="local/ubuntu-24.04-libvirt"

echo "🏗️  Setting up libvirt box for dev-box..."

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

# Check if box already exists
if vagrant box list | grep -q "$BOX_NAME.*libvirt"; then
  print_status "Box $BOX_NAME already exists"
  echo "To rebuild, first run: vagrant box remove $BOX_NAME"
  exit 0
fi

# Check if Packer is installed
if ! command -v packer &>/dev/null; then
  print_error "Packer not installed!"
  echo "Installing Packer..."
  curl -fsSL https://releases.hashicorp.com/packer/1.10.0/packer_1.10.0_linux_amd64.zip -o /tmp/packer.zip
  sudo unzip -o /tmp/packer.zip -d /usr/local/bin/
  sudo chmod +x /usr/local/bin/packer
  rm /tmp/packer.zip
  print_success "Packer installed"
fi

# Check if we have a pre-built box
if [ -f "$PACKER_DIR/output/ubuntu-24.04-dev-libvirt.box" ]; then
  print_status "Found pre-built box, adding to Vagrant..."
  vagrant box add "$BOX_NAME" "$PACKER_DIR/output/ubuntu-24.04-dev-libvirt.box"
  print_success "Box added successfully!"
else
  print_status "No pre-built box found. Building with Packer..."

  # Check dependencies
  if ! command -v qemu-system-x86_64 &>/dev/null; then
    print_error "QEMU not installed!"
    echo "Please install with: sudo apt-get install qemu-kvm"
    exit 1
  fi

  # Build the box
  cd "$PACKER_DIR"
  if [ -f "build-box.sh" ]; then
    print_status "Using build-box.sh script..."
    ./build-box.sh
  else
    print_status "Running Packer build directly..."
    packer init ubuntu-24.04-libvirt.pkr.hcl
    packer build -var-file=variables.pkrvars.hcl ubuntu-24.04-libvirt.pkr.hcl
  fi

  # Add the box
  if [ -f "output/ubuntu-24.04-dev-libvirt.box" ]; then
    vagrant box add "$BOX_NAME" "output/ubuntu-24.04-dev-libvirt.box"
    print_success "Box built and added successfully!"
  else
    print_error "Box build failed!"
    exit 1
  fi
fi

# Verify the box was added
if vagrant box list | grep -q "$BOX_NAME.*libvirt"; then
  print_success "Box $BOX_NAME is ready to use!"
  echo ""
  echo "Next steps:"
  echo "1. cd $PROJECT_ROOT"
  echo "2. vagrant up --provider=libvirt"
  echo "   (or just 'vagrant up' since libvirt is now the default)"
else
  print_error "Failed to add box!"
  exit 1
fi
