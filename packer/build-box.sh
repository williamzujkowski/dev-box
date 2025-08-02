#!/bin/bash
# Automated Packer build script for Ubuntu 24.04 libvirt box
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}"
LOG_FILE="${BUILD_DIR}/build.log"
PACKER_FILE="${BUILD_DIR}/ubuntu-24.04-libvirt.pkr.hcl"
VARIABLES_FILE="${BUILD_DIR}/variables.pkrvars.hcl"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    log "Checking build requirements..."
    
    # Check if packer is installed
    if ! command -v packer &> /dev/null; then
        error "Packer is not installed. Please install it first."
    fi
    
    # Check if KVM is available
    if ! kvm-ok &> /dev/null; then
        warn "KVM acceleration may not be available. Build will be slower."
    fi
    
    # Check if required files exist
    if [[ ! -f "$PACKER_FILE" ]]; then
        error "Packer file not found: $PACKER_FILE"
    fi
    
    if [[ ! -f "$VARIABLES_FILE" ]]; then
        error "Variables file not found: $VARIABLES_FILE"
    fi
    
    # Check cloud-init files
    if [[ ! -f "${BUILD_DIR}/cloud-init/user-data" ]]; then
        error "Cloud-init user-data file not found"
    fi
    
    if [[ ! -f "${BUILD_DIR}/cloud-init/meta-data" ]]; then
        error "Cloud-init meta-data file not found"
    fi
    
    # Check scripts directory
    if [[ ! -d "${BUILD_DIR}/scripts" ]]; then
        error "Scripts directory not found: ${BUILD_DIR}/scripts"
    fi
    
    # Make scripts executable
    chmod +x "${BUILD_DIR}"/scripts/*.sh
    
    log "All requirements satisfied!"
}

validate_config() {
    log "Validating Packer configuration..."
    
    cd "$BUILD_DIR"
    if ! packer validate -var-file="$VARIABLES_FILE" "$PACKER_FILE" >> "$LOG_FILE" 2>&1; then
        error "Packer configuration validation failed. Check $LOG_FILE for details."
    fi
    
    log "Packer configuration is valid!"
}

build_box() {
    log "Starting Packer build..."
    
    cd "$BUILD_DIR"
    
    # Clean up any previous builds
    if [[ -d "output" ]]; then
        warn "Removing previous build artifacts..."
        rm -rf output/
    fi
    
    # Start the build
    info "This may take 20-30 minutes depending on your internet connection and system performance."
    info "Build log: $LOG_FILE"
    
    if packer build -var-file="$VARIABLES_FILE" "$PACKER_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        log "Packer build completed successfully!"
    else
        error "Packer build failed. Check $LOG_FILE for details."
    fi
}

show_results() {
    log "Build completed! Results:"
    
    if [[ -d "${BUILD_DIR}/output" ]]; then
        find "${BUILD_DIR}/output" -name "*.box" -type f | while read -r boxfile; do
            local size=$(du -h "$boxfile" | cut -f1)
            info "Box file: $boxfile (Size: $size)"
        done
        
        find "${BUILD_DIR}/output" -name "*.qcow2" -type f | while read -r qcow2file; do
            local size=$(du -h "$qcow2file" | cut -f1)
            info "QCOW2 image: $qcow2file (Size: $size)"
        done
    else
        warn "No output directory found. Build may have failed."
    fi
}

cleanup() {
    log "Cleaning up temporary files..."
    # Remove any temporary files created during build
    # Be careful not to remove the actual build outputs
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build Ubuntu 24.04 libvirt box with Packer

OPTIONS:
    -h, --help          Show this help message
    -v, --validate-only Only validate configuration, don't build
    -c, --clean         Clean output directory before building
    -l, --log-file      Specify custom log file location

EXAMPLES:
    $0                  # Build the box
    $0 --validate-only  # Only validate configuration
    $0 --clean          # Clean and build
    $0 --log-file /tmp/build.log  # Use custom log file

ENVIRONMENT VARIABLES:
    PACKER_LOG=1        Enable verbose Packer logging
    VAGRANT_CLOUD_TOKEN Set to upload box to Vagrant Cloud
    VAGRANT_CLOUD_USERNAME Set username for Vagrant Cloud upload

EOF
}

# Parse command line arguments
VALIDATE_ONLY=false
CLEAN_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -l|--log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Main execution
main() {
    log "Starting Ubuntu 24.04 Libvirt box build process..."
    
    # Initialize log file
    echo "Build started at $(date)" > "$LOG_FILE"
    
    # Clean output if requested
    if [[ "$CLEAN_BUILD" == true ]] && [[ -d "${BUILD_DIR}/output" ]]; then
        log "Cleaning previous build artifacts..."
        rm -rf "${BUILD_DIR}/output"
    fi
    
    check_requirements
    validate_config
    
    if [[ "$VALIDATE_ONLY" == true ]]; then
        log "Validation completed successfully. Exiting."
        exit 0
    fi
    
    build_box
    show_results
    cleanup
    
    log "Build process completed successfully!"
    log "Check the output directory for your new Vagrant box!"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"