"""
Health Monitor - Sandbox health and availability monitoring

Monitors sandbox health including system resources, process status, network
connectivity, and overall operational health with automated recovery capabilities.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import psutil

from ..utils.filesystem import FilesystemChecker
from ..utils.stub_modules import NetworkChecker
from ..utils.stub_modules import ProcessMonitor


class HealthStatus(Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""

    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    check_duration: float = 0.0


@dataclass
class HealthReport:
    """Complete health report"""

    overall_status: HealthStatus
    checks: List[HealthCheck]
    timestamp: float
    sandbox_id: str
    uptime: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    @property
    def severity(self) -> str:
        if self.overall_status == HealthStatus.CRITICAL:
            return "critical"
        if self.overall_status == HealthStatus.WARNING:
            return "warning"
        return "normal"


class HealthMonitor:
    """
    Comprehensive sandbox health monitoring

    Monitors:
    - System resource health (CPU, memory, disk)
    - Process health and lifecycle
    - Network connectivity and performance
    - Filesystem health and accessibility
    - Application-specific health checks
    - Automated recovery actions
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(f"sandbox.{config.sandbox_id}.health")

        # Health monitoring state
        self.is_running = False
        self.is_paused = False
        self.last_health_report: Optional[HealthReport] = None
        self.start_time = time.time()

        # Health check components
        self.network_checker = NetworkChecker()
        self.process_monitor = ProcessMonitor()
        self.filesystem_checker = FilesystemChecker()

        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Configuration
        self.check_interval = config.monitoring_config.get(
            "health_check_interval", 60
        )  # seconds
        self.critical_thresholds = config.monitoring_config.get(
            "critical_thresholds", {}
        )
        self.warning_thresholds = config.monitoring_config.get("warning_thresholds", {})
        self.enabled_checks = set(
            config.monitoring_config.get(
                "enabled_health_checks",
                ["resource_usage", "filesystem", "process_health", "network"],
            )
        )

        # Recovery settings
        self.auto_recovery = config.monitoring_config.get("auto_recovery", True)
        self.recovery_attempts = {}  # Track recovery attempts

    async def start(self) -> bool:
        """
        Start health monitoring

        Returns:
            bool: True if started successfully
        """
        try:
            self.logger.info("Starting health monitor")

            self.is_running = True
            self.is_paused = False
            self.start_time = time.time()

            # Perform initial health check
            initial_report = await self.check_health()
            self.last_health_report = initial_report

            if not initial_report.is_healthy:
                self.logger.warning(
                    f"Initial health check failed: {initial_report.issues}"
                )

            # Start background monitoring
            self._monitoring_task = asyncio.create_task(self._monitor_health())

            self.logger.info("Health monitor started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start health monitor: {e}")
            return False

    async def stop(self) -> bool:
        """
        Stop health monitoring

        Returns:
            bool: True if stopped successfully
        """
        try:
            self.logger.info("Stopping health monitor")

            self.is_running = False
            self._stop_event.set()

            # Wait for monitoring task to complete
            if self._monitoring_task:
                await self._monitoring_task
                self._monitoring_task = None

            self.logger.info("Health monitor stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop health monitor: {e}")
            return False

    async def pause(self) -> bool:
        """
        Pause health monitoring

        Returns:
            bool: True if paused successfully
        """
        try:
            self.logger.info("Pausing health monitor")
            self.is_paused = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause health monitor: {e}")
            return False

    async def resume(self) -> bool:
        """
        Resume health monitoring

        Returns:
            bool: True if resumed successfully
        """
        try:
            self.logger.info("Resuming health monitor")
            self.is_paused = False
            return True
        except Exception as e:
            self.logger.error(f"Failed to resume health monitor: {e}")
            return False

    async def check_health(self) -> HealthReport:
        """
        Perform comprehensive health check

        Returns:
            HealthReport: Complete health assessment
        """
        start_time = time.time()
        checks = []
        issues = []
        warnings = []

        try:
            self.logger.debug("Performing health check")

            # Resource usage check
            if "resource_usage" in self.enabled_checks:
                resource_check = await self._check_resource_usage()
                checks.append(resource_check)
                if resource_check.status == HealthStatus.CRITICAL:
                    issues.append(resource_check.message)
                elif resource_check.status == HealthStatus.WARNING:
                    warnings.append(resource_check.message)

            # Filesystem health check
            if "filesystem" in self.enabled_checks:
                fs_check = await self._check_filesystem_health()
                checks.append(fs_check)
                if fs_check.status == HealthStatus.CRITICAL:
                    issues.append(fs_check.message)
                elif fs_check.status == HealthStatus.WARNING:
                    warnings.append(fs_check.message)

            # Process health check
            if "process_health" in self.enabled_checks:
                process_check = await self._check_process_health()
                checks.append(process_check)
                if process_check.status == HealthStatus.CRITICAL:
                    issues.append(process_check.message)
                elif process_check.status == HealthStatus.WARNING:
                    warnings.append(process_check.message)

            # Network connectivity check
            if "network" in self.enabled_checks:
                network_check = await self._check_network_health()
                checks.append(network_check)
                if network_check.status == HealthStatus.CRITICAL:
                    issues.append(network_check.message)
                elif network_check.status == HealthStatus.WARNING:
                    warnings.append(network_check.message)

            # Application-specific checks
            if "application" in self.enabled_checks:
                app_check = await self._check_application_health()
                checks.append(app_check)
                if app_check.status == HealthStatus.CRITICAL:
                    issues.append(app_check.message)
                elif app_check.status == HealthStatus.WARNING:
                    warnings.append(app_check.message)

            # Determine overall status
            overall_status = self._determine_overall_status(checks)

            # Create health report
            report = HealthReport(
                overall_status=overall_status,
                checks=checks,
                timestamp=time.time(),
                sandbox_id=self.config.sandbox_id,
                uptime=time.time() - self.start_time,
                issues=issues,
                warnings=warnings,
            )

            self.last_health_report = report
            check_duration = time.time() - start_time

            self.logger.debug(
                f"Health check completed in {check_duration:.2f}s - Status: {overall_status.value}"
            )

            return report

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")

            # Return error health report
            error_check = HealthCheck(
                name="health_check_error",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e!s}",
                details={"error": str(e)},
                check_duration=time.time() - start_time,
            )

            return HealthReport(
                overall_status=HealthStatus.CRITICAL,
                checks=[error_check],
                timestamp=time.time(),
                sandbox_id=self.config.sandbox_id,
                uptime=time.time() - self.start_time,
                issues=[f"Health check failed: {e!s}"],
            )

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status

        Returns:
            Dict containing health status information
        """
        try:
            if self.last_health_report:
                return {
                    "status": self.last_health_report.overall_status.value,
                    "is_healthy": self.last_health_report.is_healthy,
                    "last_check": self.last_health_report.timestamp,
                    "uptime": self.last_health_report.uptime,
                    "issues_count": len(self.last_health_report.issues),
                    "warnings_count": len(self.last_health_report.warnings),
                    "checks_passed": len(
                        [
                            c
                            for c in self.last_health_report.checks
                            if c.status == HealthStatus.HEALTHY
                        ]
                    ),
                    "total_checks": len(self.last_health_report.checks),
                    "is_monitoring": self.is_running and not self.is_paused,
                }
            return {
                "status": "unknown",
                "is_healthy": False,
                "is_monitoring": self.is_running and not self.is_paused,
            }

        except Exception as e:
            self.logger.error(f"Failed to get health status: {e}")
            return {"status": "error", "error": str(e)}

    async def get_detailed_report(self) -> Optional[HealthReport]:
        """
        Get the last detailed health report

        Returns:
            HealthReport or None if no report available
        """
        return self.last_health_report

    # Private methods
    async def _monitor_health(self):
        """Background health monitoring task"""
        self.logger.info("Starting background health monitoring")

        try:
            while not self._stop_event.is_set():
                try:
                    if not self.is_paused:
                        # Perform health check
                        report = await self.check_health()

                        # Handle critical issues
                        if (
                            report.overall_status == HealthStatus.CRITICAL
                            and self.auto_recovery
                        ):
                            await self._attempt_recovery(report)

                    # Wait for next check interval
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self.check_interval
                    )

                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue monitoring
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(30)  # Wait before retrying

        except Exception as e:
            self.logger.error(f"Health monitoring task failed: {e}")
        finally:
            self.logger.info("Background health monitoring stopped")

    async def _check_resource_usage(self) -> HealthCheck:
        """Check system resource usage"""
        start_time = time.time()

        try:
            # Get resource usage
            cpu_percent = psutil.cpu_percent(interval=1.0)
            memory = psutil.virtual_memory()
            disk_usage = psutil.disk_usage(str(self.config.workspace_path))

            memory_percent = memory.percent
            disk_percent = (disk_usage.used / disk_usage.total) * 100

            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_free_mb": disk_usage.free / 1024 / 1024,
            }

            # Check against thresholds
            critical_cpu = self.critical_thresholds.get("cpu_percent", 95)
            critical_memory = self.critical_thresholds.get("memory_percent", 95)
            critical_disk = self.critical_thresholds.get("disk_percent", 95)

            warning_cpu = self.warning_thresholds.get("cpu_percent", 80)
            warning_memory = self.warning_thresholds.get("memory_percent", 80)
            warning_disk = self.warning_thresholds.get("disk_percent", 80)

            # Determine status
            if (
                cpu_percent >= critical_cpu
                or memory_percent >= critical_memory
                or disk_percent >= critical_disk
            ):
                status = HealthStatus.CRITICAL
                message = f"Critical resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%, Disk {disk_percent:.1f}%"
            elif (
                cpu_percent >= warning_cpu
                or memory_percent >= warning_memory
                or disk_percent >= warning_disk
            ):
                status = HealthStatus.WARNING
                message = f"High resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%, Disk {disk_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Resource usage normal: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%, Disk {disk_percent:.1f}%"

            return HealthCheck(
                name="resource_usage",
                status=status,
                message=message,
                details=details,
                check_duration=time.time() - start_time,
            )

        except Exception as e:
            return HealthCheck(
                name="resource_usage",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check resource usage: {e!s}",
                details={"error": str(e)},
                check_duration=time.time() - start_time,
            )

    async def _check_filesystem_health(self) -> HealthCheck:
        """Check filesystem health and accessibility"""
        start_time = time.time()

        try:
            workspace_path = self.config.workspace_path

            # Check workspace accessibility
            is_accessible = await self.filesystem_checker.check_accessibility(
                workspace_path
            )

            # Check required directories
            required_dirs = ["work", "tmp", "logs", "config"]
            missing_dirs = []

            for dirname in required_dirs:
                dir_path = workspace_path / dirname
                if not dir_path.exists():
                    missing_dirs.append(dirname)

            # Check disk space
            disk_usage = psutil.disk_usage(str(workspace_path))
            free_space_mb = disk_usage.free / 1024 / 1024
            min_free_space = self.critical_thresholds.get("min_free_space_mb", 100)

            details = {
                "workspace_accessible": is_accessible,
                "missing_directories": missing_dirs,
                "free_space_mb": free_space_mb,
                "min_required_mb": min_free_space,
            }

            # Determine status
            if not is_accessible:
                status = HealthStatus.CRITICAL
                message = "Workspace not accessible"
            elif missing_dirs:
                status = HealthStatus.CRITICAL
                message = f"Missing required directories: {', '.join(missing_dirs)}"
            elif free_space_mb < min_free_space:
                status = HealthStatus.CRITICAL
                message = f"Insufficient disk space: {free_space_mb:.1f}MB available"
            else:
                status = HealthStatus.HEALTHY
                message = f"Filesystem healthy: {free_space_mb:.1f}MB free space"

            return HealthCheck(
                name="filesystem",
                status=status,
                message=message,
                details=details,
                check_duration=time.time() - start_time,
            )

        except Exception as e:
            return HealthCheck(
                name="filesystem",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check filesystem: {e!s}",
                details={"error": str(e)},
                check_duration=time.time() - start_time,
            )

    async def _check_process_health(self) -> HealthCheck:
        """Check process health and status"""
        start_time = time.time()

        try:
            # Get process information
            process_info = await self.process_monitor.get_process_info()

            # Check for zombie processes
            zombie_count = process_info.get("zombie_processes", 0)
            total_processes = process_info.get("total_processes", 0)

            # Check memory usage per process
            high_memory_processes = process_info.get("high_memory_processes", [])

            details = {
                "total_processes": total_processes,
                "zombie_processes": zombie_count,
                "high_memory_processes": len(high_memory_processes),
                "process_details": high_memory_processes[:5],  # Top 5
            }

            # Determine status
            max_zombies = self.critical_thresholds.get("max_zombie_processes", 10)
            max_processes = self.critical_thresholds.get("max_total_processes", 1000)

            if zombie_count >= max_zombies:
                status = HealthStatus.CRITICAL
                message = f"Too many zombie processes: {zombie_count}"
            elif total_processes >= max_processes:
                status = HealthStatus.WARNING
                message = f"High process count: {total_processes}"
            elif len(high_memory_processes) > 5:
                status = HealthStatus.WARNING
                message = f"{len(high_memory_processes)} processes using high memory"
            else:
                status = HealthStatus.HEALTHY
                message = f"Process health normal: {total_processes} processes"

            return HealthCheck(
                name="process_health",
                status=status,
                message=message,
                details=details,
                check_duration=time.time() - start_time,
            )

        except Exception as e:
            return HealthCheck(
                name="process_health",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check process health: {e!s}",
                details={"error": str(e)},
                check_duration=time.time() - start_time,
            )

    async def _check_network_health(self) -> HealthCheck:
        """Check network connectivity and health"""
        start_time = time.time()

        try:
            # Check network connectivity
            network_status = await self.network_checker.check_connectivity()

            details = {
                "connectivity": network_status.get("reachable", False),
                "latency_ms": network_status.get("latency_ms", 0),
                "dns_resolution": network_status.get("dns_works", False),
            }

            # Determine status based on network requirements
            network_required = self.config.safety_constraints.get("network", {}).get(
                "required", False
            )

            if network_required and not network_status.get("reachable", False):
                status = HealthStatus.CRITICAL
                message = "Network connectivity required but not available"
            elif network_status.get("latency_ms", 0) > 5000:  # 5 second threshold
                status = HealthStatus.WARNING
                message = (
                    f"High network latency: {network_status.get('latency_ms', 0)}ms"
                )
            else:
                status = HealthStatus.HEALTHY
                message = "Network health normal"

            return HealthCheck(
                name="network",
                status=status,
                message=message,
                details=details,
                check_duration=time.time() - start_time,
            )

        except Exception as e:
            return HealthCheck(
                name="network",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check network health: {e!s}",
                details={"error": str(e)},
                check_duration=time.time() - start_time,
            )

    async def _check_application_health(self) -> HealthCheck:
        """Check application-specific health indicators"""
        start_time = time.time()

        try:
            # This would be extended for specific application health checks
            # For now, just check basic sandbox functionality
            details = {"sandbox_active": True, "configuration_valid": True}

            status = HealthStatus.HEALTHY
            message = "Application health normal"

            return HealthCheck(
                name="application",
                status=status,
                message=message,
                details=details,
                check_duration=time.time() - start_time,
            )

        except Exception as e:
            return HealthCheck(
                name="application",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check application health: {e!s}",
                details={"error": str(e)},
                check_duration=time.time() - start_time,
            )

    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall health status from individual checks"""
        if not checks:
            return HealthStatus.UNKNOWN

        # If any check is critical, overall is critical
        if any(check.status == HealthStatus.CRITICAL for check in checks):
            return HealthStatus.CRITICAL

        # If any check is warning, overall is warning
        if any(check.status == HealthStatus.WARNING for check in checks):
            return HealthStatus.WARNING

        # If any check is unknown, overall is unknown
        if any(check.status == HealthStatus.UNKNOWN for check in checks):
            return HealthStatus.UNKNOWN

        # All checks are healthy
        return HealthStatus.HEALTHY

    async def _attempt_recovery(self, report: HealthReport):
        """Attempt automated recovery for critical issues"""
        try:
            recovery_key = f"recovery_{int(time.time() // 3600)}"  # Per hour

            # Limit recovery attempts
            if self.recovery_attempts.get(recovery_key, 0) >= 3:
                self.logger.warning("Maximum recovery attempts reached for this hour")
                return

            self.logger.info("Attempting automated recovery for critical health issues")

            recovery_actions = []

            # Analyze critical checks and determine recovery actions
            for check in report.checks:
                if check.status == HealthStatus.CRITICAL:
                    if check.name == "resource_usage":
                        recovery_actions.append("cleanup_resources")
                    elif check.name == "filesystem":
                        recovery_actions.append("repair_filesystem")
                    elif check.name == "process_health":
                        recovery_actions.append("cleanup_processes")

            # Execute recovery actions
            success_count = 0
            for action in recovery_actions:
                if await self._execute_recovery_action(action):
                    success_count += 1

            # Track recovery attempt
            self.recovery_attempts[recovery_key] = (
                self.recovery_attempts.get(recovery_key, 0) + 1
            )

            self.logger.info(
                f"Recovery attempt completed: {success_count}/{len(recovery_actions)} actions successful"
            )

        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")

    async def _execute_recovery_action(self, action: str) -> bool:
        """Execute a specific recovery action"""
        try:
            if action == "cleanup_resources":
                # Clear temporary files, garbage collect, etc.
                tmp_dir = self.config.workspace_path / "tmp"
                if tmp_dir.exists():
                    import shutil

                    for item in tmp_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                return True

            if action == "repair_filesystem":
                # Recreate missing directories
                required_dirs = ["work", "tmp", "logs", "config", "snapshots"]
                for dirname in required_dirs:
                    dir_path = self.config.workspace_path / dirname
                    dir_path.mkdir(exist_ok=True, mode=0o750)
                return True

            if action == "cleanup_processes":
                # Kill zombie processes, clean up resources
                # This would be implemented based on specific requirements
                return True

        except Exception as e:
            self.logger.error(f"Recovery action {action} failed: {e}")
            return False

        return False
