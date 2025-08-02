# 🎯 Prompt Templates Directory

This directory contains master prompt templates for automated testing and
development workflows.

## 📁 Available Templates

### 1. `repeat_fresh_vm_test.md`

**Purpose:** Reproducible Ubuntu 24.04 VM testing with self-healing provisioning

**Key Features:**

- Clean slate VM creation (destroy + fresh box)
- Comprehensive smoke testing (17+ validation points)
- Self-healing Guest Additions installation
- Git integration with timestamped commits
- Immutable infrastructure validation

**Usage:**

```bash
npx claude-flow@alpha swarm \
  --template .llmconfig/prompt-templates/repeat_fresh_vm_test.md \
  "Verify fresh Ubuntu 24.04 Vagrant box and dev-tool smoke-tests"
```

### 2. `fresh_vm_kvm_fix_with_smoke_test.md`

**Purpose:** Enhanced VM creation with automatic KVM conflict resolution

**Key Features:**

- **KVM-VirtualBox conflict detection and resolution**
- Automatic kernel parameter fixes for Ubuntu 24.04
- Comprehensive development environment setup
- Network connectivity validation
- Performance optimization settings

**Usage:**

```bash
npx claude-flow@alpha swarm \
  --template .llmconfig/prompt-templates/fresh_vm_kvm_fix_with_smoke_test.md \
  "Create fresh Ubuntu 24.04 VM with KVM fix and smoke tests"
```

### 3. `use_vagrant_libvirt_fresh_vm.md`

**Purpose:** Native KVM/libvirt provider alternative to VirtualBox

**Key Features:**

- **Direct KVM/QEMU integration via libvirt**
- Complete bypass of VirtualBox + KVM conflicts
- Superior performance with native virtualization
- Self-healing libvirt plugin installation
- Comprehensive hypervisor validation

**Usage:**

```bash
npx claude-flow@alpha swarm \
  --template .llmconfig/prompt-templates/use_vagrant_libvirt_fresh_vm.md \
  "Create Ubuntu 24.04 VM using native KVM/libvirt provider"
```

### 4. `provision_dev_toolchain.md`

**Purpose:** Complete development toolchain provisioning for Vagrant VMs

**Key Features:**

- **Claude Code CLI + GitHub CLI** integration
- **Python toolchain:** uv + ruff for modern development
- **Infrastructure as Code:** Terraform + TFLint + tfsec
- **Container linting:** Hadolint for Dockerfile validation
- **JavaScript/TypeScript:** ESLint + Prettier + TypeScript
- **Modern CLI tools:** fd, ripgrep, bat, exa
- **Comprehensive validation** and self-healing installation

**Usage:**

```bash
npx claude-flow@alpha swarm \
  --template .llmconfig/prompt-templates/provision_dev_toolchain.md \
  "Add Claude‑CLI, gh, ruff, terraform toolchain in Vagrant dev box"
```

## 🎯 Standards Alignment

All templates follow project standards:

| Standard                     | Implementation                                 |
| ---------------------------- | ---------------------------------------------- |
| **Reproducibility**          | Fresh box downloads, clean environment testing |
| **Self-healing**             | Automatic error recovery and fix commits       |
| **Auditability**             | Timestamped commits, comprehensive logging     |
| **Immutable Infrastructure** | Bit-for-bit reproducible environments          |
| **Clean Git History**        | Only meaningful commits with clear messages    |

## 🚀 Integration with Development Workflow

### CI/CD Pipeline Integration

```yaml
# .github/workflows/vm-validation.yml
- name: Validate VM Infrastructure
  run: |
    npx claude-flow@alpha swarm \
      --template .llmconfig/prompt-templates/repeat_fresh_vm_test.md \
      "Weekly VM infrastructure validation"
```

### Manual Testing

```bash
# Navigate to project root
cd /home/william/git/dev-box

# Execute manual test script
./scripts/execute-fresh-vm-test.sh
```

## 🚨 Known Issues and Solutions

### Ubuntu 24.04 + VirtualBox + KVM

**Issue:** `VERR_VMX_IN_VMX_ROOT_MODE` error  
**Solution 1:** Automatic KVM module unloading in templates  
**Solution 2:** Use libvirt provider instead
(`use_vagrant_libvirt_fresh_vm.md`)  
**Permanent Fix:** Kernel parameter `kvm.enable_virt_at_load=0`

### Libvirt Provider Benefits

**Performance:** Native KVM integration without VirtualBox overhead  
**Compatibility:** No conflicts with KVM modules  
**Reliability:** Purpose-built for Linux KVM/QEMU virtualization

---

_These templates provide a robust foundation for reproducible VM testing and
development environment management._
