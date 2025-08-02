# KVM Module Management Scripts

This directory contains safe and comprehensive scripts for managing KVM kernel
modules with proper safety checks, rollback capabilities, and testing utilities.

## Scripts Overview

### 1. `kvm-unload.sh` - Main KVM Module Unloader

A comprehensive bash script for safely unloading KVM modules with extensive
safety checks and rollback capabilities.

#### Key Features

- **Safety First**: Checks for running VMs before unloading
- **Comprehensive Checks**: Detects VMs from virsh, QEMU, and VirtualBox
- **Backup & Rollback**: Creates backups and provides rollback mechanism
- **Permanent Blacklisting**: Option to prevent KVM modules from loading on boot
- **Dry Run Mode**: Test what would happen without making changes
- **Verbose Logging**: Detailed logging to file and console
- **Force Mode**: Override safety checks when necessary (use carefully!)

#### Usage Examples

```bash
# Basic safe unload (recommended)
sudo ./kvm-unload.sh

# See what would happen without doing it
sudo ./kvm-unload.sh --dry-run

# Force unload even if VMs are running (DANGEROUS!)
sudo ./kvm-unload.sh --force

# Unload and create permanent blacklist
sudo ./kvm-unload.sh --permanent

# Rollback previous operation
sudo ./kvm-unload.sh --rollback

# Verbose output for debugging
sudo ./kvm-unload.sh --verbose

# Get help
./kvm-unload.sh --help
```

#### Safety Mechanisms

1. **VM Detection**: Automatically detects running VMs from:

   - virsh (libvirt/KVM)
   - QEMU processes
   - VirtualBox VMs

2. **Backup System**: Creates timestamped backups including:

   - Current module state
   - System messages (dmesg)
   - Existing blacklist files

3. **Rollback Capability**: Can restore previous state including:

   - Module loading state
   - Blacklist configurations

4. **Proper Unload Order**: Unloads modules in correct dependency order:
   - kvm_intel/kvm_amd first
   - kvm module last

### 2. `test-kvm-unload.sh` - Comprehensive Testing Script

Tests the functionality of the KVM unload script to ensure it works correctly in
your environment.

#### Usage Examples

```bash
# Run safe tests (no root required)
./test-kvm-unload.sh --safe-only

# Run all tests (requires root)
sudo ./test-kvm-unload.sh --all

# Run only root tests
sudo ./test-kvm-unload.sh --root-tests

# Get help
./test-kvm-unload.sh --help
```

#### Test Categories

**Safe Tests (No Root Required)**:

- Script syntax validation
- Help output functionality
- Permission checking
- Dependency availability

**Root Tests (Requires Root)**:

- KVM status detection
- Dry run functionality
- VM detection accuracy

## Installation and Setup

1. **Make scripts executable**:

   ```bash
   chmod +x kvm-unload.sh test-kvm-unload.sh
   ```

2. **Test the scripts**:

   ```bash
   # Test without root first
   ./test-kvm-unload.sh --safe-only

   # Test with root (if needed)
   sudo ./test-kvm-unload.sh --all
   ```

3. **Run a dry run to see what would happen**:
   ```bash
   sudo ./kvm-unload.sh --dry-run --verbose
   ```

## Common Use Cases

### Scenario 1: Need to disable KVM temporarily for testing

```bash
# Check current status
lsmod | grep kvm

# Safely unload (will fail if VMs running)
sudo ./kvm-unload.sh

# Verify unload
lsmod | grep kvm

# Later, to restore (reboot or manual modprobe)
sudo modprobe kvm_intel  # or kvm_amd for AMD
```

### Scenario 2: Permanent KVM disabling for nested virtualization

```bash
# Unload and blacklist permanently
sudo ./kvm-unload.sh --permanent

# This will prevent KVM from loading on reboot
# Useful for nested virtualization scenarios
```

### Scenario 3: Force unload when VMs are stuck

```bash
# DANGEROUS: Only use if you understand the risks
sudo ./kvm-unload.sh --force --verbose

# This will unload even if VMs appear to be running
# May cause data loss in running VMs!
```

### Scenario 4: Rollback after issues

```bash
# If something went wrong, rollback
sudo ./kvm-unload.sh --rollback

# This will restore the previous state
```

## Troubleshooting

### Script Won't Run

- Check permissions: `ls -la kvm-unload.sh`
- Ensure executable: `chmod +x kvm-unload.sh`
- Check syntax: `bash -n kvm-unload.sh`

### "Module in use" errors

- Check for hidden VM processes: `pgrep -fl qemu`
- Check for other virtualization: `lsof /dev/kvm`
- Use `--force` if absolutely necessary (DANGEROUS)

### Rollback doesn't work

- Check for backup directory: `ls -la /tmp/kvm-backup-*`
- Manual rollback: Look in backup directory for previous state
- Reboot to reset to default state

### Blacklist not working

- Verify file created: `cat /etc/modprobe.d/blacklist-kvm.conf`
- Update initramfs: `sudo update-initramfs -u`
- Reboot to test

## Log Files

The script creates detailed logs in `/tmp/kvm-unload.log` including:

- All operations performed
- Error messages and warnings
- Timestamps for all actions
- Module states before/after

## Security Considerations

- **Run as root**: Required for module operations
- **Check VMs first**: Always verify no important VMs are running
- **Use dry-run**: Test before making changes
- **Keep backups**: The script creates backups, but keep your own too
- **Understand force mode**: Only use `--force` if you understand the risks

## Dependencies

**Required**:

- bash
- lsmod, modprobe, rmmod (from kmod package)
- Basic utilities: mkdir, cp, date, pgrep

**Optional** (for VM detection):

- virsh (libvirt-clients)
- VBoxManage (virtualbox)

## Exit Codes

- `0`: Success
- `1`: General error (permission, module unload failed, etc.)
- `2`: VMs running (when not in force mode)

## Backup Directory Structure

```
/tmp/kvm-backup-YYYYMMDD-HHMMSS/
├── modules_before.txt      # lsmod output before changes
├── dmesg_before.txt       # system messages before changes
└── blacklist_backup.conf  # previous blacklist (if existed)
```

This structure allows for complete rollback of changes made by the script.
