"""Unit and contract tests for business logic breakpoint fixes."""

import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from core.database import AsyncSessionLocal
from core.security import create_access_token, Role
from modules.commitments.models import Commitment
from modules.identity.models import User
from modules.workspaces.models import Membership, Workspace
from modules.outbox.models import OutboxEvent
from jobs.tasks import scan_commitment_deadlines


@pytest.mark.asyncio
async def test_google_auth_requires_credential(client: TestClient):
    """Verify that Google authentication rejects requests without a cryptographic credential."""
    # 1. Empty payload
    res = client.post("/api/v1/auth/google", json={})
    assert res.status_code == 400
    assert "Google credential" in res.json().get("detail", "")

    # 2. Email provided without token — must NOT bypass authentication
    res = client.post("/api/v1/auth/google", json={"email": "hacker@example.com"})
    assert res.status_code == 400
    assert "Google credential" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_mcp_tools_authentication_enforced(client: TestClient):
    """Verify that MCP tool discovery and call endpoints reject unauthenticated requests."""
    # Unauthenticated GET /tools
    res = client.get("/api/v1/mcp/tools")
    assert res.status_code == 401

    # Unauthenticated POST /tools/call
    res = client.post(
        "/api/v1/mcp/tools/call",
        json={"name": "list_commitments", "arguments": {}},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_commitment_status_transitions(client: TestClient):
    """Verify that status transitions follow valid state machine and update categories."""
    async with AsyncSessionLocal() as db:
        user = User(email=f"tester_{uuid.uuid4().hex[:6]}@example.com", full_name="Tester", is_active=True)
        ws = Workspace(name="Test Transition WS", slug=f"trans-ws-{uuid.uuid4().hex[:6]}")
        db.add_all([user, ws])
        await db.flush()

        mem = Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN)
        db.add(mem)

        c = Commitment(
            workspace_id=ws.id,
            title="Database Migration Plan",
            customer_name="Alpha Corp",
            owner_name="Tester",
            owner_email=user.email,
            promised_by="Oct 20, 2026",
            status="awaiting-review",
            status_label="Awaiting review",
            category="awaiting-review",
        )
        db.add(c)
        await db.commit()
        await db.refresh(c)
        c_id = c.id

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid transition: awaiting-review -> confirmed
    res = client.patch(f"/api/v1/commitments/{c_id}", json={"status": "confirmed"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"
    assert res.json()["category"] == "on-track"

    # 2. Valid transition: confirmed -> blocked (category -> needs-attention)
    res = client.patch(f"/api/v1/commitments/{c_id}", json={"status": "blocked"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "blocked"
    assert res.json()["category"] == "needs-attention"

    # 3. Valid transition: blocked -> delivered
    res = client.patch(f"/api/v1/commitments/{c_id}", json={"status": "delivered"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "delivered"
    assert res.json()["category"] == "delivered"

    # 4. Invalid transition: delivered -> awaiting-review (terminal state cannot reopen arbitrarily)
    res = client.patch(f"/api/v1/commitments/{c_id}", json={"status": "awaiting-review"}, headers=headers)
    assert res.status_code == 422
    assert "Invalid status transition" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_draft_update_endpoint(client: TestClient):
    """Verify that generate_draft_update produces structured email content."""
    async with AsyncSessionLocal() as db:
        user = User(email=f"drafter_{uuid.uuid4().hex[:6]}@example.com", full_name="Drafter", is_active=True)
        ws = Workspace(name="Draft WS", slug=f"draft-ws-{uuid.uuid4().hex[:6]}")
        db.add_all([user, ws])
        await db.flush()

        mem = Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN)
        db.add(mem)

        c = Commitment(
            workspace_id=ws.id,
            title="Real-time Webhook Pipeline",
            customer_name="Beta Corp",
            owner_name="Drafter",
            owner_email=user.email,
            promised_by="Nov 15, 2026",
            status="confirmed",
            status_label="Confirmed",
            category="on-track",
            engineering_evidence_json={"ticketId": "ENG-500", "targetDelivery": "Nov 15, 2026"},
        )
        db.add(c)
        await db.commit()
        await db.refresh(c)
        c_id = c.id

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(f"/api/v1/commitments/{c_id}/draft-update", json={"recipient_name": "Beta Team"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "subject" in data and len(data["subject"]) > 0
    assert "body" in data and len(data["body"]) > 0
    assert data["target_channel"] == "email"


@pytest.mark.asyncio
async def test_scan_commitment_deadlines_writes_outbox():
    """Verify that scan_commitment_deadlines detects overdue commitments and queues outbox events."""
    async with AsyncSessionLocal() as db:
        ws = Workspace(name="Scan WS", slug=f"scan-ws-{uuid.uuid4().hex[:6]}")
        db.add(ws)
        await db.flush()

        # Commitment with deadline in the past
        past_due = datetime.now(timezone.utc) - timedelta(days=2)
        c = Commitment(
            workspace_id=ws.id,
            title="Overdue Feature Delivery",
            customer_name="Omega Corp",
            owner_name="Dev Lead",
            owner_email="lead@omega.corp",
            promised_by="2 days ago",
            due_date=past_due,
            status="confirmed",
            status_label="Confirmed",
            category="on-track",
        )
        db.add(c)
        await db.commit()
        await db.refresh(c)
        c_id = c.id

    # Run the deadline scan task
    result = scan_commitment_deadlines()
    assert result["status"] == "completed"
    assert result["updated_overdue"] >= 1

    # Verify commitment is now overdue and outbox has a pending notification event
    async with AsyncSessionLocal() as db:
        updated_c = await db.get(Commitment, c_id)
        assert updated_c.status == "overdue"
        assert updated_c.category == "needs-attention"

        from sqlalchemy import select
        outbox_stmt = select(OutboxEvent).where(
            OutboxEvent.workspace_id == ws.id,
            OutboxEvent.event_type == "notification.deadline.overdue",
        )
        res = await db.execute(outbox_stmt)
        events = res.scalars().all()
        assert len(events) >= 1
        ev = events[0]
        assert ev.status == "pending"
        assert ev.payload.get("commitment_id") == str(c_id)
