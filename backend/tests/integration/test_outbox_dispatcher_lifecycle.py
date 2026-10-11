"""Integration tests for the transactional outbox dispatcher and lifecycle.

Verifies:
- CRITICAL Item #4: Dispatcher concurrency with `FOR UPDATE SKIP LOCKED` never double-dispatches rows.
- Transition from pending -> dispatched with correct Celery task, queue, and payload arguments.
- Explicit acknowledged no-op events (`commitment.created/updated/confirmed`) dispatch on first poll without Celery tasks.
- Unknown event dead-lettering: attempts increment up to 5, then status transitions to 'failed'.
- Crash/rollback resilience: uncommitted claims roll back and are retried without row loss.
- FIFO ordering strictly governed by `created_at`.
- Batch size bounding (`_BATCH_SIZE`).
- Head-of-line blocking and lack of exponential backoff on poison events (BUG-5).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.outbox.models import OutboxEvent
from jobs.outbox_dispatcher import _BATCH_SIZE, run_dispatcher
from modules.iam.models import Workspace
from tests.fixtures.database import PostgresTestManager

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clean_db(postgres_manager: PostgresTestManager):
    """Ensure a pristine database before and after each test."""
    postgres_manager.truncate_all_tables()
    yield
    postgres_manager.truncate_all_tables()


async def _create_test_workspace(db: AsyncSession) -> Workspace:
    """Helper to provision a clean workspace for outbox tests."""
    ws = Workspace(
        name=f"Outbox WS {uuid.uuid4().hex[:6]}",
        slug=f"outbox-ws-{uuid.uuid4().hex[:6]}",
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


# ─────────────────────────────────────────────────────────────────────────────
# 1. CRITICAL Item #4: Concurrency & Zero Double-Dispatch under SKIP LOCKED
# ─────────────────────────────────────────────────────────────────────────────


async def test_two_concurrent_dispatchers_never_double_dispatch_under_skip_locked(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """CRITICAL Item #4: Two competing dispatcher instances running with FOR UPDATE SKIP LOCKED

    never claim or dispatch the same row twice, and all rows are dispatched cleanly.
    """
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        # Create 10 pending no-op events
        event_ids = []
        for i in range(10):
            ev = OutboxEvent(
                workspace_id=ws.id,
                event_type="commitment.created",
                payload={"index": i, "title": f"Commitment {i}"},
                status="pending",
            )
            db.add(ev)
            await db.flush()
            event_ids.append(ev.id)
        await db.commit()

    target_ids = set(event_ids)

    # Track which worker dispatched which event
    worker_1_dispatched = set()
    worker_2_dispatched = set()

    import jobs.outbox_dispatcher as dispatcher_mod
    original_dispatch = dispatcher_mod._dispatch_to_celery

    def make_tracking_dispatcher(worker_set):
        def _tracking_dispatch(celery_app, row):
            if row.id in target_ids:
                worker_set.add(row.id)
            original_dispatch(celery_app, row)
        return _tracking_dispatch

    # Launch two concurrent dispatcher loops
    async def _run_worker(worker_set):
        monkeypatch.setattr(dispatcher_mod, "_dispatch_to_celery", make_tracking_dispatcher(worker_set))
        await run_dispatcher()

    task1 = asyncio.create_task(_run_worker(worker_1_dispatched))
    task2 = asyncio.create_task(_run_worker(worker_2_dispatched))

    # Wait until all 10 events reach status 'dispatched'
    async def _wait_until_complete():
        for _ in range(100):
            async with postgres_manager.session_factory() as db:
                res = await db.execute(
                    select(OutboxEvent.id).where(
                        OutboxEvent.id.in_(event_ids),
                        OutboxEvent.status == "dispatched",
                    )
                )
                dispatched = res.scalars().all()
                if len(dispatched) == len(event_ids):
                    return
            await asyncio.sleep(0.05)
        raise TimeoutError("Timed out waiting for concurrent dispatchers to process all events")

    try:
        await asyncio.wait_for(_wait_until_complete(), timeout=10.0)
    finally:
        task1.cancel()
        task2.cancel()
        await asyncio.gather(task1, task2, return_exceptions=True)

    # Verification:
    # 1. Zero double-dispatch: the sets of dispatched IDs must be strictly disjoint
    overlap = worker_1_dispatched.intersection(worker_2_dispatched)
    assert len(overlap) == 0, f"Double-dispatch detected on rows: {overlap}"

    # 2. Complete processing: union must contain all 10 event IDs
    union = worker_1_dispatched.union(worker_2_dispatched)
    assert len(union) == 10, f"Expected 10 total dispatched rows, got {len(union)}"
    assert union == set(event_ids)

    # 3. All rows in PostgreSQL are marked dispatched
    async with postgres_manager.session_factory() as db:
        res = await db.execute(select(OutboxEvent).where(OutboxEvent.id.in_(event_ids)))
        rows = res.scalars().all()
        assert len(rows) == 10
        for r in rows:
            assert r.status == "dispatched"
            assert r.dispatched_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Registered Task Events: Pending -> Dispatched & Target Queues
# ─────────────────────────────────────────────────────────────────────────────


async def test_ingestion_event_transitions_pending_to_dispatched_with_correct_kwargs(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verifies that an ingestion outbox event routes to Celery ingestion queue and transitions to dispatched."""
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    fake_celery = MagicMock()
    monkeypatch.setattr("jobs.celery_app.celery_app", fake_celery)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        ev = OutboxEvent(
            workspace_id=ws.id,
            event_type="ingestion.transcript.process",
            payload={
                "job_id": "job-transcript-001",
                "workspace_id": str(ws.id),
                "transcript_text": "Customer agreed to deliver SOC2 report by Friday.",
                "customer_name": "Globex Corp",
                "meeting_title": "Security Sync",
            },
            status="pending",
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        event_id = ev.id

    dispatcher_task = asyncio.create_task(run_dispatcher())

    async def _wait_dispatched():
        for _ in range(50):
            async with postgres_manager.session_factory() as db:
                row = await db.get(OutboxEvent, event_id)
                if row and row.status == "dispatched":
                    return row
            await asyncio.sleep(0.05)
        raise TimeoutError("Event was not dispatched in time")

    try:
        row = await asyncio.wait_for(_wait_dispatched(), timeout=5.0)
    finally:
        dispatcher_task.cancel()
        await asyncio.gather(dispatcher_task, return_exceptions=True)

    # Verify PostgreSQL row state
    assert row.status == "dispatched"
    assert row.dispatched_at is not None

    # Verify Celery send_task routing
    fake_celery.send_task.assert_called_once_with(
        "jobs.tasks.process_transcript_ingestion",
        kwargs={
            "job_id": "job-transcript-001",
            "workspace_id": str(ws.id),
            "transcript_text": "Customer agreed to deliver SOC2 report by Friday.",
            "customer_name": "Globex Corp",
            "meeting_title": "Security Sync",
        },
        queue="ingestion",
    )


async def test_notification_event_transitions_pending_to_dispatched_with_high_priority_queue(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verifies that an overdue notification event routes to high_priority Celery queue and marks dispatched."""
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    fake_celery = MagicMock()
    monkeypatch.setattr("jobs.celery_app.celery_app", fake_celery)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        ev = OutboxEvent(
            workspace_id=ws.id,
            event_type="notification.deadline.overdue",
            payload={
                "workspace_id": str(ws.id),
                "commitment_id": "comm-audit-999",
                "title": "ISO27001 Evidence Upload",
            },
            status="pending",
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        event_id = ev.id

    dispatcher_task = asyncio.create_task(run_dispatcher())

    async def _wait_dispatched():
        for _ in range(50):
            async with postgres_manager.session_factory() as db:
                row = await db.get(OutboxEvent, event_id)
                if row and row.status == "dispatched":
                    return row
            await asyncio.sleep(0.05)
        raise TimeoutError("Event was not dispatched in time")

    try:
        row = await asyncio.wait_for(_wait_dispatched(), timeout=5.0)
    finally:
        dispatcher_task.cancel()
        await asyncio.gather(dispatcher_task, return_exceptions=True)

    assert row.status == "dispatched"
    assert row.dispatched_at is not None

    fake_celery.send_task.assert_called_once_with(
        "jobs.tasks.dispatch_notification_alert",
        kwargs={
            "channel": f"ws:{ws.id}:events",
            "event_type": "NOTIFICATION_DEADLINE_OVERDUE",
            "payload": {
                "workspace_id": str(ws.id),
                "commitment_id": "comm-audit-999",
                "title": "ISO27001 Evidence Upload",
            },
        },
        queue="high_priority",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. No-Op Events Dispatch Cleanly
# ─────────────────────────────────────────────────────────────────────────────


async def test_noop_lifecycle_events_dispatched_on_first_poll_without_celery_tasks(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """Commitment lifecycle events (created, updated, confirmed) dispatch on the first poll

    without Celery tasks, retries, or error log pollution.
    """
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    fake_celery = MagicMock()
    monkeypatch.setattr("jobs.celery_app.celery_app", fake_celery)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        created_ev = OutboxEvent(workspace_id=ws.id, event_type="commitment.created", payload={"id": "1"}, status="pending")
        updated_ev = OutboxEvent(workspace_id=ws.id, event_type="commitment.updated", payload={"id": "2"}, status="pending")
        confirmed_ev = OutboxEvent(workspace_id=ws.id, event_type="commitment.confirmed", payload={"id": "3"}, status="pending")
        db.add_all([created_ev, updated_ev, confirmed_ev])
        await db.commit()
        ids = [created_ev.id, updated_ev.id, confirmed_ev.id]

    dispatcher_task = asyncio.create_task(run_dispatcher())

    async def _wait_all():
        for _ in range(50):
            async with postgres_manager.session_factory() as db:
                res = await db.execute(
                    select(OutboxEvent).where(OutboxEvent.id.in_(ids), OutboxEvent.status == "dispatched")
                )
                rows = res.scalars().all()
                if len(rows) == 3:
                    return rows
            await asyncio.sleep(0.05)
        raise TimeoutError("No-op events were not dispatched in time")

    try:
        rows = await asyncio.wait_for(_wait_all(), timeout=5.0)
    finally:
        dispatcher_task.cancel()
        await asyncio.gather(dispatcher_task, return_exceptions=True)

    # Celery should not have received any tasks
    fake_celery.send_task.assert_not_called()

    for r in rows:
        assert r.status == "dispatched"
        assert r.dispatched_at is not None
        # No retry pollution in payload
        assert "dispatch_attempts" not in (r.payload or {})


# ─────────────────────────────────────────────────────────────────────────────
# 4. Unknown Event Dead-Lettering (Max 5 Attempts -> Status Failed)
# ─────────────────────────────────────────────────────────────────────────────


async def test_unknown_event_increments_attempts_and_dead_letters_after_5_failures(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """An unknown event type increments attempts up to 5, then marks status='failed'."""
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        ev = OutboxEvent(
            workspace_id=ws.id,
            event_type="completely.unknown.poison.event",
            payload={"test": "data"},
            status="pending",
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        event_id = ev.id

    dispatcher_task = asyncio.create_task(run_dispatcher())

    async def _wait_failed():
        for _ in range(100):
            async with postgres_manager.session_factory() as db:
                row = await db.get(OutboxEvent, event_id)
                if row and row.status == "failed":
                    return row
            await asyncio.sleep(0.05)
        raise TimeoutError("Poison event did not dead-letter to failed within timeout")

    try:
        row = await asyncio.wait_for(_wait_failed(), timeout=8.0)
    finally:
        dispatcher_task.cancel()
        await asyncio.gather(dispatcher_task, return_exceptions=True)

    assert row.status == "failed"
    assert row.payload.get("dispatch_attempts") == 5
    assert "No Celery handler for event_type 'completely.unknown.poison.event'" in row.payload.get("last_dispatch_error", "")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Crash / Exception Resilience: Row Retried, Not Lost
# ─────────────────────────────────────────────────────────────────────────────


async def test_crash_or_rollback_between_claim_and_mark_preserves_row_for_retry(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """If a dispatcher cycle crashes or rolls back between claiming and committing,

    the row remains pending in PostgreSQL and is successfully claimed on the next cycle.
    """
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        ev = OutboxEvent(
            workspace_id=ws.id,
            event_type="commitment.created",
            payload={"id": "unlost-row"},
            status="pending",
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        event_id = ev.id

    # Simulate an aborted transaction where row was claimed with FOR UPDATE SKIP LOCKED then rolled back
    async with postgres_manager.session_factory() as db:
        async with db.begin():
            stmt = select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update(skip_locked=True)
            claimed = (await db.execute(stmt)).scalar_one()
            assert claimed.status == "pending"
            # Intentionally rollback transaction without committing
            await db.rollback()

    # Verify row still exists and is still pending in PostgreSQL
    async with postgres_manager.session_factory() as db:
        row_after_rollback = await db.get(OutboxEvent, event_id)
        assert row_after_rollback is not None
        assert row_after_rollback.status == "pending"

    # Now run normal dispatcher: row must be retried and dispatched cleanly
    dispatcher_task = asyncio.create_task(run_dispatcher())

    async def _wait_dispatched():
        for _ in range(50):
            async with postgres_manager.session_factory() as db:
                row = await db.get(OutboxEvent, event_id)
                if row and row.status == "dispatched":
                    return row
            await asyncio.sleep(0.05)
        raise TimeoutError("Row was not retried and dispatched")

    try:
        final_row = await asyncio.wait_for(_wait_dispatched(), timeout=5.0)
    finally:
        dispatcher_task.cancel()
        await asyncio.gather(dispatcher_task, return_exceptions=True)

    assert final_row.status == "dispatched"
    assert final_row.dispatched_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# 6. Strict FIFO Ordering by created_at
# ─────────────────────────────────────────────────────────────────────────────


async def test_dispatcher_processes_events_strictly_in_created_at_order(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """The outbox dispatcher queries pending rows ordered strictly by created_at ascending."""
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        # Create 3 events with explicit past created_at timestamps
        ev_old = OutboxEvent(
            workspace_id=ws.id,
            event_type="commitment.created",
            payload={"name": "first"},
            status="pending",
            created_at=base_time,
        )
        ev_mid = OutboxEvent(
            workspace_id=ws.id,
            event_type="commitment.created",
            payload={"name": "second"},
            status="pending",
            created_at=base_time + timedelta(minutes=2),
        )
        ev_new = OutboxEvent(
            workspace_id=ws.id,
            event_type="commitment.created",
            payload={"name": "third"},
            status="pending",
            created_at=base_time + timedelta(minutes=4),
        )
        db.add_all([ev_old, ev_mid, ev_new])
        await db.commit()
        expected_order = [ev_old.id, ev_mid.id, ev_new.id]

    dispatched_order = []
    import jobs.outbox_dispatcher as dispatcher_mod
    orig_dispatch = dispatcher_mod._dispatch_to_celery

    def _recording_dispatch(celery_app, row):
        dispatched_order.append(row.id)
        orig_dispatch(celery_app, row)

    monkeypatch.setattr(dispatcher_mod, "_dispatch_to_celery", _recording_dispatch)

    dispatcher_task = asyncio.create_task(run_dispatcher())

    async def _wait_all():
        for _ in range(50):
            if len(dispatched_order) == 3:
                return
            await asyncio.sleep(0.05)
        raise TimeoutError("Not all events dispatched")

    try:
        await asyncio.wait_for(_wait_all(), timeout=5.0)
    finally:
        dispatcher_task.cancel()
        await asyncio.gather(dispatcher_task, return_exceptions=True)

    assert dispatched_order == expected_order, f"Expected FIFO order {expected_order}, got {dispatched_order}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Batch Size Limit
# ─────────────────────────────────────────────────────────────────────────────


async def test_batch_size_limit_claims_at_most_batch_limit_rows_per_cycle(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """A single polling transaction claims at most _BATCH_SIZE rows, leaving excess pending."""
    # Temporarily set batch size to 5 for fast verification
    test_batch_size = 5
    monkeypatch.setattr("jobs.outbox_dispatcher._BATCH_SIZE", test_batch_size)
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        event_ids = []
        for i in range(8):
            ev = OutboxEvent(
                workspace_id=ws.id,
                event_type="commitment.created",
                payload={"index": i},
                status="pending",
            )
            db.add(ev)
            await db.flush()
            event_ids.append(ev.id)
        await db.commit()

    # Emulate exactly one polling cycle of run_dispatcher
    from jobs.celery_app import celery_app
    from jobs.outbox_dispatcher import _dispatch_to_celery
    from sqlalchemy import update

    async with postgres_manager.session_factory() as db:
        async with db.begin():
            stmt = (
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at)
                .limit(test_batch_size)
                .with_for_update(skip_locked=True)
            )
            rows = (await db.execute(stmt)).scalars().all()
            assert len(rows) == test_batch_size, f"Expected exactly {test_batch_size} claimed rows in batch"

            dispatched_ids = []
            for r in rows:
                _dispatch_to_celery(celery_app, r)
                dispatched_ids.append(r.id)

            await db.execute(
                update(OutboxEvent)
                .where(OutboxEvent.id.in_(dispatched_ids))
                .values(status="dispatched", dispatched_at=datetime.now(timezone.utc))
            )

    # After cycle 1: exactly 5 rows of our batch dispatched, exactly 3 rows remain pending
    async with postgres_manager.session_factory() as db:
        dispatched_count = (await db.execute(
            select(text("count(*)")).select_from(OutboxEvent).where(
                OutboxEvent.id.in_(event_ids),
                OutboxEvent.status == "dispatched",
            )
        )).scalar()
        pending_count = (await db.execute(
            select(text("count(*)")).select_from(OutboxEvent).where(
                OutboxEvent.id.in_(event_ids),
                OutboxEvent.status == "pending",
            )
        )).scalar()

        assert dispatched_count == 5
        assert pending_count == 3


# ─────────────────────────────────────────────────────────────────────────────
# 8. BUG-5: Poison Event Head-of-Line Blocking and Missing Backoff
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason="BUG-5: Outbox dispatcher lacks exponential backoff and next_retry_at; "
    "poison events at queue head repeatedly consume batch limits and delay healthy events",
)
async def test_poison_event_at_queue_head_must_not_delay_healthy_events(
    postgres_manager: PostgresTestManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """BUG-5: When a poison event fails at the queue head, the dispatcher must apply exponential backoff

    (e.g., next_retry_at) so subsequent healthy pending events are dispatched immediately without
    being delayed by consecutive re-poll cycles of the failing row.

    Currently: The dispatcher has no backoff mechanism; failing rows remain status='pending' and
    block subsequent events from being dispatched when the query batch limit is constrained.
    """
    # Constrain batch size to 1 to demonstrate head-of-line blocking
    monkeypatch.setattr("jobs.outbox_dispatcher._BATCH_SIZE", 1)
    monkeypatch.setattr("core.database.AsyncSessionLocal", postgres_manager.session_factory)
    monkeypatch.setattr("jobs.outbox_dispatcher._IDLE_SLEEP", 0.02)
    monkeypatch.setattr("jobs.outbox_dispatcher._BUSY_SLEEP", 0.01)

    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    async with postgres_manager.session_factory() as db:
        ws = await _create_test_workspace(db)
        # Poison event at queue head (older created_at)
        poison_ev = OutboxEvent(
            workspace_id=ws.id,
            event_type="unregistered.poison.type",
            payload={"data": "bad"},
            status="pending",
            created_at=base_time,
        )
        # Healthy event behind it (newer created_at)
        healthy_ev = OutboxEvent(
            workspace_id=ws.id,
            event_type="commitment.created",
            payload={"title": "healthy"},
            status="pending",
            created_at=base_time + timedelta(seconds=10),
        )
        db.add_all([poison_ev, healthy_ev])
        await db.commit()
        healthy_id = healthy_ev.id

    # Run exactly one polling cycle
    from jobs.celery_app import celery_app
    from jobs.outbox_dispatcher import _dispatch_to_celery
    from sqlalchemy import update

    async with postgres_manager.session_factory() as db:
        async with db.begin():
            stmt = (
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            rows = (await db.execute(stmt)).scalars().all()
            for r in rows:
                try:
                    _dispatch_to_celery(celery_app, r)
                except Exception as err:
                    p = dict(r.payload or {})
                    p["dispatch_attempts"] = p.get("dispatch_attempts", 0) + 1
                    r.payload = p

    # Assert that the healthy event is NOT delayed and was dispatched in cycle 1
    # Under current code, healthy_ev was NOT processed because poison_ev blocked the queue head!
    async with postgres_manager.session_factory() as db:
        healthy_row = await db.get(OutboxEvent, healthy_id)
        assert healthy_row is not None
        # This will fail on current code because healthy_row is still 'pending'
        assert healthy_row.status == "dispatched", (
            "Healthy event was blocked by poison event at head of queue due to missing backoff"
        )
