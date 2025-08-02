# Mission: Install host tooling and smoke-test VM for Ubuntu 24.04 via VirtualBox + Vagrant

You are the `env-prep-and-verifier` agent. Perform this next:

---

## STEP 1: Host Environment Verification & Installation

If any of the following commands are not available or return error:

- `virtualbox`, `vboxmanage --version`
- `vagrant --version`

Then proceed with host setup as follows (adapt if realms differ):

```bash
# Ensure required base packages for apt and key management
sudo apt update
sudo apt install -y \
  wget gnupg2 dirmngr software-properties-common \
  apt-transport-https ca-certificates \
  build-essential dkms linux-headers-$(uname -r)
```

### VirtualBox Installation (host)

Add official Oracle VirtualBox repository, update, then install:

```bash
wget -O- https://www.virtualbox.org/download/oracle_vbox_2016.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/oracle-virtualbox-2016.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/oracle-virtualbox-2016.gpg] \
  https://download.virtualbox.org/virtualbox/debian $(lsb_release -cs) contrib" | \
  sudo tee /etc/apt/sources.list.d/virtualbox.list

sudo apt update
sudo apt install -y virtualbox-7.1
```

If users are not members of the `vboxusers` group, add automatically (able to
run guest additions builds without root):

```bash
sudo usermod -aG vboxusers $(whoami)
```

### Vagrant Installation (host)

Configure HashiCorp repository and install:

```bash
wget -qO- https://apt.releases.hashicorp.com/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update
sudo apt install -y vagrant
```

Verify binaries:

```bash
vboxmanage --version  || echo "🔍 VirtualBox not installed correctly."
vagrant --version      || echo "🔍 Vagrant not installed correctly."
```

---

## STEP 2: Vagrant Smoke Test with Ubuntu 24.04 LTS

Create or update `Vagrantfile` to use:

```ruby
config.vm.box = "hashicorp-education/ubuntu-24-04"
```

Initialize if missing:

```bash
vagrant init hashicorp-education/ubuntu-24-04 --box-version 0.1.0
git add Vagrantfile
git commit -m "feat: add Ubuntu 24.04 Vagrant base box"
```

Bring up VM:

```bash
vagrant up --provider=virtualbox
```

- **If exit code 0**: move to SSH test.
- **On failure**:

  - Inspect the last 200 lines of the output.
  - **If mentions missing Guest Additions kernel headers or DKMS**:

    ```bash
    sed -i -e '/guest additions install/a sudo apt update && sudo apt install -y build-essential dkms linux-headers-$(uname -r)' Vagrantfile \
    || echo '# Provision shells if missing build tools'
    git add Vagrantfile
    git commit -m "fix: install prerequisites for VirtualBox Guest Additions"
    vagrant up --provider=virtualbox
    ```

  - **If box not found ("cannot find box ubuntu-24-04")**: confirm fallback base
    box is set (as above) and retry.

Test VM connectivity:

```bash
vagrant ssh -c "uname -r && echo env-verifier‑host: Ubuntu‑24.04 VM SSH OK"
```

On failure, diagnose: SSH keys, port mapping, or network setup; surface errors
for manual review.

---

## STEP 3: Final Status & Reporting

Upon successful SSH connection and prior host setup:

- Log:

```
env-verifier-host: Ubuntu 24.04 VM prepared and smoke test passed 🎯
```

- If any commit operations occurred, push changes:

```bash
git push origin HEAD
```

- If remote not configured, log:

```
env-verifier-host: no remote detected — commit remains local
```

---

## Behavioral Rules

- Only install or modify files when strictly necessary (e.g. if missing binary
  or provisioning fails).
- Do NOT commit temporary files, logs, or `.ARG-files.log`.
- Use structured, audit-friendly logs for each step.
- Do not pause workflow unless ambiguity arises (e.g. conflicting commands that
  need human approval).

---

## Allowed Modifications

- `.sh` provisioner scripts and `Vagrantfile` lines needed to bootstrap
  environment.
- Host shell execution only for tool installation and VM startup, not code dump.

---

**Why This Matters**

- Ubuntu 24.04 **does not offer official Vagrant boxes**;
  `hashicorp-education/ubuntu-24-04` is the most reliable choice across
  architectures (Canonical dropped Vagrant support as of 24.04).
- Common VM failures stem from missing `linux-headers-$(uname -r)`, `dkms`, and
  `build-essential` preventing Guest Additions build (needed for folder sync and
  clipboard support).
- Installing VirtualBox via Oracle's apt repository ensures up-to-date 7.1+
  version necessary for newest host kernels and smooth lifecycle support.
- Installing Vagrant through HashiCorp's repository provides official binaries
  and checksum-verifiable packages, avoiding outdated distro versions.

---

⏱ **Estimated execution time** (including host installs): ~3–5 minutes per run.

— End of Prompt —
