"""
Safety Validator - Operation safety validation and constraints

Validates operations against safety constraints, security policies, and risk
assessments to ensure safe execution within the sandbox environment.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

from ..utils.stub_modules import PatternMatcher
from ..utils.stub_modules import RiskAssessment
from ..utils.stub_modules import SecurityAnalyzer


class RiskLevel(Enum):
    """Risk levels for operations"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationRule:
    """Individual validation rule"""

    rule_id: str
    name: str
    description: str
    rule_type: str  # pattern, content, size, permission, etc.
    pattern: Optional[str] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    blocked_values: Optional[List[str]] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    enabled: bool = True


@dataclass
class ValidationResult:
    """Result of safety validation"""

    is_safe: bool
    risk_level: RiskLevel
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    allowed_with_conditions: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)

    @property
    def severity(self) -> str:
        if self.risk_level == RiskLevel.CRITICAL:
            return "critical"
        if self.risk_level == RiskLevel.HIGH:
            return "high"
        if self.risk_level == RiskLevel.MEDIUM:
            return "medium"
        return "low"


@dataclass
class OperationConstraints:
    """Constraints for operation types"""

    operation_type: str
    max_execution_time: float = 300.0  # seconds
    max_memory_mb: float = 512.0
    max_disk_mb: float = 1024.0
    max_network_requests: int = 100
    allowed_file_extensions: Set[str] = field(default_factory=set)
    blocked_file_extensions: Set[str] = field(default_factory=set)
    allowed_commands: Set[str] = field(default_factory=set)
    blocked_commands: Set[str] = field(default_factory=set)
    require_confirmation: bool = False
    require_snapshot: bool = True


class SafetyValidator:
    """
    Comprehensive safety validation for sandbox operations

    Features:
    - Pattern-based content filtering
    - Resource usage validation
    - Command and file access restrictions
    - Risk assessment and scoring
    - Dynamic rule evaluation
    - Security policy enforcement
    - Operation-specific constraints
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(f"sandbox.{config.sandbox_id}.safety")

        # Safety components
        self.security_analyzer = SecurityAnalyzer()
        self.pattern_matcher = PatternMatcher()
        self.risk_assessment = RiskAssessment()

        # Validation rules and constraints
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.operation_constraints: Dict[str, OperationConstraints] = {}
        self.recent_violations: List[Dict[str, Any]] = []

        # Configuration
        self.safety_constraints = config.safety_constraints
        self.max_violation_history = 100

        # Default rules will be initialized on first use
        self._rules_initialized = False

    async def validate_operation(self, operation: Dict[str, Any]) -> ValidationResult:
        """
        Validate an operation against safety constraints

        Args:
            operation: Operation specification

        Returns:
            ValidationResult with safety assessment
        """
        try:
            # Initialize default rules if not already done
            if not self._rules_initialized:
                await self._initialize_default_rules()
                self._rules_initialized = True

            operation_type = operation.get("type", "unknown")
            self.logger.debug(f"Validating operation: {operation_type}")

            result = ValidationResult(is_safe=True, risk_level=RiskLevel.LOW)

            # Get operation constraints
            constraints = self.operation_constraints.get(
                operation_type,
                self.operation_constraints.get(
                    "default", OperationConstraints("default")
                ),
            )

            # Validate against multiple criteria
            await self._validate_content_safety(operation, result)
            await self._validate_resource_limits(operation, constraints, result)
            await self._validate_file_access(operation, constraints, result)
            await self._validate_command_execution(operation, constraints, result)
            await self._validate_network_access(operation, constraints, result)
            await self._validate_security_patterns(operation, result)

            # Perform risk assessment
            risk_score = await self.risk_assessment.assess_operation(operation)
            result.risk_level = self._risk_score_to_level(risk_score)

            # Determine overall safety
            if result.violations or result.risk_level == RiskLevel.CRITICAL:
                result.is_safe = False
                result.reason = self._build_rejection_reason(result)
            elif result.risk_level == RiskLevel.HIGH:
                result.is_safe = not constraints.require_confirmation
                if not result.is_safe:
                    result.reason = "High-risk operation requires confirmation"

            # Generate suggestions
            result.suggestions = await self._generate_safety_suggestions(
                operation, result
            )

            # Record validation
            await self._record_validation(operation, result)

            self.logger.debug(
                f"Validation result: safe={result.is_safe}, risk={result.risk_level.value}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Operation validation failed: {e}")
            return ValidationResult(
                is_safe=False,
                risk_level=RiskLevel.CRITICAL,
                violations=[f"Validation error: {e!s}"],
                reason="Validation system error",
            )

    async def validate_content(
        self, content: str, content_type: str = "text"
    ) -> ValidationResult:
        """
        Validate content against safety rules

        Args:
            content: Content to validate
            content_type: Type of content (text, code, data, etc.)

        Returns:
            ValidationResult
        """
        try:
            result = ValidationResult(is_safe=True, risk_level=RiskLevel.LOW)

            # Check for dangerous patterns
            dangerous_patterns = await self._check_dangerous_patterns(
                content, content_type, result
            )

            # Check content size
            await self._validate_content_size(content, result)

            # Security analysis
            security_issues = await self.security_analyzer.analyze_content(
                content, content_type
            )
            if security_issues:
                result.violations.extend(security_issues)
                result.risk_level = RiskLevel.HIGH

            # Final safety determination
            if result.violations:
                result.is_safe = False
                result.reason = "Content contains unsafe patterns or elements"

            return result

        except Exception as e:
            self.logger.error(f"Content validation failed: {e}")
            return ValidationResult(
                is_safe=False,
                risk_level=RiskLevel.CRITICAL,
                violations=[f"Content validation error: {e!s}"],
            )

    async def add_validation_rule(self, rule: ValidationRule) -> bool:
        """
        Add a custom validation rule

        Args:
            rule: Validation rule to add

        Returns:
            bool: True if added successfully
        """
        try:
            self.validation_rules[rule.rule_id] = rule
            self.logger.info(f"Added validation rule: {rule.rule_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add validation rule: {e}")
            return False

    async def remove_validation_rule(self, rule_id: str) -> bool:
        """
        Remove a validation rule

        Args:
            rule_id: Rule ID to remove

        Returns:
            bool: True if removed successfully
        """
        try:
            if rule_id in self.validation_rules:
                del self.validation_rules[rule_id]
                self.logger.info(f"Removed validation rule: {rule_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to remove validation rule: {e}")
            return False

    async def set_operation_constraints(
        self, operation_type: str, constraints: OperationConstraints
    ) -> bool:
        """
        Set constraints for an operation type

        Args:
            operation_type: Type of operation
            constraints: Constraints to apply

        Returns:
            bool: True if set successfully
        """
        try:
            self.operation_constraints[operation_type] = constraints
            self.logger.info(f"Set constraints for operation type: {operation_type}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set operation constraints: {e}")
            return False

    async def get_recent_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent safety violations

        Args:
            limit: Maximum number of violations to return

        Returns:
            List of recent violations
        """
        return self.recent_violations[-limit:] if self.recent_violations else []

    async def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics

        Returns:
            Dict containing validation statistics
        """
        try:
            total_validations = len(self.recent_violations)

            if total_validations == 0:
                return {
                    "total_validations": 0,
                    "violations": 0,
                    "violation_rate": 0.0,
                    "risk_distribution": {},
                }

            violations = sum(
                1 for v in self.recent_violations if not v.get("is_safe", True)
            )

            # Risk level distribution
            risk_distribution = {}
            for violation in self.recent_violations:
                risk = violation.get("risk_level", "unknown")
                risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

            return {
                "total_validations": total_validations,
                "violations": violations,
                "violation_rate": violations / total_validations,
                "risk_distribution": risk_distribution,
                "active_rules": len(
                    [r for r in self.validation_rules.values() if r.enabled]
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to get validation stats: {e}")
            return {}

    # Private methods
    async def _initialize_default_rules(self):
        """Initialize default validation rules"""
        try:
            # Dangerous command patterns
            await self.add_validation_rule(
                ValidationRule(
                    rule_id="dangerous_commands",
                    name="Dangerous Commands",
                    description="Block potentially dangerous system commands",
                    rule_type="pattern",
                    pattern=r"\b(rm\s+(-rf\s+)?\/|sudo\s+rm|mkfs|dd\s+if=.*of=\/dev|format|fdisk)",
                    risk_level=RiskLevel.CRITICAL,
                )
            )

            # Network access patterns
            await self.add_validation_rule(
                ValidationRule(
                    rule_id="network_commands",
                    name="Network Commands",
                    description="Restrict network access commands",
                    rule_type="pattern",
                    pattern=r"\b(wget|curl|nc|netcat|ssh|scp|rsync).*--.*",
                    risk_level=RiskLevel.HIGH,
                )
            )

            # File system modification
            await self.add_validation_rule(
                ValidationRule(
                    rule_id="filesystem_modification",
                    name="File System Modification",
                    description="Monitor file system modification commands",
                    rule_type="pattern",
                    pattern=r"\b(chmod\s+777|chown\s+root|mount|umount)",
                    risk_level=RiskLevel.HIGH,
                )
            )

            # Code injection patterns
            await self.add_validation_rule(
                ValidationRule(
                    rule_id="code_injection",
                    name="Code Injection",
                    description="Detect potential code injection attempts",
                    rule_type="pattern",
                    pattern=r"(eval\s*\(|exec\s*\(|system\s*\(|shell_exec\s*\()",
                    risk_level=RiskLevel.HIGH,
                )
            )

            # Sensitive data patterns
            await self.add_validation_rule(
                ValidationRule(
                    rule_id="sensitive_data",
                    name="Sensitive Data",
                    description="Detect sensitive data patterns",
                    rule_type="pattern",
                    pattern=r"(password\s*=|api_key\s*=|secret\s*=|token\s*=)",
                    risk_level=RiskLevel.MEDIUM,
                )
            )

            # Resource usage limits
            await self.add_validation_rule(
                ValidationRule(
                    rule_id="memory_limit",
                    name="Memory Usage Limit",
                    description="Limit memory usage",
                    rule_type="size",
                    max_value=self.safety_constraints.get("max_memory_mb", 1024),
                    risk_level=RiskLevel.MEDIUM,
                )
            )

            # Initialize default operation constraints
            self.operation_constraints["default"] = OperationConstraints(
                operation_type="default",
                max_execution_time=300.0,
                max_memory_mb=512.0,
                max_disk_mb=1024.0,
                blocked_commands={"rm", "sudo", "chmod", "chown"},
                blocked_file_extensions={".exe", ".bat", ".cmd", ".scr"},
                require_snapshot=True,
            )

            self.operation_constraints["file_operation"] = OperationConstraints(
                operation_type="file_operation",
                max_execution_time=60.0,
                max_disk_mb=100.0,
                allowed_file_extensions={".txt", ".json", ".yaml", ".py", ".js", ".md"},
                require_snapshot=True,
            )

            self.operation_constraints["network_operation"] = OperationConstraints(
                operation_type="network_operation",
                max_execution_time=120.0,
                max_network_requests=50,
                require_confirmation=True,
                require_snapshot=True,
            )

            self.logger.info("Initialized default validation rules and constraints")

        except Exception as e:
            self.logger.error(f"Failed to initialize default rules: {e}")

    async def _validate_content_safety(
        self, operation: Dict[str, Any], result: ValidationResult
    ):
        """Validate operation content for safety"""
        try:
            # Check operation parameters for dangerous content
            content_fields = ["command", "script", "code", "content", "data"]

            for field in content_fields:
                if field in operation:
                    content = str(operation[field])
                    await self._check_dangerous_patterns(content, field, result)

        except Exception as e:
            result.violations.append(f"Content safety validation error: {e!s}")

    async def _validate_resource_limits(
        self,
        operation: Dict[str, Any],
        constraints: OperationConstraints,
        result: ValidationResult,
    ):
        """Validate resource usage limits"""
        try:
            # Check execution time limit
            requested_time = operation.get("max_execution_time", 0)
            if requested_time > constraints.max_execution_time:
                result.violations.append(
                    f"Execution time limit exceeded: {requested_time}s > {constraints.max_execution_time}s"
                )

            # Check memory limit
            requested_memory = operation.get("max_memory_mb", 0)
            if requested_memory > constraints.max_memory_mb:
                result.violations.append(
                    f"Memory limit exceeded: {requested_memory}MB > {constraints.max_memory_mb}MB"
                )

            # Check disk usage limit
            requested_disk = operation.get("max_disk_mb", 0)
            if requested_disk > constraints.max_disk_mb:
                result.violations.append(
                    f"Disk usage limit exceeded: {requested_disk}MB > {constraints.max_disk_mb}MB"
                )

        except Exception as e:
            result.violations.append(f"Resource limit validation error: {e!s}")

    async def _validate_file_access(
        self,
        operation: Dict[str, Any],
        constraints: OperationConstraints,
        result: ValidationResult,
    ):
        """Validate file access permissions"""
        try:
            file_paths = operation.get("files", [])
            if isinstance(file_paths, str):
                file_paths = [file_paths]

            for file_path in file_paths:
                path = Path(file_path)

                # Check file extension
                if path.suffix:
                    if (
                        constraints.blocked_file_extensions
                        and path.suffix.lower() in constraints.blocked_file_extensions
                    ):
                        result.violations.append(
                            f"Blocked file extension: {path.suffix}"
                        )

                    if (
                        constraints.allowed_file_extensions
                        and path.suffix.lower()
                        not in constraints.allowed_file_extensions
                    ):
                        result.violations.append(
                            f"File extension not allowed: {path.suffix}"
                        )

                # Check if path is within sandbox
                try:
                    workspace = self.config.workspace_path
                    if not str(path.resolve()).startswith(str(workspace.resolve())):
                        result.violations.append(
                            f"File access outside sandbox: {file_path}"
                        )
                except:
                    result.violations.append(f"Invalid file path: {file_path}")

        except Exception as e:
            result.violations.append(f"File access validation error: {e!s}")

    async def _validate_command_execution(
        self,
        operation: Dict[str, Any],
        constraints: OperationConstraints,
        result: ValidationResult,
    ):
        """Validate command execution safety"""
        try:
            commands = []

            # Extract commands from various fields
            if "command" in operation:
                commands.append(operation["command"])
            if "commands" in operation:
                commands.extend(operation["commands"])
            if "script" in operation:
                # Extract commands from script content
                script_content = operation["script"]
                commands.extend(self._extract_commands_from_script(script_content))

            for command in commands:
                command_str = str(command).strip()

                # Check against blocked commands
                if constraints.blocked_commands:
                    command_parts = command_str.split()
                    if (
                        command_parts
                        and command_parts[0] in constraints.blocked_commands
                    ):
                        result.violations.append(f"Blocked command: {command_parts[0]}")

                # Check against allowed commands (if specified)
                if constraints.allowed_commands:
                    command_parts = command_str.split()
                    if (
                        command_parts
                        and command_parts[0] not in constraints.allowed_commands
                    ):
                        result.violations.append(
                            f"Command not in allowed list: {command_parts[0]}"
                        )

        except Exception as e:
            result.violations.append(f"Command validation error: {e!s}")

    async def _validate_network_access(
        self,
        operation: Dict[str, Any],
        constraints: OperationConstraints,
        result: ValidationResult,
    ):
        """Validate network access requirements"""
        try:
            # Check if operation requires network access
            network_required = operation.get("requires_network", False)
            network_allowed = self.safety_constraints.get("network", {}).get(
                "allow_external", False
            )

            if network_required and not network_allowed:
                result.violations.append("Network access required but not allowed")

            # Check network request limits
            max_requests = operation.get("max_network_requests", 0)
            if max_requests > constraints.max_network_requests:
                result.violations.append(
                    f"Network request limit exceeded: {max_requests} > {constraints.max_network_requests}"
                )

        except Exception as e:
            result.violations.append(f"Network access validation error: {e!s}")

    async def _validate_security_patterns(
        self, operation: Dict[str, Any], result: ValidationResult
    ):
        """Validate against security patterns"""
        try:
            # Analyze operation for security issues
            security_issues = await self.security_analyzer.analyze_operation(operation)

            if security_issues:
                result.violations.extend(security_issues)
                result.risk_level = max(result.risk_level, RiskLevel.HIGH)

        except Exception as e:
            result.violations.append(f"Security pattern validation error: {e!s}")

    async def _check_dangerous_patterns(
        self, content: str, content_type: str, result: ValidationResult
    ) -> List[str]:
        """Check content against dangerous patterns"""
        dangerous_patterns = []

        try:
            for rule in self.validation_rules.values():
                if not rule.enabled or rule.rule_type != "pattern":
                    continue

                if rule.pattern and re.search(rule.pattern, content, re.IGNORECASE):
                    violation_msg = (
                        f"Dangerous pattern detected ({rule.name}): {rule.description}"
                    )
                    result.violations.append(violation_msg)
                    result.blocked_patterns.append(rule.pattern)
                    dangerous_patterns.append(rule.pattern)

                    # Update risk level based on rule
                    if rule.risk_level.value == "critical":
                        result.risk_level = RiskLevel.CRITICAL
                    elif (
                        rule.risk_level.value == "high"
                        and result.risk_level != RiskLevel.CRITICAL
                    ):
                        result.risk_level = RiskLevel.HIGH

        except Exception as e:
            result.violations.append(f"Pattern checking error: {e!s}")

        return dangerous_patterns

    async def _validate_content_size(self, content: str, result: ValidationResult):
        """Validate content size limits"""
        try:
            content_size = len(content.encode("utf-8"))
            max_size = (
                self.safety_constraints.get("max_content_size_mb", 10) * 1024 * 1024
            )

            if content_size > max_size:
                result.violations.append(
                    f"Content size exceeds limit: {content_size} > {max_size} bytes"
                )

        except Exception as e:
            result.violations.append(f"Content size validation error: {e!s}")

    def _extract_commands_from_script(self, script_content: str) -> List[str]:
        """Extract individual commands from script content"""
        commands = []

        try:
            # Simple extraction - split by newlines and semicolons
            lines = script_content.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Split by semicolon for multiple commands on one line
                    sub_commands = line.split(";")
                    commands.extend(
                        [cmd.strip() for cmd in sub_commands if cmd.strip()]
                    )

        except Exception as e:
            self.logger.error(f"Failed to extract commands from script: {e}")

        return commands

    def _risk_score_to_level(self, risk_score: float) -> RiskLevel:
        """Convert numeric risk score to risk level"""
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        if risk_score >= 0.6:
            return RiskLevel.HIGH
        if risk_score >= 0.3:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _build_rejection_reason(self, result: ValidationResult) -> str:
        """Build human-readable rejection reason"""
        if result.violations:
            return f"Operation blocked due to safety violations: {'; '.join(result.violations[:3])}"
        return f"Operation blocked due to {result.risk_level.value} risk level"

    async def _generate_safety_suggestions(
        self, operation: Dict[str, Any], result: ValidationResult
    ) -> List[str]:
        """Generate suggestions for safer operation"""
        suggestions = []

        try:
            if result.violations:
                # Suggest alternatives based on violations
                for violation in result.violations:
                    if "command" in violation.lower():
                        suggestions.append(
                            "Consider using safer command alternatives or restrict command scope"
                        )
                    elif "file" in violation.lower():
                        suggestions.append(
                            "Limit file operations to sandbox workspace directory"
                        )
                    elif "network" in violation.lower():
                        suggestions.append(
                            "Disable network access or use local resources only"
                        )
                    elif "memory" in violation.lower() or "disk" in violation.lower():
                        suggestions.append(
                            "Reduce resource requirements or increase limits"
                        )

            if result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                suggestions.append("Consider creating a snapshot before proceeding")
                suggestions.append(
                    "Review operation parameters for potential security issues"
                )
                suggestions.append(
                    "Test operation in a more restricted environment first"
                )

        except Exception as e:
            self.logger.error(f"Failed to generate suggestions: {e}")

        return suggestions

    async def _record_validation(
        self, operation: Dict[str, Any], result: ValidationResult
    ):
        """Record validation result for tracking"""
        try:
            validation_record = {
                "timestamp": asyncio.get_event_loop().time(),
                "operation_type": operation.get("type", "unknown"),
                "operation_id": operation.get("id", "unknown"),
                "is_safe": result.is_safe,
                "risk_level": result.risk_level.value,
                "violations_count": len(result.violations),
                "violations": result.violations[:5],  # Keep first 5 violations
                "warnings_count": len(result.warnings),
            }

            self.recent_violations.append(validation_record)

            # Limit history size
            if len(self.recent_violations) > self.max_violation_history:
                self.recent_violations = self.recent_violations[
                    -self.max_violation_history :
                ]

        except Exception as e:
            self.logger.error(f"Failed to record validation: {e}")
