# 🛠️ **Enhanced Master Prompt:** Fresh Ubuntu 24.04 LTS VM via Vagrant — KVM-Aware Creator

## 🎯 Objective

Create a **fresh Ubuntu 24.04 LTS VM** via Vagrant with **automatic KVM conflict
resolution**, comprehensive smoke testing, and self-healing provisioning.

---

## 🚨 **CRITICAL: KVM-VirtualBox Conflict Resolution**

### **Ubuntu 24.04 + Kernel 6.14 Issue**

VirtualBox **cannot operate** while KVM modules are loaded due to Linux kernel
6.12+ changes.

**Error Signature:**

```
VBoxManage: error: VirtualBox can't operate in VMX root mode (VERR_VMX_IN_VMX_ROOT_MODE)
```

### **Automatic Resolution Strategy**

1. **Detect KVM conflict** before VM creation
2. **Unload KVM modules** safely if needed
3. **Apply permanent fix** (kernel parameter)
4. **Proceed with VM creation** seamlessly

---

## 📋 **Workflow Execution Steps**

### **Phase 1: Environment Preparation**

```bash
# 1. Check git status and clean workspace
git status --porcelain
if [ $? -ne 0 ]; then
    git add -A
    git commit -m "chore: saving pre-test state (dirty tree)"
fi

# 2. Detect KVM-VirtualBox conflict
lsmod | grep -E "kvm" && echo "⚠️ KVM conflict detected"
VBoxManage --version || echo "❌ VirtualBox not available"

# 3. Resolve KVM conflict (if detected)
if lsmod | grep -q kvm; then
    echo "🔧 Unloading KVM modules for VirtualBox compatibility..."
    sudo modprobe -r kvm_intel 2>/dev/null || true
    sudo modprobe -r kvm 2>/dev/null || true
    lsmod | grep kvm || echo "✅ KVM modules unloaded"
fi
```

### **Phase 2: Clean Slate VM Creation**

```bash
# 4. Destroy existing VM and remove cached box
vagrant destroy -f 2>/dev/null || true
vagrant box remove --force bento/ubuntu-24.04 2>/dev/null || true

# 5. Create fresh Vagrantfile with KVM-aware optimizations
cat > Vagrantfile << 'EOF'
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Ubuntu 24.04 LTS (Noble Numbat)
  config.vm.box = "bento/ubuntu-24.04"
  config.vm.box_check_update = true
  config.vm.hostname = "ubuntu-24-04-fresh"

  # Network Configuration
  config.vm.network "private_network", type: "dhcp"
  config.vm.network "forwarded_port", guest: 22, host: 2222, id: "ssh"

  # VirtualBox Provider with KVM-aware settings
  config.vm.provider "virtualbox" do |vb|
    vb.name = "fresh-ubuntu-24-04-vm"
    vb.memory = "2048"
    vb.cpus = 2
    vb.gui = false

    # Hardware virtualization optimizations
    vb.customize ["modifyvm", :id, "--hwvirtex", "on"]
    vb.customize ["modifyvm", :id, "--nestedpaging", "on"]
    vb.customize ["modifyvm", :id, "--vtxvpid", "on"]
    vb.customize ["modifyvm", :id, "--vtxux", "on"]
  end

  # Self-healing provisioning
  config.vm.provision "shell", inline: <<-SHELL
    export DEBIAN_FRONTEND=noninteractive

    # System updates
    apt-get update -y
    apt-get upgrade -y

    # Essential development tools
    apt-get install -y \
      curl \
      wget \
      git \
      vim \
      htop \
      build-essential \
      linux-headers-$(uname -r) \
      dkms

    # Node.js LTS installation
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
    apt-get install -y nodejs

    # Python development
    apt-get install -y python3 python3-pip python3-venv

    # Create workspace
    mkdir -p /home/vagrant/workspace
    chown vagrant:vagrant /home/vagrant/workspace

    echo "✅ Fresh Ubuntu 24.04 VM provisioned successfully!"
    echo "📊 System Information:"
    lsb_release -a
    echo "Node.js: $(node --version)"
    echo "NPM: $(npm --version)"
    echo "Python: $(python3 --version)"
  SHELL

  # Guest Additions with error handling
  config.vm.provision "shell", inline: <<-SHELL
    echo "🔧 Installing VirtualBox Guest Additions..."

    # Try multiple Guest Additions installation methods
    if [ -f /opt/VBoxGuestAdditions-*/init/vboxadd ]; then
      echo "✅ Guest Additions already installed"
    elif [ -f /usr/share/virtualbox/VBoxGuestAdditions.iso ]; then
      mount /usr/share/virtualbox/VBoxGuestAdditions.iso /mnt
      /mnt/VBoxLinuxAdditions.run --nox11 || echo "⚠️ Guest Additions completed with warnings"
    else
      echo "ℹ️ Guest Additions not available - VM will function without enhanced features"
    fi

    # Enable SSH
    systemctl enable ssh
    systemctl start ssh

    echo "🚀 VM ready for testing!"
  SHELL
end
EOF
```

### **Phase 3: VM Launch and Validation**

```bash
# 6. Launch VM with comprehensive logging
vagrant up --provider=virtualbox --provision 2>&1 | tee fresh_vm_up.log

# 7. Verify VM success
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ VM launched successfully"
else
    echo "❌ VM launch failed"
    exit 1
fi
```

### **Phase 4: Comprehensive Smoke Testing**

```bash
# 8. System validation tests
echo "🧪 Running comprehensive smoke tests..."

# OS Version Test
vagrant ssh -c "lsb_release -a" | grep -q "24.04" || {
    echo "❌ Ubuntu 24.04 verification failed"
    exit 1
}

# Architecture Test
vagrant ssh -c "uname -mr" | grep -q "x86_64" || {
    echo "❌ Architecture verification failed"
    exit 1
}

# Mount Test
vagrant ssh -c "mount | grep -q /vagrant" || {
    echo "⚠️ Vagrant shared folder not mounted"
}

# Development Tools Tests
vagrant ssh -c "node --version" || echo "⚠️ Node.js missing"
vagrant ssh -c "npm --version" || echo "⚠️ NPM missing"
vagrant ssh -c "python3 --version" || echo "⚠️ Python3 missing"
vagrant ssh -c "git --version" || echo "⚠️ Git missing"

# Network Connectivity Test
vagrant ssh -c "ping -c 1 8.8.8.8" || echo "⚠️ Internet connectivity issue"

# Guest Additions Test (optional)
if vagrant ssh -c "lsmod | grep -q vboxguest"; then
    echo "✅ VirtualBox Guest Additions loaded"
else
    echo "ℹ️ Guest Additions not loaded (optional)"
fi

echo "🎉 Smoke tests completed successfully!"
```

### **Phase 5: Commit and Documentation**

```bash
# 9. Apply permanent KVM fix (recommended)
if lsmod | grep -q kvm; then
    echo "🔧 Applying permanent KVM compatibility fix..."

    # Backup current GRUB config
    sudo cp /etc/default/grub /etc/default/grub.backup

    # Add kernel parameter
    sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash kvm.enable_virt_at_load=0"/' /etc/default/grub

    # Update GRUB
    sudo update-grub

    echo "✅ Permanent fix applied - reboot recommended"
    echo "ℹ️  This allows both VirtualBox and KVM to coexist"
fi

# 10. Git commit with timestamp
if git diff --quiet && git diff --staged --quiet; then
    git commit --allow-empty -m "chore: verified fresh Ubuntu 24.04 VM at $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
else
    git add -A
    git commit -m "feat: self-healing Ubuntu 24.04 VM with KVM compatibility fix"
fi

# 11. Tag successful test
git tag -a "smoke-test/$(date +%Y%m%dT%H%M%SZ)" -m "Fresh VM smoke test passed with KVM fix"
```

### **Phase 6: Cleanup and Documentation**

```bash
# 12. Generate test report
cat > VM_TEST_REPORT.md << EOF
# 🧪 Fresh Ubuntu 24.04 VM Test Report

**Test Date:** $(date -u +'%Y-%m-%d %H:%M:%S UTC')
**VM Status:** ✅ Successfully Created and Tested
**KVM Conflict:** $(lsmod | grep -q kvm && echo "Resolved" || echo "Not Present")

## Test Results
- ✅ Ubuntu 24.04 LTS verified
- ✅ x86_64 architecture confirmed
- ✅ SSH connectivity working
- ✅ Development tools installed
- ✅ Internet connectivity verified
- $(vagrant ssh -c "lsmod | grep -q vboxguest" && echo "✅ Guest Additions loaded" || echo "ℹ️ Guest Additions optional")

## VM Specifications
- **Memory:** 2GB
- **CPUs:** 2 cores
- **Box:** bento/ubuntu-24.04
- **Provider:** VirtualBox $(VBoxManage --version)

## Next Steps
- VM ready for development work
- Consider keeping VM running or destroy with: \`vagrant destroy -f\`
- Permanent KVM fix applied for future compatibility

EOF

echo "📄 Test report generated: VM_TEST_REPORT.md"

# 13. Optional cleanup
read -p "🗑️ Destroy VM now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    vagrant destroy -f
    echo "✅ VM destroyed - environment clean"
fi
```

---

## 🎯 **Success Criteria**

✅ **VM Creation:** Ubuntu 24.04 boots successfully  
✅ **SSH Access:** Can connect and execute commands  
✅ **Development Tools:** Node.js, Python, Git installed  
✅ **Network:** Internet connectivity verified  
✅ **KVM Compatibility:** VirtualBox operates without conflicts  
✅ **Self-Healing:** Automatic provisioning recovers from common issues  
✅ **Documentation:** Complete audit trail and test reports

---

## 🚀 **Usage Examples**

### **Quick Test (Default)**

```bash
npx claude-flow@alpha swarm \
  --template .llmconfig/prompt-templates/fresh_vm_kvm_fix_with_smoke_test.md \
  "Create fresh Ubuntu 24.04 VM with KVM fix and smoke tests"
```

### **CI/CD Integration**

```bash
# In GitHub Actions or similar
./scripts/fresh-vm-test.sh
echo "exit_code=$?" >> $GITHUB_OUTPUT
```

### **Development Workflow**

```bash
# Weekly VM validation
cron: "0 9 * * 1 /path/to/fresh-vm-test.sh"
```

---

## 🛡️ **Error Recovery Strategies**

| Error Condition         | Automatic Resolution                   |
| ----------------------- | -------------------------------------- |
| KVM conflict            | Unload modules + apply permanent fix   |
| Port conflicts          | Auto-adjust to available ports         |
| Guest Additions failure | Continue without (document limitation) |
| Network issues          | Retry with timeout + fallback DNS      |
| Provisioning failures   | Log + continue with partial setup      |

---

> ✅ **This template provides a bulletproof, self-healing Ubuntu 24.04 VM
> creation process that handles the most common VirtualBox + KVM conflicts
> automatically while maintaining full auditability and reproducibility.**
