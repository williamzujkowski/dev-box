# Developer Guide: KVM Agent Isolation System

**Version:** 1.0.0
**Status:** Phase 5 Complete (424/436 tests passing, 92.04% coverage)

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Development Setup](#development-setup)
4. [Testing Strategy](#testing-strategy)
5. [Code Organization](#code-organization)
6. [Development Workflow](#development-workflow)
7. [Code Patterns and Conventions](#code-patterns-and-conventions)
8. [Contributing Guidelines](#contributing-guidelines)
9. [Quality Gates](#quality-gates)
10. [Common Development Tasks](#common-development-tasks)

---

## Introduction

This guide provides comprehensive information for developers working on the KVM Agent Isolation System. The project follows Test-Driven Development (TDD) with strict quality standards.

### Project Goals

- **Hardware Isolation**: Use KVM/libvirt for true VM isolation
- **Real Functionality**: Enable internet access with network filtering
- **Fast Iteration**: <5s snapshot-based reset cycles
- **Production Quality**: 80%+ test coverage, type safety, monitoring

### Key Metrics (Phase 5 Complete)

- **Tests**: 424/436 passing (97.25%)
- **Coverage**: 92.04%
- **Type Safety**: mypy strict mode
- **Code Quality**: ruff linting, black formatting

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────┐
│  Control Plane (Host)               │
│  ├─ Agent Router (API/CLI)          │
│  ├─ VM Pool (pre-warmed VMs)        │
│  ├─ Lifecycle Manager (snapshots)   │
│  ├─ Metrics (Prometheus)            │
│  └─ Audit Logger (structured logs)  │
├─────────────────────────────────────┤
│  KVM/libvirt (hardware isolation)   │
├─────────────────────────────────────┤
│  Agent VM (NAT-filtered network)    │
│  ├─ 5 security layers               │
│  ├─ virtio-vsock (control channel)  │
│  ├─ virtio-9p (filesystem sharing)  │
│  ├─ qemu-guest-agent (monitoring)   │
│  └─ Agent execution environment     │
└─────────────────────────────────────┘
```

### Core Components

**See ARCHITECTURE.md for detailed design specifications**

1. **Core Layer** (`src/agent_vm/core/`)
   - `connection.py`: libvirt connection management
   - `vm.py`: VM lifecycle and state management
   - `template.py`: VM XML generation
   - `snapshot.py`: Snapshot operations

2. **Communication Layer** (`src/agent_vm/communication/`)
   - `filesystem.py`: virtio-9p file sharing
   - `vsock.py`: virtio-vsock control channel
   - `guest_agent.py`: Guest agent protocol

3. **Execution Layer** (`src/agent_vm/execution/`)
   - `executor.py`: Agent code execution
   - `pool.py`: VM pool management

4. **Monitoring Layer** (`src/agent_vm/monitoring/`)
   - `metrics.py`: Prometheus metrics
   - `audit.py`: Structured audit logging
   - `anomaly.py`: Behavioral analysis

### Technology Stack

- **Language**: Python 3.12+ (async/await, strict type hints)
- **Virtualization**: libvirt 9.0+ with QEMU/KVM 8.0+
- **Testing**: pytest + pytest-asyncio + pytest-cov
- **Type Checking**: mypy (strict mode)
- **Linting**: ruff, black
- **Security**: bandit
- **Monitoring**: Prometheus + structlog

---

## Development Setup

### Prerequisites

```bash
# 1. Verify KVM support
egrep -c '(vmx|svm)' /proc/cpuinfo  # Must be > 0

# 2. Install system dependencies
sudo apt install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils \
    python3-libvirt \
    python3.12 \
    python3.12-venv

# 3. Add user to libvirt group
sudo usermod -a -G libvirt $USER
newgrp libvirt

# 4. Verify libvirt
virsh -c qemu:///system list --all
```

### Initial Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd dev-box
git checkout kvm_switch

# 2. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip setuptools wheel

# 4. Install package in development mode
pip install -e ".[dev]"

# 5. Verify installation
pytest --version
mypy --version
ruff --version
black --version
```

### IDE Configuration

#### VS Code

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.analysis.typeCheckingMode": "strict",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

1. Configure Python interpreter: `venv/bin/python`
2. Enable pytest: Settings → Tools → Python Integrated Tools → Testing
3. Configure mypy: Settings → Tools → External Tools
4. Enable Black formatter: Settings → Tools → Black
5. Enable Ruff: Settings → Tools → External Tools

---

## Testing Strategy

### Test Pyramid

The project follows a balanced test pyramid:

- **Unit Tests** (70%): Fast, isolated tests in `tests/unit/`
- **Integration Tests** (20%): Component interaction in `tests/integration/`
- **E2E Tests** (10%): Full workflows in `tests/e2e/`

### Test-Driven Development (TDD)

**Every feature follows RED → GREEN → REFACTOR:**

```bash
# 1. RED: Write failing test
cat > tests/unit/test_feature.py << 'EOF'
def test_feature_works():
    result = my_feature()
    assert result == expected
EOF

pytest tests/unit/test_feature.py  # Should FAIL ❌

# 2. GREEN: Write minimal code to pass
cat > src/agent_vm/feature.py << 'EOF'
def my_feature():
    return expected
EOF

pytest tests/unit/test_feature.py  # Should PASS ✅

# 3. REFACTOR: Improve code quality
# Add type hints, docstrings, optimize
pytest tests/unit/test_feature.py  # Should still PASS ✅

# 4. COMMIT: After each green test
git commit -m "feat: add feature

- Implements X functionality
- Tests: 1 passing
- Coverage: 90%"
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests (requires KVM)
pytest tests/integration/ -v

# E2E tests (full workflows)
pytest tests/e2e/ -v

# With coverage report
pytest tests/ --cov --cov-report=html
open htmlcov/index.html

# Specific test file
pytest tests/unit/test_connection.py -v

# Specific test function
pytest tests/unit/test_connection.py::TestLibvirtConnection::test_connection_opens -v

# With debugging
pytest tests/unit/test_connection.py --pdb

# Show print statements
pytest tests/unit/test_connection.py -v -s
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from unittest.mock import Mock, patch
from agent_vm.core.vm import VM, VMState

class TestVM:
    """Test VM abstraction layer"""

    def test_vm_start_creates_domain(self):
        """Starting VM calls domain.create()"""
        # Arrange
        mock_domain = Mock()
        mock_domain.isActive.return_value = False
        vm = VM(mock_domain)

        # Act
        vm.start()

        # Assert
        mock_domain.create.assert_called_once()

    def test_vm_get_state_returns_running(self):
        """get_state returns RUNNING when domain is active"""
        # Arrange
        mock_domain = Mock()
        mock_domain.state.return_value = [1, 1]  # VIR_DOMAIN_RUNNING
        vm = VM(mock_domain)

        # Act
        state = vm.get_state()

        # Assert
        assert state == VMState.RUNNING
```

#### Integration Test Example

```python
import pytest
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.template import VMTemplate
from agent_vm.core.vm import VM, VMState

@pytest.mark.integration
def test_vm_lifecycle():
    """Test complete VM lifecycle: create, start, stop, destroy"""
    # Arrange
    conn = LibvirtConnection()
    conn.open()

    template = VMTemplate(name="test-vm")
    domain = conn.connection.defineXML(template.generate_xml())
    vm = VM(domain)

    try:
        # Act & Assert: Start
        vm.start()
        assert vm.get_state() == VMState.RUNNING

        # Act & Assert: Stop
        vm.stop(graceful=False)
        assert vm.get_state() == VMState.SHUTOFF

    finally:
        # Cleanup
        if domain.isActive():
            domain.destroy()
        domain.undefine()
        conn.close()
```

#### Async Test Example

```python
import pytest
from agent_vm.core.vm import VM, VMState

@pytest.mark.asyncio
async def test_vm_wait_for_state():
    """VM waits for desired state"""
    # Arrange
    mock_domain = Mock()
    mock_domain.state.side_effect = [
        [4, 0],  # SHUTDOWN
        [4, 0],  # SHUTDOWN
        [1, 1],  # RUNNING
    ]
    vm = VM(mock_domain)

    # Act
    await vm.wait_for_state(VMState.RUNNING, timeout=5)

    # Assert
    assert mock_domain.state.call_count == 3
```

---

## Code Organization

### Project Structure

```
dev-box/
├── src/agent_vm/              # Main package
│   ├── __init__.py
│   ├── core/                  # Core abstractions
│   │   ├── __init__.py
│   │   ├── connection.py      # libvirt connection
│   │   ├── vm.py              # VM lifecycle
│   │   ├── template.py        # XML generation
│   │   └── snapshot.py        # Snapshot management
│   ├── communication/         # Host-guest communication
│   │   ├── __init__.py
│   │   ├── filesystem.py      # virtio-9p
│   │   ├── vsock.py           # virtio-vsock
│   │   └── guest_agent.py     # Guest agent protocol
│   ├── execution/             # Agent execution
│   │   ├── __init__.py
│   │   ├── executor.py        # AgentExecutor
│   │   └── pool.py            # VMPool
│   ├── monitoring/            # Observability
│   │   ├── __init__.py
│   │   ├── metrics.py         # Prometheus metrics
│   │   ├── audit.py           # Audit logging
│   │   └── anomaly.py         # Anomaly detection
│   ├── network/               # Network configuration
│   ├── storage/               # Storage management
│   └── security/              # Security policies
│
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── unit/                  # Unit tests (fast)
│   │   ├── test_connection.py
│   │   ├── test_vm.py
│   │   ├── test_template.py
│   │   ├── test_snapshot.py
│   │   ├── test_executor.py
│   │   └── test_vm_pool.py
│   ├── integration/           # Integration tests
│   │   ├── test_vm_lifecycle.py
│   │   ├── test_communication.py
│   │   └── test_workflows.py
│   └── e2e/                   # End-to-end tests
│       └── test_benchmarks.py
│
├── docs/                      # Documentation
│   ├── api/                   # Generated API docs
│   ├── USER_GUIDE.md
│   └── DEVELOPER_GUIDE.md
│
├── pyproject.toml             # Project configuration
├── README.md
├── ARCHITECTURE.md
├── TDD_IMPLEMENTATION_PLAN.md
└── IMPLEMENTATION_GUIDE.md
```

### Module Organization

Each module follows this pattern:

```python
# module.py
"""Module docstring explaining purpose"""

from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

class MyClass:
    """Class docstring with examples

    Example:
        >>> obj = MyClass()
        >>> obj.method()
    """

    def __init__(self, param: str) -> None:
        """Initialize instance

        Args:
            param: Parameter description

        Raises:
            ValueError: If param is invalid
        """
        self._param = param

    def method(self) -> str:
        """Method docstring

        Returns:
            Result description
        """
        return self._param
```

---

## Development Workflow

### Daily Workflow

```bash
# 1. Start of day
git checkout kvm_switch
git pull origin kvm_switch

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Write test (RED)
cat > tests/unit/test_my_feature.py << 'EOF'
def test_my_feature():
    assert my_feature() == expected
EOF

pytest tests/unit/test_my_feature.py  # Fails ❌

# 4. Implement feature (GREEN)
cat > src/agent_vm/my_feature.py << 'EOF'
def my_feature():
    return expected
EOF

pytest tests/unit/test_my_feature.py  # Passes ✅

# 5. Run all quality checks
pytest tests/ --cov
mypy src/
ruff check src/
black --check .

# 6. Commit
git add .
git commit -m "feat: add my feature

- Description of feature
- Tests: X passing
- Coverage: Y%"

# 7. Push and create PR
git push origin feature/my-feature
gh pr create --title "feat: add my feature"
```

### Git Workflow

#### Branch Strategy

- `main`: Stable releases
- `kvm_switch`: Active development
- `feature/*`: Feature branches

#### Commit Message Format (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

**Examples**:

```
feat(core): add VM snapshot management

- Create, restore, list, delete snapshots
- Internal snapshots for speed
- Metadata tracking

Tests: 4 passing
Coverage: 90%

Implements: #123
```

```
fix(executor): handle timeout correctly

- Fix timeout enforcement in AgentExecutor
- Add test for timeout edge cases

Tests: 2 passing
Fixes: #456
```

---

## Code Patterns and Conventions

### Type Hints (Strict mypy)

All code must have complete type hints:

```python
from typing import Optional, List, Dict, Any
from pathlib import Path

def create_vm(
    name: str,
    memory_mib: int = 2048,
    disk_path: Optional[Path] = None
) -> VM:
    """Create new VM

    Args:
        name: VM name
        memory_mib: Memory in MiB
        disk_path: Optional disk path

    Returns:
        Created VM instance

    Raises:
        VMError: If creation fails
    """
    pass
```

### Async/Await

All I/O operations must be async:

```python
import asyncio

class VM:
    async def start(self) -> None:
        """Start VM and wait for ready state"""
        self._domain.create()
        await self.wait_for_state(VMState.RUNNING)

    async def wait_for_state(
        self,
        desired: VMState,
        timeout: float = 30.0
    ) -> None:
        """Wait for VM to reach desired state"""
        start = asyncio.get_event_loop().time()
        while True:
            if self.get_state() == desired:
                return
            if asyncio.get_event_loop().time() - start > timeout:
                raise VMError(f"Timeout waiting for {desired}")
            await asyncio.sleep(0.5)
```

### Error Handling

Use specific exceptions with context:

```python
# Define specific exceptions
class VMError(Exception):
    """VM operation error"""
    pass

class SnapshotError(Exception):
    """Snapshot operation error"""
    pass

# Use specific exceptions
try:
    vm.start()
except libvirt.libvirtError as e:
    logger.error("vm_start_failed", vm=vm.name, error=str(e))
    raise VMError(f"Failed to start VM: {e}") from e
```

### Structured Logging

Use structlog for all logging:

```python
import structlog

logger = structlog.get_logger(__name__)

class VM:
    def __init__(self, domain):
        self._domain = domain
        self._logger = logger.bind(vm_name=self.name, vm_uuid=self.uuid)

    def start(self):
        self._logger.info("vm_starting")
        try:
            self._domain.create()
            self._logger.info("vm_started")
        except Exception as e:
            self._logger.error("vm_start_failed", error=str(e))
            raise
```

### Docstrings (Google Style)

All public functions, classes, and modules must have docstrings:

```python
def create_snapshot(self, vm: VM, name: str, description: str = "") -> Snapshot:
    """Create VM snapshot

    Creates an internal snapshot of the VM's current state for fast restore.

    Args:
        vm: VM to snapshot
        name: Snapshot name (must be unique)
        description: Optional human-readable description

    Returns:
        Created snapshot object

    Raises:
        SnapshotError: If creation fails
        ValueError: If name is invalid

    Example:
        >>> snapshot = manager.create_snapshot(vm, "clean-state")
        >>> vm.do_something()
        >>> manager.restore_snapshot(vm, snapshot)
    """
    pass
```

---

## Contributing Guidelines

### Before Starting

1. **Read Documentation**
   - ARCHITECTURE.md for system design
   - TDD_IMPLEMENTATION_PLAN.md for test strategy
   - IMPLEMENTATION_GUIDE.md for specific tasks

2. **Check Issues**
   - Look for open issues to work on
   - Comment on issue to claim it
   - Discuss approach before implementing

3. **Create Feature Branch**
   ```bash
   git checkout kvm_switch
   git pull origin kvm_switch
   git checkout -b feature/my-feature
   ```

### During Development

1. **Write Tests First** (TDD)
   - Write failing test
   - Implement minimal code
   - Refactor while keeping tests green

2. **Follow Code Standards**
   - Type hints required
   - Docstrings required
   - Async/await for I/O
   - Structured logging

3. **Run Quality Checks**
   ```bash
   pytest tests/ --cov
   mypy src/
   ruff check src/
   black .
   ```

### Pull Request Process

1. **Before Creating PR**
   ```bash
   # Ensure all tests pass
   pytest tests/ -v

   # Check coverage
   pytest tests/ --cov --cov-fail-under=80

   # Type check
   mypy src/ --strict

   # Lint
   ruff check src/

   # Format
   black .

   # Security scan
   bandit -r src/
   ```

2. **Create PR**
   ```bash
   git push origin feature/my-feature
   gh pr create --title "feat: my feature" --body "Description"
   ```

3. **PR Description Template**
   ```markdown
   ## Summary
   Brief description of changes

   ## Changes
   - List of specific changes
   - With bullet points

   ## Testing
   - [ ] Unit tests passing
   - [ ] Integration tests passing
   - [ ] Coverage >80%

   ## Checklist
   - [ ] Tests written (TDD)
   - [ ] Type hints added
   - [ ] Docstrings updated
   - [ ] All quality gates pass

   ## Related Issues
   Closes #123
   ```

4. **Review Process**
   - Address review comments
   - Keep commits clean
   - Squash if needed
   - Wait for approval

---

## Quality Gates

### Pre-Commit Checks

All commits must pass:

```bash
# Tests
pytest tests/ -v

# Type checking
mypy src/ --strict

# Linting
ruff check src/

# Formatting
black --check .

# Coverage
pytest tests/ --cov --cov-fail-under=80

# Security
bandit -r src/
```

### Continuous Integration

GitHub Actions runs on every push:

```yaml
# .github/workflows/ci.yml
- pytest tests/ --cov --cov-fail-under=80
- mypy src/ --strict
- ruff check src/
- black --check .
- bandit -r src/
```

### Pre-Commit Hooks (Optional)

Install pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Hooks will run on git commit
git commit -m "feat: add feature"  # Runs all checks
```

---

## Common Development Tasks

### Adding a New Component

```bash
# 1. Create test file
cat > tests/unit/test_new_component.py << 'EOF'
from agent_vm.new_component import NewComponent

def test_new_component_initialization():
    component = NewComponent()
    assert component is not None
EOF

# 2. Run test (should fail)
pytest tests/unit/test_new_component.py -v

# 3. Create component
cat > src/agent_vm/new_component.py << 'EOF'
"""New component for X functionality"""

class NewComponent:
    """Component docstring"""
    pass
EOF

# 4. Run test (should pass)
pytest tests/unit/test_new_component.py -v

# 5. Add more tests and functionality
# Continue TDD cycle
```

### Debugging Tests

```bash
# Run with verbose output
pytest tests/unit/test_vm.py -vv -s

# Run with pdb debugger
pytest tests/unit/test_vm.py --pdb

# Show local variables
pytest tests/unit/test_vm.py -vv --showlocals

# Only run failed tests
pytest tests/unit/test_vm.py --lf

# Run specific test
pytest tests/unit/test_vm.py::TestVM::test_vm_start -v
```

### Type Checking

```bash
# Check all code
mypy src/

# Check specific file
mypy src/agent_vm/core/vm.py

# Show error context
mypy src/ --show-error-codes --show-error-context

# Generate HTML report
mypy src/ --html-report mypy-report
open mypy-report/index.html
```

### Code Formatting

```bash
# Format all code
black .

# Check without changing
black --check .

# Format specific file
black src/agent_vm/core/vm.py

# Show diff
black --diff .
```

### Linting

```bash
# Lint all code
ruff check src/

# Auto-fix issues
ruff check src/ --fix

# Show all errors
ruff check src/ --show-source
```

### Coverage Analysis

```bash
# Generate HTML coverage report
pytest tests/ --cov --cov-report=html

# Open in browser
open htmlcov/index.html

# Show missing lines
pytest tests/ --cov --cov-report=term-missing

# Check specific threshold
pytest tests/ --cov --cov-fail-under=90
```

### Working with libvirt

```bash
# List VMs
virsh list --all

# Start VM
virsh start <vm-name>

# Stop VM
virsh shutdown <vm-name>

# Force stop
virsh destroy <vm-name>

# Delete VM
virsh undefine <vm-name>

# VM info
virsh dominfo <vm-name>

# Snapshots
virsh snapshot-list <vm-name>
virsh snapshot-create <vm-name>
virsh snapshot-revert <vm-name> <snapshot-name>

# Networks
virsh net-list --all
virsh net-info agent-nat-filtered

# Filters
virsh nwfilter-list
virsh nwfilter-dumpxml agent-network-filter
```

---

## Additional Resources

### Documentation

- **ARCHITECTURE.md**: Complete system design
- **TDD_IMPLEMENTATION_PLAN.md**: Test strategy and examples
- **IMPLEMENTATION_GUIDE.md**: Day-by-day implementation tasks
- **CLAUDE.md**: AI assistant integration guide

### External Resources

- **libvirt Documentation**: https://libvirt.org/docs.html
- **Python libvirt**: https://libvirt.org/python.html
- **QEMU/KVM**: https://www.qemu.org/docs/
- **pytest**: https://docs.pytest.org/
- **mypy**: https://mypy.readthedocs.io/
- **structlog**: https://www.structlog.org/

### Community

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Pull Requests**: Contribute code improvements

---

**Ready to Contribute?**

1. Read ARCHITECTURE.md for system understanding
2. Set up development environment
3. Find an issue to work on
4. Follow TDD approach
5. Submit pull request

**Questions?**

- Check documentation first
- Search existing issues
- Ask in GitHub Discussions
- Review test files for examples
