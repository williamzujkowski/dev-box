# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrant configuration for dev-box environment verification
# Primary provider: libvirt (KVM/QEMU) for optimal Ubuntu 24.04 compatibility
Vagrant.configure("2") do |config|
  # Ubuntu 24.04 LTS local box optimized for libvirt
  config.vm.box = "local/ubuntu-24.04-libvirt"
  config.vm.box_version = ">= 1.0.0"
  
  # Configure VM settings
  config.vm.hostname = "dev-box-libvirt-test"
  
  # Network configuration - libvirt private network
  config.vm.network "private_network", type: "dhcp"
  config.vm.network "forwarded_port", guest: 3000, host: 3000, id: "dev-server"
  config.vm.network "forwarded_port", guest: 8080, host: 8080, id: "web-server"
  
  # Force libvirt provider for KVM/QEMU virtualization
  config.vm.provider :libvirt do |libvirt|
    libvirt.driver = "kvm"
    libvirt.memory = 2048
    libvirt.cpus = 2
    libvirt.machine_type = "pc-q35-6.2"  # Modern machine type for better performance
    libvirt.cpu_mode = "host-passthrough"  # Pass through host CPU features
    libvirt.nested = true
    
    # Storage optimization
    libvirt.volume_cache = "writeback"
    libvirt.disk_bus = "virtio"
    libvirt.storage :file, :size => '20G', :type => 'qcow2'
    
    # CPU topology for better performance
    libvirt.numa_nodes = [
      {
        :cpus => "0-1",
        :memory => "2048"
      }
    ]
    
    # Network optimization
    libvirt.nic_model_type = "virtio"
    libvirt.graphics_type = "none"
    libvirt.video_type = "none"
    
    # Management interface
    libvirt.management_network_name = "vagrant-libvirt"
    libvirt.management_network_address = "192.168.121.0/24"
  end
  
  # Libvirt-optimized provisioning script
  config.vm.provision "shell", name: "Libvirt Environment Setup", inline: <<-SHELL
    set -e
    
    echo "🚀 Starting libvirt-optimized Ubuntu 24.04 provisioning..."
    
    # Set non-interactive mode
    export DEBIAN_FRONTEND=noninteractive
    
    # Update package list
    apt-get update -y
    
    # Install essential packages for KVM guest
    apt-get install -y \
      linux-headers-$(uname -r) \
      build-essential \
      dkms \
      qemu-guest-agent \
      spice-vdagent \
      virtio-modules-$(uname -r) \
      curl \
      wget \
      git \
      vim \
      nano \
      htop \
      tree \
      jq
    
    # Configure QEMU guest agent for better host-guest integration
    systemctl enable qemu-guest-agent
    systemctl start qemu-guest-agent
    
    # Optimize for KVM environment
    echo 'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT elevator=noop"' >> /etc/default/grub
    update-grub
    
    # Set up virtio-scsi optimizations
    echo 'ACTION=="add|change", KERNEL=="sd*[!0-9]", ATTR{queue/scheduler}="mq-deadline"' > /etc/udev/rules.d/60-scheduler.rules
    
    # Create test marker with libvirt-specific info
    cat > /home/vagrant/provision-complete.txt <<EOF
env-verifier: Libvirt VM provisioned successfully on $(date)
hypervisor: $(systemd-detect-virt)
kernel: $(uname -r)
memory: $(free -h | grep Mem | awk '{print $2}')
cpus: $(nproc)
disk_scheduler: $(cat /sys/block/vda/queue/scheduler 2>/dev/null || echo "virtio-scsi")
qemu_agent: $(systemctl is-active qemu-guest-agent)
EOF
    chown vagrant:vagrant /home/vagrant/provision-complete.txt
    
    echo "✅ Libvirt provisioning completed successfully"
    echo "📊 Hypervisor: $(systemd-detect-virt)"
    echo "🔧 QEMU Guest Agent: $(systemctl is-active qemu-guest-agent)"
  SHELL
  
  # Sync project files with NFS for better performance
  config.vm.synced_folder ".", "/vagrant", type: "nfs", nfs_version: 4, nfs_udp: false
end