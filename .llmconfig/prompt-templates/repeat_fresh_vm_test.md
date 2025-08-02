# 🧪 🎯 Slave Agent Instructions — Fresh VM Smoke Test

## Objective

Ensure that `ubuntu-24.04` is reproducibly provisioned via Vagrant + VirtualBox.
Self-healing and commit interoperability as-needed.

## Workflow Steps

### 1. Bootstrapping

- `git status --porcelain` → should be clean; if changes are detected, **stage
  and commit** with message:  
  `chore: saving pre‑test state (dirty tree)`
- Switch to a working clean state:  
  `git checkout -- .` (abortable if no clean tree)

### 2. Clean Slate

- If a Vagrant machine exists in project root:  
  `vagrant destroy -f`
- Remove local box `'bento/ubuntu-24.04'` to test fresh box install:  
  `vagrant box remove --force bento/ubuntu-24.04 || true`

### 3. Test Provision

- Run `vagrant up --provider=virtualbox --provision`
- Record outcome to `fresh_vm_up.log`
- Verify exit status: must be zero for success
- SSH test:
  - `vagrant ssh -c "lsb_release -a"` → must contain: `Release: 24.04`
  - `vagrant ssh -c "uname -mr"` → must return `x86_64` architecture
  - `vagrant ssh -c "grep -c '^/vagrant' /proc/mounts"` → should show `/vagrant`
    mount

### 4. Guest Additions Check

- Within VM, check:

```bash
vagrant ssh -c "if ! lsmod | grep -q vboxguest; then echo 'NO_GUEST_ADDITIONS'; fi"
```

- If **NO_GUEST_ADDITIONS**, attempt:
- `vagrant ssh` →
  `wget -O /tmp/VBoxGuestAdditions.iso https://download.virtualbox.org/virtualbox/7.1.12/VBoxGuestAdditions_7.1.12.iso`
- Mount and install:
  ```bash
  sudo mount /tmp/VBoxGuestAdditions.iso /mnt
  sudo apt update
  sudo apt install -y build-essential dkms linux-headers-$(uname -r)
  sudo sh /mnt/VBoxLinuxAdditions.run || true
  sudo reboot
  ```
- Post-reboot, re-run `lsmod | grep vboxguest || exit 1`
- If successful, add fallback installation logic to `Vagrantfile` (Commit patch)

### 5. Additional Smoke Tests

```bash
vagrant ssh -c "node --version || echo 'NODE_MISSING'"
vagrant ssh -c "npm -v || echo 'NPM_MISSING'"
vagrant ssh -c "python3 -V || echo 'PYTHON_MISSING'"
```

If any are missing, the provisioning should attempt to install them (alongside
`curl`, `git`, `htop`), re-run those commands; failures automatically trigger a
commit with fix details.

### 6. Commit and Tag

- If `vagrant up` failed and the script completed self-healing:
  - `git add Vagrantfile`
  - `git commit -m "fix: self‑heal missing guest additions/live‑install dev tools"`
- If VM is clean and tests pass without changes:
  - `git commit --allow-empty -m "chore: verified clean Ubuntu 24.04 VM at $(date -u +'%Y-%m-%dT%H:%M:%SZ')"`
- Tag release:
  `git tag -a smoke-test/$(date +%Y%m%dT%H%M%SZ) -m "Fresh VM smoke test passed"`

### 7. Cleanup

- `vagrant destroy -f`
- Remove fresh box (optional): `vagrant box remove --force bento/ubuntu-24.04`
- Exit with 0 if success; else, exit with 1 to surface failure.

---

## 🧠 Standards Mapped

| Project Requirement            | Alignment                                                           |
| ------------------------------ | ------------------------------------------------------------------- |
| **Reproducibility**            | Tests `vagrant destroy` + fresh box removal to ensure clean install |
| **Self-healing**               | Auto-install missing guest additions/dev tools and commit patches   |
| **Logging & Auditability**     | Saves logs, uses precise timestamps in commits/tags                 |
| **Immutable Test Environment** | Same Vagrantfile produces a bit-for-bit reproducible VM environment |
| **Clean Git History**          | Only commits actual fixes or clear validation tags                  |

---

## 🧩 Usage Example

```bash
npx claude‑flow@alpha swarm \
  --template .llmconfig/prompt‑templates/repeat_fresh_vm_test.md \
  "Verify fresh Ubuntu 24.04 Vagrant box and dev-tool smoke‑tests"
```

This will:

- Destroy the existing VM and box
- Bring up a clean instance
- Run internal checks and install missing components
- Commit or tag accordingly
- Clean up the environment

---

## 🚨 KVM Compatibility Notes (Ubuntu 24.04 + VirtualBox)

### Pre-requisite: KVM Module Management

Before running this template, ensure KVM modules are unloaded:

```bash
# Check KVM status
lsmod | grep kvm

# Unload if present (requires sudo)
sudo modprobe -r kvm_intel
sudo modprobe -r kvm

# Verify unloaded
lsmod | grep kvm || echo "KVM modules successfully unloaded"
```

### Permanent Solution (Recommended)

Add to `/etc/default/grub`:

```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash kvm.enable_virt_at_load=0"
```

Then: `sudo update-grub && sudo reboot`

### Error Handling

If you encounter:

```
VBoxManage: error: VirtualBox can't operate in VMX root mode (VERR_VMX_IN_VMX_ROOT_MODE)
```

This confirms KVM modules need unloading before VirtualBox can access hardware
virtualization.

---

> ✅ When this runs cleanly, you'll have a fully reproducible, audited baseline
> VM build — and you can repeat this at will to prove that your Vagrantfile and
> provisioning scripts still work months or years later.
