"""
Performance monitoring system for the hallucination reduction feature.
Collects detailed performance metrics, monitors system health, and provides real-time monitoring.
"""

import time
import threading
import logging
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Represents a metric value with timestamp."""
    timestamp: datetime
    value: float
    labels: Dict[str, str]


@dataclass
class PerformanceMetrics:
    """Performance metrics for hallucination detection and correction."""
    # Detection metrics
    detection_count: int = 0
    detection_success_count: int = 0
    detection_failure_count: int = 0
    avg_detection_time: float = 0.0
    max_detection_time: float = 0.0
    min_detection_time: float = float('inf')
    
    # Correction metrics
    correction_count: int = 0
    correction_success_count: int = 0
    correction_failure_count: int = 0
    avg_correction_time: float = 0.0
    max_correction_time: float = 0.0
    min_correction_time: float = float('inf')
    
    # Quality metrics
    avg_quality_score: float = 0.0
    quality_score_distribution: Dict[str, int] = None
    
    # System metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_threads: int = 0
    
    # Error metrics
    error_count: int = 0
    error_rate: float = 0.0
    
    def __post_init__(self):
        if self.quality_score_distribution is None:
            self.quality_score_distribution = {}


@dataclass
class SystemHealth:
    """System health status."""
    overall_status: str  # "healthy", "warning", "critical"
    timestamp: datetime
    checks: Dict[str, Dict[str, Any]]
    alerts: List[str]


class PerformanceMonitor:
    """
    Monitors performance metrics for the hallucination reduction system.
    Provides real-time monitoring, alerting, and health checks.
    """
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.logger = logging.getLogger(__name__)
        
        # Metric storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # Performance tracking
        self.detection_times: deque = deque(maxlen=100)
        self.correction_times: deque = deque(maxlen=100)
        self.quality_scores: deque = deque(maxlen=100)
        
        # Health monitoring
        self.health_checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Setup default health checks and thresholds
        self._setup_default_monitoring()
    
    def _setup_default_monitoring(self):
        """Setup default health checks and alert thresholds."""
        # Register default health checks
        self.register_health_check("memory", self._check_memory_usage)
        self.register_health_check("cpu", self._check_cpu_usage)
        self.register_health_check("detection_performance", self._check_detection_performance)
        self.register_health_check("correction_performance", self._check_correction_performance)
        self.register_health_check("error_rate", self._check_error_rate)
        
        # Set default alert thresholds
        self.alert_thresholds = {
            "memory_usage": {"warning": 80.0, "critical": 95.0},
            "cpu_usage": {"warning": 80.0, "critical": 95.0},
            "detection_time": {"warning": 5.0, "critical": 10.0},
            "correction_time": {"warning": 3.0, "critical": 6.0},
            "error_rate": {"warning": 0.05, "critical": 0.1},
            "quality_score": {"warning": 0.6, "critical": 0.4}
        }
    
    def start_monitoring(self):
        """Start the performance monitoring system."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop the performance monitoring system."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Perform health checks
                self._perform_health_checks()
                
                # Check for alerts
                self._check_alerts()
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # Memory usage
            memory_info = psutil.virtual_memory()
            self.record_gauge("system.memory.usage_percent", memory_info.percent)
            self.record_gauge("system.memory.available_mb", memory_info.available / 1024 / 1024)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.record_gauge("system.cpu.usage_percent", cpu_percent)
            
            # Process-specific metrics
            process = psutil.Process()
            self.record_gauge("process.memory.rss_mb", process.memory_info().rss / 1024 / 1024)
            self.record_gauge("process.cpu.usage_percent", process.cpu_percent())
            self.record_gauge("process.threads.count", process.num_threads())
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    def _perform_health_checks(self):
        """Perform all registered health checks."""
        for check_name, check_func in self.health_checks.items():
            try:
                result = check_func()
                self.record_gauge(f"health.{check_name}.status", 1.0 if result.get("healthy", False) else 0.0)
                
                # Store detailed results
                timestamp = datetime.now()
                self.metrics[f"health.{check_name}"].append(MetricValue(
                    timestamp=timestamp,
                    value=1.0 if result.get("healthy", False) else 0.0,
                    labels={"details": json.dumps(result)}
                ))
                
            except Exception as e:
                self.logger.error(f"Error in health check {check_name}: {e}")
    
    def _check_alerts(self):
        """Check for alert conditions and trigger callbacks."""
        current_time = datetime.now()
        
        # Check memory usage
        memory_usage = self.get_latest_gauge("system.memory.usage_percent")
        if memory_usage is not None:
            self._check_threshold_alert("memory_usage", memory_usage, "Memory usage")
        
        # Check CPU usage
        cpu_usage = self.get_latest_gauge("system.cpu.usage_percent")
        if cpu_usage is not None:
            self._check_threshold_alert("cpu_usage", cpu_usage, "CPU usage")
        
        # Check detection performance
        if self.detection_times:
            avg_detection_time = sum(self.detection_times) / len(self.detection_times)
            self._check_threshold_alert("detection_time", avg_detection_time, "Average detection time")
        
        # Check correction performance
        if self.correction_times:
            avg_correction_time = sum(self.correction_times) / len(self.correction_times)
            self._check_threshold_alert("correction_time", avg_correction_time, "Average correction time")
        
        # Check error rate
        error_rate = self.calculate_error_rate()
        if error_rate is not None:
            self._check_threshold_alert("error_rate", error_rate, "Error rate")
        
        # Check quality score
        if self.quality_scores:
            avg_quality = sum(self.quality_scores) / len(self.quality_scores)
            # For quality score, lower values are worse (reverse threshold check)
            self._check_threshold_alert("quality_score", avg_quality, "Average quality score", reverse=True)
    
    def _check_threshold_alert(self, metric_name: str, value: float, description: str, reverse: bool = False):
        """Check if a metric value exceeds alert thresholds."""
        if metric_name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric_name]
        warning_threshold = thresholds.get("warning")
        critical_threshold = thresholds.get("critical")
        
        alert_level = None
        if reverse:
            # For metrics where lower values are worse (like quality score)
            if critical_threshold is not None and value <= critical_threshold:
                alert_level = "critical"
            elif warning_threshold is not None and value <= warning_threshold:
                alert_level = "warning"
        else:
            # For metrics where higher values are worse
            if critical_threshold is not None and value >= critical_threshold:
                alert_level = "critical"
            elif warning_threshold is not None and value >= warning_threshold:
                alert_level = "warning"
        
        if alert_level:
            alert_data = {
                "metric": metric_name,
                "value": value,
                "threshold": thresholds[alert_level],
                "level": alert_level,
                "description": description,
                "timestamp": datetime.now()
            }
            
            self._trigger_alert(alert_level, alert_data)
    
    def _trigger_alert(self, level: str, alert_data: Dict[str, Any]):
        """Trigger an alert and notify callbacks."""
        alert_message = (f"{level.upper()}: {alert_data['description']} is {alert_data['value']:.2f}, "
                        f"threshold: {alert_data['threshold']}")
        
        self.logger.warning(f"ALERT - {alert_message}")
        
        # Notify alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(level, alert_data)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Record a counter metric."""
        with self._lock:
            self.counters[name] += value
            self._record_metric(name, value, MetricType.COUNTER, labels or {})
    
    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a gauge metric."""
        with self._lock:
            self.gauges[name] = value
            self._record_metric(name, value, MetricType.GAUGE, labels or {})
    
    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Record a timer metric."""
        with self._lock:
            self.timers[name].append(duration)
            # Keep only recent values
            if len(self.timers[name]) > 100:
                self.timers[name] = self.timers[name][-100:]
            self._record_metric(name, duration, MetricType.TIMER, labels or {})
    
    def _record_metric(self, name: str, value: float, metric_type: MetricType, labels: Dict[str, str]):
        """Record a metric value with timestamp."""
        metric_value = MetricValue(
            timestamp=datetime.now(),
            value=value,
            labels=labels
        )
        self.metrics[name].append(metric_value)
    
    def get_latest_gauge(self, name: str) -> Optional[float]:
        """Get the latest value of a gauge metric."""
        with self._lock:
            return self.gauges.get(name)
    
    def get_counter_value(self, name: str) -> float:
        """Get the current value of a counter metric."""
        with self._lock:
            return self.counters.get(name, 0.0)
    
    def get_timer_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a timer metric."""
        with self._lock:
            values = self.timers.get(name, [])
            if not values:
                return None
            
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "p50": sorted(values)[len(values) // 2],
                "p95": sorted(values)[int(len(values) * 0.95)],
                "p99": sorted(values)[int(len(values) * 0.99)]
            }
    
    def record_detection_attempt(self, duration: float, success: bool, quality_score: Optional[float] = None):
        """Record a hallucination detection attempt."""
        self.record_counter("hallucination.detection.attempts")
        self.record_timer("hallucination.detection.duration", duration)
        
        if success:
            self.record_counter("hallucination.detection.success")
        else:
            self.record_counter("hallucination.detection.failures")
        
        # Track detection times for performance monitoring
        with self._lock:
            self.detection_times.append(duration)
        
        if quality_score is not None:
            self.record_gauge("hallucination.detection.quality_score", quality_score)
            with self._lock:
                self.quality_scores.append(quality_score)
    
    def record_correction_attempt(self, duration: float, success: bool, quality_score: Optional[float] = None):
        """Record a speech correction attempt."""
        self.record_counter("hallucination.correction.attempts")
        self.record_timer("hallucination.correction.duration", duration)
        
        if success:
            self.record_counter("hallucination.correction.success")
        else:
            self.record_counter("hallucination.correction.failures")
        
        # Track correction times for performance monitoring
        with self._lock:
            self.correction_times.append(duration)
        
        if quality_score is not None:
            self.record_gauge("hallucination.correction.quality_score", quality_score)
    
    def record_error(self, error_type: str, error_message: str):
        """Record an error occurrence."""
        self.record_counter("errors.total")
        self.record_counter(f"errors.{error_type}")
        
        # Store error details
        error_data = {
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        self._record_metric("errors.details", 1.0, MetricType.COUNTER, error_data)
    
    def calculate_error_rate(self, window_minutes: int = 5) -> Optional[float]:
        """Calculate error rate over a time window."""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        total_attempts = 0
        error_count = 0
        
        # Count detection attempts and errors
        detection_metrics = self.metrics.get("hallucination.detection.attempts", [])
        for metric in detection_metrics:
            if metric.timestamp >= cutoff_time:
                total_attempts += metric.value
        
        error_metrics = self.metrics.get("errors.total", [])
        for metric in error_metrics:
            if metric.timestamp >= cutoff_time:
                error_count += metric.value
        
        if total_attempts == 0:
            return None
        
        return error_count / total_attempts
    
    def get_performance_summary(self) -> PerformanceMetrics:
        """Get a summary of current performance metrics."""
        with self._lock:
            metrics = PerformanceMetrics()
            
            # Detection metrics
            metrics.detection_count = int(self.get_counter_value("hallucination.detection.attempts"))
            metrics.detection_success_count = int(self.get_counter_value("hallucination.detection.success"))
            metrics.detection_failure_count = int(self.get_counter_value("hallucination.detection.failures"))
            
            detection_stats = self.get_timer_stats("hallucination.detection.duration")
            if detection_stats:
                metrics.avg_detection_time = detection_stats["avg"]
                metrics.max_detection_time = detection_stats["max"]
                metrics.min_detection_time = detection_stats["min"]
            
            # Correction metrics
            metrics.correction_count = int(self.get_counter_value("hallucination.correction.attempts"))
            metrics.correction_success_count = int(self.get_counter_value("hallucination.correction.success"))
            metrics.correction_failure_count = int(self.get_counter_value("hallucination.correction.failures"))
            
            correction_stats = self.get_timer_stats("hallucination.correction.duration")
            if correction_stats:
                metrics.avg_correction_time = correction_stats["avg"]
                metrics.max_correction_time = correction_stats["max"]
                metrics.min_correction_time = correction_stats["min"]
            
            # Quality metrics
            if self.quality_scores:
                metrics.avg_quality_score = sum(self.quality_scores) / len(self.quality_scores)
                
                # Quality score distribution
                distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
                for score in self.quality_scores:
                    if score >= 0.8:
                        distribution["excellent"] += 1
                    elif score >= 0.6:
                        distribution["good"] += 1
                    elif score >= 0.4:
                        distribution["fair"] += 1
                    else:
                        distribution["poor"] += 1
                metrics.quality_score_distribution = distribution
            
            # System metrics
            metrics.memory_usage_mb = self.get_latest_gauge("process.memory.rss_mb") or 0.0
            metrics.cpu_usage_percent = self.get_latest_gauge("process.cpu.usage_percent") or 0.0
            metrics.active_threads = int(self.get_latest_gauge("process.threads.count") or 0)
            
            # Error metrics
            metrics.error_count = int(self.get_counter_value("errors.total"))
            error_rate = self.calculate_error_rate()
            metrics.error_rate = error_rate or 0.0
            
            return metrics
    
    def get_system_health(self) -> SystemHealth:
        """Get current system health status."""
        health_checks = {}
        alerts = []
        overall_status = "healthy"
        
        # Run all health checks
        for check_name, check_func in self.health_checks.items():
            try:
                result = check_func()
                health_checks[check_name] = result
                
                if not result.get("healthy", True):
                    if result.get("critical", False):
                        overall_status = "critical"
                        alerts.append(f"Critical: {check_name} - {result.get('message', 'Unknown issue')}")
                    elif overall_status != "critical":
                        overall_status = "warning"
                        alerts.append(f"Warning: {check_name} - {result.get('message', 'Unknown issue')}")
                        
            except Exception as e:
                health_checks[check_name] = {"healthy": False, "error": str(e)}
                if overall_status != "critical":
                    overall_status = "warning"
                alerts.append(f"Health check error: {check_name} - {e}")
        
        return SystemHealth(
            overall_status=overall_status,
            timestamp=datetime.now(),
            checks=health_checks,
            alerts=alerts
        )
    
    def register_health_check(self, name: str, check_func: Callable[[], Dict[str, Any]]):
        """Register a custom health check function."""
        self.health_checks[name] = check_func
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add an alert callback function."""
        self.alert_callbacks.append(callback)
    
    def set_alert_threshold(self, metric_name: str, warning: Optional[float] = None, 
                           critical: Optional[float] = None):
        """Set alert thresholds for a metric."""
        if metric_name not in self.alert_thresholds:
            self.alert_thresholds[metric_name] = {}
        
        if warning is not None:
            self.alert_thresholds[metric_name]["warning"] = warning
        if critical is not None:
            self.alert_thresholds[metric_name]["critical"] = critical
    
    def export_metrics(self, format: str = "json") -> str:
        """Export all metrics in the specified format."""
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": {name: self.get_timer_stats(name) for name in self.timers},
            "performance_summary": asdict(self.get_performance_summary()),
            "system_health": asdict(self.get_system_health())
        }
        
        if format.lower() == "json":
            return json.dumps(metrics_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    # Default health check implementations
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            memory_info = psutil.virtual_memory()
            usage_percent = memory_info.percent
            
            return {
                "healthy": usage_percent < 90.0,
                "critical": usage_percent >= 95.0,
                "usage_percent": usage_percent,
                "available_mb": memory_info.available / 1024 / 1024,
                "message": f"Memory usage: {usage_percent:.1f}%"
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _check_cpu_usage(self) -> Dict[str, Any]:
        """Check system CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1.0)
            
            return {
                "healthy": cpu_percent < 90.0,
                "critical": cpu_percent >= 95.0,
                "usage_percent": cpu_percent,
                "message": f"CPU usage: {cpu_percent:.1f}%"
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _check_detection_performance(self) -> Dict[str, Any]:
        """Check hallucination detection performance."""
        try:
            if not self.detection_times:
                return {"healthy": True, "message": "No detection data available"}
            
            avg_time = sum(self.detection_times) / len(self.detection_times)
            max_time = max(self.detection_times)
            
            return {
                "healthy": avg_time < 5.0 and max_time < 10.0,
                "critical": avg_time >= 10.0 or max_time >= 20.0,
                "avg_time": avg_time,
                "max_time": max_time,
                "message": f"Avg detection time: {avg_time:.2f}s, Max: {max_time:.2f}s"
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _check_correction_performance(self) -> Dict[str, Any]:
        """Check speech correction performance."""
        try:
            if not self.correction_times:
                return {"healthy": True, "message": "No correction data available"}
            
            avg_time = sum(self.correction_times) / len(self.correction_times)
            max_time = max(self.correction_times)
            
            return {
                "healthy": avg_time < 3.0 and max_time < 6.0,
                "critical": avg_time >= 6.0 or max_time >= 12.0,
                "avg_time": avg_time,
                "max_time": max_time,
                "message": f"Avg correction time: {avg_time:.2f}s, Max: {max_time:.2f}s"
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _check_error_rate(self) -> Dict[str, Any]:
        """Check system error rate."""
        try:
            error_rate = self.calculate_error_rate(window_minutes=5)
            if error_rate is None:
                return {"healthy": True, "message": "No activity data available"}
            
            return {
                "healthy": error_rate < 0.05,
                "critical": error_rate >= 0.1,
                "error_rate": error_rate,
                "message": f"Error rate (5min): {error_rate:.1%}"
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def start_monitoring():
    """Start performance monitoring."""
    get_performance_monitor().start_monitoring()


def stop_monitoring():
    """Stop performance monitoring."""
    if _performance_monitor:
        _performance_monitor.stop_monitoring()


def record_detection_attempt(duration: float, success: bool, quality_score: Optional[float] = None):
    """Record a hallucination detection attempt."""
    get_performance_monitor().record_detection_attempt(duration, success, quality_score)


def record_correction_attempt(duration: float, success: bool, quality_score: Optional[float] = None):
    """Record a speech correction attempt."""
    get_performance_monitor().record_correction_attempt(duration, success, quality_score)


def record_error(error_type: str, error_message: str):
    """Record an error occurrence."""
    get_performance_monitor().record_error(error_type, error_message)