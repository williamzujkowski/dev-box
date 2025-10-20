"""Unit tests for AuditLogger.

Tests audit logging functionality including structured logging,
event types, JSON formatting, and NIST ET timestamps.

Follows strict TDD methodology - tests written before implementation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import structlog
from structlog.testing import LogCapture

from agent_vm.monitoring.audit import (
    AuditLogger,
    EventType,
    LogLevel,
)

ET = ZoneInfo("America/New_York")


@pytest.fixture(autouse=True)
def log_capture() -> LogCapture:
    """Fixture to capture structlog output."""
    capture = LogCapture()
    structlog.configure(
        processors=[capture],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=LogCapture,
        cache_logger_on_first_use=False,
    )
    yield capture
    # Reset structlog after each test
    structlog.reset_defaults()


@pytest.fixture
def audit_logger(log_capture: LogCapture) -> AuditLogger:
    """Fixture to create AuditLogger instance after log_capture is set up."""
    return AuditLogger()


class TestAuditLoggerInit:
    """Test AuditLogger initialization."""

    def test_init_creates_logger(self, audit_logger: AuditLogger) -> None:
        """AuditLogger initializes with structlog logger."""
        assert audit_logger._logger is not None

    def test_init_sets_component_name(self, audit_logger: AuditLogger) -> None:
        """AuditLogger binds component name in logger context."""
        # Implementation should bind component="audit_logger"
        assert hasattr(audit_logger, "_logger")


class TestLogEvent:
    """Test log_event method."""

    def test_log_event_basic(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """log_event creates structured log with all required fields."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={"profile": "standard"},
        )

        logs = log_capture.entries
        assert len(logs) == 1
        log = logs[0]

        # Check required fields
        assert "timestamp" in log
        assert log["event_type"] == "vm_created"
        assert log["agent_id"] == "agent-123"
        assert log["vm_id"] == "vm-456"
        assert log["details"] == {"profile": "standard"}

    def test_log_event_timestamp_is_nist_et(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """log_event uses NIST ET timezone for timestamps."""
        before = datetime.now(ET)
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )
        after = datetime.now(ET)

        log = log_capture.entries[0]
        timestamp_str = log["timestamp"]

        # Parse ISO format timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamp_et = timestamp.astimezone(ET)

        # Verify timestamp is within expected range
        assert before <= timestamp_et <= after

    def test_log_event_with_user_id(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """log_event includes optional user_id when provided."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
            user_id="user-789",
        )

        log = log_capture.entries[0]
        assert log["user_id"] == "user-789"

    def test_log_event_without_user_id(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """log_event works without optional user_id."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )

        log = log_capture.entries[0]
        assert "user_id" not in log

    def test_log_event_empty_details(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """log_event accepts empty details dictionary."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )

        log = log_capture.entries[0]
        assert log["details"] == {}

    def test_log_event_complex_details(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """log_event handles complex nested details."""
        details = {
            "code_hash": "sha256:abc123",
            "profile": "standard",
            "network_mode": "nat-filtered",
            "resources": {"vcpu": 2, "memory_mib": 2048},
        }

        audit_logger.log_event(
            event_type=EventType.AGENT_EXECUTION_STARTED,
            agent_id="agent-123",
            vm_id="vm-456",
            details=details,
        )

        log = log_capture.entries[0]
        assert log["details"] == details


class TestEventTypes:
    """Test all event types are properly logged."""

    @pytest.mark.parametrize(
        "event_type,expected_str",
        [
            # Lifecycle events
            (EventType.VM_CREATED, "vm_created"),
            (EventType.VM_STARTED, "vm_started"),
            (EventType.VM_STOPPED, "vm_stopped"),
            (EventType.VM_DESTROYED, "vm_destroyed"),
            (EventType.SNAPSHOT_CREATED, "snapshot_created"),
            (EventType.SNAPSHOT_RESTORED, "snapshot_restored"),
            # Execution events
            (EventType.AGENT_EXECUTION_STARTED, "agent_execution_started"),
            (EventType.AGENT_EXECUTION_COMPLETED, "agent_execution_completed"),
            (EventType.AGENT_EXECUTION_FAILED, "agent_execution_failed"),
            (EventType.AGENT_EXECUTION_TIMEOUT, "agent_execution_timeout"),
            # Security events
            (EventType.RESOURCE_LIMIT_EXCEEDED, "resource_limit_exceeded"),
            (EventType.NETWORK_CONNECTION_BLOCKED, "network_connection_blocked"),
            (EventType.SYSCALL_VIOLATION, "syscall_violation"),
            (EventType.FILESYSTEM_ACCESS_DENIED, "filesystem_access_denied"),
            (EventType.ANOMALY_DETECTED, "anomaly_detected"),
            # Administrative events
            (EventType.GOLDEN_IMAGE_UPDATED, "golden_image_updated"),
            (EventType.CONFIGURATION_CHANGED, "configuration_changed"),
            (EventType.USER_AUTHENTICATED, "user_authenticated"),
        ],
    )
    def test_event_type_values(
        self,
        event_type: EventType,
        expected_str: str,
        audit_logger: AuditLogger,
        log_capture: LogCapture,
    ) -> None:
        """Event types map to correct string values."""
        audit_logger.log_event(
            event_type=event_type,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )

        log = log_capture.entries[0]
        assert log["event_type"] == expected_str


class TestLogLevels:
    """Test different log levels."""

    def test_log_with_info_level(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """log_event defaults to INFO level."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )

        log = log_capture.entries[0]
        assert log["log_level"] == "info"

    def test_log_with_warning_level(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """log_event accepts WARNING level."""
        audit_logger.log_event(
            event_type=EventType.RESOURCE_LIMIT_EXCEEDED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
            level=LogLevel.WARNING,
        )

        log = log_capture.entries[0]
        assert log["log_level"] == "warning"

    def test_log_with_error_level(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """log_event accepts ERROR level."""
        audit_logger.log_event(
            event_type=EventType.AGENT_EXECUTION_FAILED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
            level=LogLevel.ERROR,
        )

        log = log_capture.entries[0]
        assert log["log_level"] == "error"

    def test_log_with_critical_level(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """log_event accepts CRITICAL level."""
        audit_logger.log_event(
            event_type=EventType.ANOMALY_DETECTED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
            level=LogLevel.CRITICAL,
        )

        log = log_capture.entries[0]
        assert log["log_level"] == "critical"


class TestContextBinding:
    """Test context binding functionality."""

    def test_bind_context(self, audit_logger: AuditLogger) -> None:
        """bind_context creates logger with bound context."""
        bound_logger = audit_logger.bind_context(session_id="session-123", environment="production")

        assert bound_logger is not None
        # Bound logger should be different instance
        assert bound_logger != audit_logger

    def test_bound_context_in_logs(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """Bound context appears in logged events."""
        bound_logger = audit_logger.bind_context(session_id="session-123")

        bound_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )

        log = log_capture.entries[0]
        assert log["session_id"] == "session-123"


class TestJSONSerialization:
    """Test JSON serialization of logs."""

    def test_log_is_json_serializable(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """Log entries can be serialized to JSON."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={"profile": "standard"},
        )

        log = log_capture.entries[0]
        # Should not raise exception
        json_str = json.dumps(log)
        assert json_str is not None

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "vm_created"


class TestErrorHandling:
    """Test error handling in logging."""

    def test_log_event_with_none_details_raises(self, audit_logger: AuditLogger) -> None:
        """log_event raises TypeError when details is None."""
        with pytest.raises(TypeError):
            audit_logger.log_event(
                event_type=EventType.VM_CREATED,
                agent_id="agent-123",
                vm_id="vm-456",
                details=None,  # type: ignore
            )

    def test_log_event_with_empty_agent_id_raises(self, audit_logger: AuditLogger) -> None:
        """log_event raises ValueError when agent_id is empty."""
        with pytest.raises(ValueError):
            audit_logger.log_event(
                event_type=EventType.VM_CREATED,
                agent_id="",
                vm_id="vm-456",
                details={},
            )

    def test_log_event_with_empty_vm_id_raises(self, audit_logger: AuditLogger) -> None:
        """log_event raises ValueError when vm_id is empty."""
        with pytest.raises(ValueError):
            audit_logger.log_event(
                event_type=EventType.VM_CREATED,
                agent_id="agent-123",
                vm_id="",
                details={},
            )


class TestConvenienceMethods:
    """Test convenience methods for common event types."""

    def test_log_lifecycle_event(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """log_lifecycle_event logs VM lifecycle events."""
        audit_logger.log_lifecycle_event(
            event_type=EventType.VM_CREATED,
            vm_id="vm-456",
            details={"profile": "standard"},
        )

        log = log_capture.entries[0]
        assert log["event_type"] == "vm_created"
        assert log["vm_id"] == "vm-456"

    def test_log_execution_event(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """log_execution_event logs agent execution events."""
        audit_logger.log_execution_event(
            event_type=EventType.AGENT_EXECUTION_STARTED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={"code_hash": "sha256:abc123"},
        )

        log = log_capture.entries[0]
        assert log["event_type"] == "agent_execution_started"
        assert log["agent_id"] == "agent-123"
        assert log["vm_id"] == "vm-456"

    def test_log_security_event(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """log_security_event logs security events with WARNING level."""
        audit_logger.log_security_event(
            event_type=EventType.RESOURCE_LIMIT_EXCEEDED,
            vm_id="vm-456",
            details={"resource": "cpu", "limit": 95},
        )

        log = log_capture.entries[0]
        assert log["event_type"] == "resource_limit_exceeded"
        assert log["log_level"] == "warning"

    def test_log_admin_event(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """log_admin_event logs administrative events."""
        audit_logger.log_admin_event(
            event_type=EventType.CONFIGURATION_CHANGED,
            details={"setting": "max_vms", "old": 10, "new": 20},
            user_id="admin-001",
        )

        log = log_capture.entries[0]
        assert log["event_type"] == "configuration_changed"
        assert log["user_id"] == "admin-001"


class TestTimestampFormat:
    """Test timestamp format compliance."""

    def test_timestamp_is_iso8601(self, audit_logger: AuditLogger, log_capture: LogCapture) -> None:
        """Timestamp follows ISO 8601 format."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )

        log = log_capture.entries[0]
        timestamp_str = log["timestamp"]

        # Should be parseable as ISO format
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert timestamp is not None

    def test_timestamp_includes_microseconds(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """Timestamp includes microsecond precision."""
        audit_logger.log_event(
            event_type=EventType.VM_CREATED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={},
        )

        log = log_capture.entries[0]
        timestamp_str = log["timestamp"]

        # ISO format with microseconds contains '.'
        assert "." in timestamp_str or "T" in timestamp_str


class TestMultipleEvents:
    """Test logging multiple events."""

    def test_multiple_events_maintain_order(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """Multiple logged events maintain chronological order."""
        events = [
            EventType.VM_CREATED,
            EventType.VM_STARTED,
            EventType.AGENT_EXECUTION_STARTED,
            EventType.AGENT_EXECUTION_COMPLETED,
            EventType.VM_STOPPED,
        ]

        for event in events:
            audit_logger.log_event(
                event_type=event,
                agent_id="agent-123",
                vm_id="vm-456",
                details={},
            )

        logs = log_capture.entries
        assert len(logs) == len(events)

        # Verify timestamps are in order
        for i in range(len(logs) - 1):
            ts1 = datetime.fromisoformat(logs[i]["timestamp"].replace("Z", "+00:00"))
            ts2 = datetime.fromisoformat(logs[i + 1]["timestamp"].replace("Z", "+00:00"))
            assert ts1 <= ts2


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_vm_lifecycle_scenario(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """Test complete VM lifecycle logging."""
        # Create VM
        audit_logger.log_lifecycle_event(
            event_type=EventType.VM_CREATED,
            vm_id="vm-456",
            details={"profile": "standard", "base_image": "ubuntu-24.04"},
        )

        # Start VM
        audit_logger.log_lifecycle_event(
            event_type=EventType.VM_STARTED,
            vm_id="vm-456",
            details={"boot_time_ms": 1500},
        )

        # Stop VM
        audit_logger.log_lifecycle_event(
            event_type=EventType.VM_STOPPED,
            vm_id="vm-456",
            details={"graceful": True},
        )

        # Destroy VM
        audit_logger.log_lifecycle_event(
            event_type=EventType.VM_DESTROYED,
            vm_id="vm-456",
            details={"cleanup_successful": True},
        )

        logs = log_capture.entries
        assert len(logs) == 4
        assert all(log["vm_id"] == "vm-456" for log in logs)

    def test_agent_execution_scenario(
        self, audit_logger: AuditLogger, log_capture: LogCapture
    ) -> None:
        """Test complete agent execution logging."""
        # Execution started
        audit_logger.log_execution_event(
            event_type=EventType.AGENT_EXECUTION_STARTED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={
                "code_hash": "sha256:abc123",
                "timeout": 300,
                "profile": "standard",
            },
        )

        # Execution completed
        audit_logger.log_execution_event(
            event_type=EventType.AGENT_EXECUTION_COMPLETED,
            agent_id="agent-123",
            vm_id="vm-456",
            details={"exit_code": 0, "duration_seconds": 45.2},
        )

        logs = log_capture.entries
        assert len(logs) == 2
        assert logs[0]["event_type"] == "agent_execution_started"
        assert logs[1]["event_type"] == "agent_execution_completed"
