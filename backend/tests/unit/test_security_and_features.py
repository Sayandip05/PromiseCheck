"""Comprehensive unit and integration tests for middleware, connectors, and core features."""

import pytest
from fastapi.testclient import TestClient

from connectors.email import EmailConnector
from connectors.external_mcp import ExternalMCPConnector
from connectors.gmail import GmailConnector
from connectors.google_calendar import GoogleCalendarConnector
from connectors.google_drive import GoogleDriveConnector
from connectors.google_meet import GoogleMeetConnector
from connectors.jira import JiraConnector
from connectors.linear import LinearConnector
from connectors.recall import RecallConnector
from connectors.slack import SlackConnector
from connectors.speech_to_text import SpeechToTextConnector
from src.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_security_headers_and_tracing(client: TestClient):
    """Verify security headers, X-Request-ID, and X-Process-Time are present."""
    res = client.get("/healthz")
    assert res.status_code == 200

    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert "x-request-id" in res.headers
    assert "x-process-time" in res.headers
    assert "ms" in res.headers["x-process-time"]


@pytest.mark.asyncio
async def test_all_connectors_fluent_dual_mode():
    """Verify all 11 connectors run smoothly without throwing exceptions in mock fallback mode."""
    # 1. Jira
    jira = JiraConnector()
    assert await jira.verify_credentials({}) is True
    res = await jira.get_ticket("ENG-101")
    assert res["key"] == "ENG-101"


    # 2. Linear
    linear = LinearConnector()
    assert await linear.verify_credentials({}) is True
    res = await linear.get_issue("LIN-42")
    assert res["identifier"] == "LIN-42"

    # 3. Slack
    slack = SlackConnector()
    assert await slack.verify_credentials({}) is True
    res = await slack.post_message("Test alert", channel="#alerts")
    assert "delivered" in res["status"]


    # 4. Email
    email = EmailConnector()
    assert await email.verify_credentials({}) is True
    res = await email.send_email("client@acme.corp", "Update", "Body content")
    assert "sent" in res["status"]

    # 5. Google Meet
    gmeet = GoogleMeetConnector()
    assert await gmeet.verify_credentials({}) is True
    res = await gmeet.list_recent_meetings()
    assert len(res) > 0

    # 6. Gmail
    gmail = GmailConnector()
    assert await gmail.verify_credentials({}) is True
    res = await gmail.send_draft_update("client@acme.corp", "Update", "Body")
    assert "sent" in res["status"]

    # 7. Google Calendar
    gcal = GoogleCalendarConnector()
    assert await gcal.verify_credentials({}) is True
    res = await gcal.create_deadline_event("SSO SLA", "2026-10-15", "Delivery deadline")
    assert "status" in res

    # 8. Google Drive
    gdrive = GoogleDriveConnector()
    assert await gdrive.verify_credentials({}) is True
    res = await gdrive.search_documents("SLA Agreement")
    assert len(res) > 0

    # 9. External MCP
    mcp = ExternalMCPConnector()
    assert await mcp.verify_credentials({}) is True
    tools = await mcp.list_tools()
    assert len(tools) > 0


    # 10. Speech-To-Text
    stt = SpeechToTextConnector()
    assert await stt.verify_credentials({}) is True
    trans = await stt.transcribe_audio(b"fake audio data", "audio.mp3")
    assert isinstance(trans, str) and len(trans) > 0


    # 11. Recall
    recall = RecallConnector()
    assert await recall.verify_credentials({}) is True
    bot = await recall.create_bot("https://meet.google.com/xyz-abc")
    assert "id" in bot




def test_commitments_and_customers_endpoints(client: TestClient):
    """Verify commitments and live customer metric calculations."""
    comm_res = client.get("/api/v1/commitments")
    assert comm_res.status_code == 200
    # Fix #6: GET /commitments now returns a paginated response wrapper
    paginated = comm_res.json()
    assert "items" in paginated, "Expected paginated response with 'items' key"
    assert "total" in paginated
    assert "has_next" in paginated
    commitments = paginated["items"]
    assert isinstance(commitments, list)
    assert len(commitments) > 0

    cust_res = client.get("/api/v1/customers")
    assert cust_res.status_code == 200
    customers = cust_res.json()
    assert isinstance(customers, list)
    assert len(customers) > 0
    # Customer should have active promises and health score
    for c in customers:
        assert "healthScore" in c
        assert "activePromises" in c
        assert c["healthScore"] >= 0


def test_risk_evaluation_endpoint(client: TestClient):
    """Verify POST /api/v1/risk/evaluate scans commitments and returns metrics."""
    res = client.post("/api/v1/risk/evaluate")
    assert res.status_code == 200
    data = res.json()
    assert "evaluated_count" in data
    assert "at_risk_count" in data
    assert "overdue_count" in data
    assert "on_track_count" in data


def test_delivery_verification_flow(client: TestClient):
    """Verify delivery evidence endpoint returns 200."""
    res = client.get("/api/v1/delivery/evidence")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
