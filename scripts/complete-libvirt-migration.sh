#!/bin/bash
# Complete libvirt migration helper script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Libvirt Migration Helper ===${NC}"
echo ""

# Step 1: Check current status
echo -e "${YELLOW}Step 1: Checking current status...${NC}"

# Check if .vagrant exists
if [ -d ".vagrant" ]; then
  echo -e "${RED}⚠️  Found .vagrant directory - this needs to be cleaned${NC}"
  echo "   The .vagrant directory contains stale VirtualBox state"
  NEEDS_CLEANUP=true
else
  echo -e "${GREEN}✅ No .vagrant directory found - clean state${NC}"
  NEEDS_CLEANUP=false
fi

# Check if vagrant-libvirt is installed
if vagrant plugin list | grep -q vagrant-libvirt; then
  echo -e "${GREEN}✅ vagrant-libvirt plugin is installed${NC}"
  PLUGIN_INSTALLED=true
else
  echo -e "${RED}⚠️  vagrant-libvirt plugin is NOT installed${NC}"
  PLUGIN_INSTALLED=false
fi

# Check if libvirt-dev is installed
if dpkg -l | grep -q libvirt-dev; then
  echo -e "${GREEN}✅ libvirt-dev is installed${NC}"
  DEPS_INSTALLED=true
else
  echo -e "${RED}⚠️  libvirt-dev is NOT installed${NC}"
  DEPS_INSTALLED=false
fi

# Check if the box exists locally
if vagrant box list | grep -q "local/ubuntu-24.04-libvirt"; then
  echo -e "${GREEN}✅ Libvirt box is already added${NC}"
  BOX_EXISTS=true
else
  echo -e "${YELLOW}⚠️  Libvirt box not found locally${NC}"
  BOX_EXISTS=false
fi

echo ""
echo -e "${BLUE}=== Required Actions ===${NC}"
echo ""

# Step 2: Clean .vagrant if needed
if [ "$NEEDS_CLEANUP" = true ]; then
  echo -e "${YELLOW}1. Clean stale .vagrant directory:${NC}"
  echo "   rm -rf .vagrant/"
  echo ""
fi

# Step 3: Install dependencies if needed
if [ "$DEPS_INSTALLED" = false ]; then
  echo -e "${YELLOW}2. Install system dependencies:${NC}"
  echo "   sudo apt-get update"
  echo "   sudo apt-get install -y libvirt-dev ruby-dev libxml2-dev libxslt-dev libssl-dev pkg-config build-essential qemu-kvm libvirt-daemon-system libvirt-clients virtinst bridge-utils"
  echo ""
fi

# Step 4: Install plugin if needed
if [ "$PLUGIN_INSTALLED" = false ]; then
  echo -e "${YELLOW}3. Install vagrant-libvirt plugin:${NC}"
  echo "   vagrant plugin install vagrant-libvirt"
  echo ""
fi

# Step 5: Build or download box if needed
if [ "$BOX_EXISTS" = false ]; then
  echo -e "${YELLOW}4. Build or add the libvirt box:${NC}"
  echo ""
  echo "   Option A: Build locally with Packer (requires time and resources):"
  echo "     cd packer"
  echo "     ./build-box.sh"
  echo "     vagrant box add local/ubuntu-24.04-libvirt output/ubuntu-24.04-dev-libvirt.box"
  echo ""
  echo "   Option B: Wait for GitHub Actions to build (check latest release):"
  echo "     https://github.com/williamzujkowski/dev-box/releases"
  echo "     vagrant box add local/ubuntu-24.04-libvirt <URL-to-box-file>"
  echo ""
fi

# Step 6: Start the VM
echo -e "${YELLOW}5. Start the VM with libvirt:${NC}"
echo "   vagrant up --provider=libvirt"
echo "   # Or simply: vagrant up (libvirt is now the default)"
echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
if [ "$NEEDS_CLEANUP" = true ] || [ "$DEPS_INSTALLED" = false ] || [ "$PLUGIN_INSTALLED" = false ] || [ "$BOX_EXISTS" = false ]; then
  echo -e "${YELLOW}⚠️  Some actions are required before you can use vagrant up${NC}"
  echo ""
  echo "Copy and run the commands above in order, then try:"
  echo "  vagrant up --provider=libvirt"
else
  echo -e "${GREEN}✅ Everything is ready! You can now run:${NC}"
  echo "  vagrant up --provider=libvirt"
fi

echo ""
echo -e "${BLUE}Need help? Check the documentation:${NC}"
echo "  - README.md for provider migration notes"
echo "  - packer/README.md for box building instructions"
echo "  - .github/workflows/vagrant-box-build.yml for CI/CD box builds"
