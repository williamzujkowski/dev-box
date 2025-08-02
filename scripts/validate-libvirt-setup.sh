#!/bin/bash
# Validation and Cleanup Script for Libvirt Configuration
# Validates libvirt setup and removes VirtualBox dependencies

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
  echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} libvirt-validator: $1"
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

# Show usage
show_usage() {
  echo "Libvirt Configuration Validator and VirtualBox Cleanup"
  echo "Usage: $0 [COMMAND] [OPTIONS]"
  echo ""
  echo "Commands:"
  echo "  validate        Validate libvirt configuration and setup"
  echo "  cleanup         Remove VirtualBox references and dependencies"
  echo "  status          Show current virtualization status"
  echo "  requirements    Check and install libvirt requirements"
  echo "  test            Run comprehensive libvirt functionality test"
  echo "  migrate         Migrate existing VirtualBox VMs to libvirt"
  echo ""
  echo "Options:"
  echo "  --fix           Automatically fix issues found during validation"
  echo "  --force         Force operations without confirmation"
  echo "  --verbose       Show detailed output"
  echo ""
  echo "Examples:"
  echo "  $0 validate --fix       # Validate setup and fix issues"
  echo "  $0 cleanup --force      # Remove VirtualBox deps without prompts"
  echo "  $0 requirements         # Check libvirt requirements"
  echo "  $0 test                 # Test libvirt functionality"
}

# Check libvirt requirements
check_requirements() {
  log "Checking libvirt requirements..."
  
  local missing_packages=()
  local missing_tools=()
  
  # Required packages
  local required_packages=(
    "qemu-kvm"
    "libvirt-daemon-system" 
    "libvirt-clients"
    "virtinst"
    "virt-manager"
    "bridge-utils"
    "dnsmasq-base"
    "ebtables"
  )
  
  # Required tools
  local required_tools=(
    "virsh"
    "virt-install"
    "qemu-img"
    "qemu-system-x86_64"
  )
  
  # Check packages
  for package in "${required_packages[@]}"; do
    if ! dpkg -l | grep -q "^ii.*$package "; then
      missing_packages+=("$package")
    fi
  done
  
  # Check tools
  for tool in "${required_tools[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing_tools+=("$tool")
    fi
  done
  
  if [ ${#missing_packages[@]} -gt 0 ] || [ ${#missing_tools[@]} -gt 0 ]; then
    error "Missing requirements found"
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
      echo "Missing packages: ${missing_packages[*]}"
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
      echo "Missing tools: ${missing_tools[*]}"
    fi
    
    echo ""
    echo "Install missing requirements:"
    echo "  sudo apt update"
    echo "  sudo apt install -y ${missing_packages[*]}"
    echo "  sudo systemctl enable --now libvirtd"
    echo "  sudo usermod -aG libvirt \$USER"
    echo ""
    
    if [[ "${1:-}" == "--fix" ]]; then
      install_requirements
    else
      return 1
    fi
  else
    success "All libvirt requirements satisfied"
  fi
}

# Install libvirt requirements
install_requirements() {
  log "Installing libvirt requirements..."
  
  if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
    sudo apt update
    sudo apt install -y \
      qemu-kvm \
      libvirt-daemon-system \
      libvirt-clients \
      virtinst \
      virt-manager \
      bridge-utils \
      dnsmasq-base \
      ebtables \
      ruby-dev \
      libvirt-dev \
      build-essential
    
    # Enable and start libvirtd
    sudo systemctl enable --now libvirtd
    
    # Add user to libvirt group
    sudo usermod -aG libvirt "$USER"
    
    success "Libvirt requirements installed"
    warning "Please log out and back in for group changes to take effect"
  else
    error "Sudo access required to install requirements"
    return 1
  fi
}

# Validate libvirt setup
validate_setup() {
  log "Validating libvirt configuration..."
  
  local issues_found=0
  
  # Check KVM support
  if [ ! -c /dev/kvm ]; then
    error "KVM device not available"
    echo "  Check: BIOS virtualization settings enabled"
    echo "  Check: KVM modules loaded (modprobe kvm-intel or kvm-amd)"
    issues_found=$((issues_found + 1))
  else
    success "KVM device available"
  fi
  
  # Check CPU virtualization support
  if grep -q vmx /proc/cpuinfo; then
    success "Intel VT-x detected"
  elif grep -q svm /proc/cpuinfo; then
    success "AMD-V detected"
  else
    error "Hardware virtualization not supported"
    issues_found=$((issues_found + 1))
  fi
  
  # Check libvirtd service
  if systemctl is-active --quiet libvirtd; then
    success "libvirtd service is running"
  else
    error "libvirtd service not running"
    if [[ "${1:-}" == "--fix" ]]; then
      sudo systemctl start libvirtd
      success "libvirtd service started"
    else
      issues_found=$((issues_found + 1))
    fi
  fi
  
  # Check user group membership
  if groups | grep -q libvirt; then
    success "User is in libvirt group"
  else
    error "User not in libvirt group"
    if [[ "${1:-}" == "--fix" ]]; then
      sudo usermod -aG libvirt "$USER"
      warning "Please log out and back in for group changes to take effect"
    else
      issues_found=$((issues_found + 1))
    fi
  fi
  
  # Check vagrant-libvirt plugin
  if command -v vagrant >/dev/null 2>&1; then
    if vagrant plugin list | grep -q vagrant-libvirt; then
      success "vagrant-libvirt plugin installed"
    else
      error "vagrant-libvirt plugin not installed"
      if [[ "${1:-}" == "--fix" ]]; then
        vagrant plugin install vagrant-libvirt
        success "vagrant-libvirt plugin installed"
      else
        issues_found=$((issues_found + 1))
      fi
    fi
  else
    warning "Vagrant not found - skipping plugin check"
  fi
  
  # Check default network
  if virsh net-list --all | grep -q default; then
    if virsh net-list | grep -q "default.*active"; then
      success "Default libvirt network is active"
    else
      warning "Default libvirt network not active"
      if [[ "${1:-}" == "--fix" ]]; then
        virsh net-start default
        virsh net-autostart default
        success "Default network activated"
      else
        issues_found=$((issues_found + 1))
      fi
    fi
  else
    error "Default libvirt network not found"
    issues_found=$((issues_found + 1))
  fi
  
  # Summary
  if [ $issues_found -eq 0 ]; then
    success "✨ Libvirt setup validation passed!"
    return 0
  else
    error "Found $issues_found issues in libvirt setup"
    if [[ "${1:-}" != "--fix" ]]; then
      info "Run with --fix to automatically resolve issues"
    fi
    return 1
  fi
}

# Clean up VirtualBox references
cleanup_virtualbox() {
  log "Cleaning up VirtualBox references..."
  
  local files_to_clean=()
  
  # Find files with VirtualBox references
  while IFS= read -r -d '' file; do
    if grep -l -i "virtualbox\|vbox" "$file" 2>/dev/null; then
      files_to_clean+=("$file")
    fi
  done < <(find "$PROJECT_ROOT" -name "*.md" -o -name "*.sh" -o -name "Vagrantfile*" -print0)
  
  if [ ${#files_to_clean[@]} -gt 0 ]; then
    echo "Files containing VirtualBox references:"
    printf '  %s\n' "${files_to_clean[@]}"
    echo ""
    
    if [[ "${1:-}" == "--force" ]] || read -p "Update these files to remove VirtualBox references? (y/n): " -n 1 -r && [[ $REPLY =~ ^[Yy]$ ]]; then
      echo ""
      
      for file in "${files_to_clean[@]}"; do
        # Skip this script and binary files
        if [[ "$file" == *"validate-libvirt-setup.sh" ]] || [[ "$file" == *".git/"* ]]; then
          continue
        fi
        
        log "Cleaning VirtualBox references from $(basename "$file")"
        
        # Create backup
        cp "$file" "$file.virtualbox-backup"
        
        # Update common VirtualBox references in documentation
        sed -i 's/VirtualBox/libvirt (KVM)/g' "$file"
        sed -i 's/virtualbox/libvirt/g' "$file"
        sed -i 's/vbox/libvirt/g' "$file"
        
        # Update Vagrantfile-specific references
        if [[ "$file" == *"Vagrantfile"* ]]; then
          sed -i '/config\.vm\.provider "virtualbox"/,/end/d' "$file"
          sed -i 's/type: "virtualbox"/type: "nfs"/g' "$file"
        fi
        
        success "Updated $(basename "$file")"
      done
    fi
  else
    success "No VirtualBox references found"
  fi
  
  # Check for VirtualBox-specific scripts
  local vbox_scripts=(
    "$PROJECT_ROOT/scripts/virtualbox-setup.sh"
    "$PROJECT_ROOT/scripts/install-virtualbox.sh"
  )
  
  for script in "${vbox_scripts[@]}"; do
    if [ -f "$script" ]; then
      warning "Found VirtualBox-specific script: $(basename "$script")"
      if [[ "${1:-}" == "--force" ]] || read -p "Remove this script? (y/n): " -n 1 -r && [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        mv "$script" "$script.disabled"
        success "Disabled $(basename "$script")"
      fi
    fi
  done
}

# Show current status
show_status() {
  log "Current virtualization status:"
  echo ""
  
  # System information
  echo "System Information:"
  echo "  OS: $(lsb_release -d | cut -f2)"
  echo "  Kernel: $(uname -r)"
  echo "  Architecture: $(uname -m)"
  echo ""
  
  # Virtualization support
  echo "Virtualization Support:"
  if [ -c /dev/kvm ]; then
    echo "  ✅ KVM device: available"
  else
    echo "  ❌ KVM device: not available"
  fi
  
  if grep -q vmx /proc/cpuinfo; then
    echo "  ✅ CPU: Intel VT-x supported"
  elif grep -q svm /proc/cpuinfo; then
    echo "  ✅ CPU: AMD-V supported"
  else
    echo "  ❌ CPU: No virtualization support"
  fi
  echo ""
  
  # Services
  echo "Services:"
  if systemctl is-active --quiet libvirtd; then
    echo "  ✅ libvirtd: running"
  else
    echo "  ❌ libvirtd: not running"
  fi
  
  if command -v vboxmanage >/dev/null 2>&1; then
    echo "  ⚠️  VirtualBox: installed (consider removing)"
  else
    echo "  ✅ VirtualBox: not installed"
  fi
  echo ""
  
  # Vagrant
  echo "Vagrant:"
  if command -v vagrant >/dev/null 2>&1; then
    echo "  ✅ vagrant: $(vagrant --version)"
    if vagrant plugin list | grep -q vagrant-libvirt; then
      echo "  ✅ vagrant-libvirt: installed"
    else
      echo "  ❌ vagrant-libvirt: not installed"
    fi
  else
    echo "  ❌ vagrant: not installed"
  fi
  echo ""
  
  # Networks
  echo "Libvirt Networks:"
  if command -v virsh >/dev/null 2>&1; then
    virsh net-list --all 2>/dev/null || echo "  ❌ Cannot query networks (permissions?)"
  else
    echo "  ❌ virsh not available"
  fi
}

# Test libvirt functionality
test_functionality() {
  log "Testing libvirt functionality..."
  
  # Test libvirt connection
  if virsh version >/dev/null 2>&1; then
    success "Libvirt connection successful"
  else
    error "Cannot connect to libvirt"
    return 1
  fi
  
  # Test KVM access
  if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    success "KVM device accessible"
  else
    error "KVM device not accessible (check permissions)"
    return 1
  fi
  
  # Test network creation
  local test_net="test-network-$$"
  if virsh net-define /dev/stdin <<EOF >/dev/null 2>&1
<network>
  <name>$test_net</name>
  <bridge name="virbr-test"/>
  <ip address="192.168.100.1" netmask="255.255.255.0">
    <dhcp>
      <range start="192.168.100.2" end="192.168.100.254"/>
    </dhcp>
  </ip>
</network>
EOF
  then
    virsh net-start "$test_net" >/dev/null 2>&1
    if virsh net-list | grep -q "$test_net"; then
      success "Network creation test passed"
      virsh net-destroy "$test_net" >/dev/null 2>&1
    fi
    virsh net-undefine "$test_net" >/dev/null 2>&1
  else
    error "Network creation test failed"
    return 1
  fi
  
  success "✨ Libvirt functionality test passed!"
}

# Migrate VirtualBox VMs
migrate_virtualbox() {
  log "Checking for VirtualBox VMs to migrate..."
  
  if ! command -v vboxmanage >/dev/null 2>&1; then
    info "VirtualBox not installed - no VMs to migrate"
    return 0
  fi
  
  local vms
  vms=$(vboxmanage list vms 2>/dev/null || echo "")
  
  if [ -z "$vms" ]; then
    info "No VirtualBox VMs found"
    return 0
  fi
  
  echo "Found VirtualBox VMs:"
  echo "$vms"
  echo ""
  
  warning "VM migration is a complex process and may require manual intervention"
  info "Consider exporting VMs from VirtualBox and importing to libvirt"
  echo ""
  echo "Migration steps:"
  echo "1. Export VM: vboxmanage export <vm-name> --output vm.ova"
  echo "2. Convert disk: qemu-img convert vm.vmdk vm.qcow2"
  echo "3. Create libvirt domain definition"
  echo "4. Import to libvirt: virsh define vm.xml"
  echo ""
  echo "For Vagrant VMs, simply run 'vagrant destroy' and recreate with libvirt provider"
}

# Main execution
main() {
  case "${1:-help}" in
    "validate")
      check_requirements "$2"
      validate_setup "$2"
      ;;
    "cleanup")
      cleanup_virtualbox "$2"
      ;;
    "status")
      show_status
      ;;
    "requirements")
      check_requirements "$2"
      ;;
    "test")
      test_functionality
      ;;
    "migrate")
      migrate_virtualbox
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