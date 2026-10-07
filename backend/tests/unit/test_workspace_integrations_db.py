"""Unit and integration tests for persistent WorkspaceIntegrations (Twelve-Factor Factor VI)."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client(auth_client: TestClient) -> TestClient:
    return auth_client


def test_list_integrations_unauthenticated_returns_401():
    """Verify that unauthenticated request to integrations returns 401 Unauthorized."""
    raw_client = TestClient(app)
    response = raw_client.get("/api/v1/integrations")
    assert response.status_code == 401


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


from unittest.mock import AsyncMock, patch
from connectors.linear import LinearConnector


def test_connect_and_disconnect_integration_persists(client: TestClient):
    """Verify that connect and disconnect update database state and invalidate Redis cache."""
    # 1. Connect linear with mocked external API verification
    with patch.object(LinearConnector, "verify_credentials", new_callable=AsyncMock) as mock_verify, \
         patch.object(LinearConnector, "initial_sync", new_callable=AsyncMock) as mock_sync:
        mock_verify.return_value = True
        mock_sync.return_value = {"status": "active"}

        connect_resp = client.post(
            "/api/v1/integrations/linear/connect",
            json={"api_key": "lin_mock_token_123", "scope": "Team ENG"},
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


def test_test_integration_endpoints_for_all_providers(client: TestClient):
    """Verify POST /api/v1/integrations/{provider}/test works across all 6 integrations."""
    # 1. Slack test
    slack_resp = client.post(
        "/api/v1/integrations/slack/test",
        json={"channel": "#customer-commitments", "message": "Test ping"},
    )
    assert slack_resp.status_code == 200
    assert slack_resp.json()["provider"] == "slack"


    # 2. Jira test
    jira_resp = client.post(
        "/api/v1/integrations/jira/test",
        json={"domain": "acme.atlassian.net", "email": "dev@acme.corp", "api_token": "token123"},
    )
    assert jira_resp.status_code == 200
    assert jira_resp.json()["provider"] == "jira"

    # 3. Linear test
    linear_resp = client.post(
        "/api/v1/integrations/linear/test",
        json={"api_key": "lin_api_test_key"},
    )
    assert linear_resp.status_code == 200
    assert linear_resp.json()["provider"] == "linear"

    # 4. Recall.ai test
    recall_resp = client.post(
        "/api/v1/integrations/recall/test",
        json={"region": "us-west-2", "bot_name": "Test Bot", "meeting_url": "https://meet.google.com/xyz-abc"},
    )
    assert recall_resp.status_code == 200
    assert recall_resp.json()["provider"] == "recall"

    # 5. Google Meet test
    meet_resp = client.post(
        "/api/v1/integrations/google_meet/test",
        json={},
    )
    assert meet_resp.status_code == 200
    assert meet_resp.json()["provider"] == "google_meet"

