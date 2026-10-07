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
async def test_all_connectors_fail_fast_when_unconfigured():
    """Verify connectors fail fast with ConnectorNotConfiguredError instead of silent fluent mocks."""
    from connectors.base import ConnectorNotConfiguredError

    # 1. Jira
    jira = JiraConnector()
    with pytest.raises(ConnectorNotConfiguredError):
        await jira.verify_credentials({})
    with pytest.raises(ConnectorNotConfiguredError):
        await jira.get_ticket("ENG-101")

    # 2. Linear
    linear = LinearConnector()
    with pytest.raises(ConnectorNotConfiguredError):
        await linear.verify_credentials({})
    with pytest.raises(ConnectorNotConfiguredError):
        await linear.get_issue("LIN-42")

    # 3. Slack
    slack = SlackConnector()
    with pytest.raises(ConnectorNotConfiguredError):
        await slack.verify_credentials({})
    with pytest.raises(ConnectorNotConfiguredError):
        await slack.post_message("Test alert", channel="#alerts")

    # 4. Gmail
    gmail = GmailConnector()
    with pytest.raises(ConnectorNotConfiguredError):
        await gmail.verify_credentials({})
    with pytest.raises(ConnectorNotConfiguredError):
        await gmail.send_draft_update("client@acme.corp", "Update", "Body")

    # 5. Google Calendar
    gcal = GoogleCalendarConnector()
    with pytest.raises(ConnectorNotConfiguredError):
        await gcal.verify_credentials({})
    with pytest.raises(ConnectorNotConfiguredError):
        await gcal.create_deadline_event("SSO SLA", "2026-10-15", "Delivery deadline")

    # 6. Speech-To-Text
    stt = SpeechToTextConnector()
    with pytest.raises(ConnectorNotConfiguredError):
        await stt.verify_credentials({})
    with pytest.raises(ConnectorNotConfiguredError):
        await stt.transcribe_audio(b"fake audio data", "audio.mp3")

    # 7. Recall
    recall = RecallConnector()
    with pytest.raises(ConnectorNotConfiguredError):
        await recall.verify_credentials({})
    with pytest.raises(ConnectorNotConfiguredError):
        await recall.create_bot("https://meet.google.com/xyz-abc")



def test_commitments_and_customers_endpoints(auth_client: TestClient):
    """Verify commitments and live customer metric calculations with authenticated client."""
    # Create customer and commitment
    cust_create = auth_client.post(
        "/api/v1/customers",
        json={"name": "Acme Test Corp", "tier": "Enterprise", "arr": 150000, "health_score": 90},
    )
    assert cust_create.status_code == 201

    comm_create = auth_client.post(
        "/api/v1/commitments",
        json={"title": "Deliver SSO SAML", "customer": "Acme Test Corp", "promised_by": "Oct 25, 2026"},
    )
    assert comm_create.status_code == 201

    comm_res = auth_client.get("/api/v1/commitments")
    assert comm_res.status_code == 200
    paginated = comm_res.json()
    assert "items" in paginated, "Expected paginated response with 'items' key"
    assert "total" in paginated
    assert "has_next" in paginated
    commitments = paginated["items"]
    assert isinstance(commitments, list)
    assert len(commitments) > 0

    cust_res = auth_client.get("/api/v1/customers")
    assert cust_res.status_code == 200
    customers = cust_res.json()
    assert isinstance(customers, list)
    assert len(customers) > 0
    for c in customers:
        assert "healthScore" in c
        assert "activePromises" in c
        assert c["healthScore"] >= 0


def test_risk_evaluation_endpoint(auth_client: TestClient):
    """Verify POST /api/v1/risk/evaluate scans commitments and returns metrics."""
    res = auth_client.post("/api/v1/risk/evaluate")
    assert res.status_code == 200
    data = res.json()
    assert "evaluated_count" in data
    assert "at_risk_count" in data
    assert "overdue_count" in data
    assert "on_track_count" in data


def test_delivery_verification_flow(auth_client: TestClient):
    """Verify delivery evidence endpoint returns 200."""
    res = auth_client.get("/api/v1/delivery/evidence")
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
    headers = {"X-Forwarded-For": f"10.88.{uuid.uuid4().int % 200}.{uuid.uuid4().int % 200}"}
    payload = {
        "email": unique_email,
        "password": "ValidPassword123!",
        "full_name": "Test User",
    }
    # Register first time
    res1 = client.post("/api/v1/auth/register", json=payload, headers=headers)
    assert res1.status_code == 201

    # Second registration attempt must return generic error without user's email
    res2 = client.post("/api/v1/auth/register", json=payload, headers=headers)
    assert res2.status_code == 400
    detail = res2.json().get("detail", "")
    assert detail == "An account with this email address already exists."
    assert unique_email not in detail
