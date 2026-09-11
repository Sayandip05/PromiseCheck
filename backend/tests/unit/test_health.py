"""Unit tests for liveness and dynamic readiness health checks."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_liveness_probe(client: TestClient) -> None:
    """Test /healthz returns 200 OK immediately."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "promisecheck"}


@patch("src.main.check_database_health", new_callable=AsyncMock)
@patch("src.main.check_redis_health", new_callable=AsyncMock)
def test_readiness_probe_healthy(
    mock_redis: AsyncMock,
    mock_db: AsyncMock,
    client: TestClient,
) -> None:
    """Test /api/v1/health returns 200 OK when both DB and Redis are reachable."""
    mock_db.return_value = (True, "connected")
    mock_redis.return_value = (True, "connected")

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["database"] == "connected"
    assert data["checks"]["redis"] == "connected"


@patch("src.main.check_database_health", new_callable=AsyncMock)
@patch("src.main.check_redis_health", new_callable=AsyncMock)
def test_readiness_probe_degraded(
    mock_redis: AsyncMock,
    mock_db: AsyncMock,
    client: TestClient,
) -> None:
    """Test /api/v1/health returns 503 Service Unavailable when DB is down."""
    mock_db.return_value = (False, "Connection refused")
    mock_redis.return_value = (True, "connected")

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "Connection refused" in data["checks"]["database"]
