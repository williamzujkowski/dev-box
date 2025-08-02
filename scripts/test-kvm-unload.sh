#!/bin/bash

# KVM Unload Script Tester
# Tests the kvm-unload.sh script functionality

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(dirname "$0")"
readonly KVM_SCRIPT="$SCRIPT_DIR/kvm-unload.sh"

# Test functions
test_help() {
    echo -e "${BLUE}Testing help output...${NC}"
    if "$KVM_SCRIPT" --help; then
        echo -e "${GREEN}✓ Help output works${NC}"
    else
        echo -e "${RED}✗ Help output failed${NC}"
        return 1
    fi
}

test_dry_run() {
    echo -e "${BLUE}Testing dry run mode...${NC}"
    if sudo "$KVM_SCRIPT" --dry-run --verbose; then
        echo -e "${GREEN}✓ Dry run completed${NC}"
    else
        echo -e "${RED}✗ Dry run failed${NC}"
        return 1
    fi
}

test_status_check() {
    echo -e "${BLUE}Testing KVM status detection...${NC}"
    
    # Show current KVM status
    echo "Current KVM modules:"
    lsmod | grep -E "kvm" || echo "No KVM modules loaded"
    
    echo "Current VM processes:"
    pgrep -fl "qemu|kvm|virt" || echo "No VM processes found"
    
    if command -v virsh >/dev/null 2>&1; then
        echo "Virsh domains:"
        virsh list --all 2>/dev/null || echo "virsh not available or no domains"
    fi
}

test_permissions() {
    echo -e "${BLUE}Testing permission requirements...${NC}"
    
    if [[ $EUID -eq 0 ]]; then
        echo -e "${GREEN}✓ Running as root${NC}"
    else
        echo -e "${YELLOW}! Not running as root - testing user execution${NC}"
        if "$KVM_SCRIPT" --help >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Script can be executed by user for help${NC}"
        else
            echo -e "${RED}✗ Script cannot be executed by user${NC}"
            return 1
        fi
        
        # Test that it properly requires root for actual operations
        if "$KVM_SCRIPT" --dry-run 2>&1 | grep -q "must be run as root"; then
            echo -e "${GREEN}✓ Properly requires root for operations${NC}"
        else
            echo -e "${RED}✗ Does not properly check for root${NC}"
            return 1
        fi
    fi
}

test_script_syntax() {
    echo -e "${BLUE}Testing script syntax...${NC}"
    
    if bash -n "$KVM_SCRIPT"; then
        echo -e "${GREEN}✓ Script syntax is valid${NC}"
    else
        echo -e "${RED}✗ Script has syntax errors${NC}"
        return 1
    fi
}

test_dependencies() {
    echo -e "${BLUE}Testing script dependencies...${NC}"
    
    local missing_deps=()
    
    # Check for required commands
    local required_cmds=("lsmod" "modprobe" "rmmod" "pgrep" "mkdir" "cp" "date")
    
    for cmd in "${required_cmds[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps+=("$cmd")
        fi
    done
    
    # Check for optional commands
    local optional_cmds=("virsh" "VBoxManage")
    
    for cmd in "${optional_cmds[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Optional dependency available: $cmd${NC}"
        else
            echo -e "${YELLOW}! Optional dependency missing: $cmd${NC}"
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required dependencies:${NC}"
        for dep in "${missing_deps[@]}"; do
            echo -e "${RED}  - $dep${NC}"
        done
        return 1
    else
        echo -e "${GREEN}✓ All required dependencies available${NC}"
    fi
}

run_safe_tests() {
    echo -e "${BLUE}=== Running Safe Tests (No Root Required) ===${NC}"
    
    local tests=(
        "test_script_syntax"
        "test_help"
        "test_permissions"
        "test_dependencies"
    )
    
    local passed=0
    local total=${#tests[@]}
    
    for test in "${tests[@]}"; do
        echo
        if $test; then
            ((passed++))
        else
            echo -e "${RED}Test failed: $test${NC}"
        fi
    done
    
    echo
    echo -e "${BLUE}=== Safe Test Results ===${NC}"
    echo -e "Passed: ${GREEN}$passed${NC}/$total"
    
    if [[ $passed -eq $total ]]; then
        echo -e "${GREEN}All safe tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed${NC}"
        return 1
    fi
}

run_root_tests() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${YELLOW}Skipping root tests - not running as root${NC}"
        echo -e "${BLUE}To run root tests: sudo $0 --root-tests${NC}"
        return 0
    fi
    
    echo -e "${BLUE}=== Running Root Tests ===${NC}"
    
    local tests=(
        "test_status_check"
        "test_dry_run"
    )
    
    local passed=0
    local total=${#tests[@]}
    
    for test in "${tests[@]}"; do
        echo
        if $test; then
            ((passed++))
        else
            echo -e "${RED}Test failed: $test${NC}"
        fi
    done
    
    echo
    echo -e "${BLUE}=== Root Test Results ===${NC}"
    echo -e "Passed: ${GREEN}$passed${NC}/$total"
    
    if [[ $passed -eq $total ]]; then
        echo -e "${GREEN}All root tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed${NC}"
        return 1
    fi
}

show_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Test the kvm-unload.sh script functionality.

OPTIONS:
    --safe-only     Run only safe tests (no root required)
    --root-tests    Run tests that require root access
    --all          Run all available tests
    -h, --help     Show this help

EXAMPLES:
    $0 --safe-only    # Test script without root
    sudo $0 --all     # Test everything as root
    $0 --help         # Show this help

EOF
}

main() {
    if [[ ! -f "$KVM_SCRIPT" ]]; then
        echo -e "${RED}Error: KVM script not found at $KVM_SCRIPT${NC}"
        exit 1
    fi
    
    case "${1:-}" in
        --safe-only)
            run_safe_tests
            ;;
        --root-tests)
            run_root_tests
            ;;
        --all)
            run_safe_tests
            echo
            run_root_tests
            ;;
        -h|--help)
            show_usage
            ;;
        "")
            # Default: run safe tests, then suggest root tests
            run_safe_tests
            echo
            echo -e "${BLUE}To test root functionality: sudo $0 --root-tests${NC}"
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"