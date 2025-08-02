#!/bin/bash

# Script to install dependencies for vagrant-libvirt plugin
# Run with: bash install-libvirt-dependencies.sh

set -e

echo "=== Installing Dependencies for vagrant-libvirt ==="
echo ""
echo "This script will help you install the required system dependencies."
echo "You'll need to run the following command with sudo:"
echo ""
echo 'sudo apt-get update && sudo apt-get install -y \'
echo '  libvirt-dev \'
echo '  ruby-dev \'
echo '  libxml2-dev \'
echo '  libxslt-dev \'
echo '  libssl-dev \'
echo '  pkg-config \'
echo '  build-essential \'
echo '  qemu-kvm \'
echo '  libvirt-daemon-system \'
echo '  libvirt-clients \'
echo '  virtinst \'
echo "  bridge-utils"
echo ""
echo "After installing these dependencies, run:"
echo "  vagrant plugin install vagrant-libvirt"
echo ""
echo "Would you like to see the command again? Press Enter to continue..."
read -r

echo ""
echo "Copy and run this command:"
echo ""
echo 'sudo apt-get update && sudo apt-get install -y libvirt-dev ruby-dev libxml2-dev libxslt-dev libssl-dev pkg-config build-essential qemu-kvm libvirt-daemon-system libvirt-clients virtinst bridge-utils'
echo ""
echo "Then run:"
echo "  vagrant plugin install vagrant-libvirt"
