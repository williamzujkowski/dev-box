#!/bin/bash
set -euo pipefail

echo "=== Installing Development Tools ==="

# Install Node.js (LTS)
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt-get install -y nodejs

# Install Python and pip
echo "Installing Python development tools..."
apt-get install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev

# Install Docker
echo "Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add vagrant user to docker group
usermod -aG docker vagrant

# Install additional development tools
echo "Installing additional development tools..."
apt-get install -y \
  git \
  vim \
  nano \
  htop \
  tree \
  jq \
  curl \
  wget \
  unzip \
  zip \
  tmux \
  screen \
  net-tools \
  telnet \
  netcat-openbsd

# Install VS Code (optional, for GUI environments)
echo "Installing VS Code repository (for future use)..."
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor >packages.microsoft.gpg
install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" >/etc/apt/sources.list.d/vscode.list
apt-get update -y

# Create workspace directories
echo "Setting up development workspace..."
mkdir -p /home/vagrant/workspace/{projects,scripts,logs}
chown -R vagrant:vagrant /home/vagrant/workspace

# Install global npm packages
echo "Installing useful npm packages..."
su - vagrant -c "npm install -g \
    typescript \
    ts-node \
    nodemon \
    pm2 \
    http-server \
    @angular/cli \
    create-react-app \
    vue-cli"

# Install useful Python packages
echo "Installing useful Python packages..."
pip3 install \
  requests \
  flask \
  fastapi \
  uvicorn \
  pytest \
  black \
  flake8 \
  jupyter

# Set up git config template
echo "Setting up git configuration template..."
cat >/home/vagrant/.gitconfig <<EOF
[user]
    name = Test User
    email = test@example.com
[core]
    editor = vim
[init]
    defaultBranch = main
EOF
chown vagrant:vagrant /home/vagrant/.gitconfig

# Set up bashrc additions
echo "Adding useful aliases to bashrc..."
cat >>/home/vagrant/.bashrc <<'EOF'

# Custom aliases for development
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

# Docker aliases
alias dps='docker ps'
alias dpsa='docker ps -a'
alias di='docker images'
alias dex='docker exec -it'
alias dlogs='docker logs'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline'
alias gb='git branch'

# System info
alias sysinfo='echo "=== System Information ===" && uname -a && echo && free -h && echo && df -h'

EOF

echo "=== Development Tools Installation Complete ==="
