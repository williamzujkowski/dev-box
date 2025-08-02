#!/bin/bash
# Libvirt-specific optimizations for Ubuntu 24.04
set -euo pipefail

echo "=== Applying Libvirt Optimizations ==="

# Install and configure QEMU guest agent
echo "Configuring QEMU guest agent..."
sudo apt-get install -y qemu-guest-agent spice-vdagent
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent

# Install virtio drivers and tools
echo "Installing virtio drivers..."
sudo apt-get install -y \
    linux-image-virtual \
    linux-tools-virtual \
    linux-cloud-tools-virtual

# Configure kernel modules for virtio
echo "Configuring virtio kernel modules..."
sudo tee -a /etc/modules << 'EOF'
# Virtio modules for KVM/libvirt
virtio_balloon
virtio_blk
virtio_net
virtio_pci
virtio_ring
virtio_scsi
EOF

# Regenerate initramfs to include virtio modules
sudo update-initramfs -u

# Configure network interface for predictable naming
echo "Configuring network interface naming..."
sudo tee /etc/systemd/network/99-default.link << 'EOF'
[Match]
OriginalName=*

[Link]
NamePolicy=kernel database onboard slot path
MACAddressPolicy=persistent
EOF

# Enable systemd-networkd for better network performance
sudo systemctl enable systemd-networkd

# Configure grub for better console and faster boot
echo "Optimizing GRUB configuration..."
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="[^"]*/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash console=tty0 console=ttyS0,115200n8/' /etc/default/grub
sudo sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0"/' /etc/default/grub
sudo sed -i 's/#GRUB_TERMINAL=console/GRUB_TERMINAL="console serial"/' /etc/default/grub
sudo sed -i 's/#GRUB_SERIAL_COMMAND="serial"/GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"/' /etc/default/grub

# Update GRUB
sudo update-grub

# Configure systemd for faster boot
echo "Optimizing systemd configuration..."
sudo systemctl set-default multi-user.target

# Disable unnecessary services for a minimal system
echo "Disabling unnecessary services..."
sudo systemctl disable \
    apt-daily.timer \
    apt-daily-upgrade.timer \
    motd-news.timer \
    systemd-timesyncd || true

# Configure fstrim for SSD optimization
echo "Enabling periodic fstrim..."
sudo systemctl enable fstrim.timer

# Configure swap settings for better performance
echo "Optimizing swap settings..."
sudo tee -a /etc/sysctl.conf << 'EOF'

# Libvirt/KVM optimizations
vm.swappiness=1
vm.dirty_background_ratio=5
vm.dirty_ratio=10
net.core.rmem_default=262144
net.core.rmem_max=16777216
net.core.wmem_default=262144
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
EOF

# Configure rsyslog to reduce disk I/O
echo "Optimizing logging..."
sudo sed -i 's/#Storage=auto/Storage=volatile/' /etc/systemd/journald.conf
sudo sed -i 's/#RuntimeMaxUse=/RuntimeMaxUse=32M/' /etc/systemd/journald.conf

# Create libvirt-specific metadata
echo "Creating libvirt metadata..."
sudo mkdir -p /etc/libvirt-box
sudo tee /etc/libvirt-box/info << 'EOF'
{
  "box_name": "ubuntu-24.04-dev-libvirt",
  "box_version": "1.0.0",
  "description": "Ubuntu 24.04 LTS with development tools optimized for libvirt",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "provider": "libvirt",
  "architecture": "x86_64",
  "features": [
    "qemu-guest-agent",
    "virtio-drivers",
    "development-tools",
    "docker",
    "vagrant-ready"
  ]
}
EOF

# Install and configure cloud-init for libvirt
echo "Configuring cloud-init for libvirt..."
sudo apt-get install -y cloud-init
sudo tee /etc/cloud/cloud.cfg.d/99-libvirt.cfg << 'EOF'
# Libvirt-specific cloud-init configuration
datasource_list: ['NoCloud', 'ConfigDrive']
system_info:
  default_user:
    name: vagrant
    lock_passwd: false
    gecos: Vagrant User
    groups: [adm, audio, cdrom, dialout, dip, floppy, lxd, netdev, plugdev, sudo, video]
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
    shell: /bin/bash
  distro: ubuntu
  paths:
    cloud_dir: /var/lib/cloud
    run_dir: /run/cloud-init
  ssh_svcname: ssh
EOF

# Ensure proper permissions
sudo chmod 644 /etc/cloud/cloud.cfg.d/99-libvirt.cfg

# Configure udev rules for consistent device naming
echo "Setting up udev rules..."
sudo tee /etc/udev/rules.d/70-persistent-net.rules << 'EOF'
# Libvirt network device naming
SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{address}=="*", ATTR{dev_id}=="0x0", ATTR{type}=="1", KERNEL=="eth*", NAME="eth0"
EOF

# Configure systemd-resolved for better DNS performance
echo "Configuring DNS resolution..."
sudo systemctl enable systemd-resolved
sudo tee /etc/systemd/resolved.conf.d/libvirt.conf << 'EOF'
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1 1.0.0.1
DNSStubListener=yes
Cache=yes
EOF

echo "=== Libvirt optimizations completed ==="