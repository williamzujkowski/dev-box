# Task: Commit current work and run smoke-test on Ubuntu 24.04 development VM

You are the `environment-verifier` agent.

## Instructions:

### 1. Commit Pending Changes

```bash
git add .
git commit -m "chore: commit sandbox changes before smoke test"
```

### 2. Execute Vagrant Lifecycle

```bash
vagrant up --provider=virtualbox
```

- If it exits with code 0, proceed to Step 3.
- If it fails:

  - Carefully inspect the last 200 lines of the `vagrant up` output.
  - Detect if a known issue is present: VirtualBox Guest Additions installation
    fails due to missing `linux-headers-$(uname -r)`, `dkms`, or
    `build-essential`—this is a known failure pattern on Ubuntu 24.04.
  - Patch the shell provisioner or inline Vagrantfile provisioning block to
    install:

    ```bash
    sudo apt update
    sudo apt install -y build-essential dkms linux-headers-$(uname -r)
    ```

  - Commit the patch:

    ```bash
    git add .
    git commit -m "fix: install prerequisites for Guest Additions on Ubuntu 24.04"
    ```

  - Rerun `vagrant up` and retry Step 3 if required.

### 3. Smoke Test SSH Connectivity

```bash
vagrant ssh -c "uname -r && echo 'env-verifier: VM is up'"
```

- If SSH works, log:

  ```
  env-verifier: Ubuntu 24.04 VM booted successfully and SSH accessible 🎉
  ```

- If SSH fails (e.g., timeout, authentication issues), identify:

  - Incorrect or nonexistent base box; Ubuntu 24.04 Vagrant box is often
    unavailable unless using `hashicorp-education/ubuntu-24-04` or a
    custom-built box (Canonical still doesn't host official boxes).
  - Circuit-break provisioning errors or networking misconfiguration.

- If needed, update `Vagrantfile` to:

  ```ruby
  config.vm.box = "hashicorp-education/ubuntu-24-04"
  ```

  Commit:

  ```bash
  git add Vagrantfile
  git commit -m "feat: switch to hashicorp-education/ubuntu-24-04 box for reliable 24.04 support"
  ```

  Then rerun Steps 2−3.

### 4. Push the Verified State

```bash
git push origin HEAD
```

- If remote isn't configured, log a warning:

  ```
  env-verifier: No remote detected — manual push required.
  ```

---

### ✅ Output Requirements

Your agent must:

- Make as few commits as needed (ideally one commit per remediation).
- Clearly log each success or failure step.
- Store any CLI output or diffs in logs for auditing.
- Not halt mid-task unless there's ambiguity requiring human approval.

### 🛠 Allowed Edits:

- Shell provisioner scripts (`*.sh`)
- `Vagrantfile` only when fixing box names or base configuration

---

**Goal:** Automate an unattended smoke test cycle that:

- Commits current sandbox content,
- Ensures the Ubuntu 24.04 VM boots and is SSH‑accessible,
- Self-recovers from common provisioning issues,
- Pushes changes or instructs on manual steps only when needed.

Use this prompt whenever you or a swarm agent makes changes that affect the VM
lifecycle or provisioning.

---

## 📝 Usage Instructions

Save this template and invoke with Claude-Flow:

```bash
npx claude-flow@alpha swarm \
  --template prompt-templates/commit_and_vagrant_smoke_test_prompt.md \
  "Verify Ubuntu 24.04 VM boots after provisioning changes"
```

The agent will:

1. Commit any pending changes
2. Attempt to bring up the VM
3. Self-heal common Ubuntu 24.04 provisioning issues
4. Verify SSH connectivity
5. Push changes to remote (if configured)
