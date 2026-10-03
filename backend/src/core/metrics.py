"""Lightweight, thread-safe Prometheus metrics collector and exposition formatter.

Conforms to Prometheus text exposition format 0.0.4.
Zero external dependencies required.
"""

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple


class MetricsCollector:
    """Thread-safe Prometheus metrics registry."""

    HISTOGRAM_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (method, endpoint, status) -> count
        self._http_requests_total: Dict[Tuple[str, str, str], int] = defaultdict(int)
        # endpoint -> {le: count}
        self._duration_buckets: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self._duration_sum: Dict[str, float] = defaultdict(float)
        self._duration_count: Dict[str, int] = defaultdict(int)
        # endpoint -> count
        self._rate_limits_total: Dict[str, int] = defaultdict(int)
        self._idempotent_replays_total: Dict[str, int] = defaultdict(int)

    def record_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float) -> None:
        """Record HTTP request volume, status code, and latency."""
        # Normalize endpoint (strip query parameters and dynamic IDs to avoid high cardinality)
        norm_endpoint = self._normalize_endpoint(endpoint)
        status_str = str(status_code)

        with self._lock:
            self._http_requests_total[(method, norm_endpoint, status_str)] += 1
            self._duration_sum[norm_endpoint] += duration_seconds
            self._duration_count[norm_endpoint] += 1

            for bucket in self.HISTOGRAM_BUCKETS:
                if duration_seconds <= bucket:
                    self._duration_buckets[norm_endpoint][bucket] += 1

    def record_rate_limit(self, endpoint: str) -> None:
        """Record rate-limiting event (HTTP 429)."""
        norm_endpoint = self._normalize_endpoint(endpoint)
        with self._lock:
            self._rate_limits_total[norm_endpoint] += 1

    def record_idempotent_replay(self, endpoint: str) -> None:
        """Record safe duplicate mutation absorbed by idempotency engine."""
        norm_endpoint = self._normalize_endpoint(endpoint)
        with self._lock:
            self._idempotent_replays_total[norm_endpoint] += 1

    @staticmethod
    def _normalize_endpoint(path: str) -> str:
        """Collapse UUIDs or variable IDs to keep Prometheus metric cardinality low."""
        parts = path.split("?")[0].strip("/").split("/")
        norm_parts = []
        for p in parts:
            # If segment is UUID-like or numeric, replace with placeholder
            if len(p) >= 32 or p.replace("-", "").isalnum() and any(c.isdigit() for c in p) and len(p) > 8:
                norm_parts.append(":id")
            elif p.isdigit():
                norm_parts.append(":id")
            else:
                norm_parts.append(p)
        return "/" + "/".join(norm_parts) if norm_parts else "/"

    def generate_prometheus_metrics(self) -> str:
        """Format recorded metrics into Prometheus plain-text format (version 0.0.4)."""
        lines: List[str] = []

        with self._lock:
            # 1. HTTP Requests Total
            lines.append("# HELP http_requests_total Total number of HTTP requests processed.")
            lines.append("# TYPE http_requests_total counter")
            if not self._http_requests_total:
                lines.append('http_requests_total{method="GET",endpoint="/healthz",status="200"} 0')
            else:
                for (method, endpoint, status), count in sorted(self._http_requests_total.items()):
                    lines.append(
                        f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
                    )

            # 2. HTTP Request Duration Histogram
            lines.append("")
            lines.append("# HELP http_request_duration_seconds Latency of HTTP requests in seconds.")
            lines.append("# TYPE http_request_duration_seconds histogram")
            for endpoint in sorted(self._duration_count.keys()):
                running_bucket_count = 0
                for bucket in self.HISTOGRAM_BUCKETS:
                    running_bucket_count += self._duration_buckets[endpoint].get(bucket, 0)
                    lines.append(
                        f'http_request_duration_seconds_bucket{{endpoint="{endpoint}",le="{bucket}"}} {running_bucket_count}'
                    )
                # +Inf bucket
                total_count = self._duration_count[endpoint]
                lines.append(
                    f'http_request_duration_seconds_bucket{{endpoint="{endpoint}",le="+Inf"}} {total_count}'
                )
                lines.append(
                    f'http_request_duration_seconds_sum{{endpoint="{endpoint}"}} {self._duration_sum[endpoint]:.6f}'
                )
                lines.append(
                    f'http_request_duration_seconds_count{{endpoint="{endpoint}"}} {total_count}'
                )

            # 3. Rate Limit Exceeded Counter
            lines.append("")
            lines.append("# HELP rate_limit_exceeded_total Total number of rate-limited requests (HTTP 429).")
            lines.append("# TYPE rate_limit_exceeded_total counter")
            if not self._rate_limits_total:
                lines.append('rate_limit_exceeded_total{endpoint="/api/v1/auth/login"} 0')
            else:
                for endpoint, count in sorted(self._rate_limits_total.items()):
                    lines.append(f'rate_limit_exceeded_total{{endpoint="{endpoint}"}} {count}')

            # 4. Idempotency Replays Counter
            lines.append("")
            lines.append("# HELP idempotent_replays_total Total duplicate mutating requests safely replayed.")
            lines.append("# TYPE idempotent_replays_total counter")
            if not self._idempotent_replays_total:
                lines.append('idempotent_replays_total{endpoint="/api/v1/commitments"} 0')
            else:
                for endpoint, count in sorted(self._idempotent_replays_total.items()):
                    lines.append(f'idempotent_replays_total{{endpoint="{endpoint}"}} {count}')

        # 5. Database Connection Pool Gauge
        active_db_conns = 0
        try:
            from core.database import async_engine

            pool = async_engine.sync_engine.pool
            if hasattr(pool, "checkedout"):
                active_db_conns = pool.checkedout()
        except Exception:
            pass

        lines.append("")
        lines.append("# HELP active_db_connections Active checked-out database connections.")
        lines.append("# TYPE active_db_connections gauge")
        lines.append(f"active_db_connections {active_db_conns}")

        # 6. Celery Background Queue Depths & Active Workers
        celery_stats = {"queue_depth": 0, "active_workers": 0}
        queue_depths = {"high_priority": 0, "default": 0, "ingestion": 0}
        try:
            from core.redis import get_sync_redis

            r = get_sync_redis()
            for q_name in ("high_priority", "default", "ingestion"):
                depth = r.llen(q_name) or 0
                queue_depths[q_name] = depth
        except Exception:
            pass

        try:
            from modules.operations.router import _query_celery_stats

            celery_stats = _query_celery_stats()
        except Exception:
            pass

        lines.append("")
        lines.append("# HELP celery_queue_depth Pending tasks waiting in Celery background queues.")
        lines.append("# TYPE celery_queue_depth gauge")
        for q_name, depth in queue_depths.items():
            lines.append(f'celery_queue_depth{{queue="{q_name}"}} {depth}')

        lines.append("")
        lines.append("# HELP celery_active_workers Number of active Celery worker nodes.")
        lines.append("# TYPE celery_active_workers gauge")
        lines.append(f'celery_active_workers {celery_stats.get("active_workers", 0)}')

        lines.append("")
        return "\n".join(lines)


# Singleton metrics registry instance
metrics = MetricsCollector()
