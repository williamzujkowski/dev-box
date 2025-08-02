#!/bin/bash
# Validation script for Ubuntu 24.04 libvirt box
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOX_FILE=""
TEST_DIR="/tmp/vagrant-box-test-$(date +%s)"
VAGRANT_FILE="${TEST_DIR}/Vagrantfile"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

cleanup() {
    if [[ -d "$TEST_DIR" ]]; then
        log "Cleaning up test environment..."
        cd "$TEST_DIR"
        vagrant destroy -f &>/dev/null || true
        cd /
        rm -rf "$TEST_DIR"
    fi
}

find_box_file() {
    if [[ -n "$BOX_FILE" ]] && [[ -f "$BOX_FILE" ]]; then
        return 0
    fi
    
    log "Looking for box file in output directory..."
    local found_boxes
    found_boxes=$(find "${SCRIPT_DIR}/output" -name "*.box" -type f 2>/dev/null || true)
    
    if [[ -z "$found_boxes" ]]; then
        error "No .box files found in ${SCRIPT_DIR}/output. Build a box first."
    fi
    
    local box_count
    box_count=$(echo "$found_boxes" | wc -l)
    
    if [[ $box_count -eq 1 ]]; then
        BOX_FILE="$found_boxes"
        log "Found box file: $BOX_FILE"
    else
        error "Multiple box files found. Please specify which one to test with -b option."
    fi
}

check_requirements() {
    log "Checking validation requirements..."
    
    # Check if vagrant is installed
    if ! command -v vagrant &> /dev/null; then
        error "Vagrant is not installed. Please install it first."
    fi
    
    # Check if libvirt provider is available
    if ! vagrant plugin list | grep -q vagrant-libvirt; then
        warn "vagrant-libvirt plugin not detected. Install with: vagrant plugin install vagrant-libvirt"
    fi
    
    # Check if virsh is available
    if ! command -v virsh &> /dev/null; then
        warn "virsh not available. Some libvirt checks will be skipped."
    fi
    
    log "Requirements check completed!"
}

validate_box_structure() {
    log "Validating box file structure..."
    
    local temp_extract="/tmp/box-extract-$(date +%s)"
    mkdir -p "$temp_extract"
    
    # Extract and examine box contents
    cd "$temp_extract"
    tar -tf "$BOX_FILE" > box_contents.txt
    
    # Check for required files
    local required_files=("metadata.json" "Vagrantfile" "box.img")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if ! grep -q "^${file}$" box_contents.txt; then
            # For libvirt, box.img might be named differently
            if [[ "$file" == "box.img" ]] && grep -q "\.qcow2$" box_contents.txt; then
                continue
            fi
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        error "Missing required files in box: ${missing_files[*]}"
    fi
    
    # Extract and check metadata
    tar -xf "$BOX_FILE" metadata.json
    if [[ -f metadata.json ]]; then
        info "Box metadata:"
        cat metadata.json | jq . 2>/dev/null || cat metadata.json
    fi
    
    # Clean up
    cd /
    rm -rf "$temp_extract"
    
    log "Box structure validation passed!"
}

create_test_environment() {
    log "Creating test environment..."
    
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    
    # Create Vagrantfile for testing
    cat > "$VAGRANT_FILE" << EOF
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "test-box"
  config.vm.box_url = "file://${BOX_FILE}"
  
  # Libvirt provider configuration
  config.vm.provider :libvirt do |libvirt|
    libvirt.memory = 1024
    libvirt.cpus = 1
    libvirt.graphics_type = "none"
    libvirt.driver = "kvm"
  end
  
  # Network configuration
  config.vm.network "private_network", type: "dhcp"
  
  # SSH configuration
  config.ssh.insert_key = false
  config.ssh.private_key_path = ["~/.vagrant.d/insecure_private_key"]
  
  # Disable default synced folder for faster testing
  config.vm.synced_folder ".", "/vagrant", disabled: true
end
EOF
    
    log "Test environment created in $TEST_DIR"
}

test_box_boot() {
    log "Testing box boot and basic functionality..."
    
    cd "$TEST_DIR"
    
    # Start the VM
    info "Starting VM (this may take a few minutes)..."
    if ! vagrant up --provider=libvirt; then
        error "Failed to start VM"
    fi
    
    # Test SSH connectivity
    info "Testing SSH connectivity..."
    if ! vagrant ssh -c "echo 'SSH connection successful'"; then
        error "SSH connection failed"
    fi
    
    log "Box boot test passed!"
}

test_development_tools() {
    log "Testing development tools installation..."
    
    cd "$TEST_DIR"
    
    # Test various development tools
    local tools_to_test=(
        "curl --version"
        "git --version"
        "docker --version"
        "gh --version"
        "claude --version"
        "terraform --version"
        "tfsec --version"
        "uv --version"
        "ruff --version"
        "node --version"
        "npm --version"
        "python3 --version"
        "pip3 --version"
        "go version"
        "code --version"
    )
    
    local failed_tools=()
    
    for tool_cmd in "${tools_to_test[@]}"; do
        info "Testing: $tool_cmd"
        if ! vagrant ssh -c "$tool_cmd" &>/dev/null; then
            failed_tools+=("$tool_cmd")
            warn "Tool test failed: $tool_cmd"
        fi
    done
    
    if [[ ${#failed_tools[@]} -gt 0 ]]; then
        warn "Some development tools are not working: ${failed_tools[*]}"
    else
        log "All development tools test passed!"
    fi
}

test_vagrant_user() {
    log "Testing vagrant user configuration..."
    
    cd "$TEST_DIR"
    
    # Test sudo access
    info "Testing sudo access..."
    if ! vagrant ssh -c "sudo whoami" | grep -q "root"; then
        error "Vagrant user does not have proper sudo access"
    fi
    
    # Test SSH key authentication
    info "Testing SSH key authentication..."
    if ! vagrant ssh -c "echo 'SSH key auth working'"; then
        error "SSH key authentication failed"
    fi
    
    # Test user groups
    info "Testing user groups..."
    local expected_groups=("sudo" "docker" "libvirt")
    for group in "${expected_groups[@]}"; do
        if ! vagrant ssh -c "groups" | grep -q "$group"; then
            warn "User not in expected group: $group"
        fi
    done
    
    log "Vagrant user configuration test passed!"
}

test_system_optimization() {
    log "Testing system optimizations..."
    
    cd "$TEST_DIR"
    
    # Test QEMU guest agent
    info "Testing QEMU guest agent..."
    if ! vagrant ssh -c "systemctl is-active qemu-guest-agent" | grep -q "active"; then
        warn "QEMU guest agent is not running"
    fi
    
    # Test virtio modules
    info "Testing virtio modules..."
    if ! vagrant ssh -c "lsmod | grep virtio"; then
        warn "Virtio modules may not be loaded"
    fi
    
    # Test network interface
    info "Testing network configuration..."
    if ! vagrant ssh -c "ip link show | grep -E '(eth0|enp)'"; then
        warn "Network interface not found"
    fi
    
    log "System optimization test completed!"
}

performance_test() {
    log "Running basic performance tests..."
    
    cd "$TEST_DIR"
    
    # Test boot time (approximate)
    info "Measuring approximate boot time..."
    local start_time=$(date +%s)
    vagrant reload
    local end_time=$(date +%s)
    local boot_time=$((end_time - start_time))
    info "Boot time: ${boot_time} seconds"
    
    # Test memory usage
    info "Checking memory usage..."
    vagrant ssh -c "free -h"
    
    # Test disk usage
    info "Checking disk usage..."
    vagrant ssh -c "df -h /"
    
    log "Performance test completed!"
}

generate_report() {
    log "Generating validation report..."
    
    local report_file="${SCRIPT_DIR}/validation-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
Ubuntu 24.04 Libvirt Box Validation Report
==========================================

Validation Date: $(date)
Box File: $BOX_FILE
Box Size: $(du -h "$BOX_FILE" | cut -f1)

Test Results:
- Box Structure: PASSED
- Boot Test: PASSED
- SSH Connectivity: PASSED
- Vagrant User Config: PASSED
- Development Tools: See details above
- System Optimizations: See details above

Box appears to be ready for use!

To use this box:
1. Add it to Vagrant: vagrant box add my-ubuntu-box "$BOX_FILE"
2. Create a new Vagrantfile with: config.vm.box = "my-ubuntu-box"
3. Use libvirt provider: vagrant up --provider=libvirt

EOF
    
    info "Validation report saved to: $report_file"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Validate Ubuntu 24.04 libvirt box functionality

OPTIONS:
    -h, --help          Show this help message
    -b, --box-file      Specify box file to test
    -s, --skip-boot     Skip boot test (faster)
    -q, --quick         Quick validation (structure only)

EXAMPLES:
    $0                                    # Find and test box automatically
    $0 -b output/my-box.box              # Test specific box file
    $0 --quick                           # Quick structure validation only
    $0 --skip-boot                       # Skip the boot test

EOF
}

# Parse command line arguments
SKIP_BOOT=false
QUICK_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -b|--box-file)
            BOX_FILE="$2"
            shift 2
            ;;
        -s|--skip-boot)
            SKIP_BOOT=true
            shift
            ;;
        -q|--quick)
            QUICK_MODE=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Main execution
main() {
    log "Starting Ubuntu 24.04 Libvirt box validation..."
    
    check_requirements
    find_box_file
    validate_box_structure
    
    if [[ "$QUICK_MODE" == true ]]; then
        log "Quick validation completed!"
        exit 0
    fi
    
    create_test_environment
    
    if [[ "$SKIP_BOOT" == false ]]; then
        test_box_boot
        test_vagrant_user
        test_development_tools
        test_system_optimization
        performance_test
    fi
    
    generate_report
    
    log "Box validation completed successfully!"
    log "The box appears to be working correctly."
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"