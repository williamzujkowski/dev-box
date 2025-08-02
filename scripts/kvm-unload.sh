#!/bin/bash

# KVM Module Unloader Script with Safety Checks and Rollback
# Author: System Script Developer
# Version: 1.0
# Description: Safely unload KVM modules with comprehensive checks and rollback capability

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly LOG_FILE="/tmp/kvm-unload.log"
readonly BACKUP_DIR="/tmp/kvm-backup-$(date +%Y%m%d-%H%M%S)"
readonly BLACKLIST_FILE="/etc/modprobe.d/blacklist-kvm.conf"

# Global variables
FORCE_MODE=false
PERMANENT_BLACKLIST=false
VERBOSE=false
DRY_RUN=false
ROLLBACK_MODE=false

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")  echo -e "${GREEN}[INFO]${NC} $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $message" ;;
        "DEBUG") [[ "$VERBOSE" == true ]] && echo -e "${BLUE}[DEBUG]${NC} $message" ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Usage function
usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Safely unload KVM modules with comprehensive checks and rollback capability.

OPTIONS:
    -f, --force                Force unload even if VMs are running (dangerous!)
    -p, --permanent           Create permanent blacklist for KVM modules
    -v, --verbose             Enable verbose output
    -d, --dry-run            Show what would be done without executing
    -r, --rollback           Rollback previous KVM unload operation
    -h, --help               Show this help message

EXAMPLES:
    $SCRIPT_NAME                    # Safe unload with checks
    $SCRIPT_NAME -f                 # Force unload (use with caution)
    $SCRIPT_NAME -p                 # Unload and blacklist permanently
    $SCRIPT_NAME -r                 # Rollback previous operation
    $SCRIPT_NAME -d                 # Dry run to see what would happen

SAFETY FEATURES:
    - Checks for running VMs before unloading
    - Creates backup of module states
    - Provides rollback mechanism
    - Logs all operations
    - Optional permanent blacklisting

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE_MODE=true
                shift
                ;;
            -p|--permanent)
                PERMANENT_BLACKLIST=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -r|--rollback)
                ROLLBACK_MODE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR" "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Create backup directory
create_backup() {
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would create backup directory: $BACKUP_DIR"
        return
    fi
    
    mkdir -p "$BACKUP_DIR"
    log "INFO" "Created backup directory: $BACKUP_DIR"
    
    # Backup current module state
    lsmod | grep -E "kvm|qemu" > "$BACKUP_DIR/modules_before.txt" 2>/dev/null || true
    dmesg | tail -100 > "$BACKUP_DIR/dmesg_before.txt"
    
    # Backup existing blacklist if it exists
    if [[ -f "$BLACKLIST_FILE" ]]; then
        cp "$BLACKLIST_FILE" "$BACKUP_DIR/blacklist_backup.conf"
    fi
    
    log "INFO" "Module states backed up to $BACKUP_DIR"
}

# Check for running VMs
check_running_vms() {
    log "INFO" "Checking for running VMs..."
    
    local running_vms=()
    local vm_processes=()
    
    # Check virsh domains
    if command -v virsh >/dev/null 2>&1; then
        local virsh_vms
        virsh_vms=$(virsh list --state-running --name 2>/dev/null | grep -v "^$" || true)
        if [[ -n "$virsh_vms" ]]; then
            while IFS= read -r vm; do
                [[ -n "$vm" ]] && running_vms+=("virsh: $vm")
            done <<< "$virsh_vms"
        fi
    fi
    
    # Check QEMU processes
    local qemu_procs
    qemu_procs=$(pgrep -f "qemu.*kvm" 2>/dev/null || true)
    if [[ -n "$qemu_procs" ]]; then
        while IFS= read -r pid; do
            [[ -n "$pid" ]] && vm_processes+=("qemu-kvm: PID $pid")
        done <<< "$qemu_procs"
    fi
    
    # Check VirtualBox VMs
    if command -v VBoxManage >/dev/null 2>&1; then
        local vbox_vms
        vbox_vms=$(VBoxManage list runningvms 2>/dev/null | cut -d'"' -f2 || true)
        if [[ -n "$vbox_vms" ]]; then
            while IFS= read -r vm; do
                [[ -n "$vm" ]] && running_vms+=("VirtualBox: $vm")
            done <<< "$vbox_vms"
        fi
    fi
    
    local total_vms=$((${#running_vms[@]} + ${#vm_processes[@]}))
    
    if [[ $total_vms -gt 0 ]]; then
        log "WARN" "Found $total_vms running VM(s):"
        for vm in "${running_vms[@]}"; do
            log "WARN" "  - $vm"
        done
        for proc in "${vm_processes[@]}"; do
            log "WARN" "  - $proc"
        done
        
        if [[ "$FORCE_MODE" != true ]]; then
            log "ERROR" "Cannot unload KVM modules while VMs are running!"
            log "INFO" "Use --force to override (WARNING: This may crash running VMs!)"
            return 1
        else
            log "WARN" "Force mode enabled - proceeding despite running VMs!"
        fi
    else
        log "INFO" "No running VMs detected - safe to proceed"
    fi
    
    return 0
}

# Check current KVM module status
check_kvm_status() {
    log "INFO" "Checking current KVM module status..."
    
    local kvm_loaded=false
    local kvm_intel_loaded=false
    local kvm_amd_loaded=false
    
    if lsmod | grep -q "^kvm_intel"; then
        kvm_intel_loaded=true
        log "INFO" "kvm_intel module is loaded"
    fi
    
    if lsmod | grep -q "^kvm_amd"; then
        kvm_amd_loaded=true
        log "INFO" "kvm_amd module is loaded"
    fi
    
    if lsmod | grep -q "^kvm"; then
        kvm_loaded=true
        log "INFO" "kvm module is loaded"
    fi
    
    if [[ "$kvm_loaded" != true && "$kvm_intel_loaded" != true && "$kvm_amd_loaded" != true ]]; then
        log "INFO" "No KVM modules are currently loaded"
        return 1
    fi
    
    # Show module usage
    if [[ "$VERBOSE" == true ]]; then
        log "DEBUG" "Current module usage:"
        lsmod | grep -E "kvm|qemu" || log "DEBUG" "No KVM-related modules found in lsmod"
    fi
    
    return 0
}

# Unload KVM modules safely
unload_kvm_modules() {
    log "INFO" "Beginning KVM module unload process..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would unload KVM modules in this order:"
        log "INFO" "[DRY RUN]   1. kvm_intel/kvm_amd"
        log "INFO" "[DRY RUN]   2. kvm"
        return 0
    fi
    
    local modules_to_unload=()
    
    # Determine which modules are loaded and need unloading
    if lsmod | grep -q "^kvm_intel"; then
        modules_to_unload+=("kvm_intel")
    fi
    
    if lsmod | grep -q "^kvm_amd"; then
        modules_to_unload+=("kvm_amd")
    fi
    
    if lsmod | grep -q "^kvm"; then
        modules_to_unload+=("kvm")
    fi
    
    if [[ ${#modules_to_unload[@]} -eq 0 ]]; then
        log "INFO" "No KVM modules to unload"
        return 0
    fi
    
    # Unload modules in correct order
    for module in "${modules_to_unload[@]}"; do
        log "INFO" "Unloading module: $module"
        
        if ! modprobe -r "$module" 2>/dev/null; then
            log "WARN" "Failed to unload $module with modprobe, trying rmmod..."
            if ! rmmod "$module" 2>/dev/null; then
                log "ERROR" "Failed to unload module: $module"
                log "ERROR" "This may indicate the module is still in use"
                
                # Show what's using the module
                if [[ -f "/sys/module/$module/refcnt" ]]; then
                    local refcnt=$(cat "/sys/module/$module/refcnt" 2>/dev/null || echo "unknown")
                    log "ERROR" "Module $module reference count: $refcnt"
                fi
                
                # Show processes that might be using KVM
                log "ERROR" "Processes that might be using KVM:"
                pgrep -fl "qemu|kvm|virt" || log "ERROR" "No obvious KVM processes found"
                
                return 1
            fi
        fi
        
        log "INFO" "Successfully unloaded module: $module"
    done
    
    return 0
}

# Verify modules are unloaded
verify_unload() {
    log "INFO" "Verifying KVM modules are unloaded..."
    
    local still_loaded=()
    
    if lsmod | grep -q "^kvm_intel"; then
        still_loaded+=("kvm_intel")
    fi
    
    if lsmod | grep -q "^kvm_amd"; then
        still_loaded+=("kvm_amd")
    fi
    
    if lsmod | grep -q "^kvm"; then
        still_loaded+=("kvm")
    fi
    
    if [[ ${#still_loaded[@]} -gt 0 ]]; then
        log "ERROR" "The following modules are still loaded:"
        for module in "${still_loaded[@]}"; do
            log "ERROR" "  - $module"
        done
        return 1
    else
        log "INFO" "All KVM modules successfully unloaded"
        return 0
    fi
}

# Create permanent blacklist
create_blacklist() {
    if [[ "$PERMANENT_BLACKLIST" != true ]]; then
        return 0
    fi
    
    log "INFO" "Creating permanent KVM module blacklist..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would create blacklist file: $BLACKLIST_FILE"
        log "INFO" "[DRY RUN] Would add: blacklist kvm_intel, blacklist kvm_amd, blacklist kvm"
        return 0
    fi
    
    # Create blacklist configuration
    cat > "$BLACKLIST_FILE" << 'EOF'
# KVM Module Blacklist
# Created by kvm-unload.sh
# This prevents KVM modules from loading automatically

# Intel VT-x support
blacklist kvm_intel

# AMD SVM support  
blacklist kvm_amd

# Generic KVM support
blacklist kvm

# Prevent automatic loading
install kvm /bin/true
install kvm_intel /bin/true
install kvm_amd /bin/true
EOF
    
    log "INFO" "Created blacklist file: $BLACKLIST_FILE"
    log "INFO" "Run 'update-initramfs -u' to apply blacklist to initramfs"
    
    # Offer to update initramfs
    if [[ "$FORCE_MODE" == true ]]; then
        log "INFO" "Force mode: Updating initramfs automatically..."
        update-initramfs -u
    else
        read -p "Update initramfs now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            update-initramfs -u
        else
            log "INFO" "Remember to run 'update-initramfs -u' later to apply blacklist"
        fi
    fi
}

# Rollback previous operation
rollback_operation() {
    log "INFO" "Looking for rollback data..."
    
    # Find the most recent backup
    local latest_backup
    latest_backup=$(find /tmp -maxdepth 1 -name "kvm-backup-*" -type d 2>/dev/null | sort -r | head -n1)
    
    if [[ -z "$latest_backup" ]]; then
        log "ERROR" "No backup directory found for rollback"
        return 1
    fi
    
    log "INFO" "Found backup: $latest_backup"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would rollback using: $latest_backup"
        return 0
    fi
    
    # Restore blacklist if it existed
    if [[ -f "$latest_backup/blacklist_backup.conf" ]]; then
        log "INFO" "Restoring previous blacklist configuration..."
        cp "$latest_backup/blacklist_backup.conf" "$BLACKLIST_FILE"
    elif [[ -f "$BLACKLIST_FILE" ]]; then
        log "INFO" "Removing blacklist file created by this script..."
        rm -f "$BLACKLIST_FILE"
    fi
    
    # Try to reload modules that were previously loaded
    if [[ -f "$latest_backup/modules_before.txt" ]]; then
        log "INFO" "Attempting to reload previously loaded modules..."
        
        while IFS= read -r line; do
            if [[ "$line" =~ ^(kvm|kvm_intel|kvm_amd) ]]; then
                local module=$(echo "$line" | awk '{print $1}')
                log "INFO" "Reloading module: $module"
                
                if modprobe "$module" 2>/dev/null; then
                    log "INFO" "Successfully reloaded: $module"
                else
                    log "WARN" "Failed to reload: $module"
                fi
            fi
        done < "$latest_backup/modules_before.txt"
    fi
    
    log "INFO" "Rollback completed. You may need to reboot for full effect."
}

# Main execution function
main() {
    # Initialize log
    echo "=== KVM Module Unloader Log - $(date) ===" > "$LOG_FILE"
    
    log "INFO" "Starting KVM module unloader..."
    log "INFO" "Log file: $LOG_FILE"
    
    # Parse arguments
    parse_args "$@"
    
    # Check if we're in rollback mode
    if [[ "$ROLLBACK_MODE" == true ]]; then
        rollback_operation
        exit $?
    fi
    
    # Pre-flight checks
    check_root
    
    # Create backup before making changes
    create_backup
    
    # Check if KVM modules are loaded
    if ! check_kvm_status; then
        log "INFO" "No KVM modules loaded - nothing to do"
        exit 0
    fi
    
    # Check for running VMs
    if ! check_running_vms; then
        exit 1
    fi
    
    # Unload KVM modules
    if ! unload_kvm_modules; then
        log "ERROR" "Failed to unload KVM modules"
        log "INFO" "Backup available at: $BACKUP_DIR"
        log "INFO" "Use --rollback to restore previous state"
        exit 1
    fi
    
    # Verify unload was successful
    if ! verify_unload; then
        log "ERROR" "Module unload verification failed"
        exit 1
    fi
    
    # Create blacklist if requested
    create_blacklist
    
    log "INFO" "KVM module unload completed successfully"
    log "INFO" "Backup saved to: $BACKUP_DIR"
    
    if [[ "$PERMANENT_BLACKLIST" == true ]]; then
        log "INFO" "Permanent blacklist created - KVM modules will not load on reboot"
        log "INFO" "Use --rollback to reverse this change"
    else
        log "INFO" "No permanent changes made - KVM modules will reload on reboot"
    fi
}

# Run main function with all arguments
main "$@"