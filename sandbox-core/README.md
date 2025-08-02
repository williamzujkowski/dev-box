# Sandbox Lifecycle Core

A comprehensive Python framework for managing isolated execution environments
with safety guarantees, state tracking, and rollback capabilities.

## Features

### 🏗️ Core Architecture

- **Modular Design**: Clean separation of concerns with lifecycle, monitoring,
  and safety modules
- **Async/Await Support**: Fully asynchronous operations for better performance
- **Type Safety**: Comprehensive type hints and validation
- **Extensible**: Plugin-friendly architecture for custom implementations

### 🔒 Safety & Security

- **Operation Validation**: Pre-execution safety checks with configurable rules
- **Pattern Matching**: Dangerous command and content detection
- **Resource Limits**: CPU, memory, disk, and network usage constraints
- **Risk Assessment**: Multi-level risk scoring for operations
- **Sandboxing**: Isolated workspace with controlled access

### 📸 State Management & Rollback

- **State Snapshots**: Point-in-time state capture with compression
- **Rollback Capability**: Full or selective state restoration
- **Version Control**: Versioned state entries with history tracking
- **Integrity Checking**: Checksum validation and corruption detection
- **Automatic Cleanup**: Configurable retention policies

### 📊 Monitoring & Health

- **Real-time Tracking**: Resource usage and operation monitoring
- **Health Checks**: System health assessment with automated recovery
- **Performance Metrics**: Comprehensive performance analytics
- **Event System**: Extensible event notification system
- **Alerting**: Threshold-based monitoring with customizable alerts

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd sandbox-core

# Install dependencies
pip install -r requirements.txt

# Run the demo
python demo.py
```

### Basic Usage

```python
import asyncio
from pathlib import Path
from src.sandbox import SandboxCore, SandboxConfig

async def main():
    # Create configuration
    config = SandboxConfig(
        sandbox_id="my-sandbox",
        workspace_path=Path("/tmp/my-sandbox"),
        resource_limits={
            "memory_mb": 1024,
            "cpu_percent": 50,
            "disk_mb": 2048
        },
        safety_constraints={
            "max_snapshots": 10,
            "network": {"allow_external": False}
        }
    )

    # Create and initialize sandbox
    sandbox = SandboxCore(config)
    await sandbox.initialize()

    # Execute operation
    operation = {
        "type": "file_operation",
        "id": "demo_op",
        "command": "echo 'Hello, Sandbox!'",
        "files": ["output.txt"]
    }

    result = await sandbox.execute_operation(operation)
    print(f"Operation result: {result}")

    # Cleanup
    await sandbox.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## Architecture Overview

```
sandbox-core/
├── src/sandbox/
│   ├── lifecycle/          # Core lifecycle management
│   │   ├── core.py        # Main orchestrator
│   │   ├── initializer.py # Environment setup
│   │   └── state_manager.py # State persistence
│   ├── monitoring/         # System monitoring
│   │   ├── tracker.py     # Operation tracking
│   │   └── health.py      # Health monitoring
│   ├── safety/            # Security & validation
│   │   ├── validator.py   # Safety validation
│   │   └── rollback.py    # Rollback management
│   └── utils/             # Utility modules
│       ├── filesystem.py  # File system utilities
│       ├── serialization.py # Data serialization
│       └── validation.py  # Configuration validation
├── config/                # Configuration files
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## Key Components

### SandboxCore

The main orchestrator that coordinates all sandbox operations:

- Lifecycle management (initialize, suspend, resume, cleanup)
- Operation execution with safety checks
- Component coordination and error handling

### SandboxInitializer

Handles sandbox environment setup:

- Workspace creation and structure
- Resource allocation and limits
- Security configuration and validation

### StateManager

Manages persistent state with versioning:

- SQLite-based storage with encryption support
- State snapshots and history tracking
- Cross-session persistence and recovery

### StateTracker

Real-time monitoring and metrics collection:

- Resource usage tracking (CPU, memory, disk, network)
- Operation performance metrics
- Historical data analysis

### HealthMonitor

Continuous health assessment:

- System resource health checks
- Process and filesystem monitoring
- Automated recovery mechanisms

### RollbackManager

Comprehensive rollback capabilities:

- Filesystem snapshots with compression
- Incremental and full backups
- Integrity validation and corruption detection

### SafetyValidator

Security and safety validation:

- Pattern-based content filtering
- Resource usage validation
- Risk assessment and scoring

## Configuration

Sandbox behavior is controlled through YAML configuration files:

```yaml
# config/default.yaml
sandbox_id: "my-sandbox"
workspace_path: "/tmp/sandbox-workspace"

resource_limits:
  memory_mb: 1024
  cpu_percent: 50
  disk_mb: 2048

safety_constraints:
  max_snapshots: 10
  compress_snapshots: true
  network:
    allow_external: false

monitoring_config:
  collection_interval: 30
  health_check_interval: 60
  resource_thresholds:
    cpu_percent: 80
    memory_percent: 80
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_core.py -v

# Run with coverage
pytest tests/ --cov=src/sandbox --cov-report=html
```

## Safety Features

### Operation Validation

- Pre-execution safety checks
- Dangerous command detection
- Resource limit enforcement
- Risk-based approval workflows

### Content Filtering

- Pattern-based malicious content detection
- File type and extension validation
- Size limits and content scanning

### Isolation

- Workspace-confined operations
- Network access controls
- Process isolation and resource limits

## Monitoring & Observability

### Metrics Collection

- Real-time resource usage monitoring
- Operation performance tracking
- Historical trend analysis

### Health Monitoring

- Automated health checks
- System resource validation
- Self-healing capabilities

### Event System

- Operation lifecycle events
- Threshold violation alerts
- Custom event handlers

## Advanced Features

### State Management

- Versioned state with rollback support
- Cross-session persistence
- Encrypted sensitive data storage

### Snapshot & Recovery

- Point-in-time state capture
- Incremental backup support
- Automated cleanup policies

### Extensibility

- Plugin architecture for custom validators
- Custom operation types
- Configurable monitoring checks

## Development

### Project Structure

- Clean modular architecture
- Comprehensive type hints
- Extensive documentation
- Full test coverage

### Code Quality

- Black code formatting
- Flake8 linting
- MyPy type checking
- Pytest testing framework

## License

This project is licensed under the MIT License - see the LICENSE file for
details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## Support

For questions, issues, or contributions, please refer to the project's issue
tracker or documentation.
