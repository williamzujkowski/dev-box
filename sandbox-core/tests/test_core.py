"""
Basic tests for sandbox core functionality

These are minimal tests to verify the basic structure and imports work correctly.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path

# Import main modules
from sandbox import (
    SandboxCore, SandboxConfig, SandboxState,
    SandboxInitializer, StateManager,
    StateTracker, HealthMonitor,
    RollbackManager, SafetyValidator
)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def basic_config(temp_workspace):
    """Create basic sandbox configuration for testing"""
    return SandboxConfig(
        sandbox_id="test-sandbox",
        workspace_path=temp_workspace,
        resource_limits={
            "memory_mb": 512,
            "cpu_percent": 25,
            "disk_mb": 1024
        },
        safety_constraints={
            "max_snapshots": 5,
            "auto_cleanup_hours": 24,
            "network": {"allow_external": False}
        },
        monitoring_config={
            "collection_interval": 10,
            "health_check_interval": 30
        }
    )


class TestSandboxCore:
    """Test sandbox core functionality"""
    
    def test_sandbox_config_creation(self, basic_config):
        """Test sandbox configuration creation"""
        assert basic_config.sandbox_id == "test-sandbox"
        assert basic_config.resource_limits["memory_mb"] == 512
        assert basic_config.safety_constraints["max_snapshots"] == 5
    
    def test_sandbox_core_creation(self, basic_config):
        """Test sandbox core instantiation"""
        core = SandboxCore(basic_config)
        assert core.config == basic_config
        assert core.state == SandboxState.UNINITIALIZED
        assert isinstance(core.initializer, SandboxInitializer)
        assert isinstance(core.state_manager, StateManager)
        assert isinstance(core.state_tracker, StateTracker)
        assert isinstance(core.health_monitor, HealthMonitor)
        assert isinstance(core.rollback_manager, RollbackManager)
        assert isinstance(core.safety_validator, SafetyValidator)


class TestSandboxInitializer:
    """Test sandbox initializer"""
    
    def test_initializer_creation(self, basic_config):
        """Test initializer instantiation"""
        initializer = SandboxInitializer(basic_config)
        assert initializer.config == basic_config
    
    @pytest.mark.asyncio
    async def test_workspace_setup(self, basic_config):
        """Test workspace setup"""
        initializer = SandboxInitializer(basic_config)
        
        # Setup workspace
        success = await initializer.setup_workspace()
        assert success
        
        # Check workspace structure
        workspace = basic_config.workspace_path
        assert workspace.exists()
        assert (workspace / "work").exists()
        assert (workspace / "tmp").exists()
        assert (workspace / "logs").exists()
        assert (workspace / "config").exists()
        assert (workspace / "snapshots").exists()
        assert (workspace / "secrets").exists()


class TestStateManager:
    """Test state manager"""
    
    def test_state_manager_creation(self, basic_config):
        """Test state manager instantiation"""
        state_manager = StateManager(basic_config)
        assert state_manager.config == basic_config
    
    @pytest.mark.asyncio
    async def test_state_operations(self, basic_config):
        """Test basic state operations"""
        state_manager = StateManager(basic_config)
        
        # Initialize
        success = await state_manager.initialize()
        assert success
        
        # Set and get state
        success = await state_manager.set_state("test_key", "test_value")
        assert success
        
        value = await state_manager.get_state("test_key")
        assert value == "test_value"
        
        # List keys
        keys = await state_manager.list_keys()
        assert "test_key" in keys
        
        # Delete state
        success = await state_manager.delete_state("test_key")
        assert success
        
        # Verify deletion
        value = await state_manager.get_state("test_key", default="not_found")
        assert value == "not_found"
        
        # Cleanup
        await state_manager.cleanup()


class TestSafetyValidator:
    """Test safety validator"""
    
    def test_validator_creation(self, basic_config):
        """Test validator instantiation"""
        validator = SafetyValidator(basic_config)
        assert validator.config == basic_config
    
    @pytest.mark.asyncio
    async def test_operation_validation(self, basic_config):
        """Test operation validation"""
        validator = SafetyValidator(basic_config)
        
        # Test safe operation
        safe_operation = {
            "type": "file_operation",
            "command": "echo 'hello world'",
            "files": ["/tmp/test.txt"]
        }
        
        result = await validator.validate_operation(safe_operation)
        assert isinstance(result.is_safe, bool)
        assert isinstance(result.risk_level.value, str)
        
        # Test potentially unsafe operation
        unsafe_operation = {
            "type": "system_command",
            "command": "rm -rf /important/data",
            "requires_network": True
        }
        
        result = await validator.validate_operation(unsafe_operation)
        # Should detect issues with this operation
        assert len(result.violations) > 0 or not result.is_safe
    
    @pytest.mark.asyncio
    async def test_content_validation(self, basic_config):
        """Test content validation"""
        validator = SafetyValidator(basic_config)
        
        # Test safe content
        safe_content = "print('Hello, World!')"
        result = await validator.validate_content(safe_content, "code")
        assert isinstance(result.is_safe, bool)
        
        # Test potentially unsafe content
        unsafe_content = 'eval("malicious_code()")'
        result = await validator.validate_content(unsafe_content, "code")
        # Should detect dangerous patterns
        assert len(result.violations) > 0 or not result.is_safe


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_basic_sandbox_lifecycle(self, basic_config):
        """Test complete sandbox lifecycle"""
        # Create sandbox
        sandbox = SandboxCore(basic_config)
        
        # Initialize
        success = await sandbox.initialize()
        assert success
        assert sandbox.state == SandboxState.ACTIVE
        
        # Get status
        status = await sandbox.get_status()
        assert status["sandbox_id"] == basic_config.sandbox_id
        assert status["state"] == SandboxState.ACTIVE.value
        
        # Execute a simple operation
        operation = {
            "type": "file_operation",
            "id": "test_op",
            "command": "echo 'test'",
            "create_snapshot": False  # Skip snapshot for this test
        }
        
        result = await sandbox.execute_operation(operation)
        assert "success" in result
        assert result["operation_id"] == "test_op"
        
        # Cleanup
        success = await sandbox.cleanup()
        assert success
        assert sandbox.state == SandboxState.TERMINATED


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])