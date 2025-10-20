# KVM Agent Isolation System

**Hardware-isolated VM infrastructure for safely testing CLI coding agents**

[![Status: Planning Complete](https://img.shields.io/badge/Status-Planning%20Complete-brightgreen)]()
[![Branch: kvm_switch](https://img.shields.io/badge/Branch-kvm__switch-blue)]()
[![TDD: 80%+ Coverage](https://img.shields.io/badge/TDD-80%25%2B%20Coverage-success)]()

---

## 🎯 What This Is

A production-ready KVM/libvirt-based VM infrastructure for safely testing CLI coding agents (like Claude Code, GitHub Copilot, Aider) with:

- **Hardware Isolation** - True KVM virtualization (agents cannot escape)
- **Network Access** - NAT-filtered internet (DNS, HTTP/S, SSH for git)
- **Fast Iteration** - <5s snapshot-based reset cycles
- **Real Monitoring** - Prometheus metrics + structured audit logs
- **Production Quality** - 80%+ test coverage, type-safe, well-documented

## 🚀 Quick Start

### For First-Time Readers

**Start here:** Read [README_PROJECT_PLANS.md](README_PROJECT_PLANS.md) (3 minutes)

This is the **master overview** that explains all documentation and provides the reading order.

### For Developers

1. **Prerequisites**
   ```bash
   # Verify KVM support
   egrep -c '(vmx|svm)' /proc/cpuinfo  # Must be > 0

   # Install dependencies
   sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils python3-libvirt

   # Add user to libvirt group
   sudo usermod -a -G libvirt $USER
   newgrp libvirt
   ```

2. **Read the documentation in order:**
   - [README_PROJECT_PLANS.md](README_PROJECT_PLANS.md) - Start here! (3 min)
   - [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start guide (10 min)
   - [ARCHITECTURE.md](ARCHITECTURE.md) - Complete system design (30 min)
   - [TDD_IMPLEMENTATION_PLAN.md](TDD_IMPLEMENTATION_PLAN.md) - Test strategy (20 min)
   - [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Day-by-day tasks (reference)

3. **Start implementing:**
   ```bash
   git checkout kvm_switch
   source venv/bin/activate

   # Follow IMPLEMENTATION_GUIDE.md starting at Phase 1, Day 1
   ```

### For AI Assistants (Claude Code)

**Read [CLAUDE.md](CLAUDE.md)** - Complete context for AI assistants working in this repository.

---

## 📚 Documentation Overview

### Essential Documents (Read in Order)

| Document | Purpose | Time | Status |
|----------|---------|------|--------|
| **[README_PROJECT_PLANS.md](README_PROJECT_PLANS.md)** | Master overview and reading guide | 3 min | ✅ Complete |
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | Quick start for developers | 10 min | ✅ Complete |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Complete system design | 30 min | ✅ Complete |
| **[TDD_IMPLEMENTATION_PLAN.md](TDD_IMPLEMENTATION_PLAN.md)** | Test-driven development strategy | 20 min | ✅ Complete |
| **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** | Day-by-day implementation tasks | Reference | ✅ Complete |

### Supporting Documents

| Document | Purpose |
|----------|---------|
| **[CLAUDE.md](CLAUDE.md)** | Context for AI assistants |
| **[NETWORK_CONFIG_GUIDE.md](NETWORK_CONFIG_GUIDE.md)** | Network setup and security guide |
| **[NETWORK_UPDATE_SUMMARY.md](NETWORK_UPDATE_SUMMARY.md)** | Quick network changes summary |
| **[CHANGES_FROM_ORIGINAL_PLAN.md](CHANGES_FROM_ORIGINAL_PLAN.md)** | Design change log and rationale |

---

## 🏗️ What We're Building

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

### Key Features

- ✅ **Hardware Isolation** - KVM prevents VM escape attacks
- ✅ **Network Access** - Agents can use APIs, git, package managers (filtered)
- ✅ **Fast Snapshots** - Reset to clean state in <5 seconds
- ✅ **VM Pool** - Pre-warmed VMs for <100ms acquisition
- ✅ **Monitoring** - Prometheus metrics + anomaly detection
- ✅ **Audit Logs** - Structured JSON logging of all operations
- ✅ **Type Safety** - mypy strict mode + 80%+ test coverage
- ✅ **TDD First** - Write tests before code (Red-Green-Refactor)

### Network Configuration

**Default:** NAT-filtered network (controlled internet access)

**Why?** Modern CLI agents (Claude CLI, Copilot, etc.) require network access to function.

**Security:** Despite network access, VMs are isolated through:
- Hardware isolation (KVM - cannot escape)
- Network filtering (whitelist: DNS, HTTP/S, SSH)
- No incoming connections (only responses)
- All traffic logged and monitored
- Resource limits enforced

**For untrusted code:** Use `NetworkMode.ISOLATED` explicitly.

---

## 🛠️ Technology Stack

- **Language:** Python 3.12+ (async/await, strict type hints)
- **Virtualization:** libvirt 9.0+ with QEMU/KVM 8.0+
- **Testing:** pytest + pytest-asyncio + pytest-cov
- **Type Checking:** mypy (strict mode)
- **Linting:** ruff, black
- **Security:** bandit, trivy
- **Monitoring:** Prometheus + Grafana
- **Logging:** structlog

---

## 📊 Project Status

### Current Status: Planning Complete ✅

All planning and architecture documentation is complete. Ready for implementation.

### Implementation Phases (8 Weeks)

1. **Phase 1: Foundation** (Weeks 1-2) - Core libvirt abstractions ⏭️ START HERE
2. **Phase 2: Communication** (Week 3) - Host-guest channels
3. **Phase 3: Execution** (Week 4) - Agent executor + VM pool
4. **Phase 4: Monitoring** (Week 5) - Metrics + audit logs
5. **Phase 5: Integration** (Weeks 6-7) - E2E tests + performance
6. **Phase 6: Polish** (Week 8) - Optimization + security hardening

### Success Criteria

**Phase 1 Complete When:**
- ✅ Test coverage >80%
- ✅ 20+ unit tests passing
- ✅ 3+ integration tests passing
- ✅ mypy strict passing
- ✅ Can create/start/stop/snapshot VMs

**Project Complete When:**
- ✅ All 6 phases complete
- ✅ E2E tests passing
- ✅ Performance benchmarks met
- ✅ Security scan clean
- ✅ Documentation complete

---

## 🎓 Development Approach

### Test-Driven Development (TDD)

**Every feature follows RED → GREEN → REFACTOR:**

1. **RED:** Write failing test first
2. **GREEN:** Write minimal code to pass
3. **REFACTOR:** Improve code quality
4. **COMMIT:** Commit after each cycle

### Quality Gates (Must Pass)

Every commit must pass:
- ✅ All tests (`pytest tests/`)
- ✅ Type checking (`mypy src/`)
- ✅ Linting (`ruff check src/`)
- ✅ Formatting (`black --check .`)
- ✅ Coverage >80% (`pytest --cov`)
- ✅ Security scan (`bandit -r src/`)

---

## 💡 Usage Example

```python
from agent_vm.core.connection import LibvirtConnection
from agent_vm.core.template import VMTemplate, ResourceProfile
from agent_vm.core.vm import VM

# Connect to libvirt
with LibvirtConnection() as conn:
    # Create VM template (NAT-filtered by default)
    template = VMTemplate(
        name="claude-cli-vm",
        resources=ResourceProfile(vcpu=2, memory_mib=2048)
    )

    # Define and start VM
    domain = conn.connection.defineXML(template.generate_xml())
    vm = VM(domain)
    vm.start()
    await vm.wait_for_ready()

    # Execute agent code
    result = await executor.execute(vm, agent_code)

    # Cleanup
    vm.stop()
```

---

## 🤝 Contributing

This is a greenfield project on the `kvm_switch` branch. To contribute:

1. **Follow TDD approach** - Write tests first
2. **Meet quality gates** - Tests, types, lint, coverage
3. **Use clear commit messages** - Conventional Commits format
4. **Update documentation** - Keep docs in sync with code
5. **Reference line numbers** - Use `file_path:line_number` format

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.

---

## 📞 Getting Help

1. **Read documentation first:**
   - Start with [README_PROJECT_PLANS.md](README_PROJECT_PLANS.md)
   - Then [GETTING_STARTED.md](GETTING_STARTED.md)
   - Check [ARCHITECTURE.md](ARCHITECTURE.md) for design details
   - See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for tasks

2. **External resources:**
   - libvirt docs: https://libvirt.org/docs.html
   - Python libvirt: https://libvirt.org/python.html
   - QEMU/KVM: https://www.qemu.org/docs/

---

## 📜 License

[Include your license here]

---

## 🎯 Next Steps

### If This is Your First Time Here:

1. ✅ **Read [README_PROJECT_PLANS.md](README_PROJECT_PLANS.md)** (3 minutes)
2. ⏭️ **Read [GETTING_STARTED.md](GETTING_STARTED.md)** (10 minutes)
3. ⏭️ **Skim [ARCHITECTURE.md](ARCHITECTURE.md)** (30 minutes)
4. ⏭️ **Review [TDD_IMPLEMENTATION_PLAN.md](TDD_IMPLEMENTATION_PLAN.md)** (20 minutes)
5. ⏭️ **Start [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) Phase 1, Day 1**

### If You're Ready to Code:

```bash
git checkout kvm_switch
source venv/bin/activate
pip install -e ".[dev]"

# Read day-by-day tasks
less IMPLEMENTATION_GUIDE.md
# Navigate to "Phase 1: Foundation (Days 1-14)"

# Start with TDD!
# Write tests first, then make them pass
```

---

**All planning is complete. Time to build! 🚀**

*Generated with comprehensive planning documentation. See [README_PROJECT_PLANS.md](README_PROJECT_PLANS.md) for details.*
