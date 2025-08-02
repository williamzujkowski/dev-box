"""
State Tracker - Real-time sandbox state monitoring

Tracks sandbox operations, resource usage, performance metrics, and provides
comprehensive monitoring capabilities for sandbox lifecycle management.
"""

import asyncio
import logging
import time
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta

from ..utils.stub_modules import MetricsCollector, EventEmitter


@dataclass
class OperationRecord:
    """Record of a sandbox operation"""
    operation_id: str
    operation_type: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"  # running, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceSnapshot:
    """Snapshot of resource usage"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    disk_usage_mb: float
    network_io: Dict[str, int] = field(default_factory=dict)
    process_count: int = 0
    file_handles: int = 0


@dataclass
class PerformanceMetrics:
    """Performance metrics over time"""
    avg_cpu_percent: float
    max_cpu_percent: float
    avg_memory_mb: float
    max_memory_mb: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    avg_operation_duration: float
    uptime_seconds: float


class StateTracker:
    """
    Real-time sandbox state and performance tracker
    
    Tracks:
    - Operation execution and performance
    - Resource usage (CPU, memory, disk, network)
    - System health indicators
    - Error patterns and anomalies
    - Historical performance data
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(f"sandbox.{config.sandbox_id}.tracker")
        
        # Tracking data
        self.operations: Dict[str, OperationRecord] = {}
        self.resource_history: deque = deque(maxlen=1000)  # Keep last 1000 snapshots
        self.start_time = time.time()
        
        # Metrics collection
        self.metrics_collector = MetricsCollector()
        self.event_emitter = EventEmitter()
        
        # Background task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # Configuration
        self.collection_interval = config.monitoring_config.get("collection_interval", 30)  # seconds
        self.max_operation_history = config.monitoring_config.get("max_operation_history", 1000)
        
    async def start(self) -> bool:
        """
        Start the state tracker
        
        Returns:
            bool: True if started successfully
        """
        try:
            self.logger.info("Starting state tracker")
            
            # Start background monitoring
            self._monitoring_task = asyncio.create_task(self._monitor_resources())
            
            # Emit start event
            await self.event_emitter.emit("tracker_started", {
                "sandbox_id": self.config.sandbox_id,
                "start_time": self.start_time
            })
            
            self.logger.info("State tracker started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start state tracker: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the state tracker
        
        Returns:
            bool: True if stopped successfully
        """
        try:
            self.logger.info("Stopping state tracker")
            
            # Signal stop to background task
            self._stop_event.set()
            
            # Wait for monitoring task to complete
            if self._monitoring_task:
                await self._monitoring_task
                self._monitoring_task = None
            
            # Emit stop event
            await self.event_emitter.emit("tracker_stopped", {
                "sandbox_id": self.config.sandbox_id,
                "stop_time": time.time(),
                "uptime": time.time() - self.start_time
            })
            
            self.logger.info("State tracker stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop state tracker: {e}")
            return False
    
    async def track_operation_start(self, operation_id: str, operation: Dict[str, Any]):
        """
        Track the start of an operation
        
        Args:
            operation_id: Unique operation identifier
            operation: Operation details
        """
        try:
            start_time = time.time()
            
            # Create operation record
            record = OperationRecord(
                operation_id=operation_id,
                operation_type=operation.get("type", "unknown"),
                start_time=start_time,
                metadata=operation.get("metadata", {}),
                resource_usage=await self._capture_resource_snapshot_dict()
            )
            
            self.operations[operation_id] = record
            
            # Emit event
            await self.event_emitter.emit("operation_started", {
                "operation_id": operation_id,
                "operation_type": record.operation_type,
                "start_time": start_time
            })
            
            self.logger.debug(f"Started tracking operation: {operation_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to track operation start {operation_id}: {e}")
    
    async def track_operation_complete(self, operation_id: str, result: Any):
        """
        Track the completion of an operation
        
        Args:
            operation_id: Operation identifier
            result: Operation result
        """
        try:
            if operation_id not in self.operations:
                self.logger.warning(f"Operation {operation_id} not found for completion tracking")
                return
            
            end_time = time.time()
            record = self.operations[operation_id]
            
            # Update record
            record.end_time = end_time
            record.status = "completed"
            record.metadata["result"] = result
            record.metadata["duration"] = end_time - record.start_time
            
            # Emit event
            await self.event_emitter.emit("operation_completed", {
                "operation_id": operation_id,
                "duration": record.metadata["duration"],
                "result": result
            })
            
            self.logger.debug(f"Completed tracking operation: {operation_id}")
            await self._maybe_cleanup_old_operations()
            
        except Exception as e:
            self.logger.error(f"Failed to track operation completion {operation_id}: {e}")
    
    async def track_operation_failed(self, operation_id: str, error: str):
        """
        Track the failure of an operation
        
        Args:
            operation_id: Operation identifier
            error: Error message
        """
        try:
            if operation_id not in self.operations:
                self.logger.warning(f"Operation {operation_id} not found for failure tracking")
                return
            
            end_time = time.time()
            record = self.operations[operation_id]
            
            # Update record
            record.end_time = end_time
            record.status = "failed"
            record.error_message = error
            record.metadata["duration"] = end_time - record.start_time
            
            # Emit event
            await self.event_emitter.emit("operation_failed", {
                "operation_id": operation_id,
                "duration": record.metadata["duration"],
                "error": error
            })
            
            self.logger.debug(f"Failed tracking operation: {operation_id}")
            await self._maybe_cleanup_old_operations()
            
        except Exception as e:
            self.logger.error(f"Failed to track operation failure {operation_id}: {e}")
    
    async def get_uptime(self) -> float:
        """
        Get sandbox uptime in seconds
        
        Returns:
            float: Uptime in seconds
        """
        return time.time() - self.start_time
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage
        
        Returns:
            Dict containing current resource usage
        """
        try:
            snapshot = await self._capture_resource_snapshot()
            return {
                "cpu_percent": snapshot.cpu_percent,
                "memory_mb": snapshot.memory_mb,
                "disk_usage_mb": snapshot.disk_usage_mb,
                "network_io": snapshot.network_io,
                "process_count": snapshot.process_count,
                "file_handles": snapshot.file_handles,
                "timestamp": snapshot.timestamp
            }
        except Exception as e:
            self.logger.error(f"Failed to get resource usage: {e}")
            return {}
    
    async def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent operations
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of recent operations
        """
        try:
            # Sort operations by start time, most recent first
            sorted_ops = sorted(
                self.operations.values(),
                key=lambda op: op.start_time,
                reverse=True
            )
            
            recent_ops = []
            for op in sorted_ops[:limit]:
                op_dict = {
                    "operation_id": op.operation_id,
                    "operation_type": op.operation_type,
                    "start_time": op.start_time,
                    "end_time": op.end_time,
                    "status": op.status,
                    "duration": op.metadata.get("duration"),
                    "error_message": op.error_message
                }
                recent_ops.append(op_dict)
            
            return recent_ops
            
        except Exception as e:
            self.logger.error(f"Failed to get recent operations: {e}")
            return []
    
    async def get_performance_metrics(self, window_minutes: int = 60) -> PerformanceMetrics:
        """
        Get performance metrics for a time window
        
        Args:
            window_minutes: Time window in minutes
            
        Returns:
            PerformanceMetrics object
        """
        try:
            window_start = time.time() - (window_minutes * 60)
            
            # Filter resource snapshots in window
            recent_snapshots = [
                snapshot for snapshot in self.resource_history
                if snapshot.timestamp >= window_start
            ]
            
            # Filter operations in window
            recent_operations = [
                op for op in self.operations.values()
                if op.start_time >= window_start
            ]
            
            # Calculate metrics
            cpu_values = [s.cpu_percent for s in recent_snapshots] or [0]
            memory_values = [s.memory_mb for s in recent_snapshots] or [0]
            
            successful_ops = [op for op in recent_operations if op.status == "completed"]
            failed_ops = [op for op in recent_operations if op.status == "failed"]
            
            # Calculate average operation duration
            completed_ops = [op for op in recent_operations if op.end_time is not None]
            durations = [op.end_time - op.start_time for op in completed_ops]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return PerformanceMetrics(
                avg_cpu_percent=sum(cpu_values) / len(cpu_values),
                max_cpu_percent=max(cpu_values),
                avg_memory_mb=sum(memory_values) / len(memory_values),
                max_memory_mb=max(memory_values),
                total_operations=len(recent_operations),
                successful_operations=len(successful_ops),
                failed_operations=len(failed_ops),
                avg_operation_duration=avg_duration,
                uptime_seconds=await self.get_uptime()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    async def get_resource_history(self, limit: int = 100) -> List[ResourceSnapshot]:
        """
        Get resource usage history
        
        Args:
            limit: Maximum number of snapshots
            
        Returns:
            List of resource snapshots
        """
        try:
            # Return most recent snapshots
            return list(self.resource_history)[-limit:] if self.resource_history else []
            
        except Exception as e:
            self.logger.error(f"Failed to get resource history: {e}")
            return []
    
    def get_current_timestamp(self) -> float:
        """Get current timestamp"""
        return time.time()
    
    async def cleanup_old_data(self, hours: int = 24) -> int:
        """
        Clean up old tracking data
        
        Args:
            hours: Age threshold in hours
            
        Returns:
            Number of items cleaned up
        """
        try:
            cutoff_time = time.time() - (hours * 3600)
            cleaned_count = 0
            
            # Clean up old operations
            old_operations = [
                op_id for op_id, op in self.operations.items()
                if op.start_time < cutoff_time and op.status in ["completed", "failed"]
            ]
            
            for op_id in old_operations:
                del self.operations[op_id]
                cleaned_count += 1
            
            # Resource history cleanup is handled by deque maxlen
            
            self.logger.info(f"Cleaned up {cleaned_count} old tracking records")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return 0
    
    # Private methods
    async def _monitor_resources(self):
        """Background task to monitor resource usage"""
        self.logger.info("Starting resource monitoring")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Capture resource snapshot
                    snapshot = await self._capture_resource_snapshot()
                    self.resource_history.append(snapshot)
                    
                    # Check for resource threshold violations
                    await self._check_resource_thresholds(snapshot)
                    
                    # Wait for next collection interval
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.collection_interval
                    )
                    
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue monitoring
                except Exception as e:
                    self.logger.error(f"Resource monitoring error: {e}")
                    await asyncio.sleep(10)  # Wait before retrying
                    
        except Exception as e:
            self.logger.error(f"Resource monitoring task failed: {e}")
        finally:
            self.logger.info("Resource monitoring stopped")
    
    async def _capture_resource_snapshot(self) -> ResourceSnapshot:
        """Capture current resource usage snapshot"""
        try:
            # Get process information (if available)
            process = psutil.Process() if hasattr(psutil, 'Process') else None
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None) if hasattr(psutil, 'cpu_percent') else 0
            
            # Memory usage
            memory = psutil.virtual_memory() if hasattr(psutil, 'virtual_memory') else None
            memory_mb = memory.used / 1024 / 1024 if memory else 0
            
            # Disk usage for workspace
            disk_usage = psutil.disk_usage(str(self.config.workspace_path)) if hasattr(psutil, 'disk_usage') else None
            disk_usage_mb = disk_usage.used / 1024 / 1024 if disk_usage else 0
            
            # Network I/O
            network_io = {}
            if hasattr(psutil, 'net_io_counters'):
                net_io = psutil.net_io_counters()
                if net_io:
                    network_io = {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv
                    }
            
            # Process count and file handles
            process_count = len(psutil.pids()) if hasattr(psutil, 'pids') else 0
            file_handles = 0
            if process:
                try:
                    file_handles = process.num_fds() if hasattr(process, 'num_fds') else 0
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                disk_usage_mb=disk_usage_mb,
                network_io=network_io,
                process_count=process_count,
                file_handles=file_handles
            )
            
        except Exception as e:
            self.logger.error(f"Failed to capture resource snapshot: {e}")
            # Return empty snapshot
            return ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=0,
                memory_mb=0,
                disk_usage_mb=0
            )
    
    async def _capture_resource_snapshot_dict(self) -> Dict[str, Any]:
        """Capture resource snapshot as dictionary"""
        snapshot = await self._capture_resource_snapshot()
        return {
            "timestamp": snapshot.timestamp,
            "cpu_percent": snapshot.cpu_percent,
            "memory_mb": snapshot.memory_mb,
            "disk_usage_mb": snapshot.disk_usage_mb,
            "network_io": snapshot.network_io,
            "process_count": snapshot.process_count,
            "file_handles": snapshot.file_handles
        }
    
    async def _check_resource_thresholds(self, snapshot: ResourceSnapshot):
        """Check resource usage against configured thresholds"""
        try:
            thresholds = self.config.monitoring_config.get("resource_thresholds", {})
            
            # Check CPU threshold
            cpu_threshold = thresholds.get("cpu_percent", 90)
            if snapshot.cpu_percent > cpu_threshold:
                await self.event_emitter.emit("resource_threshold_exceeded", {
                    "resource": "cpu",
                    "current": snapshot.cpu_percent,
                    "threshold": cpu_threshold,
                    "timestamp": snapshot.timestamp
                })
            
            # Check memory threshold
            memory_threshold = thresholds.get("memory_mb", 1024)
            if snapshot.memory_mb > memory_threshold:
                await self.event_emitter.emit("resource_threshold_exceeded", {
                    "resource": "memory",
                    "current": snapshot.memory_mb,
                    "threshold": memory_threshold,
                    "timestamp": snapshot.timestamp
                })
            
            # Check disk threshold
            disk_threshold = thresholds.get("disk_mb", 2048)
            if snapshot.disk_usage_mb > disk_threshold:
                await self.event_emitter.emit("resource_threshold_exceeded", {
                    "resource": "disk",
                    "current": snapshot.disk_usage_mb,
                    "threshold": disk_threshold,
                    "timestamp": snapshot.timestamp
                })
                
        except Exception as e:
            self.logger.error(f"Failed to check resource thresholds: {e}")
    
    async def _maybe_cleanup_old_operations(self):
        """Clean up old operations if we exceed the limit"""
        if len(self.operations) > self.max_operation_history:
            # Remove oldest completed/failed operations
            completed_failed = [
                (op_id, op) for op_id, op in self.operations.items()
                if op.status in ["completed", "failed"]
            ]
            
            if completed_failed:
                # Sort by start time and remove oldest
                completed_failed.sort(key=lambda x: x[1].start_time)
                to_remove = len(completed_failed) - (self.max_operation_history // 2)
                
                for op_id, _ in completed_failed[:to_remove]:
                    del self.operations[op_id]