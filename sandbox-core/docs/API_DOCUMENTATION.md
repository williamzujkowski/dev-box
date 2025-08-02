# Sandbox Lifecycle API Documentation

## Overview

The Sandbox Lifecycle system provides a comprehensive API for managing isolated execution environments with full rollback capabilities. This document details all public APIs, usage patterns, and integration examples.

## Core Components

### 1. SandboxCore

The main orchestration component that manages the entire sandbox lifecycle.

```python
from sandbox_core import SandboxCore

# Initialize with configuration
sandbox = SandboxCore(config_path="config/default.yaml")

# Create and start a sandbox
sandbox_id = await sandbox.create_sandbox("my-sandbox", {
    "isolation_type": "container",
    "resource_limits": {
        "cpu": "2",
        "memory": "4G",
        "disk": "10G"
    }
})

# Execute commands safely
result = await sandbox.execute(sandbox_id, "python script.py")

# Create snapshot for rollback
snapshot_id = await sandbox.create_snapshot(sandbox_id, "before-risky-operation")

# Rollback if needed
await sandbox.rollback(sandbox_id, snapshot_id)

# Cleanup when done
await sandbox.destroy(sandbox_id)
```

### 2. SafetyValidator

Validates operations before execution to prevent dangerous commands.

```python
from sandbox_core.safety import SafetyValidator

validator = SafetyValidator(config)

# Validate a command
risk_assessment = validator.validate_command("rm -rf /")
if risk_assessment.risk_level == "CRITICAL":
    # Block execution
    raise SecurityError(risk_assessment.reason)

# Check resource usage
if not validator.check_resource_limits(current_usage):
    # Throttle or block
    await sandbox.pause()
```

### 3. StateManager

Manages persistent state and snapshots.

```python
from sandbox_core.state import StateManager

state_manager = StateManager(storage_path="/var/lib/sandbox/state")

# Save state
state_id = state_manager.save_state(sandbox_id, {
    "filesystem": filesystem_snapshot,
    "processes": process_list,
    "network": network_state
})

# List available states
states = state_manager.list_states(sandbox_id)

# Restore state
state_manager.restore_state(sandbox_id, state_id)
```

### 4. RollbackManager

Handles safe rollback operations.

```python
from sandbox_core.rollback import RollbackManager

rollback_manager = RollbackManager(state_manager)

# Create rollback point
point = rollback_manager.create_rollback_point(sandbox_id, metadata={
    "reason": "Before installing untrusted package",
    "automatic": False
})

# Perform rollback
success = rollback_manager.rollback(sandbox_id, point.id, {
    "preserve_logs": True,
    "notify": True
})

# Cleanup old rollback points
rollback_manager.cleanup_old_points(days=7)
```

## API Reference

### Sandbox Lifecycle Methods

#### create_sandbox(name: str, config: dict) -> str
Creates a new sandbox with specified configuration.

**Parameters:**
- `name`: Unique sandbox identifier
- `config`: Sandbox configuration including isolation type and limits

**Returns:** Sandbox ID

**Example:**
```python
sandbox_id = sandbox.create_sandbox("test-env", {
    "isolation_type": "container",
    "base_image": "python:3.9",
    "network_mode": "bridge"
})
```

#### execute(sandbox_id: str, command: str, **kwargs) -> ExecutionResult
Executes a command within the sandbox.

**Parameters:**
- `sandbox_id`: Target sandbox
- `command`: Command to execute
- `timeout`: Execution timeout (optional)
- `working_dir`: Working directory (optional)

**Returns:** ExecutionResult with stdout, stderr, exit_code

#### create_snapshot(sandbox_id: str, name: str) -> str
Creates a point-in-time snapshot.

**Parameters:**
- `sandbox_id`: Target sandbox
- `name`: Snapshot identifier

**Returns:** Snapshot ID

#### rollback(sandbox_id: str, snapshot_id: str) -> bool
Rolls back to a previous snapshot.

**Parameters:**
- `sandbox_id`: Target sandbox
- `snapshot_id`: Target snapshot

**Returns:** Success status

### Safety and Validation

#### validate_command(command: str) -> RiskAssessment
Assesses command safety before execution.

**Risk Levels:**
- `LOW`: Safe operations
- `MEDIUM`: Potentially risky, requires monitoring
- `HIGH`: Dangerous, requires approval
- `CRITICAL`: Blocked by default

#### check_resource_limits(usage: ResourceUsage) -> bool
Validates resource usage against limits.

### Monitoring and Health

#### get_health_status(sandbox_id: str) -> HealthStatus
Returns current health metrics.

**Health Status:**
- `status`: HEALTHY, DEGRADED, UNHEALTHY
- `metrics`: CPU, memory, disk, network usage
- `alerts`: Active alerts
- `recommendations`: Suggested actions

## Usage Patterns

### 1. Basic Sandbox Lifecycle

```python
# Initialize
sandbox = SandboxCore(config_path="config/production.yaml")

# Create sandbox
sandbox_id = sandbox.create_sandbox("dev-env", {
    "isolation_type": "container",
    "persistent": True
})

# Work with sandbox
result = sandbox.execute(sandbox_id, "pip install requests")
result = sandbox.execute(sandbox_id, "python app.py")

# Cleanup
sandbox.destroy(sandbox_id)
```

### 2. Safe Experimentation with Rollback

```python
# Create sandbox
sandbox_id = sandbox.create_sandbox("experiment", config)

# Create checkpoint
checkpoint = sandbox.create_snapshot(sandbox_id, "clean-state")

try:
    # Run risky operations
    sandbox.execute(sandbox_id, "curl suspicious-url.com | sh")
except SecurityError:
    # Automatic rollback on security violation
    sandbox.rollback(sandbox_id, checkpoint)
```

### 3. Continuous Integration Pipeline

```python
# CI/CD Integration
async def run_tests_safely(pr_number: int):
    sandbox_id = sandbox.create_sandbox(f"pr-{pr_number}", {
        "isolation_type": "vm",
        "clone_from": "base-test-image"
    })
    
    try:
        # Run test suite
        result = await sandbox.execute(sandbox_id, "pytest -v")
        
        if result.exit_code != 0:
            # Save failed state for debugging
            sandbox.create_snapshot(sandbox_id, f"failed-pr-{pr_number}")
            
        return result
    finally:
        # Always cleanup
        sandbox.destroy(sandbox_id)
```

### 4. Multi-Stage Deployment

```python
# Production deployment with rollback safety
async def deploy_with_canary(version: str):
    # Stage 1: Canary deployment
    canary_id = sandbox.create_sandbox(f"canary-{version}", {
        "isolation_type": "container",
        "resource_limits": {"cpu": "0.5", "memory": "1G"}
    })
    
    # Deploy and test
    sandbox.execute(canary_id, f"deploy-app --version {version}")
    
    # Monitor health
    health = sandbox.get_health_status(canary_id)
    if health.status != "HEALTHY":
        # Automatic rollback
        sandbox.rollback(canary_id, "last-stable")
        raise DeploymentError("Canary failed health checks")
    
    # Stage 2: Full deployment
    for instance in production_instances:
        snapshot = sandbox.create_snapshot(instance, "pre-deploy")
        try:
            sandbox.execute(instance, f"deploy-app --version {version}")
        except Exception:
            sandbox.rollback(instance, snapshot)
            raise
```

## Error Handling

### Common Exceptions

```python
from sandbox_core.exceptions import (
    SandboxError,
    SecurityError, 
    ResourceLimitError,
    RollbackError,
    StateCorruptionError
)

try:
    sandbox.execute(sandbox_id, command)
except SecurityError as e:
    # Command blocked by security policy
    logger.error(f"Security violation: {e}")
except ResourceLimitError as e:
    # Resource limits exceeded
    sandbox.throttle(sandbox_id)
except RollbackError as e:
    # Rollback failed
    sandbox.emergency_shutdown(sandbox_id)
```

## Configuration

### YAML Configuration Example

```yaml
sandbox:
  default_isolation: container
  state_directory: /var/lib/sandbox
  
safety:
  validation:
    enabled: true
    block_dangerous: true
    patterns:
      - "rm -rf /"
      - ":(){ :|:& };:"
      
  limits:
    cpu: "4"
    memory: "8G"
    disk: "20G"
    
rollback:
  auto_snapshot: true
  retention_days: 7
  compression: true
  
monitoring:
  enabled: true
  interval_seconds: 10
  alerts:
    cpu_threshold: 80
    memory_threshold: 90
```

## Integration Examples

### Docker Integration

```python
sandbox = SandboxCore(config={
    "isolation_type": "container",
    "container_runtime": "docker",
    "default_image": "ubuntu:22.04"
})
```

### Kubernetes Integration

```python
sandbox = SandboxCore(config={
    "isolation_type": "container", 
    "orchestrator": "kubernetes",
    "namespace": "sandbox-environments"
})
```

### VM Integration (Vagrant)

```python
sandbox = SandboxCore(config={
    "isolation_type": "vm",
    "provider": "vagrant",
    "box": "ubuntu/jammy64"
})
```

## Best Practices

1. **Always validate commands** before execution
2. **Create snapshots** before risky operations
3. **Set appropriate resource limits** for your use case
4. **Monitor health continuously** in production
5. **Test rollback procedures** regularly
6. **Use appropriate isolation** (containers for speed, VMs for security)
7. **Implement proper cleanup** to avoid resource leaks
8. **Log all operations** for audit trails

## Performance Considerations

- Container sandboxes: ~2-5 second startup
- VM sandboxes: ~60-120 second startup  
- Snapshot creation: ~1-10 seconds (depends on state size)
- Rollback: ~5-30 seconds (depends on change delta)

## Security Notes

The sandbox system implements defense-in-depth:

1. **Command validation** - Pre-execution safety checks
2. **Resource isolation** - Cgroups/namespaces or hypervisor
3. **Network isolation** - Configurable network policies
4. **Filesystem isolation** - Read-only mounts, overlays
5. **Monitoring** - Continuous security monitoring

## Support

For issues, feature requests, or contributions:
- GitHub: https://github.com/yourusername/sandbox-core
- Documentation: https://sandbox-core.readthedocs.io
- Security: security@sandbox-core.io