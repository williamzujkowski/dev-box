#!/bin/bash
set -euo pipefail

echo "=== Vagrant VM Cleanup Script ==="

# Function to check if VM exists
check_vm_exists() {
    if vagrant status | grep -q "running\|saved\|poweroff"; then
        return 0
    else
        return 1
    fi
}

# Function to gracefully stop VM
stop_vm() {
    echo "Stopping VM gracefully..."
    if vagrant status | grep -q "running"; then
        vagrant halt
        echo "VM stopped successfully"
    else
        echo "VM is not running"
    fi
}

# Function to destroy VM
destroy_vm() {
    echo "Destroying VM..."
    vagrant destroy -f
    echo "VM destroyed successfully"
}

# Function to clean up Vagrant box cache
cleanup_box_cache() {
    echo "Cleaning up box cache..."
    vagrant box prune
    echo "Box cache cleaned"
}

# Function to remove temporary files
cleanup_temp_files() {
    echo "Cleaning up temporary files..."
    rm -rf .vagrant/
    rm -f *.log
    rm -f *-console.log
    echo "Temporary files cleaned"
}

# Main cleanup process
main() {
    echo "Starting VM cleanup process..."
    
    if check_vm_exists; then
        echo "VM found, proceeding with cleanup..."
        
        # Stop VM first
        stop_vm
        
        # Destroy VM
        destroy_vm
        
        # Clean up cache and temp files
        cleanup_box_cache
        cleanup_temp_files
        
        echo "=== VM Cleanup Complete ==="
    else
        echo "No VM found to clean up"
        
        # Still clean up any leftover files
        cleanup_temp_files
        
        echo "=== Cleanup Complete ==="
    fi
}

# Handle script arguments
case "${1:-}" in
    --force|-f)
        echo "Force cleanup mode enabled"
        main
        ;;
    --help|-h)
        echo "Usage: $0 [--force|-f] [--help|-h]"
        echo "  --force, -f    Force cleanup without confirmation"
        echo "  --help, -h     Show this help message"
        exit 0
        ;;
    "")
        echo "This will destroy the VM and clean up all associated files."
        read -p "Are you sure you want to continue? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            main
        else
            echo "Cleanup cancelled"
            exit 0
        fi
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac