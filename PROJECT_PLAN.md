Here’s the **full project plan** for a **CLI agent that scaffolds, manages, and
safely exercises an isolated Ubuntu 24.04 LTS development sandbox via Vagrant +
VirtualBox**, applying your standards and incorporating best practices
(including LLM sandboxing, security, and quality gates).

---

# Project Plan: `llm-sandbox-vagrant-agent`

## Overview

Build a **code CLI agent** (Python-based) that lives in a Git repo and automates
creation, provisioning, lifecycle management, and safe execution of an isolated
Ubuntu 24.04 LTS VM using Vagrant + VirtualBox. The VM serves as the execution
sandbox for LLM-generated actions (e.g., running `npm`, installing software) so
the host remains untouched. The agent will enforce reproducibility, include
pre-installed development/security tooling, support snapshot/rollback, and
integrate into CI/CD with quality gates (linting, testing, security scans).

---

## 1. Tech Stack Analysis

```yaml
detected:
  languages:
    - python (CLI agent, orchestration)
    - shell (provisioning scripts, bootstrap)
    - bash (VM setup)
  frameworks:
    - Click or Typer (Python CLI)
    - Vagrant (environment definition/lifecycle)
  boxes/base-images:
    - hashicorp-education/ubuntu-24-04 (Ubuntu 24.04 LTS base box)
    - fallback: custom Vagrant box built from Ubuntu cloud image
  infrastructure:
    - VirtualBox (hypervisor)
    - GitHub (source + Actions CI/CD)
    - Git (repo + versioning)
  tooling:
    - flake8 / black / mypy (Python quality)
    - bandit (Python security static analysis)
    - shellcheck (shell script linting)
    - pytest (testing)
    - coverage (coverage metrics)
    - pre-commit (hook orchestration)
```

---

## 2. Standards Recommendations

**Essential Standards:**

- **CS\:Python** – Follow PEP8/PEP257, enforce formatting with `black`, lint
  with `flake8`/`pylint`, types with `mypy`, security static analysis with
  `bandit`. ([Medium][1], [GitHub][2], [Real Python][3])
- **TS\:Testing** – Use `pytest` for unit and integration tests, enforce
  coverage target (e.g., ≥90%) and fail CI on regressions. ([Real Python][3])
- **SEC\:LLM Agent Safety & Isolation** – Apply defense-in-depth, least
  privilege, sandbox boundaries for executing model-generated code. Reference
  agent sandbox design patterns and threat models from recent research and
  industry guidance. ([amirmalik.net][4], [Sandgarden][5], [GoPenAI][6],
  [arXiv][7], [Medium][8])
- **INFRA\:Reproducible Environments** – Use Vagrant for environment definition,
  with versioned `Vagrantfile` and deterministic provisioning. ([HashiCorp
  Developer][9])

**Recommended Standards:**

- **FE/WD:** N/A (CLI-focused), but CLI UX should follow consistency and
  composability best practices (clear commands, help text, sane defaults).
  ([Simon Willison’s Weblog][10], [Better Stack][11])
- **DOP:** GitHub Actions for CI/CD with gated merges, reproducible builds, and
  test integration.
- **OBS:** Emit structured logs from the CLI agent; surface VM state,
  provisioning steps, and failure causes for observability.
- **NIST-IG:** Map security features to relevant NIST SP 800-53 Rev 5 controls,
  e.g.:
  - **AC-6** (least privilege) for agent actions,
  - **SC-7** (boundary protection) for sandbox isolation,
  - **SI-3** (malicious code protection) via scanning code before execution,
  - **CM-6** (configuration settings) for Vagrantfile/versioned environment.
    ([arXiv][7])

**Optional / Contextual Standards:**

- **Supply Chain (SA-12/SA-11):** If downloading external boxes or tooling,
  verify integrity (e.g., checksums, signed releases).
- **Secure Defaults:** Minimize network access from the sandbox unless
  explicitly required; control egress. ([Sandgarden][5])

---

## 3. Project Structure

```
llm-sandbox-vagrant-agent/
├── src/agentcli/                       # Python CLI implementation
│   ├── __init__.py
│   ├── cli.py                         # Click/Typer entrypoint
│   ├── vagrant_wrapper.py             # Programmatic Vagrant control (python-vagrant)
│   ├── config.py                     # YAML config loader
│   └── provision/                    # Shell snippets / templates
│       ├── base.sh                  # Common bootstrap logic
│       └── dev_tools.sh             # Installs Node.js, npm, optional security tooling
├── configs/
│   └── default.yaml                  # Declarative list of software, versions, snapshot policy
├── templates/
│   └── Vagrantfile.j2               # Jinja2 template for Vagrantfile
├── tests/
│   ├── test_cli.py                  # Unit tests for CLI behaviors
│   ├── test_vagrant_wrapper.py      # Mocks Vagrant interactions
│   └── fixtures/                   # Test fixtures / sample configs
├── .github/
│   └── workflows/ci.yml             # GitHub Actions pipeline
├── .pre-commit-config.yaml          # Pre-commit hook orchestration
├── pyproject.toml                  # Python packaging + tooling
├── README.md                       # Project overview + quick start
├── LICENSE                        # License (e.g., MIT / your choice)
├── Vagrantfile                    # Generated/checked-in by CLI (or symlink to template)
└── scripts/
    └── bootstrap-repo.py          # Optional helper to initialize repo from scratch
```

---

## 4. Quick Start Commands

```bash
# Clone repository
git clone git@github.com:youruser/llm-sandbox-vagrant-agent.git
cd llm-sandbox-vagrant-agent

# Install prerequisites on host (Ubuntu 24.04 example)
# 1. VirtualBox (from official repo for latest 7.1+)
sudo apt update
sudo apt install -y wget gnupg
wget -O- https://www.virtualbox.org/download/oracle_vbox_2016.asc | \
  sudo gpg --dearmor --yes --output /usr/share/keyrings/oracle-virtualbox-2016.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/oracle-virtualbox-2016.gpg] https://download.virtualbox.org/virtualbox/debian noble contrib" | \
  sudo tee /etc/apt/sources.list.d/virtualbox.sources
sudo apt update
sudo apt install -y virtualbox-7.1

# 2. Vagrant (via HashiCorp apt repo)
wget -O- https://apt.releases.hashicorp.com/gpg | \
  gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update
sudo apt install -y vagrant

# Bootstrap project environment (install Python deps)
python -m pip install -r requirements.txt

# Initialize the sandbox (creates Vagrantfile, applies default provisioning)
./src/agentcli/cli.py init

# Bring up the VM
./src/agentcli/cli.py up

# SSH into the VM
vagrant ssh

# Snapshot before risky operations
./src/agentcli/cli.py snapshot create pre-llm-run

# Destroy environment
./src/agentcli/cli.py destroy
```

_Installation instructions for VirtualBox and Vagrant are based on official and
community-validated guides to ensure up-to-date and reproducible setup._
([Linuxiac][12], [TecAdmin][13], [Ubuntu Handbook][14], [HashiCorp
Developer][15], [HashiCorp Developer][9])

---

## 5. Implementation Checklist

- [ ] Bootstrap repo scaffold (directories, `pyproject.toml`, templates).
- [ ] Implement Python CLI with Click/Typer.
- [ ] Integrate `python-vagrant` wrapper for programmatic VM control.
      ([GitHub][16])
- [ ] Template and generate `Vagrantfile` (support
      hashicorp-education/ubuntu-24-04 with fallback builder). ([HashiCorp
      Developer][9], [ICDP Online][17], [Pie in the rain][18])
- [ ] Write provisioning scripts (install Node.js/npm, developer tools, optional
      security toolset).
- [ ] Add snapshot/rollback commands.
- [ ] Enforce LLM sandbox policies (network restrictions, least privilege,
      isolation). ([Sandgarden][5], [GoPenAI][6], [arXiv][7])
- [ ] Add unit and integration tests (pytest).
- [ ] Configure quality gates (linting, formatting, security scanning).
      ([Medium][1], [GitHub][2], [Real Python][3], [Invent with Python][19],
      [Microsoft GitHub][20])
- [ ] Build GitHub Actions CI pipeline with: lint, format check, security scan,
      test+coverage, optional integration smoke test.
- [ ] Add pre-commit hooks (black, flake8, bandit, shellcheck).
- [ ] Document usage and extension in `README.md`.
- [ ] Version and tag releases; optionally package CLI for distribution.
- [ ] Optional: Provide ability to rebuild base box from Ubuntu cloud image if
      official box is missing. ([ICDP Online][17], [Pie in the rain][18])

---

## 6. Detailed Implementation Blueprint

### 6.1 Prerequisites Installation (Host)

- **VirtualBox**: Add Oracle’s official repo, import GPG key, install
  `virtualbox-7.1`. Ensure user is in `vboxusers` group for non-root usage.
  ([TecAdmin][13], [Ubuntu Handbook][14])
- **Vagrant**: Use HashiCorp apt repository to install latest stable Vagrant.
  ([HashiCorp Developer][15], [HashiCorp Developer][21])

### 6.2 Base Box Strategy

- Primary: `hashicorp-education/ubuntu-24-04` from HashiCorp’s registry
  (official tutorial usage). ([HashiCorp Developer][9])
- Fallback/self-hosted: Build a custom Vagrant box from the official Ubuntu
  Cloud Image if you need more control or the base box is unavailable. ([ICDP
  Online][17], [Pie in the rain][18])

### 6.3 CLI Agent Design

- **Entry point** using Click (or Typer) with subcommands: `init`, `up`, `halt`,
  `destroy`, `status`, `snapshot`, `provision`, `exec` (run arbitrary commands
  inside VM safely), `config` (inspect/edit YAML manifest). ([Real Python][22],
  [Better Stack][11], [Simon Willison’s Weblog][10])
- **Configuration**: YAML manifest (`configs/default.yaml`) describing desired
  tooling (e.g., Node.js version, NPM packages, security tools), snapshot
  policy, network rules.
- **Wrapper** around CLI to call `vagrant` via `python-vagrant` for robust
  status introspection and error handling. ([GitHub][16])
- **Safety**: Before executing LLM-generated instructions, create a snapshot,
  rate-limit network (optional firewall rules inside the VM), and log all
  actions for audit. ([amirmalik.net][4], [Medium][8])

### 6.4 Provisioning

Sample installs include:

- Development tools: `nodejs`, `npm`, `git`, `build-essential`.
- Optional security tooling / Kali-style utilities: either selectively install
  packages (e.g., `nmap`, `curl`, `jq`) or add a curated subset of Kali tools
  from a trusted repository rather than pulling the entire heavy distro.
- Script templating to allow injection of additional LLM-specified commands
  after human review.
- Idempotency: provisioners should be safe to re-run without destructive side
  effects.

### 6.5 Snapshot and Rollback

- Use VirtualBox snapshotting via the CLI wrapper to capture pre-execution
  state.
- Provide `snapshot create NAME`, `snapshot list`, `snapshot restore NAME`.
- Automate snapshot before any untrusted LLM-run batch to ensure easy rollback.
  ([GoPenAI][6])

### 6.6 LLM Sandbox Isolation

- Execute LLM-generated code **only inside the VM**; never on host.
- Optionally restrict egress by configuring the VM’s networking (e.g., host-only
  or controlled NAT) to avoid data exfiltration.
- Implement “guard rails” in the CLI: validate model-supplied commands against
  allowlists or require human confirmation for high-risk commands.
- Log all inputs/outputs for traceability. ([Sandgarden][5], [Medium][8])

### 6.7 CI/CD Pipeline

GitHub Actions workflow:

- **Steps**:

  - Checkout code
  - Setup Python environment
  - Run `pre-commit` (black, flake8, shellcheck via hooks)
  - Run `bandit` for security scanning. ([GitHub][2])
  - Run tests with `pytest` and collect coverage.
  - Fail if coverage < threshold (e.g., 90%).
  - Optional: launch ephemeral Vagrant VM (`vagrant up --provider=virtualbox`),
    run smoke provisioning, then `vagrant destroy` (can be gated behind a label
    to avoid long CI).

- **Artifacts**: coverage report, linter output, optionally packaged CLI
  release.

### 6.8 Testing Strategy

- **Unit Tests**: Mock Vagrant interactions (e.g., via monkeypatch or using fake
  subprocess calls) to test CLI logic without needing real VMs.
- **Integration Tests**: Optionally spin up a lightweight VM to verify
  provisioning script runs and key tools are present; mark slow/infrequent.
- **Test Coverage**: Target ≥90% on core logic; enforce in CI. ([Real
  Python][3])

### 6.9 Quality Gates

- **Formatting**: `black --check`
- **Linting**: `flake8` / optionally `pylint` with project config.
- **Type Checking**: `mypy` for typed modules.
- **Security**: `bandit -r src/agentcli` to catch common Python security issues.
  ([GitHub][2])
- **Shell Scripts**: `shellcheck` on all provisioning scripts.
- **Coverage**: Fail if below threshold.
- **Git Hooks**: Pre-commit to run the above locally before push/PR.
  ([Medium][1], [Invent with Python][19])

---

## 7. Example Starter Code Snippets

### 7.1 `Vagrantfile` (minimal, templated)

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "hashicorp-education/ubuntu-24-04"
  config.vm.box_version = "0.1.0"

  # Network: limit to host-only by default for safety
  config.vm.network "private_network", type: "dhcp"

  # Sync folder (optional)
  config.vm.synced_folder ".", "/vagrant", disabled: false

  # Provisioning: bootstrap script
  config.vm.provision "shell", path: "src/agentcli/provision/base.sh", privileged: false
  config.vm.provision "shell", path: "src/agentcli/provision/dev_tools.sh", privileged: false
end
```

### 7.2 Sample `provision/base.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Updating package index..."
sudo apt update

# Basic dev tools
sudo apt install -y git curl wget build-essential

# Node.js (example: install LTS via nodesource)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Ensure npm is available
npm --version || echo "npm installation failed"
```

### 7.3 Python CLI Skeleton (`src/agentcli/cli.py`)

```python
import click
import vagrant
import yaml
from pathlib import Path

@click.group()
def cli():
    """LLM Sandbox Vagrant Agent CLI"""
    pass

@cli.command()
def init():
    """Initialize project: create Vagrantfile from template and default config."""
    # generate Vagrantfile, create default YAML, etc.
    click.echo("Project initialized.")

@cli.command()
def up():
    """Bring up the VM."""
    v = vagrant.Vagrant()
    v.up()
    click.echo("VM is up. SSH with 'vagrant ssh'.")

@cli.command()
@click.argument("name")
def snapshot(name):
    """Create a snapshot (VirtualBox) before risky operations."""
    # interface with VBoxManage or via vagrant wrapper
    click.echo(f"Snapshot {name} created.")

@cli.command()
def destroy():
    """Destroy the VM."""
    v = vagrant.Vagrant()
    v.destroy()
    click.echo("Destroyed the VM.")
```

### 7.4 `pyproject.toml` (partial)

```toml
[project]
name = "llm-sandbox-vagrant-agent"
version = "0.1.0"
description = "CLI agent for creating and managing an isolated Ubuntu 24.04 sandbox via Vagrant+VirtualBox."
authors = [{name="Your Name", email="you@example.com"}]
license = {text="MIT"}

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project.dependencies]
click = "^8.1"
python-vagrant = "^0.6.0"
pyyaml = "^6.0"

[tool.black]
line-length = 88

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203"]

[tool.mypy]
strict = true
```

### 7.5 GitHub Actions CI (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install black flake8 mypy bandit pytest coverage pre-commit
          pip install -e .

      - name: Run pre-commit
        run: pre-commit run --all-files

      - name: Lint & Type-check
        run: |
          black --check .
          flake8 src/
          mypy src/

      - name: Security scan
        run: bandit -r src/agentcli -ll

      - name: Run tests with coverage
        run: |
          coverage run -m pytest
          coverage report --fail-under=90
```

### 7.6 Pre-commit config (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: stable
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.1
    hooks:
      - id: bandit
  - repo: https://github.com/koalaman/shellcheck
    rev: v0.9.0
    hooks:
      - id: shellcheck
```

---

## 8. Quality Gates (automated checks)

- **Formatting:** `black --check`.
- **Style:** `flake8` (PEP8 adherence, complexity thresholds).
- **Typing:** `mypy --strict` on core modules.
- **Security:** `bandit` scan with policy failures causing CI break.
  ([GitHub][2])
- **Shell Script Hygiene:** `shellcheck` on all provisioning scripts.
- **Test Coverage:** Fail if overall coverage drops below 90%. ([Real
  Python][3])
- **CLI Behavior:** Smoke test of common subcommands.
- **Repository Health:** Pre-commit to gate all pushes/PRs. ([Medium][1],
  [Invent with Python][19])

---

## 9. Tool Recommendations

**Required:**

- `VirtualBox 7.1+` (hypervisor, install from Oracle’s repo for latest updates).
  ([Linuxiac][12], [TecAdmin][13])
- `Vagrant` (via HashiCorp apt repo). ([HashiCorp Developer][15], [HashiCorp
  Developer][21])
- `Python` (3.11+), `Click`/`Typer` for CLI. ([Real Python][22], [Better
  Stack][11])
- `python-vagrant` for programmatic control. ([GitHub][16])
- `black`, `flake8`, `mypy`, `bandit`, `shellcheck` for quality/security.
  ([Medium][1], [GitHub][2], [Real Python][3], [Invent with Python][19],
  [Microsoft GitHub][20])
- `pytest` + `coverage` for testing. ([Real Python][3])
- `pre-commit` for local gatekeeping.

**Recommended:**

- `rich` for CLI output prettiness (optional, for better UX).
- Snapshot management via `VBoxManage` integration for richer metadata.
- Logging library with structured output (e.g., `structlog`) for observability.
- Optional lightweight local DNS or network filtering tooling inside the VM to
  control egress.

**Optional:**

- Custom Vagrant box builder (script to convert Ubuntu cloud image to box) if
  you want full control. ([ICDP Online][17], [Pie in the rain][18])
- CLI auto-update or self-versioning release mechanism.
- Integration with secret vault (for future extension, e.g., to inject ephemeral
  credentials into sandboxed runs, respecting least privilege).

---

## 10. Next Steps / Milestones

1. **Week 0 (Day 1-2):** Scaffold repo, implement basic CLI (`init`, `up`,
   `destroy`), commit example `Vagrantfile`, set up Python tooling.
2. **Week 1:** Provisioning scripts, sandbox safety (snapshot, network
   constraints), add configuration manifest.
3. **Week 2:** Testing harness, implement quality gates, integrate `pre-commit`,
   build CI pipeline.
4. **Week 3:** Harden LLM integration patterns (confirmation hooks, command
   validation), add example LLM-run workflows with rollback snapshots.
5. **Week 4:** Polish documentation, publish initial release, optionally
   template reuse for other sandboxes.

---

## Citations Summary (key sources used)

- **Vagrant + Ubuntu 24.04 setup and base box:** official Vagrant tutorial and
  box (`hashicorp-education/ubuntu-24-04`), alternative box creation from cloud
  images. ([HashiCorp Developer][9], [ICDP Online][17], [Pie in the rain][18])
- **VirtualBox installation:** Oracle repository instructions and community
  validation (TecAdmin, Ubuntu Handbook). ([TecAdmin][13], [Ubuntu
  Handbook][14])
- **CLI design best practices:** Click/Typer usage and modular CLI patterns.
  ([Real Python][22], [Better Stack][11], [Simon Willison’s Weblog][10])
- **Python quality & security tooling:** black, flake8, mypy, bandit, coverage,
  testing best practices. ([Medium][1], [GitHub][2], [Real Python][3], [Invent
  with Python][19], [Microsoft GitHub][20])
- **LLM sandbox/security design:** agent sandbox design patterns, research on
  secure LLM agents, isolation philosophy. ([amirmalik.net][4], [Sandgarden][5],
  [GoPenAI][6], [arXiv][7], [Medium][8])

---

Would you like me to:

- Generate the initial repository scaffold (Python CLI + templated Vagrantfile +
  GitHub Actions) as files?
- Turn this into a `project_plan.md` file in the canvas or as a downloadable
  artifact?

[1]:
  https://medium.com/%40huzaifazahoor654/improving-code-quality-with-flake8-and-black-a-guide-for-python-developers-c374168d5884?utm_source=chatgpt.com
  "Improving Code Quality with Flake8 and Black"
[2]:
  https://github.com/PyCQA/bandit?utm_source=chatgpt.com
  "PyCQA/bandit: Bandit is a tool designed to find common ..."
[3]:
  https://realpython.com/python-code-quality/?utm_source=chatgpt.com
  "Python Code Quality: Best Practices and Tools"
[4]:
  https://amirmalik.net/2025/03/07/code-sandboxes-for-llm-ai-agents?utm_source=chatgpt.com
  "Code Sandboxes for LLMs and AI Agents - Amir's Blog"
[5]:
  https://www.sandgarden.com/learn/llm-sandbox?utm_source=chatgpt.com
  "Understanding LLM Sandbox Environments"
[6]:
  https://blog.gopenai.com/how-agent-sandboxes-power-secure-scalable-ai-innovation-f24dbd2b4a0f?utm_source=chatgpt.com
  "How Agent Sandboxes Power Secure, Scalable AI Innovation"
[7]:
  https://arxiv.org/abs/2505.24019?utm_source=chatgpt.com
  "LLM Agents Should Employ Security Principles"
[8]:
  https://medium.com/%40adnanmasood/the-sandboxed-mind-principled-isolation-patterns-for-prompt-injection-resilient-llm-agents-c14f1f5f8495?utm_source=chatgpt.com
  "The Sandboxed Mind — Principled Isolation Patterns for ..."
[9]:
  https://developer.hashicorp.com/vagrant/tutorials/get-started/setup-project
  "Set up your development environment | Vagrant | HashiCorp Developer"
[10]:
  https://simonwillison.net/2023/Sep/30/cli-tools-python/?utm_source=chatgpt.com
  "Things I've learned about building CLI tools in Python"
[11]:
  https://betterstack.com/community/guides/scaling-python/click-explained/?utm_source=chatgpt.com
  "Creating composable CLIs with click in Python"
[12]:
  https://linuxiac.com/how-to-install-virtualbox-on-ubuntu-24-04-lts/?utm_source=chatgpt.com
  "How to Install VirtualBox 7.1 on Ubuntu 24.04 LTS"
[13]:
  https://tecadmin.net/install-oracle-virtualbox-on-ubuntu/?utm_source=chatgpt.com
  "How to Install VirtualBox 7.1 on Ubuntu 24.04 LTS"
[14]:
  https://ubuntuhandbook.org/index.php/2023/12/install-virtualbox-ubuntu-2204/?utm_source=chatgpt.com
  "Install VirtualBox 7.1.x in Ubuntu 22.04/24.04 & Keep ..."
[15]:
  https://developer.hashicorp.com/vagrant/install?utm_source=chatgpt.com
  "Install | Vagrant"
[16]:
  https://github.com/pycontribs/python-vagrant?utm_source=chatgpt.com
  "Python bindings for interacting with Vagrant virtual machines."
[17]:
  https://data.icdp-online.org/mdis-docs/guide/sys-admin/installation-vagrantbox-from-cloudimage?utm_source=chatgpt.com
  "Creating a Vagrant Box from an Ubuntu Cloud Image"
[18]:
  https://beltrani.com/vagrant-boxes-from-official-ubuntu-cloud-images/?utm_source=chatgpt.com
  "Vagrant Boxes from official Ubuntu Cloud Images"
[19]:
  https://inventwithpython.com/blog/2022/11/19/python-linter-comparison-2022-pylint-vs-pyflakes-vs-flake8-vs-autopep8-vs-bandit-vs-prospector-vs-pylama-vs-pyroma-vs-black-vs-mypy-vs-radon-vs-mccabe/?utm_source=chatgpt.com
  "Python Linter Comparison 2022: Pylint vs Pyflakes ..."
[20]:
  https://microsoft.github.io/code-with-engineering-playbook/code-reviews/recipes/python/?utm_source=chatgpt.com
  "Python Code Reviews - Engineering Fundamentals Playbook"
[21]:
  https://developer.hashicorp.com/vagrant/docs/installation?utm_source=chatgpt.com
  "Install Vagrant"
[22]:
  https://realpython.com/python-click/?utm_source=chatgpt.com
  "Click and Python: Build Extensible and Composable CLI ..."
