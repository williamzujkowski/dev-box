#!/bin/bash
# Development Toolchain Provisioning Script
# Installs Claude Code, GitHub CLI, Python tools, IaC tools, and linters

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
  echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} dev-toolchain-installer: $1"
}

success() {
  echo -e "${GREEN}✅ $1${NC}"
}

warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
  echo -e "${RED}❌ $1${NC}"
}

# Track installation status
INSTALL_SUCCESS=()
INSTALL_FAILED=()

install_tool() {
  local tool_name="$1"
  local install_command="$2"

  log "Installing $tool_name..."

  if eval "$install_command"; then
    success "$tool_name installed successfully"
    INSTALL_SUCCESS+=("$tool_name")
    return 0
  else
    error "Failed to install $tool_name"
    INSTALL_FAILED+=("$tool_name")
    return 1
  fi
}

verify_tool() {
  local tool_name="$1"
  local check_command="$2"

  if eval "$check_command" >/dev/null 2>&1; then
    local version=$(eval "$check_command" 2>/dev/null | head -1)
    success "$tool_name verified: $version"
    return 0
  else
    error "$tool_name verification failed"
    return 1
  fi
}

log "🚀 Starting development toolchain installation"
log "Target: Ubuntu 24.04 with comprehensive dev tools"

# 1️⃣ System Prerequisites
log "📦 Installing system prerequisites..."
export DEBIAN_FRONTEND=noninteractive

sudo apt update -y
sudo apt install -y \
  software-properties-common \
  gnupg \
  curl \
  wget \
  apt-transport-https \
  ca-certificates \
  build-essential \
  git \
  vim \
  htop \
  unzip

success "System prerequisites installed"

# 2️⃣ HashiCorp Repository Setup
log "🏗️  Setting up HashiCorp repository..."
if ! grep -q "apt.releases.hashicorp.com" /etc/apt/sources.list.d/hashicorp.list 2>/dev/null; then
  wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
  sudo apt update -y
  success "HashiCorp repository added"
else
  log "HashiCorp repository already configured"
fi

# 3️⃣ GitHub CLI Repository Setup
log "🐙 Setting up GitHub CLI repository..."
if ! command -v gh >/dev/null 2>&1; then
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list
  sudo apt update -y
  sudo apt install -y gh
  success "GitHub CLI installed"
else
  success "GitHub CLI already installed"
fi

# 4️⃣ Node.js 18+ Setup
log "🟢 Installing Node.js 18+ and npm..."
if ! node --version 2>/dev/null | grep -q "v1[89]\|v[2-9][0-9]"; then
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt install -y nodejs
  success "Node.js $(node --version) installed"
else
  success "Node.js $(node --version) already available"
fi

# 5️⃣ Claude Code CLI Installation
log "🤖 Installing Claude Code CLI..."
if ! command -v claude >/dev/null 2>&1; then
  # Configure npm to install global packages without sudo
  mkdir -p ~/.npm-global
  npm config set prefix '~/.npm-global'
  echo 'export PATH=~/.npm-global/bin:$PATH' >>~/.bashrc
  export PATH=~/.npm-global/bin:$PATH

  # Install Claude Code
  npm install -g @anthropic-ai/claude-code

  # Verify installation
  if command -v claude >/dev/null 2>&1; then
    success "Claude Code CLI installed"
    # Run claude doctor for verification
    claude doctor || warning "Claude doctor check completed with warnings"
  else
    error "Claude Code CLI installation failed"
    INSTALL_FAILED+=("Claude Code CLI")
  fi
else
  success "Claude Code CLI already installed"
fi

# 6️⃣ Python Toolchain: uv + ruff
log "🐍 Installing Python toolchain (uv + ruff)..."

# Install uv (ultra-fast Python package installer)
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
  echo 'export PATH="$HOME/.cargo/bin:$PATH"' >>~/.bashrc
  success "uv installed"
else
  success "uv already installed"
fi

# Install ruff via uv
if ! command -v ruff >/dev/null 2>&1; then
  # Ensure uv is in PATH for this session
  export PATH="$HOME/.cargo/bin:$PATH"
  uv tool install ruff
  success "ruff installed via uv"
else
  success "ruff already installed"
fi

# 7️⃣ Infrastructure as Code Tools
log "🏗️  Installing IaC tools (Terraform, TFLint, tfsec)..."

# Install Terraform
install_tool "Terraform" "sudo apt install -y terraform"

# Install TFLint
if ! command -v tflint >/dev/null 2>&1; then
  TFLINT_VERSION=$(curl -s https://api.github.com/repos/terraform-linters/tflint/releases/latest | grep -o '"tag_name": "v[^"]*' | cut -d'"' -f4)
  wget -O /tmp/tflint.zip "https://github.com/terraform-linters/tflint/releases/latest/download/tflint_linux_amd64.zip"
  sudo unzip /tmp/tflint.zip -d /usr/local/bin/
  sudo chmod +x /usr/local/bin/tflint
  rm /tmp/tflint.zip
  success "TFLint $TFLINT_VERSION installed"
else
  success "TFLint already installed"
fi

# Install tfsec
if ! command -v tfsec >/dev/null 2>&1; then
  TFSEC_VERSION=$(curl -s https://api.github.com/repos/aquasecurity/tfsec/releases/latest | grep -o '"tag_name": "v[^"]*' | cut -d'"' -f4)
  wget -O /tmp/tfsec "https://github.com/aquasecurity/tfsec/releases/latest/download/tfsec-linux-amd64"
  sudo mv /tmp/tfsec /usr/local/bin/tfsec
  sudo chmod +x /usr/local/bin/tfsec
  success "tfsec $TFSEC_VERSION installed"
else
  success "tfsec already installed"
fi

# 8️⃣ Container & Docker Linting
log "🐳 Installing Hadolint (Dockerfile linter)..."
if ! command -v hadolint >/dev/null 2>&1; then
  sudo wget -O /usr/local/bin/hadolint "https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64"
  sudo chmod +x /usr/local/bin/hadolint
  success "Hadolint installed"
else
  success "Hadolint already installed"
fi

# 9️⃣ Optional JavaScript/TypeScript Tools
log "📜 Installing optional JavaScript/TypeScript tools..."
if command -v npm >/dev/null 2>&1; then
  npm install -g eslint prettier typescript @typescript-eslint/parser @typescript-eslint/eslint-plugin
  success "ESLint, Prettier, and TypeScript tools installed"
fi

# 🔟 Optional Ruby Tools (if Ruby is detected)
if command -v ruby >/dev/null 2>&1 && command -v gem >/dev/null 2>&1; then
  log "💎 Installing Ruby development tools..."
  sudo gem install solargraph rubocop
  success "Ruby development tools installed"
fi

# Additional Security and Development Tools
log "🔒 Installing additional security and development tools..."

# Install additional linters and security tools
sudo apt install -y shellcheck yamllint

# Install development utilities
sudo apt install -y jq tree fd-find ripgrep bat exa

# Create symlinks for modern alternatives
sudo ln -sf /usr/bin/batcat /usr/local/bin/bat 2>/dev/null || true
sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd 2>/dev/null || true

success "Additional development tools installed"

# 1️⃣1️⃣ Post-Installation Verification
log "🧪 Running post-installation verification..."

verification_passed=0
verification_total=0

tools_to_verify=(
  "claude:claude --version"
  "gh:gh --version"
  "terraform:terraform --version"
  "tflint:tflint --version"
  "tfsec:tfsec --version"
  "hadolint:hadolint --version"
  "node:node --version"
  "npm:npm --version"
  "python3:python3 --version"
  "git:git --version"
)

# Add uv and ruff with PATH
export PATH="$HOME/.cargo/bin:$PATH"
tools_to_verify+=(
  "uv:uv --version"
  "ruff:ruff --version"
)

echo ""
echo "📋 Tool Verification Report:"
echo "=========================="

for tool_info in "${tools_to_verify[@]}"; do
  tool="${tool_info%%:*}"
  check_command="${tool_info##*:}"
  verification_total=$((verification_total + 1))

  if verify_tool "$tool" "$check_command"; then
    verification_passed=$((verification_passed + 1))
  fi
done

# 1️⃣2️⃣ Generate Development Environment Configuration
log "⚙️  Generating development environment configuration..."

cat >/home/vagrant/.dev-environment <<'EOF'
# Development Environment Configuration
# Generated by dev-toolchain-installer

# PATH additions
export PATH="$HOME/.npm-global/bin:$PATH"
export PATH="$HOME/.cargo/bin:$PATH"
export PATH="/usr/local/bin:$PATH"

# Editor preferences
export EDITOR=vim
export VISUAL=vim

# Development settings
export NODE_ENV=development
export PYTHONPATH=/home/vagrant/workspace:$PYTHONPATH

# Aliases for modern tools
alias cat='bat'
alias find='fd'
alias grep='rg'
alias ls='exa'
alias ll='exa -la'
alias la='exa -a'

# Git aliases
alias gst='git status'
alias gco='git checkout'
alias gaa='git add -A'
alias gcm='git commit -m'
alias gps='git push'
alias gpl='git pull'

# Docker aliases
alias dc='docker-compose'
alias dps='docker ps'
alias dls='docker images'

# Development shortcuts
alias tf='terraform'
alias tfi='terraform init'
alias tfp='terraform plan'
alias tfa='terraform apply'
alias tfd='terraform destroy'

# Linting shortcuts
alias lint-py='ruff check'
alias lint-tf='tflint'
alias lint-docker='hadolint'
alias lint-shell='shellcheck'

echo "🛠️  Development environment loaded!"
EOF

# Add source to .bashrc if not already present
if ! grep -q ".dev-environment" /home/vagrant/.bashrc; then
  echo "source ~/.dev-environment" >>/home/vagrant/.bashrc
fi

success "Development environment configuration created"

# 1️⃣3️⃣ Create Validation Script
log "📝 Creating environment validation script..."

cat >/home/vagrant/validate-dev-env.sh <<'EOF'
#!/bin/bash
# Development Environment Validation Script

echo "🔍 Validating development environment..."
echo "======================================="

# Source environment
source ~/.dev-environment 2>/dev/null || true

# Tool validation
tools=(
    "claude:Claude Code CLI"
    "gh:GitHub CLI"
    "terraform:Terraform"
    "tflint:TFLint"
    "tfsec:tfsec"
    "hadolint:Hadolint"
    "ruff:Ruff Python linter"
    "uv:UV Python installer"
    "node:Node.js"
    "npm:NPM"
    "eslint:ESLint"
    "prettier:Prettier"
)

passed=0
total=0

for tool_info in "${tools[@]}"; do
    tool="${tool_info%%:*}"
    description="${tool_info##*:}"
    total=$((total + 1))

    if command -v "$tool" >/dev/null 2>&1; then
        version=$(eval "$tool --version 2>/dev/null | head -1" 2>/dev/null || echo "installed")
        echo "✅ $description: $version"
        passed=$((passed + 1))
    else
        echo "❌ $description: Not available"
    fi
done

echo ""
echo "📊 Validation Summary:"
echo "====================="
echo "✅ Passed: $passed/$total tools"
echo "🔧 Environment: $(lsb_release -d | cut -f2)"
echo "🐚 Shell: $SHELL"
echo "📝 Editor: ${EDITOR:-not set}"

if [ $passed -eq $total ]; then
    echo "🎉 All development tools are ready!"
    exit 0
else
    echo "⚠️  Some tools are missing - check installation"
    exit 1
fi
EOF

chmod +x /home/vagrant/validate-dev-env.sh
success "Validation script created: ~/validate-dev-env.sh"

# 1️⃣4️⃣ Final Summary
echo ""
echo "🎉 Development Toolchain Installation Complete!"
echo "=============================================="
echo ""
echo "📊 Installation Summary:"
echo "  ✅ Successful: ${#INSTALL_SUCCESS[@]} tools"
echo "  ❌ Failed: ${#INSTALL_FAILED[@]} tools"
echo "  🧪 Verified: $verification_passed/$verification_total tools"
echo ""

if [ ${#INSTALL_FAILED[@]} -gt 0 ]; then
  echo "⚠️  Failed installations:"
  for tool in "${INSTALL_FAILED[@]}"; do
    echo "  - $tool"
  done
  echo ""
fi

echo "🚀 Quick Start:"
echo "  - Source environment: source ~/.dev-environment"
echo "  - Validate tools: ~/validate-dev-env.sh"
echo "  - Start coding: cd ~/workspace"
echo ""

echo "🛠️  Available Tools:"
echo "  🤖 Claude Code CLI - AI-powered development assistant"
echo "  🐙 GitHub CLI - GitHub operations from terminal"
echo "  🐍 Python: uv (installer) + ruff (linter/formatter)"
echo "  🏗️  Infrastructure: terraform + tflint + tfsec"
echo "  🐳 Container: hadolint (Dockerfile linter)"
echo "  📜 JavaScript: eslint + prettier + typescript"
echo "  🔒 Security: shellcheck + yamllint + additional linters"
echo ""

success "Development environment ready for production use!"

# Run final validation
log "🔍 Running final validation..."
export PATH="$HOME/.npm-global/bin:$HOME/.cargo/bin:$PATH"
source /home/vagrant/.dev-environment

if /home/vagrant/validate-dev-env.sh; then
  success "🎉 Final validation passed - environment fully operational!"
  exit 0
else
  warning "⚠️  Final validation had issues - manual review recommended"
  exit 1
fi
