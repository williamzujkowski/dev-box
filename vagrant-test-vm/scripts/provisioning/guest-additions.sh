#!/bin/bash
set -euo pipefail

echo "=== Installing VirtualBox Guest Additions ==="

# Variables
VBOX_VERSION=$(dmidecode -s system-product-name | grep VirtualBox | wc -l)
GUEST_ADDITIONS_ISO="/usr/share/virtualbox/VBoxGuestAdditions.iso"

if [ "$VBOX_VERSION" -eq 0 ]; then
    echo "Not running in VirtualBox, skipping Guest Additions installation"
    exit 0
fi

# Install prerequisites
echo "Installing Guest Additions prerequisites..."
apt-get update -y
apt-get install -y \
    dkms \
    build-essential \
    linux-headers-$(uname -r) \
    gcc \
    make \
    perl

# Mount the Guest Additions ISO
echo "Mounting Guest Additions ISO..."
mkdir -p /media/cdrom

# Try to mount from different possible locations
if [ -f "/opt/VBoxGuestAdditions-*/VBoxLinuxAdditions.run" ]; then
    echo "Found VirtualBox Guest Additions installer"
    INSTALLER=$(find /opt -name "VBoxLinuxAdditions.run" | head -1)
elif mount /dev/sr0 /media/cdrom 2>/dev/null || mount /dev/cdrom /media/cdrom 2>/dev/null; then
    echo "Mounted Guest Additions from CD-ROM"
    INSTALLER="/media/cdrom/VBoxLinuxAdditions.run"
else
    echo "Guest Additions ISO not found, attempting to download..."
    # Get VirtualBox version from host
    VBOX_HOST_VERSION=$(VBoxControl --version 2>/dev/null | cut -d'r' -f1 || echo "7.0.0")
    wget -O /tmp/VBoxGuestAdditions.iso \
        "https://download.virtualbox.org/virtualbox/${VBOX_HOST_VERSION}/VBoxGuestAdditions_${VBOX_HOST_VERSION}.iso"
    mount -o loop /tmp/VBoxGuestAdditions.iso /media/cdrom
    INSTALLER="/media/cdrom/VBoxLinuxAdditions.run"
fi

# Install Guest Additions
if [ -f "$INSTALLER" ]; then
    echo "Installing VirtualBox Guest Additions..."
    chmod +x "$INSTALLER"
    "$INSTALLER" --nox11 || {
        echo "Guest Additions installation completed with warnings (normal for headless)"
        # Check if modules are loaded
        if lsmod | grep -q vboxguest; then
            echo "VirtualBox Guest modules loaded successfully"
        else
            echo "Warning: VirtualBox Guest modules not found"
        fi
    }
else
    echo "Error: Guest Additions installer not found"
    exit 1
fi

# Cleanup
echo "Cleaning up Guest Additions installation..."
umount /media/cdrom 2>/dev/null || true
rm -f /tmp/VBoxGuestAdditions.iso 2>/dev/null || true

# Verify installation
echo "Verifying Guest Additions installation..."
if command -v VBoxControl &> /dev/null; then
    echo "VBoxControl found: $(VBoxControl --version)"
else
    echo "Warning: VBoxControl not found in PATH"
fi

if lsmod | grep -q vboxguest; then
    echo "VirtualBox Guest kernel modules loaded successfully"
    lsmod | grep vbox
else
    echo "Warning: VirtualBox Guest kernel modules not loaded"
fi

# Add vagrant user to vboxsf group for shared folders
echo "Adding vagrant user to vboxsf group..."
usermod -a -G vboxsf vagrant

echo "=== VirtualBox Guest Additions Installation Complete ==="