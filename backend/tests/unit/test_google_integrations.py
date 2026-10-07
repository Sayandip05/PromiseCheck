"""Unit tests for Google Integration (Gmail & Google Calendar) endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(auth_client: TestClient) -> TestClient:
    return auth_client


def test_google_authorize_url_generation(client: TestClient):
    """Verify Google OAuth authorization URL generates correct scopes and parameters."""
    res = client.get("/api/v1/integrations/google/authorize")

    assert res.status_code == 200
    data = res.json()
    auth_url = data.get("authorization_url", "")
    assert "accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert "gmail.send" in auth_url
    assert "calendar.events" in auth_url
    assert "response_type=code" in auth_url
    assert "access_type=offline" in auth_url


def test_google_connect_direct_token(client: TestClient):
    """Verify connecting Google credentials directly updates database integration record."""
    payload = {
        "access_token": "ya29.mock_google_token_12345",
        "refresh_token": "1//mock_refresh_token_67890",
        "email": "lead@acme.corp",
        "expires_in": 3600,
    }
    res = client.post("/api/v1/integrations/google/connect-token", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "gmail"
    assert data["connected"] is True
    assert "lead@acme.corp" in data["statusText"]


from connectors.google_calendar import GoogleCalendarConnector
from connectors.gmail import GmailConnector


def test_google_calendar_sync_event(client: TestClient):
    """Verify syncing a commitment deadline to Google Calendar creates an event."""
    # First ensure token is connected
    client.post(
        "/api/v1/integrations/google/connect-token",
        json={"access_token": "mock_token", "email": "founder@acme.corp"},
    )

    payload = {
        "title": "SOC-2 Type II Compliance Deliverable",
        "due_date_iso": "2026-10-20",
        "description": "Annual security compliance sign-off for Acme Corp.",
    }
    with patch.object(GoogleCalendarConnector, "create_deadline_event", new_callable=AsyncMock) as mock_cal:
        mock_cal.return_value = {
            "status": "created",
            "id": "ev-101",
            "htmlLink": "https://calendar.google.com/event?eid=ev-101",
            "summary": "SOC-2 Type II Compliance Deliverable",
        }
        res = client.post("/api/v1/integrations/google/calendar/sync-event", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "synced"
        assert "SOC-2 Type II" in data["event"]["summary"]
        assert data["html_link"] is not None


def test_google_gmail_send_update(client: TestClient):
    """Verify sending customer update via Gmail connector."""
    client.post(
        "/api/v1/integrations/google/connect-token",
        json={"access_token": "mock_token", "email": "founder@acme.corp"},
    )

    payload = {
        "to_email": "client.vp@acme.corp",
        "subject": "Delivery Milestone On Track",
        "body": "Hi team, our engineering verification cycle has finished and we are on track for Oct 20.",
    }
    with patch.object(GmailConnector, "send_draft_update", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent", "id": "msg-99"}
        res = client.post("/api/v1/integrations/google/gmail/send-update", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "sent"

