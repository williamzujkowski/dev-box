#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging
LOG_FILE="vm-integration-test-$(date +%Y%m%d-%H%M%S).log"

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

print_header() {
  echo -e "${BLUE}======================================${NC}"
  echo -e "${BLUE}  Vagrant VM Integration Test Suite  ${NC}"
  echo -e "${BLUE}======================================${NC}"
  log "Starting integration test suite"
}

print_result() {
  local test_name="$1"
  local result="$2"
  local message="$3"

  ((TOTAL_TESTS++))

  if [ "$result" = "PASS" ]; then
    echo -e "✅ ${GREEN}PASS${NC}: $test_name"
    ((PASSED_TESTS++))
    log "PASS: $test_name - $message"
  else
    echo -e "❌ ${RED}FAIL${NC}: $test_name - $message"
    ((FAILED_TESTS++))
    log "FAIL: $test_name - $message"
  fi
}

# Test functions
test_vm_status() {
  local test_name="VM Status Check"
  if vagrant status | grep -q "running"; then
    print_result "$test_name" "PASS" "VM is running"
    return 0
  else
    print_result "$test_name" "FAIL" "VM is not running"
    return 1
  fi
}

test_ssh_connectivity() {
  local test_name="SSH Connectivity"
  if vagrant ssh -c "exit 0" >/dev/null 2>&1; then
    print_result "$test_name" "PASS" "SSH connection successful"
    return 0
  else
    print_result "$test_name" "FAIL" "SSH connection failed"
    return 1
  fi
}

test_guest_additions() {
  local test_name="VirtualBox Guest Additions"
  local result=$(vagrant ssh -c "lsmod | grep vboxguest | wc -l" 2>/dev/null || echo "0")
  if [ "$result" -gt 0 ]; then
    print_result "$test_name" "PASS" "Guest Additions modules loaded"
    return 0
  else
    print_result "$test_name" "FAIL" "Guest Additions not found"
    return 1
  fi
}

test_shared_folders() {
  local test_name="Shared Folders"
  if vagrant ssh -c "test -d /vagrant && test -d /home/vagrant/tests && test -d /home/vagrant/scripts" 2>/dev/null; then
    print_result "$test_name" "PASS" "All shared folders accessible"
    return 0
  else
    print_result "$test_name" "FAIL" "Shared folders not accessible"
    return 1
  fi
}

test_port_forwarding() {
  local test_name="Port Forwarding"
  local ssh_port=$(netstat -tln | grep -c ":2222 " || echo "0")
  if [ "$ssh_port" -gt 0 ]; then
    print_result "$test_name" "PASS" "SSH port forwarding active"
    return 0
  else
    print_result "$test_name" "FAIL" "SSH port forwarding not found"
    return 1
  fi
}

test_system_packages() {
  local test_name="System Packages"
  local packages=("curl" "git" "vim" "htop" "docker" "nodejs" "python3")
  local missing_packages=()

  for package in "${packages[@]}"; do
    if ! vagrant ssh -c "command -v $package >/dev/null 2>&1" 2>/dev/null; then
      missing_packages+=("$package")
    fi
  done

  if [ ${#missing_packages[@]} -eq 0 ]; then
    print_result "$test_name" "PASS" "All required packages installed"
    return 0
  else
    print_result "$test_name" "FAIL" "Missing packages: ${missing_packages[*]}"
    return 1
  fi
}

test_docker_functionality() {
  local test_name="Docker Functionality"
  if vagrant ssh -c "docker --version && docker ps" >/dev/null 2>&1; then
    print_result "$test_name" "PASS" "Docker is functional"
    return 0
  else
    print_result "$test_name" "FAIL" "Docker is not working"
    return 1
  fi
}

test_network_connectivity() {
  local test_name="Network Connectivity"
  if vagrant ssh -c "ping -c 1 8.8.8.8" >/dev/null 2>&1; then
    print_result "$test_name" "PASS" "External network connectivity working"
    return 0
  else
    print_result "$test_name" "FAIL" "No external network connectivity"
    return 1
  fi
}

test_file_permissions() {
  local test_name="File Permissions"
  local test_file="/vagrant/test-write-$(date +%s).tmp"
  if vagrant ssh -c "echo 'test' > $test_file && rm $test_file" >/dev/null 2>&1; then
    print_result "$test_name" "PASS" "File operations working"
    return 0
  else
    print_result "$test_name" "FAIL" "File operations failed"
    return 1
  fi
}

test_resource_allocation() {
  local test_name="Resource Allocation"
  local cpu_count=$(vagrant ssh -c "nproc" 2>/dev/null || echo "0")
  local memory_mb=$(vagrant ssh -c "free -m | grep '^Mem:' | awk '{print \$2}'" 2>/dev/null || echo "0")

  if [ "$cpu_count" -ge 2 ] && [ "$memory_mb" -ge 1800 ]; then
    print_result "$test_name" "PASS" "CPU: $cpu_count cores, Memory: ${memory_mb}MB"
    return 0
  else
    print_result "$test_name" "FAIL" "Insufficient resources - CPU: $cpu_count, Memory: ${memory_mb}MB"
    return 1
  fi
}

# Performance tests
test_boot_time() {
  local test_name="Boot Time Performance"
  log "Testing VM boot time (this may take a few minutes)..."

  # Stop VM if running
  if vagrant status | grep -q "running"; then
    vagrant halt >/dev/null 2>&1
  fi

  # Time the boot process
  local start_time=$(date +%s)
  if vagrant up >/dev/null 2>&1; then
    local end_time=$(date +%s)
    local boot_time=$((end_time - start_time))

    if [ "$boot_time" -le 120 ]; then # 2 minutes
      print_result "$test_name" "PASS" "Boot time: ${boot_time}s"
      return 0
    else
      print_result "$test_name" "FAIL" "Boot time too slow: ${boot_time}s"
      return 1
    fi
  else
    print_result "$test_name" "FAIL" "VM failed to boot"
    return 1
  fi
}

# Test lifecycle operations
test_lifecycle_operations() {
  local test_name="VM Lifecycle Operations"
  log "Testing VM lifecycle operations..."

  # Test halt and start
  if vagrant halt >/dev/null 2>&1 && vagrant up >/dev/null 2>&1; then
    print_result "$test_name" "PASS" "Halt and restart successful"
    return 0
  else
    print_result "$test_name" "FAIL" "Lifecycle operations failed"
    return 1
  fi
}

# Main test execution
run_all_tests() {
  echo -e "${YELLOW}Starting comprehensive integration tests...${NC}"

  # Core functionality tests
  test_vm_status
  test_ssh_connectivity
  test_shared_folders
  test_port_forwarding

  # System configuration tests
  test_guest_additions
  test_system_packages
  test_docker_functionality
  test_network_connectivity
  test_file_permissions
  test_resource_allocation

  # Performance tests (optional - can be slow)
  if [ "${SKIP_PERFORMANCE_TESTS:-}" != "true" ]; then
    test_boot_time
    test_lifecycle_operations
  fi
}

# Summary report
print_summary() {
  echo
  echo -e "${BLUE}======================================${NC}"
  echo -e "${BLUE}         Test Summary Report          ${NC}"
  echo -e "${BLUE}======================================${NC}"
  echo -e "Total Tests: $TOTAL_TESTS"
  echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
  echo -e "${RED}Failed: $FAILED_TESTS${NC}"

  local success_rate=0
  if [ "$TOTAL_TESTS" -gt 0 ]; then
    success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
  fi

  echo -e "Success Rate: ${success_rate}%"
  echo -e "Log File: $LOG_FILE"

  if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! VM is ready for use.${NC}"
    log "All integration tests passed successfully"
    return 0
  else
    echo -e "${RED}⚠️  Some tests failed. Please review the issues above.${NC}"
    log "Integration tests completed with $FAILED_TESTS failures"
    return 1
  fi
}

# Script entry point
main() {
  print_header

  # Check if Vagrant is available
  if ! command -v vagrant >/dev/null 2>&1; then
    echo -e "${RED}Error: Vagrant is not installed or not in PATH${NC}"
    exit 1
  fi

  # Change to the vagrant directory if specified
  if [ -n "${VAGRANT_DIR:-}" ]; then
    cd "$VAGRANT_DIR"
  fi

  # Run all tests
  run_all_tests

  # Print summary
  print_summary
}

# Handle command line arguments
case "${1:-}" in
--help | -h)
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --help, -h                 Show this help message"
  echo "  --skip-performance         Skip performance tests"
  echo ""
  echo "Environment variables:"
  echo "  VAGRANT_DIR               Directory containing Vagrantfile"
  echo "  SKIP_PERFORMANCE_TESTS    Set to 'true' to skip performance tests"
  exit 0
  ;;
--skip-performance)
  export SKIP_PERFORMANCE_TESTS=true
  main
  ;;
"")
  main
  ;;
*)
  echo "Unknown option: $1"
  echo "Use --help for usage information"
  exit 1
  ;;
esac
