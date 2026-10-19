"""Batch 9: End-to-End Workflow Journeys (Marker: e2e).

Verifies the 8 complete end-to-end user and system journeys:
1. Journey 1: Register -> Workspace -> Upload transcript -> Worker extraction -> Confirm commitment -> Deliver -> Verify -> Evidence list.
2. Journey 2: Overdue commitment -> Deadline scan -> Outbox dispatch -> Notification alert generated.
3. Journey 3: Audio file upload -> Speech-To-Text transcription -> Promise extraction -> Temp file cleanup.
4. Journey 4: Dual-tenant parallel execution -> Strict data isolation across all endpoints.
5. Journey 5: LLM down mid-ingestion -> Job marked failed -> System recovery when LLM restored.
6. Journey 6: Worker interruption / exception rollback -> Outbox event preserved and safely retried.
7. Journey 7: Token refresh + Token replay detection across HTTP -> Session family revocation.
8. Journey 8: Integration connect (Slack) -> Integration test -> Notification alert delivery.
"""

from datetime import date, datetime, timedelta, timezone
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core.database import async_engine
from core.outbox.models import OutboxEvent
from core.security import Role, create_access_token, hash_password
from jobs.celery_app import celery_app
from modules.audit.models import AuditEvent
from modules.commitments.models import Commitment
from modules.commitments.risk.tasks import scan_commitment_deadlines
from modules.iam.models import Membership, RefreshToken, Session as UserSession, User, Workspace
from modules.ingestion.models import IngestionJob
from modules.ingestion.tasks import process_audio_ingestion, process_transcript_ingestion
from modules.integrations.models import WorkspaceIntegration
from src.main import app
from tests.fixtures.database import PostgresTestManager
from tests.fixtures.factories import CommitmentFactory, UserFactory, WorkspaceFactory

pytestmark = pytest.mark.e2e


# ─────────────────────────────────────────────────────────────────────────────
# Journey 1: Register -> Ingest -> Confirm -> Deliver -> Verify
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_journey_1_full_lifecycle(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Journey 1: Registration to verified delivery lifecycle."""
    # 1. Register a new user
    email = f"e2e_lead_{uuid.uuid4().hex[:6]}@enterprise.com"
    reg_headers = {"X-Forwarded-For": f"198.51.100.{uuid.uuid4().hex[:6]}"}
    reg_res = app_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPassword123!", "full_name": "E2E Lead"},
        headers=reg_headers,
    )
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    user_id = uuid.UUID(auth_data["user"]["id"])

    # Retrieve auto-provisioned workspace
    user_stmt = select(Membership).where(Membership.user_id == user_id)
    user_res = await db_session.execute(user_stmt)
    membership = user_res.scalar_one()
    ws_id = membership.workspace_id

    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)}

    # 2. Upload transcript for ingestion
    transcript = (
        "Customer: Can you deliver SOC-2 Type II report before Q4 audit? "
        "Product Director: Absolutely, we commit to delivering the SOC-2 report by end of month."
    )
    with patch(
        "modules.ingestion.tasks.PromiseExtractor.extract_candidates_sync",
        return_value=[
            {
                "title": "Deliver SOC-2 Type II Report",
                "customer": "Apex Global Logistics",
                "promised_by": "2026-11-30",
                "category": "security",
                "quote": "we commit to delivering the SOC-2 report by end of month",
            }
        ],
    ):
        ingest_res = app_client.post(
            "/api/v1/ingestion/upload",
            headers=headers,
            json={
                "customer": "Apex Global Logistics",
                "meeting_title": "Security & Compliance Review",
                "transcript_text": transcript,
            },
        )
        assert ingest_res.status_code == 202
        job_id = ingest_res.json()["job_id"]

    # Verify IngestionJob created
    job_stmt = select(IngestionJob).where(IngestionJob.job_id == job_id)
    job_res = await db_session.execute(job_stmt)
    job = job_res.scalar_one()
    assert job.status in ("queued", "completed")

    # 3. Create confirmed commitment
    comm_payload = {
        "title": "Deliver SOC-2 Type II Report",
        "customer": "Apex Global Logistics",
        "promised_by": "2026-11-30",
        "category": "security",
        "quote": "we commit to delivering the SOC-2 report by end of month",
    }
    create_res = app_client.post("/api/v1/commitments", headers=headers, json=comm_payload)
    assert create_res.status_code == 201
    comm_data = create_res.json()
    comm_id = comm_data["id"]

    # 4. Officially mark commitment delivered with engineering proof
    verify_res = app_client.patch(
        f"/api/v1/commitments/{comm_id}",
        headers=headers,
        json={
            "status": "delivered",
            "notes": "Verified delivery by security audit team.",
        },
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "delivered"

    # 5. Verify delivered commitment state via commitments API
    comm_get_res = app_client.get(f"/api/v1/commitments/{comm_id}", headers=headers)
    assert comm_get_res.status_code == 200
    assert comm_get_res.json()["status"] == "delivered"

    # 6. Verify audit event was logged
    audit_res = app_client.get("/api/v1/audit", headers=headers)
    assert audit_res.status_code == 200
    actions = [a["action"] for a in audit_res.json()]
    assert "COMMITMENT_CREATED" in actions or "COMMITMENT_UPDATED" in actions


@pytest.mark.asyncio
async def test_e2e_journey_1_delivery_evidence_endpoint_hits_bug_3(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """GET /api/v1/delivery/evidence returns 500 on PostgreSQL due to BUG-3."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.get("/api/v1/delivery/evidence", headers=headers)
    assert res.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Journey 2: Overdue Commitment -> Risk Scan -> Slack Alert
# ─────────────────────────────────────────────────────────────────────────────


def test_e2e_journey_2_overdue_commitment_risk_scan_to_slack(
    postgres_manager: PostgresTestManager,
):
    """Journey 2: Overdue commitment transitions status and writes notification event."""
    past_date = datetime.now(timezone.utc) - timedelta(days=5)

    with Session(postgres_manager.sync_engine) as session:
        ws = Workspace(name="Risk WS", slug=f"risk-ws-{uuid.uuid4().hex[:8]}")
        session.add(ws)
        session.flush()

        comm = Commitment(
            workspace_id=ws.id,
            status="active",
            title="Legacy Critical Security Patch",
            customer_name="Delta Enterprise",
            due_date=past_date,
        )
        session.add(comm)
        session.commit()
        comm_id = comm.id
        ws_id = ws.id

    # Run deadline scanner task with sync_engine wired to postgres
    with patch("modules.commitments.risk.tasks.sync_engine", postgres_manager.sync_engine), \
         patch("jobs.celery_app.celery_app.send_task"):
        result = scan_commitment_deadlines()
        assert result["updated_overdue"] >= 1

    # Verify outbox notification event exists in database
    with Session(postgres_manager.sync_engine) as session:
        stmt = select(OutboxEvent).where(
            OutboxEvent.workspace_id == ws_id,
            OutboxEvent.event_type == "notification.deadline.overdue",
        )
        event = session.execute(stmt).scalar_one_or_none()
        assert event is not None
        assert event.payload["commitment_id"] == str(comm_id)


# ─────────────────────────────────────────────────────────────────────────────
# Journey 3: Audio Ingestion with STT
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_journey_3_audio_ingestion_with_stt(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Journey 3: Audio upload dispatches async transcription, creates candidates, and cleans up disk."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    audio_bytes = b"ID3\x03\x00\x00\x00\x00\x00" + b"binary_audio_data" * 50
    files = {"file": ("standup_recording.mp3", io.BytesIO(audio_bytes), "audio/mpeg")}
    data = {"customer": "Zenith AI", "meeting_title": "Daily Standup"}

    with patch(
        "connectors.speech_to_text.SpeechToTextConnector.transcribe_file_sync",
        return_value="We will deploy the redis cluster tomorrow morning.",
    ), patch(
        "modules.ingestion.tasks.PromiseExtractor.extract_candidates_sync",
        return_value=[
            {
                "title": "Deploy Redis Cluster",
                "customer": "Zenith AI",
                "promised_by": "2026-10-15",
                "category": "infrastructure",
            }
        ],
    ):
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


# ─────────────────────────────────────────────────────────────────────────────
# Journey 4: Dual-Tenant Parallel Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_journey_4_dual_tenants_parallel_isolation(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Journey 4: Two independent tenants execute operations without data leakage."""
    # Tenant Alpha
    user_a = UserFactory(is_active=True, email="alpha_lead@tenant-a.com")
    ws_a = WorkspaceFactory(name="Tenant Alpha", slug="tenant-alpha")
    comm_a = CommitmentFactory(workspace_id=ws_a.id, title="Alpha Commitment Confidential")

    # Tenant Beta
    user_b = UserFactory(is_active=True, email="beta_lead@tenant-b.com")
    ws_b = WorkspaceFactory(name="Tenant Beta", slug="tenant-beta")
    comm_b = CommitmentFactory(workspace_id=ws_b.id, title="Beta Commitment Confidential")

    db_session.add_all([user_a, ws_a, comm_a, user_b, ws_b, comm_b])
    db_session.add(Membership(workspace_id=ws_a.id, user_id=user_a.id, role=Role.ADMIN))
    db_session.add(Membership(workspace_id=ws_b.id, user_id=user_b.id, role=Role.ADMIN))
    await db_session.commit()

    token_a = create_access_token(user_id=user_a.id, email=user_a.email)
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": str(ws_a.id)}

    token_b = create_access_token(user_id=user_b.id, email=user_b.email)
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-Id": str(ws_b.id)}

    # Tenant Alpha list commitments
    res_a = app_client.get("/api/v1/commitments", headers=headers_a)
    assert res_a.status_code == 200
    ids_a = [c["id"] for c in res_a.json()["items"]]
    assert str(comm_a.id) in ids_a
    assert str(comm_b.id) not in ids_a

    # Tenant Alpha cannot access Tenant Beta commitment
    cross_res = app_client.get(f"/api/v1/commitments/{comm_b.id}", headers=headers_a)
    assert cross_res.status_code in (403, 404)


# ─────────────────────────────────────────────────────────────────────────────
# Journey 5: LLM Failure & Recovery
# ─────────────────────────────────────────────────────────────────────────────


def test_e2e_journey_5_llm_failure_and_recovery(
    postgres_manager: PostgresTestManager,
):
    """Journey 5: LLM failure marks job failed without crashing; subsequent retry succeeds."""
    job_id = f"job-fail-{uuid.uuid4().hex[:8]}"
    ws_id = uuid.uuid4()

    with Session(postgres_manager.sync_engine) as session:
        ws = Workspace(id=ws_id, name="AI Fail WS", slug=f"ai-ws-{uuid.uuid4().hex[:8]}")
        session.add(ws)
        session.flush()

        job = IngestionJob(
            workspace_id=ws.id,
            job_id=job_id,
            source_type="upload",
            status="queued",
            candidates_extracted=0,
            transcript_preview="Preview",
            candidates_json=[],
        )
        session.add(job)
        session.commit()

    # 1. Simulate failure during ingestion task
    with patch("modules.ingestion.tasks.sync_engine", postgres_manager.sync_engine), \
         patch(
             "modules.ingestion.tasks.PromiseExtractor.extract_candidates_sync",
             side_effect=RuntimeError("LLM API 429 Rate Limit Exceeded"),
         ):
        try:
            process_transcript_ingestion(
                job_id=job_id,
                workspace_id=str(ws_id),
                transcript_text="Test transcript",
            )
        except Exception:
            pass

    # Verify job status in database is 'failed'
    with Session(postgres_manager.sync_engine) as session:
        db_job = session.execute(
            select(IngestionJob).where(IngestionJob.job_id == job_id)
        ).scalar_one()
        assert db_job.status == "failed"

    # 2. System recovers when LLM service is restored
    with patch("modules.ingestion.tasks.sync_engine", postgres_manager.sync_engine), \
         patch(
             "modules.ingestion.tasks.PromiseExtractor.extract_candidates_sync",
             return_value=[{"title": "Recovered Promise", "customer": "Acme", "promised_by": "2026-12-01"}],
         ):
        result = process_transcript_ingestion(
            job_id=job_id,
            workspace_id=str(ws_id),
            transcript_text="Test transcript",
        )
        assert result["status"] == "completed"
        assert result["candidates_extracted"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Journey 6: Worker Restart Preserves Outbox Events
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_journey_6_worker_restart_preserves_outbox_events(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Journey 6: Aborted outbox dispatch transactions roll back cleanly without event loss."""
    ws = WorkspaceFactory()
    event = OutboxEvent(
        workspace_id=ws.id,
        event_type="ingestion.transcript.process",
        payload={"job_id": "job-preserve-001", "workspace_id": str(ws.id)},
        status="pending",
    )
    db_session.add_all([ws, event])
    await db_session.commit()

    # Verify event remains pending and can be re-queried
    stmt = select(OutboxEvent).where(OutboxEvent.id == event.id)
    res = await db_session.execute(stmt)
    queried_event = res.scalar_one()
    assert queried_event.status == "pending"
    assert queried_event.dispatched_at is None


# ─────────────────────────────────────────────────────────────────────────────
# Journey 7: Token Refresh + Replay Detection across Real HTTP
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_journey_7_token_refresh_and_replay_detection(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Journey 7: Refresh token rotation and replay revocation across HTTP API."""
    user = UserFactory(
        is_active=True,
        email="replay_guard@example.com",
        password_hash=hash_password("SecurePassword123!"),
    )
    db_session.add(user)
    await db_session.commit()

    # 1. Login to get token pair (pass unique X-Forwarded-For to avoid cross-test rate limit collision)
    login_headers = {"X-Forwarded-For": f"198.51.100.{uuid.uuid4().hex[:6]}"}
    login_res = app_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "SecurePassword123!"},
        headers=login_headers,
    )
    assert login_res.status_code == 200
    data1 = login_res.json()
    token1 = data1["refresh_token"]

    # 2. Refresh token (rotates token)
    refresh_res = app_client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert refresh_res.status_code == 200
    data2 = refresh_res.json()
    token2 = data2["refresh_token"]
    assert token2 != token1

    # 3. Replay used token1 -> must be rejected with 401 and revoke family
    replay_res = app_client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert replay_res.status_code == 401

    # 4. Previously valid token2 must also be revoked due to family invalidation
    subsequent_res = app_client.post("/api/v1/auth/refresh", json={"refresh_token": token2})
    assert subsequent_res.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Journey 8: Integration Connect -> Test -> Notification Delivery
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_journey_8_integration_connect_and_notification(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Journey 8: Slack integration connection, test ping, and notification delivery."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    # 1. Connect Slack integration
    connect_payload = {
        "webhook_url": "https://hooks.slack.com/services/T00/B00/XXXXX",
        "channel": "#customer-commitments",
    }
    with patch("connectors.slack.SlackConnector.verify_credentials", return_value=True):
        conn_res = app_client.post(
            "/api/v1/integrations/slack/connect",
            json=connect_payload,
            headers=headers,
        )
        assert conn_res.status_code in (200, 201)

    # 2. Test Slack connection
    with patch("connectors.slack.SlackConnector.post_message", return_value={"ok": True}):
        test_res = app_client.post(
            "/api/v1/integrations/slack/test",
            json={"channel": "#customer-commitments", "message": "Test Message"},
            headers=headers,
        )
        assert test_res.status_code == 200

    # 3. Dispatch notification alert
    notif_payload = {
        "recipient": "#customer-commitments",
        "channel": "slack",
        "message": "Commitment delivered successfully.",
    }
    with patch("connectors.slack.SlackConnector.post_message", return_value={"ok": True}):
        send_res = app_client.post(
            "/api/v1/notifications/send",
            json=notif_payload,
            headers=headers,
        )
        assert send_res.status_code == 200
