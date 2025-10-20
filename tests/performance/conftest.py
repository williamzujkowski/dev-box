"""Fixtures for performance benchmarks."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def mock_pooled_vm():
    """Mock PooledVM for performance tests."""
    vm = AsyncMock()
    vm.name = "perf-vm"
    vm.get_state = AsyncMock(return_value="running")

    # Create a PooledVM wrapper with proper attributes
    from agent_vm.execution.pool import PooledVM

    pooled = PooledVM(vm=vm, snapshot_name="golden", created_at=datetime.now())
    return pooled
