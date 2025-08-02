#!/bin/bash
# Final cleanup script for Ubuntu 24.04 box preparation
set -euo pipefail

echo "=== Starting final cleanup ==="

# Clean package cache
echo "Cleaning package cache..."
sudo apt-get autoremove -y
sudo apt-get autoclean
sudo apt-get clean

# Remove package lists (they'll be regenerated on first apt update)
sudo rm -rf /var/lib/apt/lists/*

# Clean temporary files
echo "Cleaning temporary files..."
sudo rm -rf /tmp/* /var/tmp/*
sudo rm -rf /root/.cache
sudo rm -rf /home/vagrant/.cache

# Clean log files
echo "Cleaning log files..."
sudo truncate -s 0 /var/log/lastlog
sudo truncate -s 0 /var/log/faillog
sudo truncate -s 0 /var/log/wtmp
sudo truncate -s 0 /var/log/btmp
sudo find /var/log -type f -name "*.log" -exec truncate -s 0 {} \;
sudo find /var/log -type f -name "*.gz" -delete
sudo find /var/log -type f -name "*.1" -delete

# Clean journal logs
echo "Cleaning systemd journal..."
sudo journalctl --vacuum-time=1s
sudo journalctl --vacuum-size=1M

# Remove SSH host keys (they'll be regenerated on first boot)
echo "Removing SSH host keys..."
sudo rm -f /etc/ssh/ssh_host_*

# Clean cloud-init state
echo "Cleaning cloud-init state..."
sudo cloud-init clean --logs
sudo rm -rf /var/lib/cloud/instances/*
sudo rm -rf /var/lib/cloud/instance

# Remove machine-id (will be regenerated)
echo "Removing machine-id..."
sudo truncate -s 0 /etc/machine-id
sudo rm -f /var/lib/dbus/machine-id

# Clean network configuration
echo "Cleaning network configuration..."
sudo rm -f /etc/netplan/50-cloud-init.yaml
sudo rm -f /etc/systemd/network/10-netplan-*.network

# Clean bash history
echo "Cleaning bash history..."
sudo rm -f /root/.bash_history
sudo rm -f /home/vagrant/.bash_history
sudo -u vagrant history -c

# Clean vim and other editor temporary files
echo "Cleaning editor temporary files..."
sudo rm -rf /root/.vim*
sudo rm -rf /home/vagrant/.vim*
sudo find /home/vagrant -name ".viminfo" -delete
sudo find /root -name ".viminfo" -delete

# Clean wget/curl cache
sudo rm -rf /root/.wget-hsts
sudo rm -rf /home/vagrant/.wget-hsts

# Zero out swap space to reduce box size
echo "Zeroing swap space..."
if [ -f /swapfile ]; then
    sudo swapoff /swapfile
    sudo dd if=/dev/zero of=/swapfile bs=1M count=1024 conv=notrunc || true
    sudo mkswap /swapfile
    sudo swapon /swapfile
fi

# Clean up any swap partitions
for swap in $(swapon --show=NAME --noheadings); do
    if [[ "$swap" =~ ^/dev/ ]]; then
        echo "Zeroing swap partition $swap..."
        sudo swapoff "$swap"
        sudo dd if=/dev/zero of="$swap" bs=1M || true
        sudo mkswap "$swap"
        sudo swapon "$swap"
    fi
done

# Remove build artifacts and development files that aren't needed
echo "Cleaning development artifacts..."
sudo rm -rf /usr/src/*
sudo rm -rf /var/cache/debconf/*

# Clean up any core dumps
echo "Removing core dumps..."
sudo rm -f /core*

# Clean up any .pyc files
echo "Cleaning Python cache files..."
sudo find / -name "*.pyc" -delete 2>/dev/null || true
sudo find / -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clean Docker if installed
if command -v docker &> /dev/null; then
    echo "Cleaning Docker..."
    sudo docker system prune -af || true
fi

# Clean snap cache
if command -v snap &> /dev/null; then
    echo "Cleaning snap cache..."
    sudo snap list --all | awk '/disabled/{print $1, $3}' | while read snapname revision; do
        sudo snap remove "$snapname" --revision="$revision" || true
    done
fi

# Defragment the disk (optional, for better compression)
echo "Defragmenting free space..."
sudo dd if=/dev/zero of=/EMPTY bs=1M || true
sudo rm -f /EMPTY

# Sync filesystem
echo "Syncing filesystem..."
sync

# Clear the history again (in case any commands above added to it)
sudo rm -f /root/.bash_history
sudo rm -f /home/vagrant/.bash_history
sudo -u vagrant history -c

# Create a file to indicate the box has been properly prepared
echo "Creating box preparation marker..."
sudo tee /etc/box-build-info << EOF
Box built on: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Packer version: $(packer version 2>/dev/null || echo "unknown")
Ubuntu version: $(lsb_release -d | cut -f2)
Kernel version: $(uname -r)
Box type: libvirt/qemu
Build optimizations: enabled
EOF

echo "=== Final cleanup completed ==="
echo "Box is ready for packaging!"

# Optional: Show disk usage
echo "Final disk usage:"
df -h /