# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrant configuration for dev-box environment verification
Vagrant.configure("2") do |config|
  # Use reliable Ubuntu 24.04 box
  config.vm.box = "hashicorp-education/ubuntu-24-04"
  config.vm.box_version = ">= 1.0.0"
  
  # Configure VM settings
  config.vm.hostname = "dev-box-smoke-test"
  
  # Network configuration
  config.vm.network "private_network", type: "dhcp"
  
  # VirtualBox provider configuration
  config.vm.provider "virtualbox" do |vb|
    vb.name = "dev-box-smoke-test"
    vb.memory = "1024"
    vb.cpus = 2
    vb.gui = false
    
    # Enable virtualization features
    vb.customize ["modifyvm", :id, "--vram", "16"]
    vb.customize ["modifyvm", :id, "--nested-hw-virt", "on"]
  end
  
  # Provisioning script to handle common Ubuntu 24.04 issues
  config.vm.provision "shell", inline: <<-SHELL
    # Update package list
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    
    # Install essential packages for VirtualBox Guest Additions
    apt-get install -y linux-headers-$(uname -r) build-essential dkms
    
    # Install common development tools
    apt-get install -y curl wget git vim nano
    
    # Create test marker
    echo "env-verifier: VM provisioned successfully on $(date)" > /home/vagrant/provision-complete.txt
    chown vagrant:vagrant /home/vagrant/provision-complete.txt
    
    echo "✅ Provisioning completed successfully"
  SHELL
  
  # Sync project files (optional, for development)
  # config.vm.synced_folder ".", "/vagrant", type: "virtualbox"
end