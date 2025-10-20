"""
Anomaly detection for VM behavior monitoring

Implements statistical (z-score) and rule-based anomaly detection to identify
potentially malicious or problematic agent behavior patterns.
"""

import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

import structlog

# Note: AuditLogger import will be added when implementing integration
from agent_vm.monitoring.audit import AuditLogger

logger = structlog.get_logger()


class AnomalyType(Enum):
    """Types of anomalies that can be detected"""

    # Statistical anomalies
    CPU_SPIKE = "cpu_spike"
    MEMORY_SPIKE = "memory_spike"
    NETWORK_SPIKE = "network_spike"
    DISK_SPIKE = "disk_spike"

    # Rule-based anomalies
    EXCESSIVE_CONNECTIONS = "excessive_connections"
    HIGH_CPU_SUSTAINED = "high_cpu_sustained"
    EXCESSIVE_DISK_WRITES = "excessive_disk_writes"
    RAPID_PROCESS_SPAWNING = "rapid_process_spawning"
    UNUSUAL_SYSCALL = "unusual_syscall"
    FORK_BOMB = "fork_bomb"
    CRYPTO_MINING = "crypto_mining"
    DATA_EXFILTRATION = "data_exfiltration"


class AnomalySeverity(Enum):
    """Severity levels for anomalies"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """Detected anomaly"""

    type: AnomalyType
    severity: AnomalySeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(ZoneInfo("America/New_York"))
    )

    def __eq__(self, other: object) -> bool:
        """Anomalies are equal if type and details match (for deduplication)"""
        if not isinstance(other, Anomaly):
            return NotImplemented
        return self.type == other.type and self.details == other.details


class AnomalyError(Exception):
    """Anomaly detection error"""

    pass


class AnomalyDetector:
    """
    Detect behavioral anomalies in VM execution

    Uses both statistical (z-score) and rule-based detection algorithms to
    identify potentially malicious or problematic patterns.
    """

    # Baseline collection settings
    MIN_BASELINE_SAMPLES = 30
    MAX_BASELINE_SAMPLES = 1000

    # Rule-based thresholds
    EXCESSIVE_CONNECTIONS_THRESHOLD = 100  # per minute
    HIGH_CPU_THRESHOLD = 90.0  # percent
    HIGH_CPU_DURATION_THRESHOLD = 30.0  # seconds
    EXCESSIVE_DISK_WRITES_THRESHOLD = 1024**3  # 1GB per minute
    RAPID_PROCESS_SPAWNING_THRESHOLD = 50  # per minute
    FORK_BOMB_PROCESS_THRESHOLD = 1000  # total processes
    FORK_BOMB_DURATION_THRESHOLD = 5.0  # seconds
    DATA_EXFILTRATION_BYTES_THRESHOLD = 100 * 1024**2  # 100MB
    DATA_EXFILTRATION_DURATION_THRESHOLD = 10.0  # seconds

    # Known malicious patterns
    SUSPICIOUS_SYSCALLS: ClassVar[set[str]] = {
        "ptrace", "kexec_load", "create_module", "delete_module"
    }
    KNOWN_MINING_POOLS: ClassVar[set[str]] = {
        "pool.minexmr.com",
        "xmr-eu1.nanopool.org",
        "xmrpool.eu",
        "monero.crypto-pool.fr",
    }

    def __init__(
        self,
        vm_id: str,
        z_score_threshold: float = 3.0,
        enabled: bool = True,
        dedup_window_seconds: float = 60.0,
    ) -> None:
        """
        Initialize anomaly detector.

        Args:
            vm_id: VM identifier
            z_score_threshold: Z-score threshold for statistical anomalies (default: 3.0)
            enabled: Enable/disable detection (default: True)
            dedup_window_seconds: Alert deduplication window in seconds (default: 60)

        """
        self.vm_id = vm_id
        self.z_score_threshold = z_score_threshold
        self.enabled = enabled
        self.dedup_window_seconds = dedup_window_seconds

        # Baseline metrics storage: metric_name -> deque of values
        self._baseline_metrics: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self.MAX_BASELINE_SAMPLES)
        )

        # Sustained metric tracking (for rule-based detection)
        self._sustained_cpu: dict[str, float] | None = None

        # Alert deduplication
        self._recent_alerts: dict[str, datetime] = {}

        # Audit logger integration
        self._audit_logger = AuditLogger()

        self._logger = logger.bind(vm_id=vm_id, component="anomaly_detector")

    def record_metric(self, metric_name: str, value: float) -> None:
        """
        Record metric value for baseline calculation.

        Args:
            metric_name: Name of metric (e.g., "cpu_percent", "memory_bytes")
            value: Metric value

        Raises:
            AnomalyError: If value is invalid

        """
        try:
            # Validate value is numeric
            float_value = float(value)
            self._baseline_metrics[metric_name].append(float_value)
            self._logger.debug(
                "metric_recorded",
                metric=metric_name,
                value=float_value,
                samples=len(self._baseline_metrics[metric_name]),
            )
        except (TypeError, ValueError) as e:
            raise AnomalyError(f"Invalid metric value: {value}") from e

    def record_sustained_cpu(self, cpu_percent: float, duration_seconds: float) -> None:
        """
        Record sustained CPU usage for rule-based detection.

        Args:
            cpu_percent: CPU usage percentage
            duration_seconds: Duration of sustained usage

        """
        self._sustained_cpu = {
            "cpu_percent": cpu_percent,
            "duration_seconds": duration_seconds,
        }

    def detect(self, current_metrics: dict[str, Any]) -> list[Anomaly]:
        """
        Detect anomalies in current metrics.

        Combines statistical (z-score) and rule-based detection.

        Args:
            current_metrics: Current metric values to analyze

        Returns:
            List of detected anomalies

        """
        if not self.enabled:
            return []

        anomalies: list[Anomaly] = []

        try:
            # Statistical detection (z-score)
            anomalies.extend(self._detect_statistical(current_metrics))

            # Rule-based detection
            anomalies.extend(self._detect_rule_based(current_metrics))

            # Log detected anomalies
            for anomaly in anomalies:
                self._logger.warning(
                    "anomaly_detected",
                    type=anomaly.type.value,
                    severity=anomaly.severity.value,
                    message=anomaly.message,
                    details=anomaly.details,
                )

            return anomalies

        except Exception as e:
            self._logger.error("anomaly_detection_failed", error=str(e))
            return []

    async def detect_async(self, current_metrics: dict[str, Any]) -> list[Anomaly]:
        """
        Async version of detect (wraps synchronous detection).

        Args:
            current_metrics: Current metric values to analyze

        Returns:
            List of detected anomalies

        """
        # For now, just wrap synchronous detection
        # Could be enhanced to run in executor for heavy workloads
        return self.detect(current_metrics)

    def _detect_statistical(self, current_metrics: dict[str, Any]) -> list[Anomaly]:
        """
        Detect statistical anomalies using z-score.

        Args:
            current_metrics: Current metric values

        Returns:
            List of statistical anomalies

        """
        anomalies: list[Anomaly] = []

        # Map metrics to anomaly types
        metric_mapping = {
            "cpu_percent": AnomalyType.CPU_SPIKE,
            "memory_bytes": AnomalyType.MEMORY_SPIKE,
            "network_tx_bytes": AnomalyType.NETWORK_SPIKE,
            "disk_write_bytes": AnomalyType.DISK_SPIKE,
        }

        for metric_name, anomaly_type in metric_mapping.items():
            if metric_name not in current_metrics:
                continue

            try:
                current_value = float(current_metrics[metric_name])
            except (TypeError, ValueError):
                continue

            baseline = self._calculate_baseline(metric_name)
            if baseline is None:
                continue

            # Calculate z-score
            z_score = (current_value - baseline["mean"]) / baseline["stddev"]

            if abs(z_score) > self.z_score_threshold:
                # Determine severity based on z-score magnitude
                severity = self._z_score_to_severity(abs(z_score))

                anomaly = Anomaly(
                    type=anomaly_type,
                    severity=severity,
                    message=f"{metric_name} anomaly detected (z-score: {z_score:.2f})",
                    details={
                        "metric": metric_name,
                        "current_value": current_value,
                        "baseline_mean": baseline["mean"],
                        "baseline_stddev": baseline["stddev"],
                        "z_score": z_score,
                    },
                )
                anomalies.append(anomaly)

        return anomalies

    def _detect_rule_based(self, current_metrics: dict[str, Any]) -> list[Anomaly]:
        """
        Detect rule-based anomalies.

        Args:
            current_metrics: Current metric values

        Returns:
            List of rule-based anomalies

        """
        anomalies: list[Anomaly] = []

        # Excessive network connections
        connections = current_metrics.get("network_connections_per_min", 0)
        if connections > self.EXCESSIVE_CONNECTIONS_THRESHOLD:
            anomalies.append(
                Anomaly(
                    type=AnomalyType.EXCESSIVE_CONNECTIONS,
                    severity=AnomalySeverity.MEDIUM,
                    message=(
                        f"Excessive network connections: {connections} per minute"
                    ),
                    details={
                        "connections_per_min": current_metrics["network_connections_per_min"],
                        "threshold": self.EXCESSIVE_CONNECTIONS_THRESHOLD,
                    },
                )
            )

        # Sustained high CPU
        if self._sustained_cpu:
            cpu = self._sustained_cpu["cpu_percent"]
            duration = self._sustained_cpu["duration_seconds"]
            if cpu > self.HIGH_CPU_THRESHOLD and duration > self.HIGH_CPU_DURATION_THRESHOLD:
                anomalies.append(
                    Anomaly(
                        type=AnomalyType.HIGH_CPU_SUSTAINED,
                        severity=AnomalySeverity.HIGH,
                        message=f"Sustained high CPU: {cpu:.1f}% for {duration:.1f}s",
                        details={
                            "cpu_percent": cpu,
                            "duration_seconds": duration,
                            "cpu_threshold": self.HIGH_CPU_THRESHOLD,
                            "duration_threshold": self.HIGH_CPU_DURATION_THRESHOLD,
                        },
                    )
                )

        # Excessive disk writes
        disk_writes = current_metrics.get("disk_write_bytes_per_min", 0)
        if disk_writes > self.EXCESSIVE_DISK_WRITES_THRESHOLD:
            anomalies.append(
                Anomaly(
                    type=AnomalyType.EXCESSIVE_DISK_WRITES,
                    severity=AnomalySeverity.MEDIUM,
                    message=(
                        f"Excessive disk writes: "
                        f"{current_metrics['disk_write_bytes_per_min'] / 1024**3:.2f}GB per minute"
                    ),
                    details={
                        "bytes_per_min": current_metrics["disk_write_bytes_per_min"],
                        "threshold": self.EXCESSIVE_DISK_WRITES_THRESHOLD,
                    },
                )
            )

        # Rapid process spawning
        if current_metrics.get("process_spawns_per_min", 0) > self.RAPID_PROCESS_SPAWNING_THRESHOLD:
            anomalies.append(
                Anomaly(
                    type=AnomalyType.RAPID_PROCESS_SPAWNING,
                    severity=AnomalySeverity.HIGH,
                    message=(
                        f"Rapid process spawning: "
                        f"{current_metrics['process_spawns_per_min']} per minute"
                    ),
                    details={
                        "spawns_per_min": current_metrics["process_spawns_per_min"],
                        "threshold": self.RAPID_PROCESS_SPAWNING_THRESHOLD,
                    },
                )
            )

        # Unusual syscalls
        suspicious_syscalls = current_metrics.get("suspicious_syscalls", [])
        if suspicious_syscalls:
            detected = set(suspicious_syscalls) & self.SUSPICIOUS_SYSCALLS
            if detected:
                anomalies.append(
                    Anomaly(
                        type=AnomalyType.UNUSUAL_SYSCALL,
                        severity=AnomalySeverity.CRITICAL,
                        message=f"Suspicious syscalls detected: {', '.join(detected)}",
                        details={"syscalls": list(detected)},
                    )
                )

        # Fork bomb detection
        total_procs = current_metrics.get("total_processes", 0)
        spawn_duration = current_metrics.get("process_spawn_duration", float("inf"))
        if (
            total_procs > self.FORK_BOMB_PROCESS_THRESHOLD
            and spawn_duration < self.FORK_BOMB_DURATION_THRESHOLD
        ):
            anomalies.append(
                Anomaly(
                    type=AnomalyType.FORK_BOMB,
                    severity=AnomalySeverity.CRITICAL,
                    message=f"Fork bomb detected: {total_procs} processes in {spawn_duration:.1f}s",
                    details={
                        "total_processes": total_procs,
                        "spawn_duration": spawn_duration,
                    },
                )
            )

        # Crypto mining detection
        network_destinations = current_metrics.get("network_destinations", [])
        cpu_percent = current_metrics.get("cpu_percent", 0.0)
        mining_pools = set(network_destinations) & self.KNOWN_MINING_POOLS
        if mining_pools and cpu_percent > 90.0:
            anomalies.append(
                Anomaly(
                    type=AnomalyType.CRYPTO_MINING,
                    severity=AnomalySeverity.CRITICAL,
                    message=f"Crypto mining detected: connections to {', '.join(mining_pools)}",
                    details={
                        "mining_pools": list(mining_pools),
                        "cpu_percent": cpu_percent,
                    },
                )
            )

        # Data exfiltration detection
        network_tx_bytes = current_metrics.get("network_tx_bytes", 0)
        network_tx_duration = current_metrics.get("network_tx_duration", float("inf"))
        if (
            network_tx_bytes > self.DATA_EXFILTRATION_BYTES_THRESHOLD
            and network_tx_duration < self.DATA_EXFILTRATION_DURATION_THRESHOLD
            and network_destinations
        ):
            # Check if destinations are unknown/suspicious
            # For simplicity, any destination is considered suspicious for high-volume transfers
            anomalies.append(
                Anomaly(
                    type=AnomalyType.DATA_EXFILTRATION,
                    severity=AnomalySeverity.CRITICAL,
                    message=(
                        f"Potential data exfiltration: "
                        f"{network_tx_bytes / 1024**2:.1f}MB in {network_tx_duration:.1f}s"
                    ),
                    details={
                        "bytes_transferred": network_tx_bytes,
                        "duration": network_tx_duration,
                        "destinations": network_destinations,
                    },
                )
            )

        return anomalies

    def _calculate_baseline(self, metric_name: str) -> dict[str, float] | None:
        """
        Calculate baseline statistics for a metric.

        Args:
            metric_name: Name of metric

        Returns:
            dict with 'mean' and 'stddev', or None if insufficient data

        """
        samples = self._baseline_metrics.get(metric_name, deque())

        if len(samples) < self.MIN_BASELINE_SAMPLES:
            return None

        try:
            mean = statistics.mean(samples)
            stddev = statistics.stdev(samples)

            # Avoid division by zero
            if stddev == 0:
                stddev = 0.1  # Small epsilon

            return {"mean": mean, "stddev": stddev}

        except statistics.StatisticsError:
            return None

    def _z_score_to_severity(self, z_score: float) -> AnomalySeverity:
        """
        Convert z-score magnitude to severity level.

        Args:
            z_score: Absolute z-score value

        Returns:
            Severity level

        """
        if z_score > 5.0:
            return AnomalySeverity.CRITICAL
        elif z_score > 4.0:
            return AnomalySeverity.HIGH
        elif z_score > 3.0:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def generate_alert(self, anomaly: Anomaly) -> dict[str, Any] | None:
        """
        Generate alert for anomaly with deduplication.

        Args:
            anomaly: Detected anomaly

        Returns:
            Alert dict, or None if deduplicated

        """
        if not self.enabled:
            return None

        # Check deduplication
        alert_key = f"{anomaly.type.value}:{hash(frozenset(anomaly.details.items()))}"
        now = datetime.now(ZoneInfo("America/New_York"))

        if alert_key in self._recent_alerts:
            last_alert_time = self._recent_alerts[alert_key]
            time_since_last = (now - last_alert_time).total_seconds()

            if time_since_last < self.dedup_window_seconds:
                self._logger.debug(
                    "alert_deduplicated",
                    anomaly_type=anomaly.type.value,
                    time_since_last=time_since_last,
                )
                return None

        # Generate alert
        alert = {
            "vm_id": self.vm_id,
            "anomaly_type": anomaly.type.value,
            "severity": anomaly.severity.value,
            "message": anomaly.message,
            "details": anomaly.details,
            "timestamp": now,
        }

        # Update deduplication tracking
        self._recent_alerts[alert_key] = now

        self._logger.info(
            "alert_generated",
            anomaly_type=anomaly.type.value,
            severity=anomaly.severity.value,
        )

        return alert

    def log_anomaly(self, anomaly: Anomaly) -> None:
        """
        Log anomaly to AuditLogger.

        Args:
            anomaly: Anomaly to log

        """
        # Log to AuditLogger
        from ..monitoring.audit import EventType
        self._audit_logger.log_event(
            event_type=EventType.ANOMALY_DETECTED,
            agent_id="system",
            vm_id=self.vm_id,
            details={
                "anomaly_type": anomaly.type.value,
                "severity": anomaly.severity.value,
                "message": anomaly.message,
                "details": anomaly.details,
                "timestamp": anomaly.timestamp.isoformat(),
            },
        )

        # Also log to structlog for debugging
        self._logger.warning(
            "anomaly_logged",
            event_type="anomaly_detected",
            vm_id=self.vm_id,
            details={
                "anomaly_type": anomaly.type.value,
                "severity": anomaly.severity.value,
                "message": anomaly.message,
                "details": anomaly.details,
                "timestamp": anomaly.timestamp.isoformat(),
            },
        )

        # When AuditLogger is available:
        # audit_logger = AuditLogger()
        # audit_logger.log_event(
        #     event_type="anomaly_detected",
        #     vm_id=self.vm_id,
        #     details={
        #         "anomaly_type": anomaly.type.value,
        #         "severity": anomaly.severity.value,
        #         "message": anomaly.message,
        #         "details": anomaly.details,
        #     }
        # )
