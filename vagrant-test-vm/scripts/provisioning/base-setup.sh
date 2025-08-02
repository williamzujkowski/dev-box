#!/bin/bash
set -euo pipefail

echo "=== Starting Base System Setup ==="

# Update system packages
echo "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install essential packages
echo "Installing essential packages..."
apt-get install -y \
  curl \
  wget \
  git \
  vim \
  htop \
  tree \
  unzip \
  software-properties-common \
  apt-transport-https \
  ca-certificates \
  gnupg \
  lsb-release \
  build-essential \
  dkms \
  linux-headers-$(uname -r)

# Configure timezone
echo "Configuring timezone..."
timedatectl set-timezone UTC

# Configure locale
echo "Configuring locale..."
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8

# Create test user directories
echo "Setting up test directories..."
mkdir -p /home/vagrant/{logs,temp,workspace}
chown -R vagrant:vagrant /home/vagrant/{logs,temp,workspace}

# Set up basic security
echo "Configuring basic security..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

# Configure SSH for testing
echo "Configuring SSH..."
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh

# Clean up package cache
echo "Cleaning up..."
apt-get autoremove -y
apt-get autoclean

echo "=== Base System Setup Complete ==="
