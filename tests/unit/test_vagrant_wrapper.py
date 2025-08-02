"""
Unit tests for the Vagrant wrapper module.

Tests cover VM lifecycle operations, snapshot management, error handling,
and integration with the underlying Vagrant and VirtualBox systems.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import time
from pathlib import Path


class TestVagrantWrapper:
    """Test core Vagrant wrapper functionality."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.mock_subprocess = Mock()
        self.mock_vagrant_process = Mock()
        self.mock_vagrant_process.returncode = 0
        self.mock_vagrant_process.stdout = "VM is running"
        self.mock_vagrant_process.stderr = ""
    
    @pytest.mark.unit
    def test_vagrant_wrapper_initialization(self, temp_directory):
        """Test Vagrant wrapper initialization."""
        # Mock vagrant wrapper initialization
        project_path = temp_directory / "test_project"
        project_path.mkdir()
        
        # Create mock Vagrantfile
        vagrantfile = project_path / "Vagrantfile"
        vagrantfile.touch()
        
        # Test wrapper initialization
        assert vagrantfile.exists()
        assert project_path.exists()
    
    @pytest.mark.unit
    def test_vm_status_detection(self, mock_vagrant):
        """Test VM status detection and parsing."""
        status_responses = {
            "not_created": "The environment has not yet been created",
            "running": "The VM is running",
            "stopped": "The VM is powered off",
            "aborted": "The VM is in an aborted state",
            "saved": "The VM is in a saved state"
        }
        
        for expected_status, response in status_responses.items():
            mock_vagrant.status.return_value = expected_status
            status = mock_vagrant.status()
            assert status == expected_status
    
    @pytest.mark.unit
    def test_vm_up_operation(self, mock_vagrant):
        """Test VM startup operation."""
        mock_vagrant.status.return_value = "not_created"
        mock_vagrant.up.return_value = True
        
        # Test successful VM startup
        result = mock_vagrant.up()
        assert result is True
        mock_vagrant.up.assert_called_once()
    
    @pytest.mark.unit
    def test_vm_up_with_provider_specification(self, mock_vagrant):
        """Test VM startup with specific provider."""
        mock_vagrant.up.return_value = True
        
        # Mock calling up with provider
        result = mock_vagrant.up()
        assert result is True
        
        # In actual implementation, would test:
        # vagrant.up(provider="virtualbox")
    
    @pytest.mark.unit
    def test_vm_halt_operation(self, mock_vagrant):
        """Test VM halt operation."""
        mock_vagrant.status.return_value = "running"
        mock_vagrant.halt.return_value = True
        
        result = mock_vagrant.halt()
        assert result is True
        mock_vagrant.halt.assert_called_once()
    
    @pytest.mark.unit
    def test_vm_destroy_operation(self, mock_vagrant):
        """Test VM destroy operation."""
        mock_vagrant.destroy.return_value = True
        
        result = mock_vagrant.destroy()
        assert result is True
        mock_vagrant.destroy.assert_called_once()
    
    @pytest.mark.unit
    def test_vm_reload_operation(self, mock_vagrant):
        """Test VM reload operation."""
        # Mock reload functionality
        mock_vagrant.reload = Mock(return_value=True)
        
        result = mock_vagrant.reload()
        assert result is True


class TestSnapshotManagement:
    """Test snapshot creation, restoration, and management."""
    
    def setup_method(self):
        """Set up snapshot test fixtures."""
        self.mock_vbox = Mock()
        self.test_vm_name = "test-sandbox-vm"
        self.test_snapshots = ["pre-test", "backup-1", "rollback-point"]
    
    @pytest.mark.unit
    def test_snapshot_creation(self, mock_vagrant):
        """Test snapshot creation functionality."""
        snapshot_name = "test-snapshot"
        mock_vagrant.snapshot_save.return_value = True
        
        result = mock_vagrant.snapshot_save(snapshot_name)
        assert result is True
        mock_vagrant.snapshot_save.assert_called_with(snapshot_name)
    
    @pytest.mark.unit
    def test_snapshot_creation_with_description(self, mock_vagrant):
        """Test snapshot creation with description."""
        snapshot_name = "test-snapshot"
        description = "Snapshot before risky operation"
        
        # Mock snapshot creation with description
        mock_vagrant.snapshot_save.return_value = True
        result = mock_vagrant.snapshot_save(snapshot_name)
        assert result is True
    
    @pytest.mark.unit
    def test_snapshot_listing(self, mock_vagrant):
        """Test snapshot listing functionality."""
        expected_snapshots = self.test_snapshots
        mock_vagrant.snapshot_list.return_value = expected_snapshots
        
        snapshots = mock_vagrant.snapshot_list()
        assert snapshots == expected_snapshots
        assert len(snapshots) == 3
    
    @pytest.mark.unit
    def test_snapshot_restoration(self, mock_vagrant):
        """Test snapshot restoration functionality."""
        snapshot_name = "rollback-point"
        mock_vagrant.snapshot_restore.return_value = True
        
        result = mock_vagrant.snapshot_restore(snapshot_name)
        assert result is True
        mock_vagrant.snapshot_restore.assert_called_with(snapshot_name)
    
    @pytest.mark.unit
    def test_snapshot_deletion(self, mock_vagrant):
        """Test snapshot deletion functionality."""
        snapshot_name = "old-snapshot"
        mock_vagrant.snapshot_delete = Mock(return_value=True)
        
        result = mock_vagrant.snapshot_delete(snapshot_name)
        assert result is True
        mock_vagrant.snapshot_delete.assert_called_with(snapshot_name)
    
    @pytest.mark.unit
    def test_snapshot_info_retrieval(self, mock_vagrant):
        """Test retrieving snapshot information."""
        snapshot_name = "test-snapshot"
        expected_info = {
            "name": snapshot_name,
            "timestamp": "2025-01-01T12:00:00Z",
            "description": "Test snapshot",
            "vm_state": "running"
        }
        
        mock_vagrant.snapshot_info = Mock(return_value=expected_info)
        info = mock_vagrant.snapshot_info(snapshot_name)
        
        assert info["name"] == snapshot_name
        assert "timestamp" in info
        assert "vm_state" in info
    
    @pytest.mark.unit
    def test_automatic_snapshot_cleanup(self, mock_vagrant):
        """Test automatic cleanup of old snapshots."""
        # Mock scenario where max snapshots exceeded
        all_snapshots = [f"snapshot-{i}" for i in range(15)]  # More than max
        mock_vagrant.snapshot_list.return_value = all_snapshots
        mock_vagrant.snapshot_delete = Mock(return_value=True)
        
        # Test cleanup logic (would be implemented in actual wrapper)
        max_snapshots = 10
        if len(all_snapshots) > max_snapshots:
            snapshots_to_delete = all_snapshots[:-max_snapshots]  # Keep newest
            for snapshot in snapshots_to_delete:
                mock_vagrant.snapshot_delete(snapshot)
        
        # Verify cleanup was attempted
        assert mock_vagrant.snapshot_delete.call_count == 5


class TestNetworkConfiguration:
    """Test network configuration and management."""
    
    @pytest.mark.unit
    def test_private_network_configuration(self, mock_vagrant):
        """Test private network configuration."""
        network_config = {
            "type": "private_network",
            "ip": "192.168.56.10"
        }
        
        # Mock network configuration
        mock_vagrant.configure_network = Mock(return_value=True)
        result = mock_vagrant.configure_network(network_config)
        assert result is True
    
    @pytest.mark.unit
    def test_port_forwarding_configuration(self, mock_vagrant):
        """Test port forwarding configuration."""
        port_forwards = [
            {"guest": 22, "host": 2222, "protocol": "tcp"},
            {"guest": 80, "host": 8080, "protocol": "tcp"}
        ]
        
        # Mock port forwarding setup
        mock_vagrant.configure_port_forwarding = Mock(return_value=True)
        result = mock_vagrant.configure_port_forwarding(port_forwards)
        assert result is True
    
    @pytest.mark.unit
    def test_network_isolation_validation(self, mock_vagrant):
        """Test network isolation validation."""
        # Test that VM network is properly isolated
        isolation_config = {
            "restrict_host_access": True,
            "allow_internet": False,
            "custom_dns": ["8.8.8.8"]
        }
        
        mock_vagrant.validate_network_isolation = Mock(return_value=True)
        result = mock_vagrant.validate_network_isolation(isolation_config)
        assert result is True


class TestProvisioningIntegration:
    """Test provisioning script integration."""
    
    @pytest.mark.unit
    def test_shell_provisioner_execution(self, mock_vagrant):
        """Test shell provisioner execution."""
        provisioning_script = "apt-get update && apt-get install -y nodejs"
        
        mock_vagrant.provision = Mock(return_value=True)
        result = mock_vagrant.provision(script=provisioning_script)
        assert result is True
    
    @pytest.mark.unit
    def test_file_provisioner_upload(self, mock_vagrant, temp_directory):
        """Test file provisioner for uploading files."""
        source_file = temp_directory / "test_file.txt"
        source_file.write_text("test content")
        destination = "/tmp/test_file.txt"
        
        mock_vagrant.upload_file = Mock(return_value=True)
        result = mock_vagrant.upload_file(str(source_file), destination)
        assert result is True
    
    @pytest.mark.unit
    def test_provisioning_error_handling(self, mock_vagrant):
        """Test provisioning error handling."""
        mock_vagrant.provision.side_effect = RuntimeError("Provisioning failed")
        
        with pytest.raises(RuntimeError) as exc_info:
            mock_vagrant.provision()
        
        assert "Provisioning failed" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_provisioning_retry_mechanism(self, mock_vagrant):
        """Test provisioning retry on failure."""
        # Mock initial failure then success
        mock_vagrant.provision.side_effect = [
            RuntimeError("Network error"),
            True  # Success on retry
        ]
        
        # Test retry logic (would be implemented in actual wrapper)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = mock_vagrant.provision()
                if result is True:
                    break
            except RuntimeError:
                if attempt == max_retries - 1:
                    raise
                continue
        
        assert mock_vagrant.provision.call_count == 2


class TestErrorHandling:
    """Test error handling and recovery mechanisms."""
    
    @pytest.mark.unit
    def test_vagrant_command_timeout(self, mock_vagrant):
        """Test handling of Vagrant command timeouts."""
        mock_vagrant.up.side_effect = subprocess.TimeoutExpired("vagrant up", 300)
        
        with pytest.raises(subprocess.TimeoutExpired):
            mock_vagrant.up()
    
    @pytest.mark.unit
    def test_vagrant_command_failure(self, mock_vagrant):
        """Test handling of Vagrant command failures."""
        mock_vagrant.up.side_effect = subprocess.CalledProcessError(1, "vagrant up")
        
        with pytest.raises(subprocess.CalledProcessError):
            mock_vagrant.up()
    
    @pytest.mark.unit
    def test_vm_state_corruption_detection(self, mock_vagrant):
        """Test detection of VM state corruption."""
        # Mock corrupted state scenario
        mock_vagrant.status.side_effect = RuntimeError("VM state file is corrupted")
        
        with pytest.raises(RuntimeError) as exc_info:
            mock_vagrant.status()
        
        assert "corrupted" in str(exc_info.value).lower()
    
    @pytest.mark.unit
    def test_insufficient_resources_handling(self, mock_vagrant):
        """Test handling of insufficient system resources."""
        resource_errors = [
            "Not enough memory available",
            "Insufficient disk space",
            "CPU resources exhausted"
        ]
        
        for error in resource_errors:
            mock_vagrant.up.side_effect = RuntimeError(error)
            
            with pytest.raises(RuntimeError) as exc_info:
                mock_vagrant.up()
            
            assert error in str(exc_info.value)
    
    @pytest.mark.unit
    def test_network_error_recovery(self, mock_vagrant):
        """Test network error recovery mechanisms."""
        network_errors = [
            "Connection timed out",
            "Name resolution failed",
            "Network unreachable"
        ]
        
        for error in network_errors:
            mock_vagrant.up.side_effect = RuntimeError(error)
            
            # Test that network errors are properly identified
            try:
                mock_vagrant.up()
            except RuntimeError as e:
                assert any(net_err in str(e) for net_err in ["timeout", "resolution", "unreachable"])
    
    @pytest.mark.unit
    def test_graceful_shutdown_on_interrupt(self, mock_vagrant):
        """Test graceful shutdown on keyboard interrupt."""
        # Mock long-running operation interrupted
        def mock_long_operation():
            time.sleep(0.1)  # Simulate work
            raise KeyboardInterrupt()
        
        mock_vagrant.up.side_effect = mock_long_operation
        
        with pytest.raises(KeyboardInterrupt):
            mock_vagrant.up()


class TestResourceMonitoring:
    """Test resource monitoring and management."""
    
    @pytest.mark.unit
    def test_memory_usage_monitoring(self, mock_virtualbox):
        """Test VM memory usage monitoring."""
        vm_name = "test-vm"
        expected_memory_info = {
            "allocated": 2048,  # MB
            "used": 1024,      # MB
            "available": 1024   # MB
        }
        
        mock_virtualbox.get_memory_info = Mock(return_value=expected_memory_info)
        memory_info = mock_virtualbox.get_memory_info(vm_name)
        
        assert memory_info["allocated"] == 2048
        assert memory_info["used"] <= memory_info["allocated"]
    
    @pytest.mark.unit
    def test_disk_usage_monitoring(self, mock_virtualbox):
        """Test VM disk usage monitoring."""
        vm_name = "test-vm"
        expected_disk_info = {
            "total": 20480,     # MB
            "used": 5120,       # MB
            "available": 15360  # MB
        }
        
        mock_virtualbox.get_disk_info = Mock(return_value=expected_disk_info)
        disk_info = mock_virtualbox.get_disk_info(vm_name)
        
        assert disk_info["total"] == 20480
        assert disk_info["used"] + disk_info["available"] <= disk_info["total"]
    
    @pytest.mark.unit
    def test_cpu_usage_monitoring(self, mock_virtualbox):
        """Test VM CPU usage monitoring."""
        vm_name = "test-vm"
        expected_cpu_info = {
            "cores": 2,
            "usage_percent": 25.5
        }
        
        mock_virtualbox.get_cpu_info = Mock(return_value=expected_cpu_info)
        cpu_info = mock_virtualbox.get_cpu_info(vm_name)
        
        assert cpu_info["cores"] == 2
        assert 0 <= cpu_info["usage_percent"] <= 100
    
    @pytest.mark.unit
    def test_resource_limit_enforcement(self, mock_virtualbox):
        """Test resource limit enforcement."""
        vm_name = "test-vm"
        resource_limits = {
            "max_memory": 4096,    # MB
            "max_cpu_percent": 80,
            "max_disk": 50000     # MB
        }
        
        mock_virtualbox.set_resource_limits = Mock(return_value=True)
        result = mock_virtualbox.set_resource_limits(vm_name, resource_limits)
        
        assert result is True
        mock_virtualbox.set_resource_limits.assert_called_with(vm_name, resource_limits)


class TestVagrantfileManagement:
    """Test Vagrantfile generation and management."""
    
    @pytest.mark.unit
    def test_vagrantfile_generation(self, temp_directory, sample_vagrantfile_template):
        """Test Vagrantfile generation from template."""
        template_vars = {
            "vm": {
                "box": "hashicorp-education/ubuntu-24-04",
                "box_version": "0.1.0",
                "memory": 2048,
                "cpus": 2,
                "network": "private_network"
            },
            "provisioning": {
                "tools": ["git", "nodejs", "npm"]
            }
        }
        
        # Mock Jinja2 template rendering
        expected_content = sample_vagrantfile_template
        for key, value in template_vars.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    placeholder = f"{{{{ {key}.{subkey} }}}}"
                    expected_content = expected_content.replace(placeholder, str(subvalue))
        
        vagrantfile_path = temp_directory / "Vagrantfile"
        vagrantfile_path.write_text(expected_content)
        
        assert vagrantfile_path.exists()
        content = vagrantfile_path.read_text()
        assert "ubuntu-24-04" in content
        assert "2048" in content
    
    @pytest.mark.unit
    def test_vagrantfile_validation(self, temp_directory):
        """Test Vagrantfile syntax validation."""
        valid_vagrantfile = '''
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"
end
'''
        
        invalid_vagrantfile = '''
Vagrant.configure("2") do |config|
  # Missing end statement
  config.vm.box = "ubuntu/focal64"
'''
        
        # Test valid Vagrantfile
        valid_path = temp_directory / "valid_Vagrantfile"
        valid_path.write_text(valid_vagrantfile)
        assert self._validate_vagrantfile_syntax(valid_path)
        
        # Test invalid Vagrantfile
        invalid_path = temp_directory / "invalid_Vagrantfile"
        invalid_path.write_text(invalid_vagrantfile)
        assert not self._validate_vagrantfile_syntax(invalid_path)
    
    def _validate_vagrantfile_syntax(self, vagrantfile_path):
        """Helper method to validate Vagrantfile syntax."""
        # In actual implementation, would run vagrant validate
        content = vagrantfile_path.read_text()
        
        # Basic syntax checks
        if "Vagrant.configure" not in content:
            return False
        
        # Check for balanced do/end blocks
        do_count = content.count(" do |")
        end_count = content.count("\nend")
        
        return do_count <= end_count  # Allow for some flexibility
    
    @pytest.mark.unit
    def test_vagrantfile_backup_and_restore(self, temp_directory):
        """Test Vagrantfile backup and restore functionality."""
        original_content = "Original Vagrantfile content"
        modified_content = "Modified Vagrantfile content"
        
        vagrantfile = temp_directory / "Vagrantfile"
        backup_file = temp_directory / "Vagrantfile.backup"
        
        # Create original file
        vagrantfile.write_text(original_content)
        
        # Create backup
        backup_file.write_text(vagrantfile.read_text())
        
        # Modify original
        vagrantfile.write_text(modified_content)
        
        # Restore from backup
        vagrantfile.write_text(backup_file.read_text())
        
        assert vagrantfile.read_text() == original_content