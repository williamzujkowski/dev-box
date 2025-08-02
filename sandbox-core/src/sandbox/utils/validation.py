"""
Configuration validation utilities

Provides comprehensive validation for sandbox configurations and settings.
"""

import logging
import re
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List


@dataclass
class ValidationError:
    """Individual validation error"""

    field: str
    message: str
    severity: str = "error"  # error, warning
    value: Any = None


@dataclass
class ValidationResult:
    """Result of configuration validation"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[ValidationError] = field(default_factory=list)

    def add_error(self, field: str, message: str, value: Any = None):
        """Add validation error"""
        self.errors.append(f"{field}: {message}")
        self.validation_errors.append(ValidationError(field, message, "error", value))
        self.is_valid = False

    def add_warning(self, field: str, message: str, value: Any = None):
        """Add validation warning"""
        self.warnings.append(f"{field}: {message}")
        self.validation_errors.append(ValidationError(field, message, "warning", value))


class ConfigValidator:
    """
    Configuration validator for sandbox settings

    Validates sandbox configuration parameters for correctness,
    security, and operational feasibility.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ConfigValidator")

    async def validate(self, config) -> ValidationResult:
        """
        Validate complete sandbox configuration

        Args:
            config: Sandbox configuration object

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult(is_valid=True)

        try:
            # Validate basic required fields
            await self._validate_required_fields(config, result)

            # Validate sandbox ID
            await self._validate_sandbox_id(config.sandbox_id, result)

            # Validate workspace path
            await self._validate_workspace_path(config.workspace_path, result)

            # Validate resource limits
            await self._validate_resource_limits(config.resource_limits, result)

            # Validate safety constraints
            await self._validate_safety_constraints(config.safety_constraints, result)

            # Validate monitoring configuration
            await self._validate_monitoring_config(config.monitoring_config, result)

            # Validate consistency between settings
            await self._validate_consistency(config, result)

        except Exception as e:
            result.add_error("validation", f"Configuration validation failed: {e!s}")

        return result

    async def validate_resource_limits(
        self, resource_limits: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate resource limit configuration

        Args:
            resource_limits: Resource limits dictionary

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult(is_valid=True)

        try:
            # Memory limits
            memory_mb = resource_limits.get("memory_mb")
            if memory_mb is not None:
                if not isinstance(memory_mb, (int, float)) or memory_mb <= 0:
                    result.add_error(
                        "memory_mb", "Must be a positive number", memory_mb
                    )
                elif memory_mb < 64:
                    result.add_warning(
                        "memory_mb", "Very low memory limit may cause issues", memory_mb
                    )
                elif memory_mb > 8192:
                    result.add_warning("memory_mb", "High memory limit", memory_mb)

            # CPU limits
            cpu_percent = resource_limits.get("cpu_percent")
            if cpu_percent is not None:
                if (
                    not isinstance(cpu_percent, (int, float))
                    or cpu_percent <= 0
                    or cpu_percent > 100
                ):
                    result.add_error(
                        "cpu_percent", "Must be between 0 and 100", cpu_percent
                    )
                elif cpu_percent > 90:
                    result.add_warning(
                        "cpu_percent",
                        "High CPU limit may affect system performance",
                        cpu_percent,
                    )

            # Disk limits
            disk_mb = resource_limits.get("disk_mb")
            if disk_mb is not None:
                if not isinstance(disk_mb, (int, float)) or disk_mb <= 0:
                    result.add_error("disk_mb", "Must be a positive number", disk_mb)
                elif disk_mb < 100:
                    result.add_warning(
                        "disk_mb", "Very low disk limit may cause issues", disk_mb
                    )

            # Network limits
            network_config = resource_limits.get("network", {})
            if network_config:
                await self._validate_network_limits(network_config, result)

        except Exception as e:
            result.add_error("resource_limits", f"Validation failed: {e!s}")

        return result

    async def validate_safety_constraints(
        self, safety_constraints: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate safety constraint configuration

        Args:
            safety_constraints: Safety constraints dictionary

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult(is_valid=True)

        try:
            # Snapshot settings
            max_snapshots = safety_constraints.get("max_snapshots")
            if max_snapshots is not None:
                if not isinstance(max_snapshots, int) or max_snapshots < 1:
                    result.add_error(
                        "max_snapshots", "Must be a positive integer", max_snapshots
                    )
                elif max_snapshots > 100:
                    result.add_warning(
                        "max_snapshots",
                        "High snapshot count may use excessive disk space",
                        max_snapshots,
                    )

            # Auto cleanup settings
            auto_cleanup_hours = safety_constraints.get("auto_cleanup_hours")
            if auto_cleanup_hours is not None:
                if (
                    not isinstance(auto_cleanup_hours, (int, float))
                    or auto_cleanup_hours < 1
                ):
                    result.add_error(
                        "auto_cleanup_hours",
                        "Must be at least 1 hour",
                        auto_cleanup_hours,
                    )
                elif auto_cleanup_hours < 24:
                    result.add_warning(
                        "auto_cleanup_hours",
                        "Short cleanup interval may delete recent snapshots",
                        auto_cleanup_hours,
                    )

            # Network constraints
            network_config = safety_constraints.get("network", {})
            if network_config:
                allow_external = network_config.get("allow_external")
                if allow_external is not None and not isinstance(allow_external, bool):
                    result.add_error(
                        "network.allow_external",
                        "Must be a boolean value",
                        allow_external,
                    )

            # Encryption settings
            encrypt_state = safety_constraints.get("encrypt_state")
            if encrypt_state is not None and not isinstance(encrypt_state, bool):
                result.add_error(
                    "encrypt_state", "Must be a boolean value", encrypt_state
                )

            encrypt_snapshots = safety_constraints.get("encrypt_snapshots")
            if encrypt_snapshots is not None and not isinstance(
                encrypt_snapshots, bool
            ):
                result.add_error(
                    "encrypt_snapshots", "Must be a boolean value", encrypt_snapshots
                )

        except Exception as e:
            result.add_error("safety_constraints", f"Validation failed: {e!s}")

        return result

    # Private validation methods
    async def _validate_required_fields(self, config, result: ValidationResult):
        """Validate required configuration fields"""
        required_fields = ["sandbox_id", "workspace_path"]

        for field in required_fields:
            if not hasattr(config, field) or getattr(config, field) is None:
                result.add_error(field, "Required field is missing")

    async def _validate_sandbox_id(self, sandbox_id: str, result: ValidationResult):
        """Validate sandbox ID format and safety"""
        if not isinstance(sandbox_id, str):
            result.add_error("sandbox_id", "Must be a string", sandbox_id)
            return

        if not sandbox_id:
            result.add_error("sandbox_id", "Cannot be empty")
            return

        # Check format - alphanumeric with hyphens and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", sandbox_id):
            result.add_error(
                "sandbox_id",
                "Can only contain letters, numbers, hyphens, and underscores",
                sandbox_id,
            )

        # Check length
        if len(sandbox_id) < 3:
            result.add_error(
                "sandbox_id", "Must be at least 3 characters long", sandbox_id
            )
        elif len(sandbox_id) > 64:
            result.add_error(
                "sandbox_id", "Must be no more than 64 characters long", sandbox_id
            )

        # Check for reserved names
        reserved_names = ["admin", "root", "system", "default", "temp", "tmp"]
        if sandbox_id.lower() in reserved_names:
            result.add_error("sandbox_id", "Cannot use reserved name", sandbox_id)

    async def _validate_workspace_path(
        self, workspace_path: Path, result: ValidationResult
    ):
        """Validate workspace path"""
        if not isinstance(workspace_path, Path):
            try:
                workspace_path = Path(workspace_path)
            except Exception:
                result.add_error(
                    "workspace_path", "Must be a valid path", workspace_path
                )
                return

        # Check if path is absolute
        if not workspace_path.is_absolute():
            result.add_warning(
                "workspace_path", "Relative paths may cause issues", str(workspace_path)
            )

        # Check for dangerous paths
        dangerous_paths = ["/", "/etc", "/var", "/usr", "/bin", "/sbin", "/boot"]
        workspace_str = str(workspace_path)

        for dangerous_path in dangerous_paths:
            if (
                workspace_str.startswith(dangerous_path)
                and workspace_str != dangerous_path + "/sandbox"
            ):
                result.add_error(
                    "workspace_path",
                    f"Cannot use system path: {dangerous_path}",
                    workspace_str,
                )

        # Check parent directory accessibility
        try:
            parent = workspace_path.parent
            if parent.exists() and not parent.is_dir():
                result.add_error(
                    "workspace_path", "Parent is not a directory", str(parent)
                )
        except Exception as e:
            result.add_warning(
                "workspace_path", f"Cannot validate parent directory: {e!s}"
            )

    async def _validate_resource_limits(
        self, resource_limits: Dict[str, Any], result: ValidationResult
    ):
        """Validate resource limits configuration"""
        if not isinstance(resource_limits, dict):
            result.add_error(
                "resource_limits", "Must be a dictionary", type(resource_limits)
            )
            return

        # Use the dedicated resource limits validator
        resource_result = await self.validate_resource_limits(resource_limits)

        # Merge results
        result.errors.extend(resource_result.errors)
        result.warnings.extend(resource_result.warnings)
        result.validation_errors.extend(resource_result.validation_errors)

        if not resource_result.is_valid:
            result.is_valid = False

    async def _validate_safety_constraints(
        self, safety_constraints: Dict[str, Any], result: ValidationResult
    ):
        """Validate safety constraints configuration"""
        if not isinstance(safety_constraints, dict):
            result.add_error(
                "safety_constraints", "Must be a dictionary", type(safety_constraints)
            )
            return

        # Use the dedicated safety constraints validator
        safety_result = await self.validate_safety_constraints(safety_constraints)

        # Merge results
        result.errors.extend(safety_result.errors)
        result.warnings.extend(safety_result.warnings)
        result.validation_errors.extend(safety_result.validation_errors)

        if not safety_result.is_valid:
            result.is_valid = False

    async def _validate_monitoring_config(
        self, monitoring_config: Dict[str, Any], result: ValidationResult
    ):
        """Validate monitoring configuration"""
        if not isinstance(monitoring_config, dict):
            result.add_error(
                "monitoring_config", "Must be a dictionary", type(monitoring_config)
            )
            return

        # Collection interval
        collection_interval = monitoring_config.get("collection_interval")
        if collection_interval is not None:
            if (
                not isinstance(collection_interval, (int, float))
                or collection_interval <= 0
            ):
                result.add_error(
                    "monitoring_config.collection_interval",
                    "Must be a positive number",
                    collection_interval,
                )
            elif collection_interval < 1:
                result.add_warning(
                    "monitoring_config.collection_interval",
                    "Very frequent collection may impact performance",
                    collection_interval,
                )

        # Health check interval
        health_check_interval = monitoring_config.get("health_check_interval")
        if health_check_interval is not None:
            if (
                not isinstance(health_check_interval, (int, float))
                or health_check_interval <= 0
            ):
                result.add_error(
                    "monitoring_config.health_check_interval",
                    "Must be a positive number",
                    health_check_interval,
                )

        # Resource thresholds
        resource_thresholds = monitoring_config.get("resource_thresholds", {})
        if resource_thresholds:
            await self._validate_resource_thresholds(resource_thresholds, result)

    async def _validate_resource_thresholds(
        self, thresholds: Dict[str, Any], result: ValidationResult
    ):
        """Validate resource threshold configuration"""
        threshold_fields = {
            "cpu_percent": (0, 100),
            "memory_mb": (1, None),
            "disk_mb": (1, None),
            "memory_percent": (0, 100),
            "disk_percent": (0, 100),
        }

        for field, (min_val, max_val) in threshold_fields.items():
            value = thresholds.get(field)
            if value is not None:
                if not isinstance(value, (int, float)):
                    result.add_error(
                        f"resource_thresholds.{field}", "Must be a number", value
                    )
                elif value < min_val:
                    result.add_error(
                        f"resource_thresholds.{field}",
                        f"Must be at least {min_val}",
                        value,
                    )
                elif max_val is not None and value > max_val:
                    result.add_error(
                        f"resource_thresholds.{field}",
                        f"Must be at most {max_val}",
                        value,
                    )

    async def _validate_network_limits(
        self, network_config: Dict[str, Any], result: ValidationResult
    ):
        """Validate network limit configuration"""
        # Bandwidth limits
        max_bandwidth_mbps = network_config.get("max_bandwidth_mbps")
        if max_bandwidth_mbps is not None:
            if (
                not isinstance(max_bandwidth_mbps, (int, float))
                or max_bandwidth_mbps <= 0
            ):
                result.add_error(
                    "network.max_bandwidth_mbps",
                    "Must be a positive number",
                    max_bandwidth_mbps,
                )

        # Connection limits
        max_connections = network_config.get("max_connections")
        if max_connections is not None:
            if not isinstance(max_connections, int) or max_connections <= 0:
                result.add_error(
                    "network.max_connections",
                    "Must be a positive integer",
                    max_connections,
                )

    async def _validate_consistency(self, config, result: ValidationResult):
        """Validate consistency between different configuration sections"""
        try:
            # Check if resource limits are consistent with monitoring thresholds
            resource_limits = config.resource_limits
            monitoring_config = config.monitoring_config

            resource_thresholds = monitoring_config.get("resource_thresholds", {})

            # Memory consistency
            memory_limit = resource_limits.get("memory_mb")
            memory_threshold = resource_thresholds.get("memory_mb")

            if memory_limit and memory_threshold and memory_threshold > memory_limit:
                result.add_warning(
                    "consistency",
                    f"Memory threshold ({memory_threshold}MB) exceeds memory limit ({memory_limit}MB)",
                )

            # Disk consistency
            disk_limit = resource_limits.get("disk_mb")
            disk_threshold = resource_thresholds.get("disk_mb")

            if disk_limit and disk_threshold and disk_threshold > disk_limit:
                result.add_warning(
                    "consistency",
                    f"Disk threshold ({disk_threshold}MB) exceeds disk limit ({disk_limit}MB)",
                )

        except Exception as e:
            result.add_warning("consistency", f"Could not validate consistency: {e!s}")


def validate_config_dict(config_dict: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate configuration dictionary

    Args:
        config_dict: Configuration dictionary

    Returns:
        ValidationResult: Validation results
    """

    # Create a mock config object for validation
    class MockConfig:
        def __init__(self, config_dict):
            for key, value in config_dict.items():
                setattr(self, key, value)

    mock_config = MockConfig(config_dict)
    validator = ConfigValidator()

    try:
        import asyncio

        return asyncio.run(validator.validate(mock_config))
    except Exception as e:
        result = ValidationResult(is_valid=False)
        result.add_error("validation", f"Configuration validation failed: {e!s}")
        return result
