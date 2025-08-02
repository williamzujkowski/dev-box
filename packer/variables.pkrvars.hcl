# Ubuntu 24.04 Libvirt Box Variables
# Customize these values for your build environment

# VM Resource Configuration
cpus       = "4"
memory     = "4096"
disk_size  = "25G"

# Build Configuration
vm_name          = "ubuntu-24.04-dev-libvirt"
output_directory = "output"

# Ubuntu 24.04.1 LTS ISO (verify checksum before use)
iso_url      = "https://releases.ubuntu.com/24.04/ubuntu-24.04.1-live-server-amd64.iso"
iso_checksum = "sha256:e240e4b801f7bb68c20d1356b60968ad0c33a41d00d828e74ceb3364a0317be9"

# Vagrant Cloud Configuration (optional - leave empty to skip upload)
# Set these as environment variables or uncomment and fill:
# vagrant_cloud_token    = "your-vagrant-cloud-token"
# vagrant_cloud_username = "your-username"

# Example alternative ISOs (uncomment to use)
# Ubuntu 24.04 Daily Build
# iso_url      = "https://cdimage.ubuntu.com/ubuntu-server/daily-live/current/noble-live-server-amd64.iso"
# iso_checksum = "file:https://cdimage.ubuntu.com/ubuntu-server/daily-live/current/SHA256SUMS"

# Local ISO (if you have downloaded it)
# iso_url      = "file:///path/to/ubuntu-24.04.1-live-server-amd64.iso"
# iso_checksum = "sha256:e240e4b801f7bb68c20d1356b60968ad0c33a41d00d828e74ceb3364a0317be9"