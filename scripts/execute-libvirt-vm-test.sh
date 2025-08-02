#!/bin/bash
# Execute Libvirt VM Test - KVM/QEMU Alternative to VirtualBox
# Handles Ubuntu 24.04 + KVM conflicts by using libvirt provider directly

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/libvirt_vm_test_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} libvirt-fresh-test: $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

# STEP 0: Host & Hypervisor Requirements
log "🚀 Starting libvirt Ubuntu 24.04 VM test"
log "📁 Project root: $PROJECT_ROOT"
log "📄 Log file: $LOG_FILE"

cd "$PROJECT_ROOT"

# Check KVM availability
log "🔍 Checking KVM and hardware virtualization support..."

if [ ! -c /dev/kvm ]; then
    error "/dev/kvm not available - KVM not properly installed"
    log "Installing KVM prerequisites..."
    
    if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
        sudo apt update
        sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients \
          ruby-dev libvirt-dev build-essential dnsmasq-base ebtables \
          libxslt-dev libxml2-dev zlib1g-dev nfs-kernel-server
        sudo systemctl enable --now libvirtd
        sudo usermod -aG libvirt $USER
        success "KVM prerequisites installed"
    else
        error "Cannot install KVM prerequisites - sudo required"
        exit 1
    fi
else
    success "KVM device available: /dev/kvm"
fi

# Check CPU virtualization support
if grep -q vmx /proc/cpuinfo; then
    success "Intel VT-x detected"
elif grep -q svm /proc/cpuinfo; then
    success "AMD-V detected"
else
    error "Hardware virtualization not supported"
    exit 1
fi

# Check libvirt service
if systemctl is-active --quiet libvirtd; then
    success "libvirtd service is running"
else
    warning "libvirtd not running - attempting to start"
    sudo systemctl start libvirtd
    if systemctl is-active --quiet libvirtd; then
        success "libvirtd started successfully"
    else
        error "Failed to start libvirtd service"
        exit 1
    fi
fi

# Check vagrant-libvirt plugin
log "🔌 Checking vagrant-libvirt plugin..."
if vagrant plugin list | grep -q vagrant-libvirt; then
    success "vagrant-libvirt plugin installed"
else
    warning "vagrant-libvirt plugin not found - installing"
    if vagrant plugin install vagrant-libvirt; then
        success "vagrant-libvirt plugin installed"
    else
        error "Failed to install vagrant-libvirt plugin"
        log "Make sure ruby-dev and libvirt-dev are installed"
        exit 1
    fi
fi

# STEP 1: Initialize Vagrant Configuration
log "📋 Checking git workspace status..."

# Ensure clean git state
if ! git status --porcelain | grep -q .; then
    success "Git workspace is clean"
else
    warning "Git workspace has changes - staging and committing"
    git add -A
    git commit -m "chore: clean working directory before libvirt test"
fi

# Create libvirt test directory
LIBVIRT_DIR="$PROJECT_ROOT/libvirt-fresh-vm"
log "🏗️  Creating libvirt VM test directory: $LIBVIRT_DIR"

if [ -d "$LIBVIRT_DIR" ]; then
    warning "Directory exists - cleaning up previous test"
    cd "$LIBVIRT_DIR"
    vagrant destroy -f 2>/dev/null || true
    cd "$PROJECT_ROOT"
    rm -rf "$LIBVIRT_DIR"
fi

mkdir -p "$LIBVIRT_DIR"
cd "$LIBVIRT_DIR"

# Initialize git repo
git init
log "📝 Initializing Vagrant configuration for libvirt provider"

# Create enhanced Vagrantfile
cat > Vagrantfile << 'EOF'
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Ubuntu 24.04 LTS via hashicorp-education (libvirt compatible)
  config.vm.box = "hashicorp-education/ubuntu-24-04"
  config.vm.box_version = "0.1.0"
  
  # VM hostname
  config.vm.hostname = "ubuntu-24-04-libvirt"
  
  # Libvirt provider configuration
  config.vm.provider :libvirt do |libvirt|
    libvirt.driver = "kvm"
    libvirt.memory = 2048
    libvirt.cpus = 2
    libvirt.machine_type = "pc-i440fx-2.11"
    libvirt.cpu_mode = "host-passthrough"
    libvirt.nested = true
    libvirt.volume_cache = "writeback"
  end
  
  # Network configuration
  config.vm.network "private_network", ip: "192.168.121.10"
  
  # Self-healing provisioning
  config.vm.provision "shell", inline: <<-SHELL
    export DEBIAN_FRONTEND=noninteractive
    
    echo "🔧 Starting Ubuntu 24.04 provisioning with libvirt..."
    
    # System updates
    apt-get update -y
    apt-get upgrade -y
    
    # Essential development tools
    apt-get install -y \
      curl \
      wget \
      git \
      vim \
      htop \
      build-essential \
      python3 \
      python3-pip \
      nodejs \
      npm
    
    # Create workspace
    mkdir -p /home/vagrant/workspace
    chown vagrant:vagrant /home/vagrant/workspace
    
    echo "✅ Ubuntu 24.04 VM with libvirt provider ready!"
    echo "📊 System: $(lsb_release -d | cut -f2)"
    echo "🔧 Hypervisor: $(systemd-detect-virt)"
    echo "💾 Memory: $(free -h | grep Mem | awk '{print $2}')"
    echo "🖥️  CPUs: $(nproc)"
  SHELL
end
EOF

git add Vagrantfile
git commit -m "feat: initialize Ubuntu 24.04 Vagrantfile using libvirt provider"
success "Vagrant configuration initialized with libvirt provider"

# STEP 2: Bring Up VM & Policy-Based Self-Healing
log "🚀 Launching VM with libvirt provider..."

if vagrant up --provider=libvirt 2>&1 | tee -a "$LOG_FILE"; then
    success "VM launched successfully with libvirt"
else
    warning "VM launch failed - attempting self-healing"
    
    # Self-healing: Install additional prerequisites
    log "🔧 Installing additional libvirt prerequisites..."
    sudo apt update && sudo apt install -y dnsmasq-base ebtables ruby-libvirt
    
    # Retry VM launch
    if vagrant up --provider=libvirt 2>&1 | tee -a "$LOG_FILE"; then
        success "VM launched after self-healing"
        git add .
        git commit -m "fix: install libvirt plugin prerequisites (ruby-libvirt, dnsmasq, ebtables)"
    else
        error "VM launch failed even after self-healing"
        exit 1
    fi
fi

# STEP 3: SSH Smoke Tests inside Guest
log "🧪 Running comprehensive smoke tests..."

test_count=0
passed_tests=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    test_count=$((test_count + 1))
    
    log "Test $test_count: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        success "PASS: $test_name"
        passed_tests=$((passed_tests + 1))
        return 0
    else
        error "FAIL: $test_name"
        return 1
    fi
}

# Core system tests
run_test "VM Boot and SSH" "vagrant ssh -c 'echo test' 2>/dev/null"
run_test "Ubuntu 24.04 Version" "vagrant ssh -c 'lsb_release -r' 2>/dev/null | grep -q '24.04'"
run_test "KVM Hypervisor Detection" "vagrant ssh -c 'systemd-detect-virt' 2>/dev/null | grep -q 'kvm'"
run_test "CPU Allocation" "vagrant ssh -c 'nproc' 2>/dev/null | grep -q '2'"
run_test "Memory Allocation" "vagrant ssh -c 'free -g | grep Mem | awk \"{print \\$2}\"' 2>/dev/null | grep -E '^[2-9]|^[1-9][0-9]+'"

# Network tests
run_test "Internet Connectivity" "vagrant ssh -c 'ping -c 1 8.8.8.8' 2>/dev/null"
run_test "DNS Resolution" "vagrant ssh -c 'nslookup google.com' 2>/dev/null"

# Development tools tests
run_test "Python3 Installation" "vagrant ssh -c 'python3 --version' 2>/dev/null"
run_test "Node.js Installation" "vagrant ssh -c 'node --version' 2>/dev/null"
run_test "NPM Installation" "vagrant ssh -c 'npm --version' 2>/dev/null"
run_test "Git Installation" "vagrant ssh -c 'git --version' 2>/dev/null"
run_test "Build Tools" "vagrant ssh -c 'which gcc' 2>/dev/null"

# Display detailed system information
log "📊 VM System Information:"
vagrant ssh -c "uname -r && echo 'libvirt-fresh-test: VM version OK'" 2>/dev/null | tee -a "$LOG_FILE"
vagrant ssh -c "echo 'Hypervisor: '$(systemd-detect-virt)" 2>/dev/null | tee -a "$LOG_FILE"
vagrant ssh -c "echo 'Memory: '$(free -h | grep Mem | awk '{print \$2}')" 2>/dev/null | tee -a "$LOG_FILE"
vagrant ssh -c "echo 'CPUs: '$(nproc)" 2>/dev/null | tee -a "$LOG_FILE"

# Test results summary
log "📊 Test Results Summary:"
log "Total Tests: $test_count"
log "Passed: $passed_tests"
log "Failed: $((test_count - passed_tests))"

# STEP 4: Final Status, Tagging & Cleanup
if [ $passed_tests -eq $test_count ]; then
    success "🎉 ALL TESTS PASSED!"
    
    # Generate test report
    cat > VM_LIBVIRT_REPORT.md << EOF
# 🧪 Libvirt Ubuntu 24.04 VM Test Report

**Test Date:** $(date -u +'%Y-%m-%d %H:%M:%S UTC')
**VM Status:** ✅ Successfully Created and Tested with libvirt
**Test Results:** $passed_tests/$test_count tests passed
**Hypervisor:** KVM/QEMU via libvirt

## System Information
- **OS:** Ubuntu 24.04 LTS
- **Provider:** libvirt (KVM/QEMU)
- **Memory:** 2GB
- **CPUs:** 2 cores
- **Box:** hashicorp-education/ubuntu-24-04
- **Hypervisor Detection:** $(vagrant ssh -c 'systemd-detect-virt' 2>/dev/null)

## Test Results
- ✅ All $test_count tests passed
- ✅ SSH connectivity verified
- ✅ KVM hypervisor confirmed
- ✅ Development tools installed
- ✅ Network connectivity verified

## Advantages over VirtualBox
- ✅ No KVM conflict issues (VERR_VMX_IN_VMX_ROOT_MODE)
- ✅ Native KVM integration for better performance
- ✅ Proper hardware virtualization support
- ✅ Ubuntu 24.04 compatibility guaranteed

## Log File
Full test log available at: $LOG_FILE

---
*Generated by libvirt-fresh-test agent at $(date)*
EOF
    
    success "Test report generated: VM_LIBVIRT_REPORT.md"
    
    # Git operations
    git add VM_LIBVIRT_REPORT.md 2>/dev/null || true
    git commit --allow-empty -m "chore: libvirt Ubuntu 24.04 smoke test passed cleanly"
    git tag "smoke-test/libvirt/$(date +%Y%m%dT%H%M%SZ)"
    success "Git commit and tag created"
    
    # Check for remote
    if git remote | grep -q origin; then
        log "🔄 Pushing to remote repository..."
        git push origin HEAD --tags
        success "Changes pushed to remote"
    else
        log "libvirt-fresh-test: no remote defined — commit pending push"
    fi
    
else
    warning "Some tests failed - VM may have issues"
fi

# Cleanup options
log "🗑️  Cleanup options:"
echo "VM is currently running. Options:"
echo "1. Keep VM running for development"
echo "2. Halt VM (vagrant halt)"
echo "3. Destroy VM (vagrant destroy -f)"
echo ""

read -p "Choose cleanup option (1/2/3) [1]: " -n 1 -r
echo

case $REPLY in
    2)
        log "⏸️  Halting VM..."
        vagrant halt
        success "VM halted"
        ;;
    3)
        log "🗑️  Destroying VM..."
        vagrant destroy -f
        success "VM destroyed - environment clean"
        ;;
    *)
        success "VM kept running for development"
        log "Access VM: vagrant ssh"
        log "VM IP: 192.168.121.10"
        log "Halt VM: vagrant halt"
        log "Destroy VM: vagrant destroy -f"
        ;;
esac

# Final status
if [ $passed_tests -eq $test_count ]; then
    success "🎉 libvirt VM test completed successfully!"
    log "📄 Report: $LIBVIRT_DIR/VM_LIBVIRT_REPORT.md"
    log "📝 Full log: $LOG_FILE"
    exit 0
else
    warning "libvirt VM test completed with issues"
    log "📄 Report: $LIBVIRT_DIR/VM_LIBVIRT_REPORT.md"
    log "📝 Full log: $LOG_FILE"
    exit 1
fi