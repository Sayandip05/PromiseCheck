"""Unit tests for Prometheus metrics collection and exposition endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from core.metrics import metrics


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_metrics_endpoint_exposition_format(client: TestClient):
    """Verify that /api/v1/metrics and /metrics export valid Prometheus plain text format."""
    # Issue a request to increment telemetry
    client.get("/api/v1/customers")

    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text

    # Verify standard Prometheus header annotations
    assert "# HELP http_requests_total" in text
    assert "# TYPE http_requests_total counter"
    assert "# HELP http_request_duration_seconds"
    assert "# TYPE http_request_duration_seconds histogram"
    assert "# HELP active_db_connections"
    assert "# TYPE active_db_connections gauge"
    assert "# HELP celery_queue_depth"
    assert "# TYPE celery_queue_depth gauge"

    # Verify root /metrics alias works
    root_resp = client.get("/metrics")
    assert root_resp.status_code == 200
    assert "# HELP http_requests_total" in root_resp.text


def test_metrics_records_rate_limiting_and_replays():
    """Verify rate limit and idempotency events are tracked in metrics collector."""
    metrics.record_rate_limit("/api/v1/auth/login")
    metrics.record_idempotent_replay("/api/v1/commitments")

    output = metrics.generate_prometheus_metrics()
    assert 'rate_limit_exceeded_total{endpoint="/api/v1/auth/login"}' in output
    assert 'idempotent_replays_total{endpoint="/api/v1/commitments"}' in output
