"""Unit and integration tests for persistent WorkspaceIntegrations (Twelve-Factor Factor VI)."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_integrations_seeds_default_database_records(client: TestClient):
    """Verify that listing integrations auto-provisions the standard 6 providers in the DB."""
    response = client.get("/api/v1/integrations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 6

    providers = {item["provider"] for item in data}
    expected = {"google_meet", "jira", "slack", "linear", "gmail", "recall"}
    assert expected.issubset(providers)

    # Verify field schema conforms to IntegrationDTO
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "connected" in first
    assert "statusText" in first


def test_connect_and_disconnect_integration_persists(client: TestClient):
    """Verify that connect and disconnect update database state and invalidate Redis cache."""
    # 1. Connect linear
    connect_resp = client.post(
        "/api/v1/integrations/linear/connect",
        json={"scope": "Team ENG"},
    )
    assert connect_resp.status_code == 200
    item = connect_resp.json()
    assert item["provider"] == "linear"
    assert item["connected"] is True
    assert "Team ENG" in (item.get("channelOrScope") or "")

    # 2. Verify state persists on subsequent listing
    list_resp = client.get("/api/v1/integrations")
    assert list_resp.status_code == 200
    linear_item = next((i for i in list_resp.json() if i["provider"] == "linear"), None)
    assert linear_item is not None
    assert linear_item["connected"] is True

    # 3. Disconnect linear
    disconnect_resp = client.post("/api/v1/integrations/linear/disconnect")
    assert disconnect_resp.status_code == 200
    disc_item = disconnect_resp.json()
    assert disc_item["provider"] == "linear"
    assert disc_item["connected"] is False

    # 4. Verify disconnected state persists
    list_resp_2 = client.get("/api/v1/integrations")
    linear_item_2 = next((i for i in list_resp_2.json() if i["provider"] == "linear"), None)
    assert linear_item_2 is not None
    assert linear_item_2["connected"] is False


def test_unknown_provider_returns_404(client: TestClient):
    """Verify 404 is returned when attempting to connect an unsupported provider."""
    resp = client.post(
        "/api/v1/integrations/non_existent_provider/connect",
        json={"scope": "Test"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
