# Task: Add provisioning to Vagrantfile to install Claude Code, gh CLI, linters, IaC tools, and modern dev toolchain

You are the `dev-toolchain-installer` agent. Starting from a clean Ubuntu 24.04
Vagrantfile using `vagrant-libvirt`, your task is to:

## ✅ Provisioning Requirements

Include an inline shell (or external `scripts/provision.sh`) which, on first
`vagrant up`:

### 1️⃣ System Repos & Prerequisites

```bash
sudo apt update -y
sudo apt install -y software-properties-common gnupg curl wget apt-transport-https ca-certificates
```

- Add **HashiCorp apt repo** and install `terraform` via `apt install terraform`
  as per HashiCorp's official instructions for Ubuntu/Debian to ensure you get
  the most recent version.

- Add the **GitHub CLI apt repo** or install via package, e.g.:

```bash
# GitHub CLI repo setup
type gh || { curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | sudo gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg &&
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
    https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list &&
  sudo apt update -y && sudo apt install -y gh; }
```

### 2️⃣ Claude Code (AI CLI tool)

Install the Claude Code CLI using Node.js 18+ and
`npm install -g @anthropic-ai/claude-code`. Do **not** use `sudo` with `npm -g`
to avoid permission issues. Run `claude doctor` after installation to verify.

Ensure `nodejs 18+` and `npm` are installed (via NodeSource or apt):

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 3️⃣ Python Toolchain: uv + ruff

Install `uv` (Astral's ultra-fast Python tool runner)—use pipx or run via `curl`
as documented. Install `ruff`, Python linter & formatter via `uv` or direct
download of latest release tarball and place in `/usr/local/bin`. This ensures
fast linting with minimal overhead.

```bash
curl -fsSL https://get.astral.sh | bash
uv tool install ruff@latest
```

### 4️⃣ IaC Tools: Terraform + TFLint + tfsec

- Install `terraform` via HashiCorp's apt repository.
- Install `tflint` by downloading the latest binary, placing it in
  `/usr/local/bin`, and optionally initialize provider plugins using
  `tflint --init`.
- Install `tfsec` via `go install` or downloading the binary to
  `/usr/local/bin`.

### 5️⃣ Container & Docker Linting

Install **Hadolint** for Dockerfile linting via a release binary:

```bash
curl -fsSL https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 \
  -o /usr/local/bin/hadolint
chmod +x /usr/local/bin/hadolint
```

This ensures Dockerfile best practices with ShellCheck integration built in.

### 6️⃣ Optional Extras (if dependencies detected during boot)

- **ESLint / Prettier** for JavaScript/TypeScript:

  ```bash
  npm install -g eslint prettier
  ```

- **Solargraph** for Ruby language server (if Ruby installed):

  ```bash
  sudo gem install solargraph
  ```

### 7️⃣ Post-Provision Smoke Tests

After installing:

```bash
which claude && claude --version
which gh && gh --version
ruff --version
terraform --version
tflint --version
tfsec --version
hadolint --version
```

- On failure: the provisioning should retry install or emit structured error
  log, then exit non-zero.

### 8️⃣ Commit Strategy (Git)

- The first commit: Vagrantfile + provisioning additions.

  ```
  git add Vagrantfile scripts/provision.sh
  git commit -m "feat: add developer toolchain provisioning (claude, gh, linters, IaC tools)"
  ```

- If provisioning auto-recovers (e.g. built-ins paths were missing, retries
  occurred):

  ```
  git commit -m "fix: self-healed missing dev-tool prerequisites"
  ```

- If clean pass:

  ```
  git commit --allow-empty -m "chore: dev-toolchain smoke test passed at $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  ```

### 9️⃣ Logging & Behavior Rules

- Log key phases as single timestamped lines prefixed with
  `dev-toolchain-installer:`
- Do **not** commit caches, logs, or credential files.
- If installation fails due to ambiguous errors (unknown exception), log the
  failing commands and **request human confirmation** rather than exiting
  silently.

---

## 🧠 Standards Alignment

| Requirement               | Alignment                                                                 |
| ------------------------- | ------------------------------------------------------------------------- |
| **Reproducible tooling**  | All versions pinned (e.g. apt repo, release-binaried tools) per standards |
| **Self‑healing & audit**  | Provisioning scripts handle retries and commit remediation automatically  |
| **Compliance & security** | Tools like tfsec help enforce security checks left-shifted into dev setup |

---

## 📌 Usage

```bash
npx claude-flow@alpha swarm \
  --template .llmconfig/prompt-templates/provision_dev_toolchain.md \
  "Add Claude‑CLI, gh, ruff, terraform toolchain in Vagrant dev box"
```

---

## 🚀 Enhanced Features for Production Development

### Additional Security Tools

- **Trivy** - Container vulnerability scanner
- **Semgrep** - Static analysis for multiple languages
- **Bandit** - Python security linter
- **ShellCheck** - Shell script analysis

### Language Servers & IDE Support

- **Pylsp** - Python Language Server Protocol
- **TypeScript Language Server** - For TS/JS development
- **Rust Analyzer** - For Rust development
- **Go Language Server** - For Go development

### Enhanced Development Tools

```bash
# Advanced Git tooling
sudo apt install -y git-flow git-extras

# Database tools
sudo apt install -y postgresql-client mysql-client redis-tools

# Container tools
sudo apt install -y docker-compose podman buildah

# Network debugging
sudo apt install -y net-tools tcpdump wireshark-common

# Performance monitoring
sudo apt install -y htop iotop nethogs
```

### IDE and Editor Configurations

```bash
# VS Code via snap (optional)
sudo snap install code --classic

# Vim with modern configuration
sudo apt install -y vim-nox
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim

# Neovim with LSP support
sudo apt install -y neovim
```

### Development Environment Variables

```bash
# Set up development environment
echo 'export EDITOR=vim' >> ~/.bashrc
echo 'export BROWSER=firefox' >> ~/.bashrc
echo 'export TERM=xterm-256color' >> ~/.bashrc

# Python development
echo 'export PYTHONPATH=/home/vagrant/workspace:$PYTHONPATH' >> ~/.bashrc

# Node.js development
echo 'export NODE_ENV=development' >> ~/.bashrc
```

### Tool Version Management

```bash
# Install version managers for multiple language runtimes
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash  # Node.js
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  # Rust
curl -sSL https://install.python-poetry.org | python3 -  # Python Poetry
```

### Automated Configuration Validation

```bash
#!/bin/bash
# validate-dev-environment.sh

echo "🔍 Validating development environment..."

# Core tools validation
tools=(
    "claude:Claude Code CLI"
    "gh:GitHub CLI"
    "ruff:Python linter"
    "terraform:Infrastructure as Code"
    "tflint:Terraform linter"
    "tfsec:Terraform security scanner"
    "hadolint:Dockerfile linter"
)

for tool_info in "${tools[@]}"; do
    tool="${tool_info%%:*}"
    description="${tool_info##*:}"

    if command -v "$tool" >/dev/null 2>&1; then
        version=$(eval "$tool --version 2>/dev/null | head -1")
        echo "✅ $description: $version"
    else
        echo "❌ $description: Not installed"
    fi
done

# Environment validation
echo "🌍 Environment validation:"
echo "  - Shell: $SHELL"
echo "  - Editor: ${EDITOR:-not set}"
echo "  - Python: $(python3 --version 2>/dev/null || echo 'not available')"
echo "  - Node.js: $(node --version 2>/dev/null || echo 'not available')"
echo "  - Docker: $(docker --version 2>/dev/null || echo 'not available')"

echo "🎉 Development environment validation complete!"
```

---

End of **`dev-toolchain-installer`** prompt template 🎯
