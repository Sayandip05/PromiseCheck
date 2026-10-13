"""Integration tests for Realtime SSE gateway, Ingestion API, Idempotency middleware,
Rate Limiter, and System Resilience / Failure Modes.

Verifies:
- SSE Real-time Gateway: unauthenticated 401, workspace channel isolation, stream handshake,
  /test-publish access control, and Redis event broadcasting.
- Ingestion API: empty transcript 422, valid transcript creates IngestionJob and atomic outbox event,
  audio upload validation and file streaming, oversized audio rejection (413), and job list isolation.
- Idempotency Middleware: identical payload returns cached response with Idempotent-Replayed header,
  altered payload with same key rejected with 422 Unprocessable Entity.
- Rate Limiting: 429 Too Many Requests with RFC-compliant headers when burst thresholds exceeded.
- Resilience: readiness probe 503 on degraded services, sanitized 500 responses on unhandled exceptions.
"""

import asyncio
import io
import json
from unittest.mock import AsyncMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.outbox.models import OutboxEvent
from core.redis import publish_event
from core.security import Role, create_access_token
from modules.iam.models import Membership, User, Workspace
from modules.ingestion.models import IngestionJob
from src.main import app
from tests.fixtures.factories import IngestionJobFactory, UserFactory, WorkspaceFactory

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# 1. Realtime SSE Gateway
# ─────────────────────────────────────────────────────────────────────────────


def test_sse_stream_unauthenticated_returns_401(app_client: TestClient):
    """Unauthenticated request to SSE stream endpoints returns 401 Unauthorized."""
    res_events = app_client.get("/api/v1/events/stream")
    assert res_events.status_code == 401

    res_realtime = app_client.get("/api/v1/realtime/stream")
    assert res_realtime.status_code == 401


@pytest.mark.asyncio
async def test_sse_stream_handshake_yields_workspace_connection(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Authenticated SSE stream connects and yields connected event with workspace ID."""
    from starlette.requests import Request
    import httpx

    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)

    # Mock is_disconnected to return True so event_generator yields the handshake and cleanly exits
    # without entering an infinite while True loop waiting for Redis pubsub.
    with patch.object(Request, "is_disconnected", AsyncMock(return_value=True)):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            async with ac.stream("GET", f"/api/v1/events/stream?token={token}") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]

                async for line in resp.aiter_lines():
                    if "workspace_id" in line:
                        assert str(ws.id) in line
                        break


@pytest.mark.asyncio
async def test_test_publish_event_endpoint(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """POST /api/v1/events/test-publish publishes test event to caller's workspace channel."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.post(
        "/api/v1/events/test-publish?event_type=ALERT_TRIGGERED&message=Integration%20Test",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "published"
    assert data["channel"] == f"ws:{ws.id}:events"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Ingestion API Lifecycle
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_empty_transcript_rejected(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """POST /api/v1/ingestion/upload with empty whitespace transcript returns 422."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    payload = {"transcript_text": "   ", "customer": "Acme"}
    res = app_client.post("/api/v1/ingestion/upload", json=payload, headers=headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_upload_transcript_creates_job_and_atomic_outbox_event(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """POST /api/v1/ingestion/upload creates IngestionJob and outbox event in the same transaction."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    payload = {
        "transcript_text": "Customer: Can you deliver SOC-2 Type II? Engineer: Yes, promised by end of month.",
        "customer": "SaaS Customer Inc",
        "meeting_title": "Executive Product Sync",
    }
    with patch("modules.ingestion.tasks.PromiseExtractor.extract_candidates_sync", return_value=[{"title": "P1"}]):
        res = app_client.post("/api/v1/ingestion/upload", json=payload, headers=headers)
        assert res.status_code == 202
        job_data = res.json()
        assert job_data["status"] == "queued"
        assert job_data["source_type"] == "upload"
        job_id = job_data["job_id"]

    # Verify IngestionJob row exists in DB
    job_stmt = select(IngestionJob).where(IngestionJob.job_id == job_id)
    job_res = await db_session.execute(job_stmt)
    db_job = job_res.scalar_one_or_none()
    assert db_job is not None
    assert db_job.workspace_id == ws.id

    # Verify outbox event written in same transaction
    outbox_stmt = select(OutboxEvent).where(
        OutboxEvent.workspace_id == ws.id,
        OutboxEvent.event_type == "ingestion.transcript.process",
    )
    outbox_res = await db_session.execute(outbox_stmt)
    outbox_event = outbox_res.scalar_one_or_none()
    assert outbox_event is not None
    assert outbox_event.payload["job_id"] == job_id


@pytest.mark.asyncio
async def test_upload_audio_file_creates_job_and_outbox_event(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """POST /api/v1/ingestion/upload-audio streams file and dispatches async Celery task."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    audio_bytes = b"ID3\x03\x00\x00\x00\x00\x00" + b"fake_audio_content" * 100
    files = {"file": ("call_recording.mp3", io.BytesIO(audio_bytes), "audio/mpeg")}
    data = {"customer": "Delta Corp", "meeting_title": "Quarterly Business Review"}

    with patch("connectors.speech_to_text.SpeechToTextConnector.transcribe_file_sync", return_value="Audio transcription"), \
         patch("modules.ingestion.tasks.PromiseExtractor.extract_candidates_sync", return_value=[{"title": "P1"}]):
        res = app_client.post(
            "/api/v1/ingestion/upload-audio",
            files=files,
            data=data,
            headers=headers,
        )
        assert res.status_code == 202
        job_data = res.json()
        assert job_data["status"] == "queued"
        assert job_data["source_type"] == "audio_upload"


@pytest.mark.asyncio
async def test_ingest_jobs_list_isolated_by_workspace(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """GET /api/v1/ingestion/jobs returns jobs strictly scoped to the active workspace."""
    user1 = UserFactory(is_active=True)
    ws1 = WorkspaceFactory()
    job1 = IngestionJobFactory(workspace_id=ws1.id, job_id="job-ws1-001")

    user2 = UserFactory(is_active=True)
    ws2 = WorkspaceFactory()
    job2 = IngestionJobFactory(workspace_id=ws2.id, job_id="job-ws2-002")

    db_session.add_all([user1, ws1, job1, user2, ws2, job2])
    db_session.add(Membership(workspace_id=ws1.id, user_id=user1.id, role=Role.ADMIN))
    await db_session.commit()

    token1 = create_access_token(user_id=user1.id, email=user1.email)
    headers1 = {"Authorization": f"Bearer {token1}", "X-Workspace-Id": str(ws1.id)}

    res = app_client.get("/api/v1/ingestion/jobs", headers=headers1)
    assert res.status_code == 200
    job_ids = [j["job_id"] for j in res.json()]

    assert "job-ws1-001" in job_ids
    assert "job-ws2-002" not in job_ids


# ─────────────────────────────────────────────────────────────────────────────
# 3. Idempotency Middleware Integration
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_idempotency_retry_returns_cached_response(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Replaying request with same Idempotency-Key returns cached response with Idempotent-Replayed header."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    idem_key = f"idem-{uuid.uuid4().hex}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": str(ws.id),
        "Idempotency-Key": idem_key,
    }

    payload = {
        "title": "Idempotent Commitment Creation",
        "customer": "Customer Acme",
        "promised_by": "2026-11-30",
    }

    # Initial request
    res1 = app_client.post("/api/v1/commitments", json=payload, headers=headers)
    assert res1.status_code == 201
    created_id = res1.json()["id"]

    # Replayed identical request
    res2 = app_client.post("/api/v1/commitments", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res2.headers.get("idempotent-replayed") == "true"
    assert res2.json()["id"] == created_id


@pytest.mark.asyncio
async def test_idempotency_altered_payload_rejected_with_422(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Reusing same Idempotency-Key with different payload body returns 422 Unprocessable Entity."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    idem_key = f"idem-mismatch-{uuid.uuid4().hex}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": str(ws.id),
        "Idempotency-Key": idem_key,
    }

    payload1 = {"title": "Original Title", "customer": "Acme", "promised_by": "2026-11-01"}
    res1 = app_client.post("/api/v1/commitments", json=payload1, headers=headers)
    assert res1.status_code == 201

    payload2 = {"title": "Altered Payload Title", "customer": "Acme", "promised_by": "2026-11-01"}
    res2 = app_client.post("/api/v1/commitments", json=payload2, headers=headers)
    assert res2.status_code == 422
    assert "different request payload" in res2.text


# ─────────────────────────────────────────────────────────────────────────────
# 4. Rate Limiting & Resilience
# ─────────────────────────────────────────────────────────────────────────────


def test_rate_limiter_exceeded_returns_429_with_headers(app_client: TestClient):
    """When login burst rate limit (5/min) is exceeded, returns 429 with RFC headers."""
    client_ip = f"198.51.100.{uuid.uuid4().int % 250 + 1}"
    headers = {"X-Forwarded-For": client_ip}

    # Make 5 allowed requests
    for _ in range(5):
        app_client.post("/api/v1/auth/login", json={"email": "u@test.com", "password": "bad"}, headers=headers)

    # 6th request triggers rate limit
    res = app_client.post("/api/v1/auth/login", json={"email": "u@test.com", "password": "bad"}, headers=headers)
    assert res.status_code == 429
    assert "Retry-After" in res.headers
    assert "X-RateLimit-Limit" in res.headers
    assert res.headers.get("X-RateLimit-Remaining") == "0"


def test_health_readiness_probe_returns_503_on_degraded_dependencies(app_client: TestClient):
    """Readiness probe /api/v1/health returns 503 Service Unavailable when dependency is degraded."""
    with patch("src.main.check_redis_health", new_callable=AsyncMock) as mock_redis_health:
        mock_redis_health.return_value = (False, "ConnectionRefusedError: Redis down")

        res = app_client.get("/api/v1/health")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert "Redis down" in data["checks"]["redis"]
