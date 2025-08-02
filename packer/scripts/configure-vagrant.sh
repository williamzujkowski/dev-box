#!/bin/bash
# Vagrant User Configuration Script
set -euo pipefail

echo "=== Configuring Vagrant User and SSH ==="

# Ensure vagrant user exists and is properly configured
if ! id vagrant &>/dev/null; then
    echo "Creating vagrant user..."
    sudo useradd -m -s /bin/bash vagrant
fi

# Set up vagrant user sudoers
echo "Configuring sudo access for vagrant user..."
sudo tee /etc/sudoers.d/vagrant << 'EOF'
vagrant ALL=(ALL) NOPASSWD:ALL
Defaults:vagrant !requiretty
EOF
sudo chmod 440 /etc/sudoers.d/vagrant

# Create .ssh directory for vagrant user
echo "Setting up SSH for vagrant user..."
sudo -u vagrant mkdir -p /home/vagrant/.ssh
sudo chmod 700 /home/vagrant/.ssh

# Install Vagrant insecure public key
echo "Installing Vagrant insecure public key..."
sudo -u vagrant tee /home/vagrant/.ssh/authorized_keys << 'EOF'
ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key
EOF
sudo chmod 600 /home/vagrant/.ssh/authorized_keys
sudo chown -R vagrant:vagrant /home/vagrant/.ssh

# Configure SSH daemon for security and Vagrant compatibility
echo "Configuring SSH daemon..."
sudo tee -a /etc/ssh/sshd_config << 'EOF'

# Vagrant-specific SSH configuration
UseDNS no
GSSAPIAuthentication no
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile %h/.ssh/authorized_keys
UsePAM yes
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
EOF

# Restart SSH service
sudo systemctl restart ssh
sudo systemctl enable ssh

# Set up vagrant user home directory permissions
echo "Setting home directory permissions..."
sudo chmod 755 /home/vagrant
sudo chown vagrant:vagrant /home/vagrant

# Create useful directories
echo "Creating user directories..."
sudo -u vagrant mkdir -p /home/vagrant/{bin,src,tmp,projects}

# Set up git configuration
echo "Setting up Git configuration..."
sudo -u vagrant git config --global user.name "Vagrant User"
sudo -u vagrant git config --global user.email "vagrant@localhost"
sudo -u vagrant git config --global init.defaultBranch main
sudo -u vagrant git config --global pull.rebase false

# Set up SSH client configuration
echo "Setting up SSH client configuration..."
sudo -u vagrant tee /home/vagrant/.ssh/config << 'EOF'
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel QUIET
    IdentitiesOnly yes
EOF
sudo chmod 600 /home/vagrant/.ssh/config
sudo chown vagrant:vagrant /home/vagrant/.ssh/config

# Install vagrant-libvirt plugin (will be available when box is used)
echo "Preparing for vagrant-libvirt plugin..."
sudo -u vagrant tee /home/vagrant/.vagrant_setup << 'EOF'
#!/bin/bash
# Run this after first boot to install vagrant-libvirt plugin
vagrant plugin install vagrant-libvirt
EOF
sudo chmod +x /home/vagrant/.vagrant_setup

echo "=== Vagrant user configuration completed ==="