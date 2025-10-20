#!/bin/bash
#
# Setup libvirt networks for integration testing
#
# This script creates the required networks for dev-box integration tests:
#   - agent-nat-filtered: NAT with filtering (default for CLI agents)
#   - agent-isolated: Completely isolated (high-security testing)
#   - agent-network-filter: Network filter for security
#
# Usage: sudo ./setup_networks.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Dev-Box Network Setup for Integration Testing"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Usage: sudo $0"
    exit 1
fi

# Check if virsh is available
if ! command -v virsh &> /dev/null; then
    echo -e "${RED}Error: virsh command not found${NC}"
    echo "Please install libvirt: sudo apt install libvirt-daemon-system"
    exit 1
fi

# Function to create NAT-filtered network
setup_nat_filtered_network() {
    echo -e "${YELLOW}Setting up agent-nat-filtered network...${NC}"

    cat > /tmp/agent-nat-filtered.xml << 'EOF'
<network>
  <name>agent-nat-filtered</name>
  <forward mode='nat'>
    <nat><port start='1024' end='65535'/></nat>
  </forward>
  <ip address='192.168.101.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.101.10' end='192.168.101.254'/>
    </dhcp>
  </ip>
</network>
EOF

    # Check if network already exists
    if virsh net-info agent-nat-filtered &> /dev/null; then
        echo -e "${YELLOW}Network agent-nat-filtered already exists. Destroying...${NC}"
        virsh net-destroy agent-nat-filtered 2>/dev/null || true
        virsh net-undefine agent-nat-filtered
    fi

    # Define and start network
    virsh net-define /tmp/agent-nat-filtered.xml
    virsh net-start agent-nat-filtered
    virsh net-autostart agent-nat-filtered

    echo -e "${GREEN}✓ agent-nat-filtered network configured${NC}"
    rm /tmp/agent-nat-filtered.xml
}

# Function to create isolated network
setup_isolated_network() {
    echo -e "${YELLOW}Setting up agent-isolated network...${NC}"

    cat > /tmp/agent-isolated.xml << 'EOF'
<network>
  <name>agent-isolated</name>
  <bridge name='virbr-isolated'/>
  <forward mode='none'/>
  <ip address='192.168.100.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.100.10' end='192.168.100.254'/>
    </dhcp>
  </ip>
</network>
EOF

    # Check if network already exists
    if virsh net-info agent-isolated &> /dev/null; then
        echo -e "${YELLOW}Network agent-isolated already exists. Destroying...${NC}"
        virsh net-destroy agent-isolated 2>/dev/null || true
        virsh net-undefine agent-isolated
    fi

    # Define and start network
    virsh net-define /tmp/agent-isolated.xml
    virsh net-start agent-isolated
    virsh net-autostart agent-isolated

    echo -e "${GREEN}✓ agent-isolated network configured${NC}"
    rm /tmp/agent-isolated.xml
}

# Function to create network filter
setup_network_filter() {
    echo -e "${YELLOW}Setting up agent-network-filter...${NC}"

    cat > /tmp/agent-network-filter.xml << 'EOF'
<filter name='agent-network-filter' chain='root'>
  <!-- Allow DNS (required for all internet access) -->
  <rule action='accept' direction='out'>
    <udp dstportstart='53' dstportend='53'/>
  </rule>

  <!-- Allow HTTP/HTTPS (for API calls, package managers) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='80' dstportend='80'/>
  </rule>
  <rule action='accept' direction='out'>
    <tcp dstportstart='443' dstportend='443'/>
  </rule>

  <!-- Allow SSH (for git operations) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='22' dstportend='22'/>
  </rule>

  <!-- Allow git protocol (port 9418) -->
  <rule action='accept' direction='out'>
    <tcp dstportstart='9418' dstportend='9418'/>
  </rule>

  <!-- Allow established connections (responses to outgoing requests) -->
  <rule action='accept' direction='in'>
    <all state='ESTABLISHED,RELATED'/>
  </rule>

  <!-- Block all unsolicited incoming connections -->
  <rule action='drop' direction='in' priority='1000'>
    <all state='NEW'/>
  </rule>

  <!-- Log and drop other outgoing connections (for monitoring) -->
  <rule action='drop' direction='out' priority='1000'>
    <all/>
  </rule>
</filter>
EOF

    # Check if filter already exists
    if virsh nwfilter-dumpxml agent-network-filter &> /dev/null; then
        echo -e "${YELLOW}Filter agent-network-filter already exists. Undefining...${NC}"
        virsh nwfilter-undefine agent-network-filter
    fi

    # Define filter
    virsh nwfilter-define /tmp/agent-network-filter.xml

    echo -e "${GREEN}✓ agent-network-filter configured${NC}"
    rm /tmp/agent-network-filter.xml
}

# Main execution
echo "Step 1/3: Creating NAT-filtered network..."
setup_nat_filtered_network
echo ""

echo "Step 2/3: Creating isolated network..."
setup_isolated_network
echo ""

echo "Step 3/3: Creating network filter..."
setup_network_filter
echo ""

# Verify setup
echo "========================================="
echo "Verification"
echo "========================================="
echo ""

echo "Networks:"
virsh net-list --all | grep -E "(agent-nat-filtered|agent-isolated|Name)"
echo ""

echo "Filters:"
virsh nwfilter-list | grep -E "(agent-network-filter|UUID)"
echo ""

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Network setup completed successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Run integration tests: pytest tests/integration/ -v"
echo "  2. See tests/integration/README.md for more information"
echo ""
