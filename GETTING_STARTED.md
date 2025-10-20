# Getting Started: KVM Agent Isolation System

**Welcome!** This guide will help you understand and begin implementing the KVM-based CLI agent isolation system.

## 📚 Documentation Overview

This project includes comprehensive planning documentation:

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component design
2. **[TDD_IMPLEMENTATION_PLAN.md](TDD_IMPLEMENTATION_PLAN.md)** - Test-driven development strategy
3. **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Day-by-day implementation tasks
4. **[CLAUDE.md](CLAUDE.md)** - Claude Code integration (existing)

## 🎯 Project Goal

Build a production-ready KVM/libvirt-based VM infrastructure for safely testing CLI coding agents (like Claude Code) with:

- **Hardware isolation** (KVM virtualization)
- **Network access** (NAT with filtering for API calls, git, package managers)
- **Fast iteration** (<5s reset cycles with snapshots)
- **Real-world functionality** (agents can use internet while isolated)
- **Safety guardrails** (resource limits, network filtering, monitoring)
- **TDD approach** (80%+ test coverage)

## 🏗️ What We're Building

```
┌─────────────────────────────────────────┐
│  Control Plane (Host)                   │
│  ┌────────────────────────────────┐     │
│  │ Agent Router (API/CLI)         │     │
│  │ VM Pool (pre-warmed VMs)       │     │
│  │ Lifecycle Manager (snapshots)  │     │
│  └────────────────────────────────┘     │
│                                          │
│  ┌────────────────────────────────┐     │
│  │ Observability Layer            │     │
│  │ - Prometheus metrics           │     │
│  │ - Structured audit logs        │     │
│  │ - Anomaly detection            │     │
│  └────────────────────────────────┘     │
│                                          │
├──────────────────────────────────────────┤
│  KVM Hypervisor (hardware isolation)    │
├──────────────────────────────────────────┤
│                                          │
│  ┌────────────────────────────────┐     │
│  │  Agent VM (isolated)           │     │
│  │  - 5 security layers           │     │
│  │  - virtio-vsock (control)      │     │
│  │  - virtio-9p (filesystem)      │     │
│  │  - qemu-guest-agent            │     │
│  │                                │     │
│  │  ┌──────────────────────────┐  │     │
│  │  │ Agent Execution Env      │  │     │
│  │  │ - Python, Node.js        │  │     │
│  │  │ - Dev tools              │  │     │
│  │  │ - Your agent code        │  │     │
│  │  └──────────────────────────┘  │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘
```

## 🚀 Quick Start (For Developers)

### Prerequisites

```bash
# 1. Ubuntu 24.04 with KVM support
egrep -c '(vmx|svm)' /proc/cpuinfo  # Should be > 0

# 2. Install KVM and libvirt
sudo apt update
sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients \
    bridge-utils virt-manager python3-libvirt

# 3. Add user to libvirt group
sudo usermod -a -G libvirt $USER
newgrp libvirt

# 4. Verify setup
virsh -c qemu:///system list --all

# 5. Python 3.12+
python3 --version  # Should be >= 3.12
```

### Initial Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd dev-box
git checkout kvm_switch

# 2. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Install dependencies (once project is bootstrapped)
pip install -e ".[dev]"

# 4. Verify tools work
pytest --version
mypy --version
ruff --version
```

## 📖 Understanding the Documentation

### Start Here: Architecture

Read **[ARCHITECTURE.md](ARCHITECTURE.md)** first to understand:
- Overall system design
- Component interactions
- Security model (5 layers of isolation)
- Communication channels (vsock, 9p, guest agent)
- Performance targets
- Technology choices

**Key Sections:**
- Core Components (section 1)
- Security Model (section on Defense-in-Depth)
- Agent Execution Profiles (section 8)

### Next: TDD Strategy

Read **[TDD_IMPLEMENTATION_PLAN.md](TDD_IMPLEMENTATION_PLAN.md)** to understand:
- Red-Green-Refactor approach
- Test pyramid (unit → integration → E2E)
- Code quality standards (mypy, ruff, coverage)
- Phase-by-phase test specifications
- Acceptance criteria for each component

**Key Sections:**
- Development Principles (section at top)
- Phase 1: Foundation (shows TDD pattern)
- Best Practices Enforcement (pre-commit hooks, CI/CD)

### Then: Implementation Guide

Use **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** for daily work:
- Day-by-day tasks (56 days total, 8 weeks)
- Exact commands to run
- Test-first examples
- Commit message templates
- Acceptance criteria checkboxes
- Troubleshooting tips

**Key Sections:**
- Phase 1: Foundation (Days 1-14) - START HERE
- Daily Workflow (section near end)
- Claude-Flow Integration (for parallel development)

## 🎓 Implementation Approach

### Test-Driven Development (TDD)

**Every feature follows this cycle:**

```bash
# 1. RED: Write failing test
cat > tests/unit/test_feature.py << 'EOF'
def test_feature_works():
    result = my_feature()
    assert result == expected
EOF

pytest tests/unit/test_feature.py  # Fails ❌

# 2. GREEN: Write minimal code to pass
cat > src/agent_vm/feature.py << 'EOF'
def my_feature():
    return expected
EOF

pytest tests/unit/test_feature.py  # Passes ✅

# 3. REFACTOR: Improve code quality
# Clean up, add type hints, improve performance

pytest tests/unit/test_feature.py  # Still passes ✅

# 4. COMMIT
git commit -m "feat: add feature

- Test coverage: 90%
- Type safe (mypy)

Tests: 1 passing"
```

### Quality Gates

**Every commit must pass:**
- ✅ All tests pass (`pytest tests/`)
- ✅ Type checking passes (`mypy src/`)
- ✅ Linting passes (`ruff check src/`)
- ✅ Formatting passes (`black --check .`)
- ✅ Coverage >80% (`pytest --cov`)
- ✅ Security scan clean (`bandit -r src/`)

### Phase Overview

**8 weeks, 6 phases:**

1. **Phase 1 (Weeks 1-2):** Foundation
   - Project setup
   - Libvirt abstractions
   - VM lifecycle
   - Snapshot management

2. **Phase 2 (Week 3):** Communication
   - virtio-9p filesystem
   - virtio-vsock protocol
   - Guest agent

3. **Phase 3 (Week 4):** Execution
   - Agent executor
   - Timeout enforcement
   - VM pool

4. **Phase 4 (Week 5):** Monitoring
   - Prometheus metrics
   - Audit logging
   - Anomaly detection

5. **Phase 5 (Week 6-7):** Integration
   - E2E tests
   - Performance testing
   - Concurrent execution

6. **Phase 6 (Week 8):** Polish
   - Documentation
   - Optimization
   - Security hardening

## 🛠️ Your First Task

**Start with Phase 1, Day 1: Project Bootstrap**

```bash
# 1. Read the detailed instructions
less IMPLEMENTATION_GUIDE.md
# Navigate to "Phase 1: Foundation (Days 1-14)"
# Read "Day 1-2: Project Bootstrap"

# 2. Create test file
cat > tests/test_project_structure.py << 'EOF'
# Copy test from IMPLEMENTATION_GUIDE.md Task 1.1
EOF

# 3. Run test (should fail - RED)
pytest tests/test_project_structure.py -v

# 4. Create structure (GREEN)
mkdir -p src/agent_vm/{core,network,storage,security,monitoring,execution,communication}
mkdir -p tests/{unit,integration,e2e}
# ... (follow guide)

# 5. Run test again (should pass)
pytest tests/test_project_structure.py -v

# 6. Commit
git add .
git commit -m "feat: initialize project structure with TDD

Test: test_project_structure.py"
```

## 💡 Pro Tips

### Use Claude-Flow for Parallel Work

```bash
# Initialize development swarm
/swarm-init hierarchical --max-agents=8

# Spawn specialized agents
/agent-spawn type=coder name=test-writer
/agent-spawn type=coder name=impl-writer
/agent-spawn type=reviewer name=code-reviewer

# Orchestrate parallel tasks
/task-orchestrate "Implement Phase 1 components" --strategy=parallel
```

### Daily Rhythm

1. **Morning:** Review day's tasks in IMPLEMENTATION_GUIDE.md
2. **Work:** Follow TDD cycle (Red → Green → Refactor → Commit)
3. **Afternoon:** Run full test suite, push branch
4. **Evening:** Update progress, create PR if task complete

### When Stuck

1. Check ARCHITECTURE.md for design details
2. Check TDD_IMPLEMENTATION_PLAN.md for test examples
3. Check IMPLEMENTATION_GUIDE.md for troubleshooting
4. Run tests with verbose output: `pytest -vv -s`
5. Check libvirt status: `sudo systemctl status libvirtd`

## 📊 Success Metrics

### Phase 1 Complete When:
- ✅ Test coverage >80%
- ✅ 20+ unit tests passing
- ✅ 3+ integration tests passing
- ✅ mypy strict passing
- ✅ No ruff warnings
- ✅ Can create/start/stop/snapshot VMs

### Project Complete When:
- ✅ All 6 phases complete
- ✅ E2E tests passing
- ✅ Performance benchmarks met (<2s boot, <100ms pool acquire)
- ✅ Security scan clean
- ✅ Documentation complete
- ✅ Can safely execute agent code in isolated VMs

## 🔗 Key Concepts

### Why KVM Instead of Containers?

**Hardware isolation:** True virtualization prevents escape attacks that are possible with container breakouts.

### Why TDD?

**Confidence:** Every feature has tests proving it works. Refactoring is safe because tests catch regressions.

### Why Snapshots?

**Fast iteration:** Reset VM to clean state in <5 seconds. Test agent, rollback, test again.

### Why VM Pool?

**Performance:** Pre-warmed VMs eliminate boot time. Acquire VM in <100ms instead of 2+ seconds.

### Why virtio-9p?

**Simple file exchange:** Share filesystem between host and guest. Inject agent code, extract results.

### Why virtio-vsock?

**Low-latency control:** Direct host-guest communication without network stack. Send commands, receive status.

## 📞 Getting Help

1. **Documentation:** Read ARCHITECTURE.md, TDD_IMPLEMENTATION_PLAN.md, IMPLEMENTATION_GUIDE.md
2. **Examples:** Check test files for usage examples
3. **Libvirt Docs:** https://libvirt.org/docs.html
4. **Python libvirt:** https://libvirt.org/python.html
5. **Claude-Flow:** https://github.com/williamzujkowski/claude-flow

## 🎯 Next Steps

1. ✅ **Read this file** (you're here!)
2. → **Read ARCHITECTURE.md** (30 minutes)
3. → **Skim TDD_IMPLEMENTATION_PLAN.md** (15 minutes)
4. → **Start IMPLEMENTATION_GUIDE.md Phase 1, Day 1** (4 hours)
5. → **Follow the guide day by day** (8 weeks)

## ⚡ Ready to Start?

```bash
# Let's begin!
cd dev-box
git checkout kvm_switch

# Read the architecture
less ARCHITECTURE.md

# When ready, start implementing
less IMPLEMENTATION_GUIDE.md
# Navigate to "Phase 1: Foundation (Days 1-14)"

# Good luck! 🚀
```

---

**Remember:** This is a greenfield project on the `kvm_switch` branch. We're building from scratch with best practices:
- **TDD first** (write tests before code)
- **Type safe** (mypy strict)
- **Well documented** (docstrings, guides)
- **Production ready** (monitoring, security, performance)

You've got comprehensive plans, detailed tasks, and clear acceptance criteria. Follow the guides and you'll build a robust, production-quality system! 💪
