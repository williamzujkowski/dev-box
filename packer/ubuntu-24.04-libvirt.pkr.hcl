# Ubuntu 24.04 LTS Libvirt Box Configuration
# Based on hashicorp-education template with cloud-init autoinstall

packer {
  required_version = ">= 1.10.0"
  required_plugins {
    qemu = {
      version = "~> 1.1.0"
      source  = "github.com/hashicorp/qemu"
    }
  }
}

# Variables
variable "cpus" {
  type        = string
  default     = "2"
  description = "Number of CPUs"
}

variable "memory" {
  type        = string
  default     = "2048"
  description = "Amount of memory in MB"
}

variable "disk_size" {
  type        = string
  default     = "20G"
  description = "Disk size"
}

variable "iso_url" {
  type        = string
  default     = "https://releases.ubuntu.com/24.04/ubuntu-24.04.1-live-server-amd64.iso"
  description = "Ubuntu 24.04 ISO URL"
}

variable "iso_checksum" {
  type        = string
  default     = "sha256:e240e4b801f7bb68c20d1356b60968ad0c33a41d00d828e74ceb3364a0317be9"
  description = "ISO checksum"
}

variable "output_directory" {
  type        = string
  default     = "output"
  description = "Output directory for built images"
}

variable "vm_name" {
  type        = string
  default     = "ubuntu-24.04-libvirt"
  description = "VM name"
}

variable "vagrant_cloud_token" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Vagrant Cloud API token"
}

variable "vagrant_cloud_username" {
  type        = string
  default     = ""
  description = "Vagrant Cloud username"
}

# Local variables
locals {
  timestamp = regex_replace(timestamp(), "[- TZ:]", "")
  vm_name   = "${var.vm_name}-${local.timestamp}"
}

# Source configuration for QEMU/KVM (libvirt)
source "qemu" "ubuntu-24-04" {
  # ISO configuration
  iso_url      = var.iso_url
  iso_checksum = var.iso_checksum
  
  # VM specifications
  cpus         = var.cpus
  memory       = var.memory
  disk_size    = var.disk_size
  format       = "qcow2"
  accelerator  = "kvm"
  
  # Network configuration
  net_device     = "virtio-net"
  disk_interface = "virtio"
  
  # Display and interaction
  headless       = true
  vnc_bind_address = "0.0.0.0"
  vnc_port_min   = 5900
  vnc_port_max   = 5999
  
  # Output configuration
  output_directory = "${var.output_directory}/${local.vm_name}"
  vm_name         = "${local.vm_name}.qcow2"
  
  # Cloud-init configuration
  cd_files = [
    "./cloud-init/user-data",
    "./cloud-init/meta-data"
  ]
  cd_label = "cidata"
  
  # Boot configuration
  boot_wait = "5s"
  boot_command = [
    "c<wait>",
    "linux /casper/vmlinuz autoinstall ds='nocloud;s=/dev/sr1/' quiet ---",
    "<enter><wait>",
    "initrd /casper/initrd",
    "<enter><wait>",
    "boot",
    "<enter>"
  ]
  
  # SSH configuration
  ssh_username     = "vagrant"
  ssh_private_key_file = "~/.ssh/id_rsa"
  ssh_timeout     = "20m"
  ssh_wait_timeout = "20m"
  
  # Shutdown configuration
  shutdown_command = "echo 'vagrant' | sudo -S shutdown -P now"
  shutdown_timeout = "5m"
}

# Build configuration
build {
  name = "ubuntu-24-04-libvirt"
  sources = ["source.qemu.ubuntu-24-04"]
  
  # Wait for cloud-init to complete
  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to complete...'",
      "cloud-init status --wait",
      "echo 'Cloud-init completed successfully'"
    ]
  }
  
  # System updates and cleanup
  provisioner "shell" {
    inline = [
      "echo 'Updating system packages...'",
      "sudo apt-get update",
      "sudo apt-get upgrade -y",
      "sudo apt-get autoremove -y",
      "sudo apt-get autoclean"
    ]
  }
  
  # Install development toolchain
  provisioner "shell" {
    script = "./scripts/install-dev-tools.sh"
  }
  
  # Configure vagrant user and SSH
  provisioner "shell" {
    script = "./scripts/configure-vagrant.sh"
  }
  
  # Libvirt optimizations
  provisioner "shell" {
    script = "./scripts/libvirt-optimizations.sh"
  }
  
  # Final cleanup and preparation
  provisioner "shell" {
    script = "./scripts/cleanup.sh"
  }
  
  # Create Vagrant box
  post-processor "vagrant" {
    output = "${var.output_directory}/${var.vm_name}.box"
    provider_override = "libvirt"
  }
  
  # Upload to Vagrant Cloud (optional)
  post-processor "vagrant-cloud" {
    access_token        = var.vagrant_cloud_token
    box_tag            = "${var.vagrant_cloud_username}/${var.vm_name}"
    version            = "1.0.${local.timestamp}"
    version_description = "Ubuntu 24.04 LTS with development tools for libvirt"
    no_release         = false
    
    # Only run if token is provided
    only = var.vagrant_cloud_token != "" ? ["qemu.ubuntu-24-04"] : []
  }
}