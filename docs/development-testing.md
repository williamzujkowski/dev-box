# Development Testing Procedures

## Overview

This document provides comprehensive testing procedures for local development and CI/CD validation of the Vagrant box build system.

## Local Development Testing

### Prerequisites

Before running tests locally, ensure you have the following installed:

```bash
# Check prerequisites
vagrant --version  # >= 2.4.0
packer version     # >= 1.10.0
virsh list --all   # Libvirt connection working
kvm-ok            # KVM acceleration available
```

### Quick Development Cycle

#### 1. Basic Validation Test

```bash
#!/bin/bash
# scripts/quick-test.sh

set -euo pipefail

echo "Running quick validation test..."

# Check Packer configuration
cd packer
packer validate ubuntu-24.04-libvirt.pkr.hcl

# Quick build test (minimal configuration)
packer build -var "headless=true" -var "skip_export=true" ubuntu-24.04-libvirt.pkr.hcl

echo "Quick test completed successfully"
```

#### 2. Incremental Testing

```bash
#!/bin/bash
# scripts/incremental-test.sh

set -euo pipefail

COMPONENT="${1:-all}"

case "$COMPONENT" in
  "packer")
    echo "Testing Packer configuration..."
    cd packer
    packer validate ubuntu-24.04-libvirt.pkr.hcl
    packer inspect ubuntu-24.04-libvirt.pkr.hcl
    ;;
  "scripts")
    echo "Testing provisioning scripts..."
    for script in scripts/*.sh; do
      echo "Checking $script..."
      shellcheck "$script" || echo "Warning: ShellCheck issues in $script"
      bash -n "$script"  # Syntax check
    done
    ;;
  "vagrant")
    echo "Testing Vagrant configuration..."
    vagrant validate
    vagrant status
    ;;
  "all")
    echo "Running comprehensive test..."
    $0 packer
    $0 scripts
    $0 vagrant
    ;;
  *)
    echo "Unknown component: $COMPONENT"
    echo "Usage: $0 [packer|scripts|vagrant|all]"
    exit 1
    ;;
esac
```

### Local Box Building

#### 1. Standard Build Process

```bash
#!/bin/bash
# scripts/build-local.sh

set -euo pipefail

echo "Starting local box build..."

# Preparation
cd packer
mkdir -p output logs

# Set environment for local build
export PACKER_LOG=1
export PACKER_LOG_PATH="logs/packer-$(date +%Y%m%d-%H%M%S).log"

# Build with local optimizations
packer build \
  -var "headless=false" \
  -var "cpus=4" \
  -var "memory=4096" \
  -var "disk_size=20480" \
  ubuntu-24.04-libvirt.pkr.hcl

echo "Build completed. Box file:"
ls -lh output/*.box
```

#### 2. Development Build (Faster)

```bash
#!/bin/bash
# scripts/dev-build.sh

set -euo pipefail

echo "Starting development build (faster, less validation)..."

cd packer

# Development build with minimal features
packer build \
  -var "headless=true" \
  -var "skip_cleanup=true" \
  -var "cpus=2" \
  -var "memory=2048" \
  -var "disk_size=10240" \
  -var "ssh_timeout=10m" \
  -only="qemu.ubuntu" \
  ubuntu-24.04-libvirt.pkr.hcl

echo "Development build completed"
```

### Local Testing Framework

#### 1. Test Suite Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_packer_config.py
│   ├── test_vagrant_config.py
│   └── test_scripts.py
├── integration/             # Integration tests
│   ├── test_box_build.py
│   ├── test_vagrant_up.py
│   └── test_provisioning.py
├── performance/             # Performance tests
│   ├── test_build_time.py
│   ├── test_boot_time.py
│   └── test_resource_usage.py
└── helpers/                 # Test utilities
    ├── box_manager.py
    ├── vagrant_helper.py
    └── test_config.py
```

#### 2. Unit Test Example

```python
#!/usr/bin/env python3
# tests/unit/test_packer_config.py

import json
import subprocess
import unittest
from pathlib import Path

class TestPackerConfig(unittest.TestCase):
    def setUp(self):
        self.packer_dir = Path("packer")
        self.config_file = self.packer_dir / "ubuntu-24.04-libvirt.pkr.hcl"
    
    def test_config_validation(self):
        """Test that Packer configuration is valid"""
        result = subprocess.run(
            ["packer", "validate", str(self.config_file)],
            cwd=self.packer_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Packer validation failed: {result.stderr}")
    
    def test_config_inspection(self):
        """Test that configuration can be inspected"""
        result = subprocess.run(
            ["packer", "inspect", str(self.config_file)],
            cwd=self.packer_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("qemu.ubuntu", result.stdout)
    
    def test_required_variables(self):
        """Test that required variables are defined"""
        # This would parse the HCL file to check for required variables
        # Implementation depends on HCL parsing library
        pass

if __name__ == "__main__":
    unittest.main()
```

#### 3. Integration Test Example

```python
#!/usr/bin/env python3
# tests/integration/test_vagrant_up.py

import subprocess
import tempfile
import unittest
from pathlib import Path
import os

class TestVagrantIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.box_name = "test-dev-box"
        
    def tearDown(self):
        # Cleanup test environment
        subprocess.run(["vagrant", "destroy", "-f"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["vagrant", "box", "remove", self.box_name], capture_output=True)
    
    def test_vagrant_up_and_ssh(self):
        """Test that Vagrant can start VM and SSH works"""
        # Find built box
        box_files = list(Path("packer/output").glob("*.box"))
        self.assertTrue(box_files, "No box file found")
        
        box_file = box_files[0]
        
        # Add box to Vagrant
        result = subprocess.run([
            "vagrant", "box", "add", "--name", self.box_name, 
            str(box_file), "--provider", "libvirt"
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to add box: {result.stderr}")
        
        # Create Vagrantfile
        vagrantfile_content = f"""
Vagrant.configure("2") do |config|
  config.vm.box = "{self.box_name}"
  config.vm.provider :libvirt do |libvirt|
    libvirt.memory = 1024
    libvirt.cpus = 1
  end
end
"""
        
        with open(os.path.join(self.test_dir, "Vagrantfile"), "w") as f:
            f.write(vagrantfile_content)
        
        # Test vagrant up
        result = subprocess.run(
            ["vagrant", "up", "--provider=libvirt"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        self.assertEqual(result.returncode, 0, f"Vagrant up failed: {result.stderr}")
        
        # Test SSH connectivity
        result = subprocess.run(
            ["vagrant", "ssh", "-c", "echo 'SSH test successful'"],
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("SSH test successful", result.stdout)

if __name__ == "__main__":
    unittest.main()
```

#### 4. Performance Test Example

```python
#!/usr/bin/env python3
# tests/performance/test_build_time.py

import time
import subprocess
import unittest
import json
from pathlib import Path

class TestBuildPerformance(unittest.TestCase):
    def setUp(self):
        self.packer_dir = Path("packer")
        self.performance_log = Path("performance_metrics.json")
        
    def test_build_time_regression(self):
        """Test that build time hasn't regressed significantly"""
        start_time = time.time()
        
        # Run development build
        result = subprocess.run([
            "packer", "build", 
            "-var", "headless=true",
            "-var", "cpus=2",
            "-var", "memory=2048",
            "ubuntu-24.04-libvirt.pkr.hcl"
        ], cwd=self.packer_dir, capture_output=True)
        
        end_time = time.time()
        build_duration = end_time - start_time
        
        # Check if build succeeded
        self.assertEqual(result.returncode, 0, "Build failed")
        
        # Performance assertions
        self.assertLess(build_duration, 2400, "Build took longer than 40 minutes")
        
        # Log performance data
        perf_data = {
            "timestamp": time.time(),
            "build_duration": build_duration,
            "success": result.returncode == 0
        }
        
        if self.performance_log.exists():
            with open(self.performance_log) as f:
                data = json.load(f)
        else:
            data = {"build_times": []}
        
        data["build_times"].append(perf_data)
        
        with open(self.performance_log, "w") as f:
            json.dump(data, f, indent=2)
        
        # Check for regression (if we have historical data)
        if len(data["build_times"]) > 5:
            recent_times = [t["build_duration"] for t in data["build_times"][-5:]]
            avg_time = sum(recent_times) / len(recent_times)
            
            # Allow 20% variance
            max_acceptable = avg_time * 1.2
            self.assertLess(build_duration, max_acceptable, 
                          f"Build time {build_duration}s significantly higher than average {avg_time}s")

if __name__ == "__main__":
    unittest.main()
```

### Test Execution Scripts

#### 1. Run All Tests

```bash
#!/bin/bash
# scripts/run-tests.sh

set -euo pipefail

echo "Running comprehensive test suite..."

# Set up test environment
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"
export TEST_DATA_DIR="${PWD}/tests/data"

# Create test data directory if it doesn't exist
mkdir -p "$TEST_DATA_DIR"

# Run unit tests
echo "Running unit tests..."
python3 -m pytest tests/unit/ -v --tb=short

# Run integration tests (only if environment supports it)
if command -v vagrant >/dev/null 2>&1 && command -v packer >/dev/null 2>&1; then
    echo "Running integration tests..."
    python3 -m pytest tests/integration/ -v --tb=short -x  # Stop on first failure
else
    echo "Skipping integration tests (vagrant/packer not available)"
fi

# Run performance tests (optional)
if [[ "${RUN_PERFORMANCE_TESTS:-false}" == "true" ]]; then
    echo "Running performance tests..."
    python3 -m pytest tests/performance/ -v --tb=short
else
    echo "Skipping performance tests (set RUN_PERFORMANCE_TESTS=true to enable)"
fi

echo "Test suite completed successfully!"
```

#### 2. Continuous Testing

```bash
#!/bin/bash
# scripts/watch-tests.sh

set -euo pipefail

echo "Starting continuous test monitoring..."

# Install prerequisites if available
if command -v inotifywait >/dev/null 2>&1; then
    WATCH_CMD="inotifywait -m -r -e modify,create,delete --include='.*\.(py|sh|hcl|rb)$'"
else
    echo "inotifywait not available, using polling mode"
    WATCH_CMD="while true; do sleep 5; done"
fi

run_tests() {
    echo "$(date): Running tests due to file changes..."
    
    # Run quick tests first
    if python3 -m pytest tests/unit/ -q --tb=no; then
        echo "$(date): Unit tests passed"
        
        # Run integration tests if unit tests pass
        if [[ "${SKIP_INTEGRATION:-false}" != "true" ]]; then
            python3 -m pytest tests/integration/ -q --tb=line -x
        fi
    else
        echo "$(date): Unit tests failed, skipping integration tests"
    fi
    
    echo "$(date): Test run completed"
    echo "----------------------------------------"
}

# Run tests initially
run_tests

# Watch for changes
$WATCH_CMD packer/ scripts/ tests/ Vagrantfile* | while read -r event; do
    echo "File change detected: $event"
    # Debounce - wait a bit for multiple changes
    sleep 2
    run_tests
done
```

## CI/CD Integration Testing

### 1. Pre-commit Testing

```bash
#!/bin/bash
# .git/hooks/pre-commit

set -euo pipefail

echo "Running pre-commit tests..."

# Syntax checks
echo "Checking shell scripts..."
find scripts -name "*.sh" -exec shellcheck {} \;

echo "Checking Python syntax..."
find tests -name "*.py" -exec python3 -m py_compile {} \;

# Packer validation
if command -v packer >/dev/null 2>&1; then
    echo "Validating Packer configuration..."
    cd packer
    packer validate ubuntu-24.04-libvirt.pkr.hcl
    cd ..
fi

# Run critical unit tests
echo "Running critical unit tests..."
python3 -m pytest tests/unit/test_packer_config.py -v

echo "Pre-commit tests passed!"
```

### 2. Local CI Simulation

```bash
#!/bin/bash
# scripts/simulate-ci.sh

set -euo pipefail

echo "Simulating CI/CD pipeline locally..."

# Environment setup (similar to CI)
export PACKER_LOG=1
export VAGRANT_LOG=info
export CI_SIMULATION=true

# Step 1: Environment setup
echo "=== Step 1: Environment Setup ==="
./scripts/setup-environment.sh

# Step 2: Build
echo "=== Step 2: Build ==="
./scripts/build-local.sh

# Step 3: Validation
echo "=== Step 3: Validation ==="
./scripts/validate-box.sh

# Step 4: Testing
echo "=== Step 4: Testing ==="
./scripts/run-tests.sh

# Step 5: Cleanup
echo "=== Step 5: Cleanup ==="
./scripts/cleanup.sh

echo "CI simulation completed successfully!"
```

### 3. Performance Benchmarking

```bash
#!/bin/bash
# scripts/benchmark.sh

set -euo pipefail

echo "Running performance benchmarks..."

BENCHMARK_DIR="benchmarks/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BENCHMARK_DIR"

# Build time benchmark
echo "Benchmarking build time..."
time ./scripts/build-local.sh 2>&1 | tee "$BENCHMARK_DIR/build-time.log"

# Box size benchmark
echo "Benchmarking box size..."
if ls packer/output/*.box >/dev/null 2>&1; then
    du -h packer/output/*.box > "$BENCHMARK_DIR/box-size.log"
fi

# Boot time benchmark
echo "Benchmarking boot time..."
./scripts/benchmark-boot-time.sh > "$BENCHMARK_DIR/boot-time.log"

# Resource usage benchmark
echo "Benchmarking resource usage..."
./scripts/benchmark-resources.sh > "$BENCHMARK_DIR/resource-usage.log"

# Generate summary
cat > "$BENCHMARK_DIR/summary.md" << EOF
# Performance Benchmark Summary

**Date:** $(date)
**Commit:** $(git rev-parse HEAD)

## Results

### Build Time
\`\`\`
$(cat "$BENCHMARK_DIR/build-time.log" | grep real)
\`\`\`

### Box Size
\`\`\`
$(cat "$BENCHMARK_DIR/box-size.log")
\`\`\`

### Boot Time
\`\`\`
$(cat "$BENCHMARK_DIR/boot-time.log")
\`\`\`

### Resource Usage
\`\`\`
$(cat "$BENCHMARK_DIR/resource-usage.log")
\`\`\`

EOF

echo "Benchmark results saved to: $BENCHMARK_DIR/"
```

## Testing Best Practices

### 1. Test Environment Isolation

```bash
# Use separate test environments
export VAGRANT_HOME="$PWD/.vagrant-test"
export PACKER_CACHE_DIR="$PWD/.packer-cache-test"

# Cleanup after tests
cleanup_test_env() {
    rm -rf "$VAGRANT_HOME"
    rm -rf "$PACKER_CACHE_DIR"
    vagrant global-status --prune || true
}

trap cleanup_test_env EXIT
```

### 2. Deterministic Testing

```python
# Use fixed seeds and configurations for reproducible tests
import os
import random

# Set environment for consistent results
os.environ['TZ'] = 'UTC'
random.seed(12345)

# Use fixed test data
TEST_CONFIG = {
    "box_name": "test-box-12345",
    "memory": 1024,
    "cpus": 1,
    "timeout": 300
}
```

### 3. Resource Management

```bash
# Monitor and limit resource usage during tests
ulimit -v 8388608  # Limit virtual memory to 8GB
ulimit -t 3600     # Limit CPU time to 1 hour

# Monitor disk space
check_disk_space() {
    local available=$(df / | awk 'NR==2 {print $4}')
    if [[ $available -lt 5242880 ]]; then  # Less than 5GB
        echo "Warning: Low disk space"
        df -h
    fi
}

check_disk_space
```

### 4. Parallel Testing

```bash
#!/bin/bash
# scripts/parallel-tests.sh

set -euo pipefail

# Run tests in parallel with job control
run_test_category() {
    local category="$1"
    echo "Starting $category tests..."
    python3 -m pytest "tests/$category/" -v --tb=short \
        --junitxml="test-results/$category.xml" \
        > "test-logs/$category.log" 2>&1
    echo "$category tests completed with exit code $?"
}

# Create output directories
mkdir -p test-results test-logs

# Start test categories in parallel
run_test_category "unit" &
UNIT_PID=$!

run_test_category "integration" &
INTEGRATION_PID=$!

# Wait for completion
wait $UNIT_PID
UNIT_EXIT=$?

wait $INTEGRATION_PID
INTEGRATION_EXIT=$?

# Report results
echo "Unit tests exit code: $UNIT_EXIT"
echo "Integration tests exit code: $INTEGRATION_EXIT"

if [[ $UNIT_EXIT -eq 0 && $INTEGRATION_EXIT -eq 0 ]]; then
    echo "All tests passed!"
    exit 0
else
    echo "Some tests failed!"
    exit 1
fi
```

## Troubleshooting Development Issues

### 1. Debug Mode

```bash
#!/bin/bash
# scripts/debug-mode.sh

set -euo pipefail

echo "Enabling debug mode for development testing..."

# Set debug environment
export PACKER_LOG=1
export PACKER_LOG_PATH="debug-packer.log"
export VAGRANT_LOG=debug
export VAGRANT_LOG_PATH="debug-vagrant.log"

# Enable verbose output for all tools
export VERBOSE=1

# Run with debug settings
"$@"

echo "Debug logs available:"
echo "- Packer: debug-packer.log"
echo "- Vagrant: debug-vagrant.log"
```

### 2. Clean Environment

```bash
#!/bin/bash
# scripts/clean-environment.sh

set -euo pipefail

echo "Cleaning development environment..."

# Stop all VMs
vagrant global-status | grep libvirt | cut -d' ' -f1 | xargs -r vagrant destroy

# Remove test boxes
vagrant box list | grep -E "(test-|dev-)" | cut -d' ' -f1 | xargs -r vagrant box remove

# Clean libvirt
sudo virsh list --all --name | grep -E "(packer-|vagrant-)" | xargs -r sudo virsh destroy
sudo virsh list --all --name | grep -E "(packer-|vagrant-)" | xargs -r sudo virsh undefine

# Clean caches
rm -rf .vagrant/
rm -rf packer/output/
rm -rf packer/packer_cache/

echo "Environment cleaned successfully!"
```

### 3. Health Check

```bash
#!/bin/bash
# scripts/health-check.sh

set -euo pipefail

echo "Running development environment health check..."

# Check tools
echo "=== Tool Versions ==="
packer version || echo "Packer not found"
vagrant version || echo "Vagrant not found"
virsh version || echo "Libvirt not found"

# Check system
echo "=== System Status ==="
systemctl is-active libvirtd || echo "Libvirt service not running"
kvm-ok || echo "KVM not available"

# Check resources
echo "=== Resource Status ==="
df -h /
free -h
lscpu | grep -E "(CPU|Virtualization)"

# Check network
echo "=== Network Status ==="
virsh net-list --all || echo "Cannot list libvirt networks"

echo "Health check completed!"
```

This comprehensive testing framework provides robust validation for both local development and CI/CD integration, ensuring reliable and maintainable Vagrant box builds.