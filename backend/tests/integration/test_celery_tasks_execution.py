"""Integration tests for Celery task execution, SLA deadline calculations, and background workers.

CRITICAL Item #6:
- scan_commitment_deadlines logic: overdue, at-risk, on-track, already-delivered.
- Boundary condition at exact deadline, timezone-aware vs naive timestamps, and DST day.
- Multi-workspace isolation and idempotency on re-run.

Ingestion & Maintenance Tasks:
- process_transcript_ingestion happy path and LLM failure recovery.
- process_audio_ingestion transcription, candidates persistence, and guaranteed audio file cleanup.
- dispatch_notification_alert Redis publishing.
- cleanup_expired_tokens batched purging.
"""

from datetime import date, datetime, timedelta, timezone
import json
import os
import tempfile
from unittest.mock import MagicMock, patch
import uuid
import pytest
from freezegun import freeze_time
import respx
from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from core.outbox.models import OutboxEvent
from modules.commitments.models import Commitment
from modules.commitments.risk.tasks import scan_commitment_deadlines
from modules.iam.models import RefreshToken, Session as UserSession, User, Workspace
from modules.ingestion.models import IngestionJob
from modules.ingestion.tasks import process_audio_ingestion, process_transcript_ingestion
from modules.notifications.tasks import dispatch_notification_alert
from modules.iam.tasks import cleanup_expired_tokens
from tests.fixtures.database import PostgresTestManager

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _setup_test_db(postgres_manager: PostgresTestManager, monkeypatch: pytest.MonkeyPatch):
    """Ensure database is clean and sync_engine in all task modules points to PostgreSQL."""
    postgres_manager.truncate_all_tables()
    monkeypatch.setattr("core.database.sync_engine", postgres_manager.sync_engine)
    monkeypatch.setattr("modules.commitments.risk.tasks.sync_engine", postgres_manager.sync_engine)
    monkeypatch.setattr("modules.ingestion.tasks.sync_engine", postgres_manager.sync_engine)
    monkeypatch.setattr("modules.iam.tasks.sync_engine", postgres_manager.sync_engine)
    yield
    postgres_manager.truncate_all_tables()


def _create_workspace(session: Session, name: str = "Test WS") -> Workspace:
    ws = Workspace(name=name, slug=f"ws-{uuid.uuid4().hex[:8]}")
    session.add(ws)
    session.flush()
    return ws


# ─────────────────────────────────────────────────────────────────────────────
# 1. CRITICAL Item #6: Deadline & SLA Health Calculations with freezegun
# ─────────────────────────────────────────────────────────────────────────────


@freeze_time("2026-10-15 12:00:00+00:00")
def test_scan_commitment_deadlines_overdue_and_at_risk_transitions(postgres_manager: PostgresTestManager):
    """CRITICAL Item #6: scan_commitment_deadlines accurately transitions overdue (< now)

    and at-risk (< now + 7 days) commitments, and records outbox notification events.
    """
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)

        # 1. Overdue: due 5 days ago
        c_overdue = Commitment(
            workspace_id=ws.id,
            title="Past Due Security Audit",
            customer_name="Acme Corp",
            status="active",
            due_date=now - timedelta(days=5),
        )
        # 2. At-risk: due in 3 days (within 7 day window)
        c_at_risk = Commitment(
            workspace_id=ws.id,
            title="Approaching Cloud Migration",
            customer_name="Beta Inc",
            status="active",
            due_date=now + timedelta(days=3),
        )
        # 3. On-track: due in 20 days (outside 7 day window)
        c_on_track = Commitment(
            workspace_id=ws.id,
            title="Future Feature Delivery",
            customer_name="Gamma LLC",
            status="active",
            due_date=now + timedelta(days=20),
        )
        # 4. Terminal (already delivered): due 10 days ago, must be ignored
        c_delivered = Commitment(
            workspace_id=ws.id,
            title="Completed Scope",
            customer_name="Delta Co",
            status="delivered",
            due_date=now - timedelta(days=10),
        )
        # 5. Terminal (canceled): due 10 days ago, must be ignored
        c_canceled = Commitment(
            workspace_id=ws.id,
            title="Canceled Scope",
            customer_name="Delta Co",
            status="canceled",
            due_date=now - timedelta(days=10),
        )
        session.add_all([c_overdue, c_at_risk, c_on_track, c_delivered, c_canceled])
        session.commit()
        overdue_id = c_overdue.id
        at_risk_id = c_at_risk.id
        on_track_id = c_on_track.id
        delivered_id = c_delivered.id
        canceled_id = c_canceled.id
        ws_id = ws.id

    # Execute risk scan task
    result = scan_commitment_deadlines()

    assert result["status"] == "completed"
    assert result["updated_overdue"] == 1
    assert result["updated_at_risk"] == 1

    with Session(postgres_manager.sync_engine) as session:
        # Check database statuses
        c1 = session.get(Commitment, overdue_id)
        assert c1.status == "overdue"
        assert c1.status_label == "Overdue"
        assert c1.category == "needs-attention"

        c2 = session.get(Commitment, at_risk_id)
        assert c2.status == "at-risk"
        assert c2.status_label == "At risk"
        assert c2.category == "needs-attention"

        c3 = session.get(Commitment, on_track_id)
        assert c3.status == "active"

        c4 = session.get(Commitment, delivered_id)
        assert c4.status == "delivered"

        c5 = session.get(Commitment, canceled_id)
        assert c5.status == "canceled"

        # Check outbox events written
        outbox_rows = session.execute(
            sa_select(OutboxEvent).where(OutboxEvent.workspace_id == ws_id)
        ).scalars().all()
        assert len(outbox_rows) == 2
        event_types = {row.event_type for row in outbox_rows}
        assert "notification.deadline.overdue" in event_types
        assert "notification.deadline.at_risk" in event_types


@freeze_time("2026-10-15 12:00:00+00:00")
def test_scan_commitment_deadlines_boundary_exact_match(postgres_manager: PostgresTestManager):
    """CRITICAL Item #6: Commitment due at exactly the current moment is classified as at-risk."""
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)
        c_exact = Commitment(
            workspace_id=ws.id,
            title="Exact Deadline Delivery",
            customer_name="Acme",
            status="active",
            due_date=now,
        )
        session.add(c_exact)
        session.commit()
        comm_id = c_exact.id

    result = scan_commitment_deadlines()
    assert result["updated_at_risk"] == 1

    with Session(postgres_manager.sync_engine) as session:
        comm = session.get(Commitment, comm_id)
        assert comm.status == "at-risk"


@freeze_time("2026-10-15 12:00:00+00:00")
def test_scan_commitment_deadlines_timezone_aware_and_naive(postgres_manager: PostgresTestManager):
    """CRITICAL Item #6: Correctly handles naive datetimes, non-UTC timezones, and promised_date Date objects."""
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)

        # 1. Naive datetime in the past
        c_naive_past = Commitment(
            workspace_id=ws.id,
            title="Naive Past",
            customer_name="Acme",
            status="active",
            due_date=datetime(2026, 10, 10, 10, 0, 0),  # naive past
        )
        # 2. Offset datetime: 2026-10-15 10:00:00 -04:00 (= 14:00:00 UTC -> in the future by 2 hours) -> at-risk
        edt_tz = timezone(timedelta(hours=-4))
        c_edt_future = Commitment(
            workspace_id=ws.id,
            title="EDT Near Future",
            customer_name="Acme",
            status="active",
            due_date=datetime(2026, 10, 15, 10, 0, 0, tzinfo=edt_tz),
        )
        # 3. Only promised_date (Date column): 2026-10-10 -> past -> overdue
        c_date_past = Commitment(
            workspace_id=ws.id,
            title="Promised Date Past",
            customer_name="Acme",
            status="active",
            due_date=None,
            promised_date=date(2026, 10, 10),
        )
        session.add_all([c_naive_past, c_edt_future, c_date_past])
        session.commit()
        ids = [c_naive_past.id, c_edt_future.id, c_date_past.id]

    result = scan_commitment_deadlines()
    assert result["updated_overdue"] == 2  # c_naive_past and c_date_past
    assert result["updated_at_risk"] == 1   # c_edt_future

    with Session(postgres_manager.sync_engine) as session:
        assert session.get(Commitment, ids[0]).status == "overdue"
        assert session.get(Commitment, ids[1]).status == "at-risk"
        assert session.get(Commitment, ids[2]).status == "overdue"


@freeze_time("2026-03-08 12:00:00+00:00")
def test_scan_commitment_deadlines_dst_transition_day(postgres_manager: PostgresTestManager):
    """CRITICAL Item #6: Correctly handles DST day transition (US Spring Forward day)."""
    now = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)
        c_past = Commitment(
            workspace_id=ws.id,
            title="DST Past",
            customer_name="Acme",
            status="active",
            due_date=now - timedelta(hours=2),
        )
        c_future = Commitment(
            workspace_id=ws.id,
            title="DST Future",
            customer_name="Acme",
            status="active",
            due_date=now + timedelta(days=2),
        )
        session.add_all([c_past, c_future])
        session.commit()

    result = scan_commitment_deadlines()
    assert result["updated_overdue"] == 1
    assert result["updated_at_risk"] == 1


@freeze_time("2026-10-15 12:00:00+00:00")
def test_scan_commitment_deadlines_multitenant_workspace_isolation(postgres_manager: PostgresTestManager):
    """Commitments in different workspaces emit outbox events scoped strictly to their respective workspace."""
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    with Session(postgres_manager.sync_engine) as session:
        ws_a = _create_workspace(session, name="Tenant A")
        ws_b = _create_workspace(session, name="Tenant B")

        c_a = Commitment(
            workspace_id=ws_a.id,
            title="Tenant A Task",
            customer_name="Customer A",
            status="active",
            due_date=now - timedelta(days=1),
        )
        c_b = Commitment(
            workspace_id=ws_b.id,
            title="Tenant B Task",
            customer_name="Customer B",
            status="active",
            due_date=now + timedelta(days=2),
        )
        session.add_all([c_a, c_b])
        session.commit()
        ws_a_id = ws_a.id
        ws_b_id = ws_b.id

    scan_commitment_deadlines()

    with Session(postgres_manager.sync_engine) as session:
        outbox_a = session.execute(
            sa_select(OutboxEvent).where(OutboxEvent.workspace_id == ws_a_id)
        ).scalars().all()
        outbox_b = session.execute(
            sa_select(OutboxEvent).where(OutboxEvent.workspace_id == ws_b_id)
        ).scalars().all()

        assert len(outbox_a) == 1
        assert outbox_a[0].event_type == "notification.deadline.overdue"
        assert outbox_a[0].payload["workspace_id"] == str(ws_a_id)

        assert len(outbox_b) == 1
        assert outbox_b[0].event_type == "notification.deadline.at_risk"
        assert outbox_b[0].payload["workspace_id"] == str(ws_b_id)


@freeze_time("2026-10-15 12:00:00+00:00")
def test_scan_commitment_deadlines_idempotency_on_rerun(postgres_manager: PostgresTestManager):
    """Running scan_commitment_deadlines multiple times consecutively does not duplicate alerts."""
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)
        c1 = Commitment(
            workspace_id=ws.id,
            title="Overdue Item",
            customer_name="Acme",
            status="active",
            due_date=now - timedelta(days=2),
        )
        session.add(c1)
        session.commit()

    # First run: updates status to overdue and writes outbox event
    res1 = scan_commitment_deadlines()
    assert res1["updated_overdue"] == 1

    # Second run immediately following: commitment is already overdue; no updates, no duplicate outbox event
    res2 = scan_commitment_deadlines()
    assert res2["updated_overdue"] == 0
    assert res2["updated_at_risk"] == 0

    with Session(postgres_manager.sync_engine) as session:
        outbox_rows = session.execute(sa_select(OutboxEvent)).scalars().all()
        assert len(outbox_rows) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 2. Ingestion Tasks: Transcript & Audio Ingestion
# ─────────────────────────────────────────────────────────────────────────────


@respx.mock
def test_process_transcript_ingestion_success(postgres_manager: PostgresTestManager):
    """process_transcript_ingestion parses transcript via LLM, persists candidate commitments, and completes job."""
    # Mock LLM API endpoint
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps([
                                {
                                    "title": "Deliver Single Sign-On by Q4",
                                    "customer_name": "Globex",
                                    "promised_by": "2026-12-01",
                                    "confidence": 0.92,
                                    "category": "security",
                                }
                            ])
                        }
                    }
                ]
            },
        )
    )

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)
        job = IngestionJob(
            workspace_id=ws.id,
            job_id=f"job-{uuid.uuid4().hex[:8]}",
            source_type="upload",
            status="pending",
        )
        session.add(job)
        session.commit()
        job_id = job.job_id
        ws_id = ws.id

    result = process_transcript_ingestion(
        job_id=job_id,
        workspace_id=str(ws_id),
        transcript_text="We promise to deliver Single Sign-On by Dec 1st for Globex.",
        customer_name="Globex",
        meeting_title="Q3 Roadmap Sync",
    )

    assert result["status"] == "completed"
    assert result["candidates_extracted"] >= 1

    with Session(postgres_manager.sync_engine) as session:
        db_job = session.execute(
            sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
        ).scalar_one()
        assert db_job.status == "completed"
        assert db_job.candidates_extracted >= 1

        # Check candidate commitment persisted in awaiting-review status
        candidates = session.execute(
            sa_select(Commitment).where(
                Commitment.workspace_id == ws_id,
                Commitment.status == "awaiting-review",
            )
        ).scalars().all()
        assert len(candidates) >= 1
        assert "Single Sign-On" in candidates[0].title


@respx.mock
def test_process_transcript_ingestion_llm_failure_sets_failed_status(postgres_manager: PostgresTestManager):
    """When the LLM API fails, IngestionJob is marked failed with error details and retry is triggered."""
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=respx.MockResponse(500, json={"error": "LLM Service Unavailable"})
    )

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)
        job = IngestionJob(
            workspace_id=ws.id,
            job_id=f"job-{uuid.uuid4().hex[:8]}",
            source_type="upload",
            status="pending",
        )
        session.add(job)
        session.commit()
        job_id = job.job_id
        ws_id = ws.id

    # Running with retry should raise exception
    with pytest.raises(Exception):
        process_transcript_ingestion(
            job_id=job_id,
            workspace_id=str(ws_id),
            transcript_text="Customer commitment text",
        )

    with Session(postgres_manager.sync_engine) as session:
        db_job = session.execute(
            sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
        ).scalar_one()
        assert db_job.status == "failed"
        assert db_job.candidates_json.get("status") == "failed_dead_letter"


@respx.mock
def test_process_audio_ingestion_success_cleans_up_audio_file(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """process_audio_ingestion transcribes audio, persists candidates, and guarantees audio file deletion."""
    monkeypatch.setattr(
        "connectors.speech_to_text.SpeechToTextConnector.transcribe_file_sync",
        lambda self, p: "We commit to deliver API rate limit controls.",
    )
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps([
                                {
                                    "title": "API Rate Limit Controls",
                                    "customer_name": "Initech",
                                    "promised_by": "2026-11-15",
                                    "confidence": 0.90,
                                    "category": "infrastructure",
                                }
                            ])
                        }
                    }
                ]
            },
        )
    )

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)
        job = IngestionJob(
            workspace_id=ws.id,
            job_id=f"audio-job-{uuid.uuid4().hex[:8]}",
            source_type="audio_upload",
            status="pending",
        )
        session.add(job)
        session.commit()
        job_id = job.job_id
        ws_id = ws.id

    # Create temporary audio file on disk
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(b"fake audio stream content")
        tmp_path = tmp.name

    assert os.path.exists(tmp_path)

    try:
        result = process_audio_ingestion(
            job_id=job_id,
            workspace_id=str(ws_id),
            file_path=tmp_path,
            customer_name="Initech",
            meeting_title="Sprint Planning",
        )
        assert result["status"] == "completed"

        # Crucial check: audio file was cleanly unlinked from disk
        assert not os.path.exists(tmp_path), "Audio file was not removed from disk after processing"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    with Session(postgres_manager.sync_engine) as session:
        db_job = session.execute(
            sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
        ).scalar_one()
        assert db_job.status == "completed"
        assert "API rate limit controls" in (db_job.transcript_preview or "")


@respx.mock
def test_process_audio_ingestion_stt_failure_cleans_up_file_and_fails(postgres_manager: PostgresTestManager):
    """When speech-to-text fails, the temporary file is still removed from disk in finally block."""
    respx.post("https://api.groq.com/openai/v1/audio/transcriptions").mock(
        return_value=respx.MockResponse(500, json={"error": "Audio parsing error"})
    )

    with Session(postgres_manager.sync_engine) as session:
        ws = _create_workspace(session)
        job = IngestionJob(
            workspace_id=ws.id,
            job_id=f"audio-job-fail-{uuid.uuid4().hex[:8]}",
            source_type="audio_upload",
            status="pending",
        )
        session.add(job)
        session.commit()
        job_id = job.job_id
        ws_id = ws.id

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"bad audio stream")
        tmp_path = tmp.name

    try:
        with pytest.raises(Exception):
            process_audio_ingestion(
                job_id=job_id,
                workspace_id=str(ws_id),
                file_path=tmp_path,
            )
        # Even on exception, the file must be deleted from disk
        assert not os.path.exists(tmp_path), "Audio file leaked on disk after STT exception"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    with Session(postgres_manager.sync_engine) as session:
        db_job = session.execute(
            sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
        ).scalar_one()
        assert db_job.status == "failed"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Notification & Maintenance Tasks
# ─────────────────────────────────────────────────────────────────────────────


def test_dispatch_notification_alert_publishes_event_sync():
    """dispatch_notification_alert task forwards payload to Redis channel."""
    with patch("modules.notifications.tasks.publish_event_sync") as mock_pub:
        dispatch_notification_alert(
            channel="ws:test-channel:events",
            event_type="TEST_ALERT",
            payload={"message": "hello", "workspace_id": "ws-123"},
        )
        mock_pub.assert_called_once_with(
            "ws:test-channel:events",
            "TEST_ALERT",
            {"message": "hello", "workspace_id": "ws-123"},
        )


def test_cleanup_expired_tokens_batched_deletion(postgres_manager: PostgresTestManager):
    """cleanup_expired_tokens purges tokens and sessions expired > 24 hours ago in batches."""
    from core.security import hash_password, hash_token

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=2)  # expired 2 days ago
    active_date = now + timedelta(days=7)  # valid for 7 more days

    with Session(postgres_manager.sync_engine) as session:
        user = User(
            email=f"celery_cleanup_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password"),
            full_name="Cleanup Celery User",
        )
        session.add(user)
        session.flush()
        user_id = user.id

        # 3 expired tokens, 2 active tokens
        for _ in range(3):
            session.add(
                RefreshToken(
                    user_id=user_id,
                    token_jti=uuid.uuid4().hex,
                    token_hash=hash_token(uuid.uuid4().hex),
                    family_id=uuid.uuid4().hex,
                    expires_at=cutoff,
                )
            )
        for _ in range(2):
            session.add(
                RefreshToken(
                    user_id=user_id,
                    token_jti=uuid.uuid4().hex,
                    token_hash=hash_token(uuid.uuid4().hex),
                    family_id=uuid.uuid4().hex,
                    expires_at=active_date,
                )
            )

        # 2 expired sessions, 1 active session
        for _ in range(2):
            session.add(
                UserSession(
                    user_id=user_id,
                    token_hash=hash_token(uuid.uuid4().hex),
                    expires_at=cutoff,
                )
            )
        session.add(
            UserSession(
                user_id=user_id,
                token_hash=hash_token(uuid.uuid4().hex),
                expires_at=active_date,
            )
        )
        session.commit()

    result = cleanup_expired_tokens()
    assert result["refresh_tokens_deleted"] == 3
    assert result["sessions_deleted"] == 2

    with Session(postgres_manager.sync_engine) as session:
        remaining_tokens = session.execute(
            sa_select(RefreshToken).where(RefreshToken.user_id == user_id)
        ).scalars().all()
        assert len(remaining_tokens) == 2
        for t in remaining_tokens:
            assert t.expires_at > now

        remaining_sessions = session.execute(
            sa_select(UserSession).where(UserSession.user_id == user_id)
        ).scalars().all()
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].expires_at > now
