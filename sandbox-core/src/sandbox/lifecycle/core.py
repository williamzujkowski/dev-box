"""
Sandbox Lifecycle Core - Main orchestration engine

Coordinates all aspects of sandbox lifecycle management including initialization,
monitoring, safety checks, and cleanup operations.
"""

import asyncio
import logging
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from ..monitoring.health import HealthMonitor
from ..monitoring.tracker import StateTracker
from ..safety.rollback import RollbackManager
from ..safety.validator import SafetyValidator
from .initializer import SandboxInitializer
from .state_manager import StateManager


class SandboxState(Enum):
    """Sandbox lifecycle states"""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ROLLING_BACK = "rolling_back"
    CLEANUP = "cleanup"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class SandboxConfig:
    """Configuration for sandbox instance"""

    sandbox_id: str
    workspace_path: Path
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    safety_constraints: Dict[str, Any] = field(default_factory=dict)
    monitoring_config: Dict[str, Any] = field(default_factory=dict)
    auto_cleanup: bool = True
    snapshot_frequency: int = 300  # seconds
    max_execution_time: int = 3600  # seconds


class SandboxCore:
    """
    Main sandbox lifecycle orchestrator

    Manages the complete lifecycle of a sandbox environment including:
    - Initialization and setup
    - State tracking and monitoring
    - Safety validation and constraints
    - Rollback and recovery mechanisms
    - Resource cleanup
    """

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.state = SandboxState.UNINITIALIZED
        self.logger = logging.getLogger(f"sandbox.{config.sandbox_id}")

        # Initialize components
        self.initializer = SandboxInitializer(config)
        self.state_manager = StateManager(config)
        self.state_tracker = StateTracker(config)
        self.health_monitor = HealthMonitor(config)
        self.rollback_manager = RollbackManager(config)
        self.safety_validator = SafetyValidator(config)

        # Runtime state
        self._tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> bool:
        """
        Initialize the sandbox environment

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.state = SandboxState.INITIALIZING
            self.logger.info(f"Initializing sandbox {self.config.sandbox_id}")

            # Initialize workspace
            if not await self.initializer.setup_workspace():
                raise Exception("Workspace setup failed")

            # Initialize state management
            if not await self.state_manager.initialize():
                raise Exception("State manager initialization failed")

            # Start monitoring
            await self.state_tracker.start()
            await self.health_monitor.start()

            # Create initial snapshot
            snapshot_id = await self.rollback_manager.create_snapshot("initial")
            if not snapshot_id:
                raise Exception("Failed to create initial snapshot")

            self.state = SandboxState.ACTIVE
            self.logger.info(
                f"Sandbox {self.config.sandbox_id} initialized successfully"
            )

            # Start background tasks
            await self._start_background_tasks()

            return True

        except Exception as e:
            self.logger.error(f"Sandbox initialization failed: {e}")
            self.state = SandboxState.ERROR
            await self.cleanup()
            return False

    async def execute_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an operation within the sandbox with safety checks

        Args:
            operation: Operation specification

        Returns:
            Dict containing operation results and metadata
        """
        if self.state != SandboxState.ACTIVE:
            raise Exception(f"Sandbox not active: {self.state}")

        operation_id = operation.get("id", "unknown")
        self.logger.info(f"Executing operation: {operation_id}")

        try:
            # Pre-execution safety check
            safety_result = await self.safety_validator.validate_operation(operation)
            if not safety_result.is_safe:
                raise Exception(
                    f"Operation failed safety check: {safety_result.reason}"
                )

            # Create pre-execution snapshot if needed
            snapshot_id = None
            if operation.get("create_snapshot", True):
                snapshot_id = await self.rollback_manager.create_snapshot(
                    f"pre-{operation_id}"
                )

            # Track operation start
            await self.state_tracker.track_operation_start(operation_id, operation)

            # Execute the operation (this would be implemented by subclasses)
            result = await self._execute_operation_impl(operation)

            # Track operation completion
            await self.state_tracker.track_operation_complete(operation_id, result)

            self.logger.info(f"Operation {operation_id} completed successfully")
            return {
                "success": True,
                "operation_id": operation_id,
                "result": result,
                "snapshot_id": snapshot_id,
                "timestamp": self.state_tracker.get_current_timestamp(),
            }

        except Exception as e:
            self.logger.error(f"Operation {operation_id} failed: {e}")

            # Track operation failure
            await self.state_tracker.track_operation_failed(operation_id, str(e))

            # Rollback if snapshot was created
            if snapshot_id and operation.get("auto_rollback", True):
                await self.rollback_manager.restore_snapshot(snapshot_id)

            return {
                "success": False,
                "operation_id": operation_id,
                "error": str(e),
                "snapshot_id": snapshot_id,
                "timestamp": self.state_tracker.get_current_timestamp(),
            }

    async def _execute_operation_impl(self, operation: Dict[str, Any]) -> Any:
        """
        Implementation-specific operation execution
        Override in subclasses for specific sandbox types
        """
        # Default implementation - placeholder
        await asyncio.sleep(0.1)  # Simulate operation
        return {"status": "completed", "message": "Default operation executed"}

    async def suspend(self) -> bool:
        """
        Suspend sandbox operations while preserving state

        Returns:
            bool: True if suspension successful
        """
        if self.state != SandboxState.ACTIVE:
            return False

        try:
            self.state = SandboxState.SUSPENDED
            self.logger.info("Suspending sandbox operations")

            # Pause monitoring
            await self.health_monitor.pause()

            # Create suspension snapshot
            snapshot_id = await self.rollback_manager.create_snapshot("suspension")

            return snapshot_id is not None

        except Exception as e:
            self.logger.error(f"Suspension failed: {e}")
            return False

    async def resume(self) -> bool:
        """
        Resume suspended sandbox operations

        Returns:
            bool: True if resumption successful
        """
        if self.state != SandboxState.SUSPENDED:
            return False

        try:
            self.logger.info("Resuming sandbox operations")

            # Resume monitoring
            await self.health_monitor.resume()

            self.state = SandboxState.ACTIVE
            return True

        except Exception as e:
            self.logger.error(f"Resumption failed: {e}")
            return False

    async def cleanup(self) -> bool:
        """
        Clean up sandbox resources and perform shutdown

        Returns:
            bool: True if cleanup successful
        """
        self.logger.info(f"Starting cleanup for sandbox {self.config.sandbox_id}")
        self.state = SandboxState.CLEANUP

        try:
            # Signal shutdown to background tasks
            self._shutdown_event.set()

            # Wait for background tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

            # Stop monitoring components
            await self.health_monitor.stop()
            await self.state_tracker.stop()

            # Cleanup resources
            await self.rollback_manager.cleanup()
            await self.state_manager.cleanup()

            # Remove workspace if configured
            if self.config.auto_cleanup:
                await self.initializer.cleanup_workspace()

            self.state = SandboxState.TERMINATED
            self.logger.info("Sandbox cleanup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive sandbox status

        Returns:
            Dict containing current sandbox status and metrics
        """
        return {
            "sandbox_id": self.config.sandbox_id,
            "state": self.state.value,
            "uptime": await self.state_tracker.get_uptime(),
            "health": await self.health_monitor.get_health_status(),
            "resource_usage": await self.state_tracker.get_resource_usage(),
            "recent_operations": await self.state_tracker.get_recent_operations(10),
            "available_snapshots": await self.rollback_manager.list_snapshots(),
            "safety_violations": await self.safety_validator.get_recent_violations(),
        }

    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        # Periodic snapshot creation
        if self.config.snapshot_frequency > 0:
            task = asyncio.create_task(self._periodic_snapshot_task())
            self._tasks.append(task)

        # Health monitoring task
        task = asyncio.create_task(self._health_monitoring_task())
        self._tasks.append(task)

        # Resource cleanup task
        task = asyncio.create_task(self._cleanup_task())
        self._tasks.append(task)

    async def _periodic_snapshot_task(self):
        """Background task for periodic snapshot creation"""
        while not self._shutdown_event.is_set():
            try:
                if self.state == SandboxState.ACTIVE:
                    timestamp = int(asyncio.get_event_loop().time())
                    await self.rollback_manager.create_snapshot(f"periodic-{timestamp}")

                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=self.config.snapshot_frequency
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Periodic snapshot task error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _health_monitoring_task(self):
        """Background task for continuous health monitoring"""
        while not self._shutdown_event.is_set():
            try:
                if self.state == SandboxState.ACTIVE:
                    health_status = await self.health_monitor.check_health()
                    if not health_status.is_healthy:
                        self.logger.warning(
                            f"Health check failed: {health_status.issues}"
                        )

                        # Consider automatic recovery actions
                        if health_status.severity == "critical":
                            await self.suspend()

                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Health monitoring task error: {e}")
                await asyncio.sleep(60)

    async def _cleanup_task(self):
        """Background task for periodic cleanup"""
        while not self._shutdown_event.is_set():
            try:
                if self.state == SandboxState.ACTIVE:
                    # Cleanup old snapshots
                    await self.rollback_manager.cleanup_old_snapshots()

                    # Cleanup state tracking data
                    await self.state_tracker.cleanup_old_data()

                await asyncio.sleep(3600)  # Cleanup every hour
            except Exception as e:
                self.logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(300)
