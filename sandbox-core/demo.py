#!/usr/bin/env python3
"""
Sandbox Core Demo

Demonstrates the basic functionality of the sandbox lifecycle core.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Import sandbox components
from src.sandbox import SafetyValidator
from src.sandbox import SandboxConfig
from src.sandbox import SandboxCore


async def demo_basic_sandbox():
    """Demonstrate basic sandbox operations"""
    print("🚀 Starting Sandbox Core Demo")
    print("=" * 50)

    # Create temporary workspace
    temp_dir = Path(tempfile.mkdtemp(prefix="sandbox_demo_"))
    print(f"📁 Created temporary workspace: {temp_dir}")

    try:
        # Create sandbox configuration
        config = SandboxConfig(
            sandbox_id="demo-sandbox",
            workspace_path=temp_dir / "workspace",
            resource_limits={"memory_mb": 512, "cpu_percent": 25, "disk_mb": 1024},
            safety_constraints={
                "max_snapshots": 5,
                "auto_cleanup_hours": 24,
                "network": {"allow_external": False},
                "compress_snapshots": True,
            },
            monitoring_config={
                "collection_interval": 10,
                "health_check_interval": 30,
                "resource_thresholds": {
                    "cpu_percent": 80,
                    "memory_percent": 80,
                    "disk_percent": 80,
                },
            },
        )

        print(f"⚙️  Created sandbox configuration: {config.sandbox_id}")

        # Create and initialize sandbox
        sandbox = SandboxCore(config)
        print(f"🔧 Created sandbox core (state: {sandbox.state.value})")

        # Initialize sandbox
        print("\n📋 Initializing sandbox...")
        success = await sandbox.initialize()

        if success:
            print(f"✅ Sandbox initialized successfully (state: {sandbox.state.value})")
        else:
            print("❌ Sandbox initialization failed")
            return

        # Get initial status
        print("\n📊 Getting sandbox status...")
        status = await sandbox.get_status()
        print(f"   Sandbox ID: {status['sandbox_id']}")
        print(f"   State: {status['state']}")
        print(f"   Uptime: {status['uptime']:.2f} seconds")
        print(f"   Health: {status['health']}")

        # Create a snapshot
        print("\n📸 Creating initial snapshot...")
        snapshot_id = await sandbox.rollback_manager.create_snapshot(
            "Initial demo snapshot", "manual", tags=["demo", "initial"]
        )

        if snapshot_id:
            print(f"✅ Created snapshot: {snapshot_id}")
        else:
            print("❌ Failed to create snapshot")

        # Execute some operations
        print("\n🔄 Executing demo operations...")

        operations = [
            {
                "type": "file_operation",
                "id": "create_file",
                "description": "Create demo file",
                "files": [str(config.workspace_path / "work" / "demo.txt")],
                "create_snapshot": False,
            },
            {
                "type": "data_processing",
                "id": "process_data",
                "description": "Process demo data",
                "max_memory_mb": 100,
                "create_snapshot": False,
            },
        ]

        for i, operation in enumerate(operations, 1):
            print(f"\n   Operation {i}: {operation['description']}")
            result = await sandbox.execute_operation(operation)

            if result["success"]:
                print(f"   ✅ {operation['id']} completed successfully")
            else:
                print(
                    f"   ❌ {operation['id']} failed: {result.get('error', 'Unknown error')}"
                )

        # List snapshots
        print("\n📸 Listing available snapshots...")
        snapshots = await sandbox.rollback_manager.list_snapshots()
        for snapshot in snapshots:
            print(f"   • {snapshot['snapshot_id']}: {snapshot['description']}")
            print(
                f"     Created: {snapshot['created_at']}, Size: {snapshot['size_bytes']} bytes"
            )

        # Demonstrate state management
        print("\n💾 Demonstrating state management...")
        state_manager = sandbox.state_manager

        # Set some state
        await state_manager.set_state("demo.counter", 42)
        await state_manager.set_state("demo.message", "Hello from sandbox!")

        # Retrieve state
        counter = await state_manager.get_state("demo.counter")
        message = await state_manager.get_state("demo.message")

        print(f"   Counter: {counter}")
        print(f"   Message: {message}")

        # List all state keys
        keys = await state_manager.list_keys()
        print(f"   Total state keys: {len(keys)}")

        # Create state snapshot
        state_snapshot = await state_manager.create_snapshot("demo_state")
        if state_snapshot:
            print(f"   Created state snapshot: {state_snapshot.snapshot_id}")

        # Test safety validation
        print("\n🛡️  Testing safety validation...")
        validator = sandbox.safety_validator

        safe_operation = {
            "type": "file_operation",
            "command": "echo 'Hello World'",
            "files": ["demo.txt"],
        }

        result = await validator.validate_operation(safe_operation)
        print(
            f"   Safe operation validation: {'✅ SAFE' if result.is_safe else '❌ UNSAFE'}"
        )
        print(f"   Risk level: {result.risk_level.value}")

        potentially_unsafe_operation = {
            "type": "system_command",
            "command": "rm -rf /tmp/*",
            "requires_network": True,
        }

        result = await validator.validate_operation(potentially_unsafe_operation)
        print(
            f"   Unsafe operation validation: {'✅ SAFE' if result.is_safe else '❌ UNSAFE'}"
        )
        print(f"   Risk level: {result.risk_level.value}")
        if result.violations:
            print(f"   Violations: {', '.join(result.violations[:3])}")

        # Suspend and resume
        print("\n⏸️  Testing suspend/resume...")
        suspend_success = await sandbox.suspend()
        print(f"   Suspend: {'✅ SUCCESS' if suspend_success else '❌ FAILED'}")
        print(f"   State: {sandbox.state.value}")

        await asyncio.sleep(1)  # Brief pause

        resume_success = await sandbox.resume()
        print(f"   Resume: {'✅ SUCCESS' if resume_success else '❌ FAILED'}")
        print(f"   State: {sandbox.state.value}")

        # Final status
        print("\n📊 Final sandbox status...")
        final_status = await sandbox.get_status()
        print(f"   Uptime: {final_status['uptime']:.2f} seconds")
        print(f"   Recent operations: {len(final_status['recent_operations'])}")
        print(f"   Available snapshots: {len(final_status['available_snapshots'])}")

        # Cleanup
        print("\n🧹 Cleaning up sandbox...")
        cleanup_success = await sandbox.cleanup()

        if cleanup_success:
            print(f"✅ Sandbox cleaned up successfully (state: {sandbox.state.value})")
        else:
            print("❌ Sandbox cleanup failed")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up temporary directory
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"🗑️  Cleaned up temporary workspace: {temp_dir}")

    print("\n" + "=" * 50)
    print("🎉 Sandbox Core Demo completed!")


async def demo_safety_features():
    """Demonstrate safety and validation features"""
    print("\n🛡️  Safety Features Demo")
    print("-" * 30)

    # Create minimal config for safety testing
    temp_dir = Path(tempfile.mkdtemp(prefix="sandbox_safety_"))

    try:
        config = SandboxConfig(
            sandbox_id="safety-demo",
            workspace_path=temp_dir / "workspace",
            resource_limits={"memory_mb": 256, "cpu_percent": 10},
            safety_constraints={
                "network": {"allow_external": False},
                "max_content_size_mb": 1,
            },
        )

        validator = SafetyValidator(config)

        # Test various operation types
        test_operations = [
            {
                "name": "Safe file operation",
                "operation": {
                    "type": "file_operation",
                    "command": "cat demo.txt",
                    "files": ["demo.txt"],
                },
            },
            {
                "name": "Potentially dangerous command",
                "operation": {
                    "type": "system_command",
                    "command": "rm -rf /important/data",
                },
            },
            {
                "name": "Network operation",
                "operation": {
                    "type": "network_operation",
                    "requires_network": True,
                    "max_network_requests": 10,
                },
            },
            {
                "name": "Resource-intensive operation",
                "operation": {
                    "type": "computation",
                    "max_memory_mb": 2048,
                    "max_execution_time": 7200,
                },
            },
        ]

        for test in test_operations:
            print(f"\n   Testing: {test['name']}")
            result = await validator.validate_operation(test["operation"])

            status = "✅ SAFE" if result.is_safe else "❌ UNSAFE"
            print(f"   Result: {status} (Risk: {result.risk_level.value})")

            if result.violations:
                print(f"   Violations: {', '.join(result.violations[:2])}")

            if result.suggestions:
                print(f"   Suggestions: {result.suggestions[0]}")

        # Test content validation
        print("\n   Testing content validation...")

        safe_content = "print('Hello, World!')"
        result = await validator.validate_content(safe_content, "code")
        print(f"   Safe code: {'✅ SAFE' if result.is_safe else '❌ UNSAFE'}")

        unsafe_content = 'eval("malicious_code()"); import os; os.system("rm -rf /")'
        result = await validator.validate_content(unsafe_content, "code")
        print(f"   Unsafe code: {'✅ SAFE' if result.is_safe else '❌ UNSAFE'}")
        if result.violations:
            print(f"   Issues found: {len(result.violations)}")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


async def main():
    """Main demo function"""
    await demo_basic_sandbox()
    await demo_safety_features()


if __name__ == "__main__":
    asyncio.run(main())
