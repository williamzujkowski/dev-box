"""Structured audit logging for security-relevant events.

This module provides the AuditLogger class for comprehensive structured logging
of all security-relevant events in the agent VM system. All timestamps use NIST ET
timezone for compliance.

Follows NIST ET timezone convention for all timestamps.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

import structlog

ET = ZoneInfo("America/New_York")


class EventType(str, Enum):
    """Audit event types.

    Categorized by:
    - Lifecycle: VM and snapshot operations
    - Execution: Agent code execution events
    - Security: Security violations and anomalies
    - Administrative: System configuration and user events
    """

    # Lifecycle events
    VM_CREATED = "vm_created"
    VM_STARTED = "vm_started"
    VM_STOPPED = "vm_stopped"
    VM_DESTROYED = "vm_destroyed"
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_RESTORED = "snapshot_restored"

    # Execution events
    AGENT_EXECUTION_STARTED = "agent_execution_started"
    AGENT_EXECUTION_COMPLETED = "agent_execution_completed"
    AGENT_EXECUTION_FAILED = "agent_execution_failed"
    AGENT_EXECUTION_TIMEOUT = "agent_execution_timeout"

    # Security events
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    NETWORK_CONNECTION_BLOCKED = "network_connection_blocked"
    SYSCALL_VIOLATION = "syscall_violation"
    FILESYSTEM_ACCESS_DENIED = "filesystem_access_denied"
    ANOMALY_DETECTED = "anomaly_detected"

    # Administrative events
    GOLDEN_IMAGE_UPDATED = "golden_image_updated"
    CONFIGURATION_CHANGED = "configuration_changed"
    USER_AUTHENTICATED = "user_authenticated"


class LogLevel(str, Enum):
    """Log severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """Structured audit logger for security events.

    Provides comprehensive logging of all security-relevant events with:
    - NIST ET timestamps (America/New_York timezone)
    - Structured JSON output
    - Event type validation
    - Context binding for session/environment tracking
    - Multiple log levels

    Example:
        >>> logger = AuditLogger()
        >>> logger.log_event(
        ...     event_type=EventType.VM_CREATED,
        ...     agent_id="agent-123",
        ...     vm_id="vm-456",
        ...     details={"profile": "standard"}
        ... )

        >>> # Bind context for multiple related events
        >>> session_logger = logger.bind_context(session_id="session-789")
        >>> session_logger.log_event(...)
    """

    def __init__(self) -> None:
        """Initialize AuditLogger with structlog.

        Creates a bound logger with component context for audit tracking.
        """
        self._logger = structlog.get_logger().bind(component="audit_logger")

    def log_event(
        self,
        event_type: EventType,
        agent_id: str,
        vm_id: str,
        details: dict[str, Any],
        user_id: str | None = None,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """Log a structured audit event.

        Args:
            event_type: Type of event being logged
            agent_id: Agent identifier
            vm_id: VM identifier
            details: Event-specific details dictionary
            user_id: Optional user identifier
            level: Log level (default: INFO)

        Raises:
            ValueError: If agent_id or vm_id is empty
            TypeError: If details is None

        Example:
            >>> logger.log_event(
            ...     event_type=EventType.AGENT_EXECUTION_STARTED,
            ...     agent_id="agent-123",
            ...     vm_id="vm-456",
            ...     details={"code_hash": "sha256:abc", "timeout": 300},
            ...     user_id="user-789"
            ... )
        """
        # Validate inputs
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")
        if not vm_id or not vm_id.strip():
            raise ValueError("vm_id cannot be empty")
        if details is None:
            raise TypeError("details cannot be None")

        # Create timestamp in NIST ET
        timestamp = datetime.now(ET).isoformat()

        # Build log entry
        log_data = {
            "timestamp": timestamp,
            "event_type": event_type.value,
            "agent_id": agent_id,
            "vm_id": vm_id,
            "details": details,
            "log_level": level.value,
        }

        # Add optional user_id if provided
        if user_id is not None:
            log_data["user_id"] = user_id

        # Log at appropriate level
        if level == LogLevel.INFO:
            self._logger.info(event_type.value, **log_data)
        elif level == LogLevel.WARNING:
            self._logger.warning(event_type.value, **log_data)
        elif level == LogLevel.ERROR:
            self._logger.error(event_type.value, **log_data)
        elif level == LogLevel.CRITICAL:
            self._logger.critical(event_type.value, **log_data)

    def log_lifecycle_event(
        self,
        event_type: EventType,
        vm_id: str,
        details: dict[str, Any],
        agent_id: str = "system",
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """Log VM lifecycle event (convenience method).

        Args:
            event_type: Lifecycle event type
            vm_id: VM identifier
            details: Event-specific details
            agent_id: Agent identifier (default: "system")
            level: Log level (default: INFO)

        Example:
            >>> logger.log_lifecycle_event(
            ...     event_type=EventType.VM_CREATED,
            ...     vm_id="vm-456",
            ...     details={"profile": "standard", "base_image": "ubuntu-24.04"}
            ... )
        """
        self.log_event(
            event_type=event_type,
            agent_id=agent_id,
            vm_id=vm_id,
            details=details,
            level=level,
        )

    def log_execution_event(
        self,
        event_type: EventType,
        agent_id: str,
        vm_id: str,
        details: dict[str, Any],
        user_id: str | None = None,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """Log agent execution event (convenience method).

        Args:
            event_type: Execution event type
            agent_id: Agent identifier
            vm_id: VM identifier
            details: Event-specific details
            user_id: Optional user identifier
            level: Log level (default: INFO)

        Example:
            >>> logger.log_execution_event(
            ...     event_type=EventType.AGENT_EXECUTION_STARTED,
            ...     agent_id="agent-123",
            ...     vm_id="vm-456",
            ...     details={"code_hash": "sha256:abc", "timeout": 300}
            ... )
        """
        self.log_event(
            event_type=event_type,
            agent_id=agent_id,
            vm_id=vm_id,
            details=details,
            user_id=user_id,
            level=level,
        )

    def log_security_event(
        self,
        event_type: EventType,
        vm_id: str,
        details: dict[str, Any],
        agent_id: str = "system",
        user_id: str | None = None,
        level: LogLevel = LogLevel.WARNING,
    ) -> None:
        """Log security event (convenience method).

        Security events default to WARNING level.

        Args:
            event_type: Security event type
            vm_id: VM identifier
            details: Event-specific details
            agent_id: Agent identifier (default: "system")
            user_id: Optional user identifier
            level: Log level (default: WARNING)

        Example:
            >>> logger.log_security_event(
            ...     event_type=EventType.RESOURCE_LIMIT_EXCEEDED,
            ...     vm_id="vm-456",
            ...     details={"resource": "cpu", "limit": 95}
            ... )
        """
        self.log_event(
            event_type=event_type,
            agent_id=agent_id,
            vm_id=vm_id,
            details=details,
            user_id=user_id,
            level=level,
        )

    def log_admin_event(
        self,
        event_type: EventType,
        details: dict[str, Any],
        user_id: str | None = None,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """Log administrative event (convenience method).

        Args:
            event_type: Administrative event type
            details: Event-specific details
            user_id: Optional user identifier
            level: Log level (default: INFO)

        Example:
            >>> logger.log_admin_event(
            ...     event_type=EventType.CONFIGURATION_CHANGED,
            ...     details={"setting": "max_vms", "old": 10, "new": 20},
            ...     user_id="admin-001"
            ... )
        """
        # Admin events use system placeholders for agent/vm
        self.log_event(
            event_type=event_type,
            agent_id="system",
            vm_id="system",
            details=details,
            user_id=user_id,
            level=level,
        )

    def bind_context(self, **kwargs: Any) -> "AuditLogger":
        """Create new logger with bound context.

        Useful for binding session_id, environment, or other contextual
        information that should appear in all subsequent log entries.

        Args:
            **kwargs: Context key-value pairs to bind

        Returns:
            New AuditLogger instance with bound context

        Example:
            >>> session_logger = logger.bind_context(
            ...     session_id="session-123",
            ...     environment="production"
            ... )
            >>> session_logger.log_event(...)  # Includes session_id and environment
        """
        bound_logger = AuditLogger()
        bound_logger._logger = self._logger.bind(**kwargs)
        return bound_logger
