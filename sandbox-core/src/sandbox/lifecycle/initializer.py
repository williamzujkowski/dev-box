"""
Sandbox Initializer - Environment setup and configuration

Handles the initialization of sandbox environments including workspace setup,
resource allocation, and initial configuration validation.
"""

import os
import shutil
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from ..utils.filesystem import safe_mkdir, safe_chmod, validate_path
from ..utils.resources import ResourceManager
from ..utils.validation import ConfigValidator


@dataclass
class InitializationResult:
    """Result of sandbox initialization"""
    success: bool
    sandbox_id: str
    workspace_path: Path
    allocated_resources: Dict[str, Any] = field(default_factory=dict)
    initialization_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SandboxInitializer:
    """
    Handles sandbox environment initialization
    
    Responsibilities:
    - Workspace creation and setup
    - Resource allocation and limits
    - Security configuration
    - Initial environment validation
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(f"sandbox.{config.sandbox_id}.initializer")
        self.resource_manager = ResourceManager(config.resource_limits)
        self.config_validator = ConfigValidator()
        
    async def setup_workspace(self) -> bool:
        """
        Set up the sandbox workspace directory structure
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            self.logger.info(f"Setting up workspace at {self.config.workspace_path}")
            
            # Validate workspace path
            if not validate_path(self.config.workspace_path):
                raise ValueError(f"Invalid workspace path: {self.config.workspace_path}")
            
            # Create main workspace directory
            await safe_mkdir(self.config.workspace_path, mode=0o750)
            
            # Create subdirectories
            subdirs = [
                "work",      # Main working directory
                "tmp",       # Temporary files
                "logs",      # Operation logs
                "snapshots", # State snapshots
                "config",    # Configuration files
                "secrets",   # Secure storage (restricted access)
            ]
            
            for subdir in subdirs:
                subdir_path = self.config.workspace_path / subdir
                await safe_mkdir(subdir_path, mode=0o750)
                
                # Special handling for secrets directory
                if subdir == "secrets":
                    await safe_chmod(subdir_path, 0o700)
            
            # Create workspace metadata
            await self._create_workspace_metadata()
            
            # Set up resource limits
            await self._setup_resource_limits()
            
            # Initialize logging
            await self._setup_logging()
            
            self.logger.info("Workspace setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Workspace setup failed: {e}")
            return False
    
    async def validate_environment(self) -> InitializationResult:
        """
        Validate the sandbox environment before activation
        
        Returns:
            InitializationResult: Comprehensive validation results
        """
        start_time = asyncio.get_event_loop().time()
        result = InitializationResult(
            success=False,
            sandbox_id=self.config.sandbox_id,
            workspace_path=self.config.workspace_path
        )
        
        try:
            self.logger.info("Validating sandbox environment")
            
            # Validate configuration
            config_validation = await self.config_validator.validate(self.config)
            if not config_validation.is_valid:
                result.errors.extend(config_validation.errors)
                result.warnings.extend(config_validation.warnings)
            
            # Check workspace accessibility
            workspace_check = await self._validate_workspace()
            if not workspace_check["accessible"]:
                result.errors.append(f"Workspace not accessible: {workspace_check['error']}")
            
            # Validate resource allocations
            resource_validation = await self.resource_manager.validate_allocations()
            if not resource_validation.is_valid:
                result.errors.extend(resource_validation.errors)
                result.warnings.extend(resource_validation.warnings)
            else:
                result.allocated_resources = resource_validation.allocated_resources
            
            # Check system dependencies
            dependency_check = await self._check_dependencies()
            if not dependency_check["all_available"]:
                missing = dependency_check["missing"]
                result.errors.append(f"Missing dependencies: {', '.join(missing)}")
            
            # Validate security configuration
            security_check = await self._validate_security_config()
            if not security_check["secure"]:
                result.warnings.extend(security_check["issues"])
            
            result.success = len(result.errors) == 0
            result.initialization_time = asyncio.get_event_loop().time() - start_time
            
            if result.success:
                self.logger.info("Environment validation completed successfully")
            else:
                self.logger.error(f"Environment validation failed: {result.errors}")
                
            return result
            
        except Exception as e:
            result.errors.append(f"Validation error: {str(e)}")
            result.initialization_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"Environment validation error: {e}")
            return result
    
    async def cleanup_workspace(self) -> bool:
        """
        Clean up the sandbox workspace
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            self.logger.info(f"Cleaning up workspace {self.config.workspace_path}")
            
            # Stop any running processes in the workspace
            await self._terminate_workspace_processes()
            
            # Clear temporary files first
            tmp_path = self.config.workspace_path / "tmp"
            if tmp_path.exists():
                shutil.rmtree(tmp_path, ignore_errors=True)
            
            # Archive logs if needed
            await self._archive_logs()
            
            # Remove entire workspace
            if self.config.workspace_path.exists():
                shutil.rmtree(self.config.workspace_path, ignore_errors=True)
            
            self.logger.info("Workspace cleanup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Workspace cleanup failed: {e}")
            return False
    
    async def _create_workspace_metadata(self):
        """Create metadata files for the workspace"""
        metadata = {
            "sandbox_id": self.config.sandbox_id,
            "created_at": asyncio.get_event_loop().time(),
            "version": "0.1.0",
            "resource_limits": self.config.resource_limits,
            "safety_constraints": self.config.safety_constraints
        }
        
        metadata_path = self.config.workspace_path / "config" / "metadata.json"
        
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def _setup_resource_limits(self):
        """Configure resource limits for the sandbox"""
        try:
            # Apply memory limits
            memory_limit = self.config.resource_limits.get("memory_mb", 1024)
            await self.resource_manager.set_memory_limit(memory_limit)
            
            # Apply CPU limits
            cpu_limit = self.config.resource_limits.get("cpu_percent", 50)
            await self.resource_manager.set_cpu_limit(cpu_limit)
            
            # Apply disk space limits
            disk_limit = self.config.resource_limits.get("disk_mb", 2048)
            await self.resource_manager.set_disk_limit(disk_limit)
            
            # Apply network limits if specified
            if "network" in self.config.resource_limits:
                await self.resource_manager.set_network_limits(
                    self.config.resource_limits["network"]
                )
                
            self.logger.info("Resource limits configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup resource limits: {e}")
            raise
    
    async def _setup_logging(self):
        """Configure logging for the sandbox"""
        log_dir = self.config.workspace_path / "logs"
        
        # Create log configuration
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_dir / "sandbox.log"),
                    "formatter": "detailed",
                    "level": "INFO"
                },
                "error_file": {
                    "class": "logging.FileHandler", 
                    "filename": str(log_dir / "error.log"),
                    "formatter": "detailed",
                    "level": "ERROR"
                }
            },
            "loggers": {
                f"sandbox.{self.config.sandbox_id}": {
                    "handlers": ["file", "error_file"],
                    "level": "INFO",
                    "propagate": False
                }
            }
        }
        
        import logging.config
        logging.config.dictConfig(log_config)
    
    async def _validate_workspace(self) -> Dict[str, Any]:
        """Validate workspace accessibility and permissions"""
        try:
            workspace_path = self.config.workspace_path
            
            # Check if workspace exists and is accessible
            if not workspace_path.exists():
                return {"accessible": False, "error": "Workspace does not exist"}
            
            if not workspace_path.is_dir():
                return {"accessible": False, "error": "Workspace is not a directory"}
            
            # Check read/write permissions
            test_file = workspace_path / "tmp" / ".access_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError):
                return {"accessible": False, "error": "No write permission"}
            
            return {"accessible": True}
            
        except Exception as e:
            return {"accessible": False, "error": str(e)}
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """Check for required system dependencies"""
        required_commands = ["python3", "bash", "sh"]
        optional_commands = ["git", "curl", "wget"]
        
        missing_required = []
        missing_optional = []
        
        for cmd in required_commands:
            if not shutil.which(cmd):
                missing_required.append(cmd)
        
        for cmd in optional_commands:
            if not shutil.which(cmd):
                missing_optional.append(cmd)
        
        return {
            "all_available": len(missing_required) == 0,
            "missing": missing_required,
            "missing_optional": missing_optional
        }
    
    async def _validate_security_config(self) -> Dict[str, Any]:
        """Validate security configuration"""
        issues = []
        
        # Check if workspace permissions are too permissive
        workspace_stat = self.config.workspace_path.stat()
        if workspace_stat.st_mode & 0o077:  # Others have any permissions
            issues.append("Workspace permissions too permissive")
        
        # Check for security constraints
        if not self.config.safety_constraints:
            issues.append("No safety constraints configured")
        
        # Validate network restrictions
        network_config = self.config.safety_constraints.get("network", {})
        if network_config.get("allow_external", True):
            issues.append("External network access allowed - consider restricting")
        
        return {
            "secure": len(issues) == 0,
            "issues": issues
        }
    
    async def _terminate_workspace_processes(self):
        """Terminate any processes running in the workspace"""
        try:
            import psutil
            
            # Find processes with working directory in workspace
            workspace_str = str(self.config.workspace_path)
            terminated_count = 0
            
            for proc in psutil.process_iter(['pid', 'cwd']):
                try:
                    if proc.info['cwd'] and workspace_str in proc.info['cwd']:
                        proc.terminate()
                        terminated_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if terminated_count > 0:
                self.logger.info(f"Terminated {terminated_count} workspace processes")
                
                # Wait for processes to exit
                await asyncio.sleep(2)
                
                # Force kill any remaining processes
                for proc in psutil.process_iter(['pid', 'cwd']):
                    try:
                        if proc.info['cwd'] and workspace_str in proc.info['cwd']:
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
        except ImportError:
            self.logger.warning("psutil not available - cannot terminate workspace processes")
        except Exception as e:
            self.logger.error(f"Error terminating workspace processes: {e}")
    
    async def _archive_logs(self):
        """Archive logs before cleanup"""
        try:
            log_dir = self.config.workspace_path / "logs"
            if not log_dir.exists():
                return
            
            import tarfile
            import datetime
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"sandbox_{self.config.sandbox_id}_{timestamp}.tar.gz"
            archive_path = Path.home() / ".sandbox_logs" / archive_name
            
            # Create archive directory
            archive_path.parent.mkdir(exist_ok=True)
            
            # Create archive
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(log_dir, arcname=f"sandbox_{self.config.sandbox_id}")
            
            self.logger.info(f"Logs archived to {archive_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to archive logs: {e}")