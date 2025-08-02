"""
Sandbox Lifecycle Core - Safe Execution Environment Management

This module provides a comprehensive framework for managing isolated execution
environments with safety guarantees, state tracking, and rollback capabilities.
"""

from .lifecycle.core import SandboxConfig
from .lifecycle.core import SandboxCore
from .lifecycle.core import SandboxState
from .lifecycle.initializer import SandboxInitializer
from .lifecycle.state_manager import StateManager
from .monitoring.health import HealthMonitor
from .monitoring.tracker import StateTracker
from .safety.rollback import RollbackManager
from .safety.validator import SafetyValidator

__version__ = "0.1.0"
__all__ = [
    "HealthMonitor",
    "RollbackManager",
    "SafetyValidator",
    "SandboxConfig",
    "SandboxCore",
    "SandboxInitializer",
    "SandboxState",
    "StateManager",
    "StateTracker",
]
