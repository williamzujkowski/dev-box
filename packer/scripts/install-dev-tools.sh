#!/bin/bash
# Development Tools Installation Script
set -euo pipefail

echo "=== Installing Development Toolchain ==="

# Update package cache
sudo apt-get update

# Install Python UV package manager
echo "Installing UV Python package manager..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Install Ruff Python linter/formatter
echo "Installing Ruff..."
uv tool install ruff

# Install GitHub CLI
echo "Installing GitHub CLI..."
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt-get update
sudo apt-get install -y gh

# Install Claude CLI
echo "Installing Claude CLI..."
sudo npm install -g @anthropic-ai/claude-cli

# Install Terraform
echo "Installing Terraform..."
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update
sudo apt-get install -y terraform

# Install tfsec (Terraform security scanner)
echo "Installing tfsec..."
curl -s https://raw.githubusercontent.com/aquasecurity/tfsec/master/scripts/install_linux.sh | bash
sudo mv tfsec /usr/local/bin/

# Install Docker
echo "Installing Docker..."
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove -y $pkg; done || true
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add vagrant user to docker group
sudo usermod -aG docker vagrant

# Install additional development tools
echo "Installing additional development tools..."
sudo apt-get install -y \
    zsh \
    fish \
    tmux \
    screen \
    ripgrep \
    fd-find \
    bat \
    exa \
    fzf \
    tig \
    httpie \
    jq \
    yq \
    parallel \
    ncdu \
    duf \
    bottom \
    procs

# Install Oh My Zsh for vagrant user
echo "Installing Oh My Zsh..."
sudo -u vagrant sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" || true

# Install Rust and Cargo
echo "Installing Rust..."
sudo -u vagrant curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sudo -u vagrant sh -s -- -y

# Install useful Rust tools
sudo -u vagrant bash -c 'source ~/.cargo/env && cargo install cargo-edit cargo-audit cargo-outdated'

# Install Node.js LTS via NodeSource
echo "Installing Node.js LTS..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install useful npm packages globally
sudo npm install -g \
    @commitlint/cli \
    @commitlint/config-conventional \
    conventional-changelog-cli \
    standard-version \
    husky \
    lint-staged \
    prettier \
    eslint \
    typescript \
    ts-node \
    nodemon \
    pm2

# Install Packer and Vagrant for development
echo "Installing Packer and Vagrant..."
sudo apt-get install -y packer vagrant

# Install libvirt and related tools
echo "Installing libvirt tools..."
sudo apt-get install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    virtinst \
    virt-manager \
    cpu-checker

# Add vagrant user to libvirt group
sudo usermod -aG libvirt vagrant

# Install vagrant-libvirt plugin dependencies
sudo apt-get install -y \
    build-essential \
    ruby-dev \
    libvirt-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev

# Create useful aliases and environment setup
echo "Setting up development environment..."
sudo -u vagrant tee -a /home/vagrant/.bashrc << 'EOF'

# Development aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'
alias ls='exa'
alias cat='bat'
alias find='fd'
alias ps='procs'
alias top='btm'
alias du='duf'
alias df='duf'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline'
alias gd='git diff'

# Development paths
export PATH="$HOME/.cargo/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"

# UV Python environment
export UV_PYTHON_PREFERENCE=system

# Node.js optimization
export NODE_OPTIONS="--max-old-space-size=4096"
EOF

# Copy bashrc to zshrc for consistency
sudo -u vagrant cp /home/vagrant/.bashrc /home/vagrant/.zshrc

echo "=== Development toolchain installation completed ==="