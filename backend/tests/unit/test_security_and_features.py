"""Comprehensive unit and integration tests for middleware, connectors, and core features."""

import os
from unittest.mock import AsyncMock, patch
import uuid
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


def test_jwt_secret_crash_on_missing_key():
    """Verify _get_jwt_secret raises RuntimeError when no secret key is configured."""
    from core.security import _get_jwt_secret
    from core.config import settings

    with patch.object(settings, "JWT_SECRET_KEY", ""), \
         patch.object(settings, "SECRET_KEY", ""), \
         patch.object(settings, "SESSION_SIGNING_KEY", ""), \
         patch.dict(os.environ, {"JWT_SECRET_KEY": "", "SECRET_KEY": "", "SESSION_SIGNING_KEY": ""}):
        with pytest.raises(RuntimeError) as exc:
            _get_jwt_secret()
        assert "JWT signing secret is not configured" in str(exc.value)


def test_csp_production_policy_no_unsafe_inline(client: TestClient):
    """Verify CSP header strictly forbids unsafe-inline in production mode."""
    from core.config import settings

    with patch.object(settings, "APP_ENV", "production"):
        res = client.get("/healthz")
        csp = res.headers.get("content-security-policy", "")
        assert "unsafe-inline" not in csp
        assert "default-src 'none'" in csp


@pytest.mark.asyncio
async def test_audio_upload_size_limit_rejection():
    """Verify audio file upload exceeding 200 MB raises HTTP 413 Payload Too Large."""
    from fastapi import HTTPException, UploadFile
    from modules.ingestion.router import upload_audio_file

    class HugeBytes:
        def __len__(self):
            return 200_000_001

    mock_file = AsyncMock(spec=UploadFile)
    mock_file.read.return_value = HugeBytes()
    mock_file.filename = "large_recording.mp3"

    with pytest.raises(HTTPException) as exc:
        await upload_audio_file(file=mock_file, db=AsyncMock())
    assert exc.value.status_code == 413
    assert "200 MB" in exc.value.detail


def test_registration_error_does_not_leak_email_pii(client: TestClient):
    """Verify duplicate user registration does not echo back email address (PII protection)."""
    unique_email = f"pii_check_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "ValidPassword123!",
        "full_name": "Test User",
    }
    # Register first time
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration attempt must return generic error without user's email
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    detail = res2.json().get("detail", "")
    assert detail == "An account with this email address already exists."
    assert unique_email not in detail
