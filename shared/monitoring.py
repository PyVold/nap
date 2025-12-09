# ============================================================================
# shared/monitoring.py - Application monitoring and metrics
# ============================================================================

import time
import os
import psutil
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import asyncio

from shared.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(tags=["monitoring"])


class MetricsCollector:
    """
    Collects and exposes application metrics in Prometheus format.

    Tracks:
    - Request counts and latencies
    - Error rates
    - Database connection pool stats
    - System resource usage
    """

    def __init__(self):
        self._request_count: Dict[str, int] = defaultdict(int)
        self._request_latency: Dict[str, list] = defaultdict(list)
        self._error_count: Dict[str, int] = defaultdict(int)
        self._start_time = time.time()
        self._custom_metrics: Dict[str, Any] = {}

    def record_request(self, method: str, path: str, status_code: int, latency_ms: float):
        """Record a request metric"""
        key = f"{method}:{path}"
        self._request_count[key] += 1

        # Keep last 1000 latencies per endpoint
        latencies = self._request_latency[key]
        latencies.append(latency_ms)
        if len(latencies) > 1000:
            self._request_latency[key] = latencies[-1000:]

        if status_code >= 400:
            self._error_count[f"{key}:{status_code}"] += 1

    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge metric value"""
        label_str = ",".join(f'{k}="{v}"' for k, v in (labels or {}).items())
        key = f"{name}{{{label_str}}}" if label_str else name
        self._custom_metrics[key] = value

    def increment_counter(self, name: str, labels: Optional[Dict] = None):
        """Increment a counter metric"""
        label_str = ",".join(f'{k}="{v}"' for k, v in (labels or {}).items())
        key = f"{name}{{{label_str}}}" if label_str else name
        self._custom_metrics[key] = self._custom_metrics.get(key, 0) + 1

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        # Uptime
        uptime = time.time() - self._start_time
        lines.append(f"# HELP nap_uptime_seconds Time since application start")
        lines.append(f"# TYPE nap_uptime_seconds gauge")
        lines.append(f"nap_uptime_seconds {uptime:.2f}")

        # Request counts
        lines.append(f"# HELP nap_http_requests_total Total HTTP requests")
        lines.append(f"# TYPE nap_http_requests_total counter")
        for key, count in self._request_count.items():
            method, path = key.split(":", 1)
            lines.append(f'nap_http_requests_total{{method="{method}",path="{path}"}} {count}')

        # Request latency (p50, p95, p99)
        lines.append(f"# HELP nap_http_request_duration_ms HTTP request latency in milliseconds")
        lines.append(f"# TYPE nap_http_request_duration_ms summary")
        for key, latencies in self._request_latency.items():
            if latencies:
                method, path = key.split(":", 1)
                sorted_lat = sorted(latencies)
                p50 = sorted_lat[len(sorted_lat) // 2]
                p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
                p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
                lines.append(f'nap_http_request_duration_ms{{method="{method}",path="{path}",quantile="0.5"}} {p50:.2f}')
                lines.append(f'nap_http_request_duration_ms{{method="{method}",path="{path}",quantile="0.95"}} {p95:.2f}')
                lines.append(f'nap_http_request_duration_ms{{method="{method}",path="{path}",quantile="0.99"}} {p99:.2f}')

        # Error counts
        lines.append(f"# HELP nap_http_errors_total Total HTTP errors")
        lines.append(f"# TYPE nap_http_errors_total counter")
        for key, count in self._error_count.items():
            parts = key.rsplit(":", 1)
            if len(parts) == 2:
                endpoint, status = parts
                method, path = endpoint.split(":", 1)
                lines.append(f'nap_http_errors_total{{method="{method}",path="{path}",status="{status}"}} {count}')

        # System metrics
        lines.append(f"# HELP nap_process_cpu_percent Process CPU usage percentage")
        lines.append(f"# TYPE nap_process_cpu_percent gauge")
        lines.append(f"nap_process_cpu_percent {psutil.Process().cpu_percent():.2f}")

        lines.append(f"# HELP nap_process_memory_bytes Process memory usage in bytes")
        lines.append(f"# TYPE nap_process_memory_bytes gauge")
        lines.append(f"nap_process_memory_bytes {psutil.Process().memory_info().rss}")

        lines.append(f"# HELP nap_system_cpu_percent System CPU usage percentage")
        lines.append(f"# TYPE nap_system_cpu_percent gauge")
        lines.append(f"nap_system_cpu_percent {psutil.cpu_percent():.2f}")

        lines.append(f"# HELP nap_system_memory_percent System memory usage percentage")
        lines.append(f"# TYPE nap_system_memory_percent gauge")
        lines.append(f"nap_system_memory_percent {psutil.virtual_memory().percent:.2f}")

        # Custom metrics
        for key, value in self._custom_metrics.items():
            lines.append(f"{key} {value}")

        return "\n".join(lines)

    def get_health_status(self) -> Dict[str, Any]:
        """Get application health status"""
        return {
            "status": "healthy",
            "uptime_seconds": time.time() - self._start_time,
            "timestamp": datetime.utcnow().isoformat(),
            "version": os.environ.get("APP_VERSION", "unknown"),
        }


# Global metrics collector
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector"""
    return _metrics


# Monitoring routes
@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes.
    Verifies the service is ready to accept traffic.
    """
    # Add checks for dependencies (DB, cache, etc.)
    checks = {
        "database": True,  # TODO: Add actual DB check
        "cache": True,     # TODO: Add actual cache check
    }

    all_ready = all(checks.values())
    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes.
    Returns 200 if the process is alive.
    """
    return {"alive": True}


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    """
    from starlette.responses import PlainTextResponse
    return PlainTextResponse(
        content=_metrics.get_prometheus_metrics(),
        media_type="text/plain"
    )


@router.get("/status")
async def detailed_status():
    """
    Detailed system status including resource usage.
    """
    process = psutil.Process()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.environ.get("APP_VERSION", "unknown"),
        "uptime_seconds": time.time() - _metrics._start_time,
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        },
        "process": {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "threads": process.num_threads(),
        }
    }
