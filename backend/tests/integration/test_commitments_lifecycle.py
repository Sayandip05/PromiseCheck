"""Integration tests for commitments lifecycle: atomic same-transaction outbox write (CRITICAL),
audit logging, state machine transitions, pagination, filtering, attention list, and customer SLA health calculations.
"""

from datetime import datetime, date, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.outbox.models import OutboxEvent
from modules.audit.models import AuditEvent
from modules.commitments.models import Commitment
from modules.commitments.schemas import CommitmentCreateRequest, CommitmentUpdateRequest
from modules.commitments.service import CommitmentService
from modules.customers.models import Customer
from modules.customers.service import CustomerService
from tests.fixtures.factories import CommitmentFactory, CustomerFactory, UserFactory, WorkspaceFactory

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# 1. CRITICAL Item #3: Same-Transaction Outbox Write
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_commitment_writes_outbox_event_in_same_transaction(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """CRITICAL Item #3: Creating a commitment writes an outbox_events row atomically in the same transaction."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    payload = {
        "title": "Deliver SAML SSO integration",
        "customer": "Enterprise Alpha Corp",
        "promised_by": "Q4 2026",
    }
    res = app_client.post("/api/v1/commitments", json=payload, headers=headers)
    assert res.status_code == 201
    comm_id = res.json()["id"]

    # Verify outbox event exists in PostgreSQL
    outbox_stmt = select(OutboxEvent).where(
        OutboxEvent.workspace_id == ws.id,
        OutboxEvent.event_type == "commitment.created",
    )
    outbox_res = await db_session.execute(outbox_stmt)
    event = outbox_res.scalar_one_or_none()

    assert event is not None, "outbox_events row must be created in the same transaction"
    assert event.status == "pending"
    assert event.payload["id"] == comm_id
    assert event.payload["title"] == payload["title"]
    assert event.payload["customer"] == payload["customer"]


@pytest.mark.asyncio
async def test_confirm_commitment_writes_outbox_event_in_same_transaction(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Confirming a commitment writes commitment.confirmed into outbox_events in the same transaction."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    comm = CommitmentFactory(
        workspace_id=ws.id,
        status="awaiting-review",
        is_confirmed=False,
    )
    db_session.add_all([mem, comm])
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.post(f"/api/v1/commitments/{comm.id}/confirm", headers=headers)
    assert res.status_code == 200

    outbox_stmt = select(OutboxEvent).where(
        OutboxEvent.workspace_id == ws.id,
        OutboxEvent.event_type == "commitment.confirmed",
    )
    event = (await db_session.execute(outbox_stmt)).scalar_one_or_none()
    assert event is not None
    assert event.status == "pending"
    assert event.payload["id"] == str(comm.id)


@pytest.mark.asyncio
async def test_rollback_prevents_outbox_event_write(db_session: AsyncSession):
    """When a transaction rolls back, NO row is committed to outbox_events."""
    ws = WorkspaceFactory()
    user = UserFactory()
    db_session.add_all([ws, user])
    await db_session.commit()

    # In a separate transaction, create an outbox event and roll back
    from core.outbox.service import create_outbox_event
    test_event_type = f"test.rollback.{uuid.uuid4().hex[:6]}"

    async with db_session.begin_nested():
        await create_outbox_event(
            db=db_session,
            workspace_id=ws.id,
            event_type=test_event_type,
            payload={"should_be_rolled_back": True},
        )
        # Explicit rollback of the nested savepoint
        await db_session.rollback()

    # Verify no row was persisted
    outbox_res = await db_session.execute(
        select(OutboxEvent).where(OutboxEvent.event_type == test_event_type)
    )
    assert outbox_res.scalar_one_or_none() is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Audit Trail Verification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_event_written_for_all_commitment_actions(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Every commitment lifecycle action (CREATE, UPDATE, CONFIRM, DELETE) emits an audit_events record."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    # 1. CREATE
    res_create = app_client.post(
        "/api/v1/commitments",
        json={"title": "Audit Test Promise", "customer": "Acme Bank"},
        headers=headers,
    )
    assert res_create.status_code == 201
    comm_id = res_create.json()["id"]

    audit_create = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.workspace_id == ws.id,
                AuditEvent.action == "COMMITMENT_CREATED",
            )
        )
    ).scalar_one_or_none()
    assert audit_create is not None
    assert audit_create.workspace_id == ws.id
    assert audit_create.actor_id == user.id

    # 2. UPDATE
    res_patch = app_client.patch(
        f"/api/v1/commitments/{comm_id}",
        json={"title": "Audit Test Promise Updated"},
        headers=headers,
    )
    assert res_patch.status_code == 200

    audit_update = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.target_id == comm_id,
                AuditEvent.action == "COMMITMENT_UPDATED",
            )
        )
    ).scalar_one_or_none()
    assert audit_update is not None

    # 3. CONFIRM
    res_confirm = app_client.post(f"/api/v1/commitments/{comm_id}/confirm", headers=headers)
    assert res_confirm.status_code == 200

    audit_confirm = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.target_id == comm_id,
                AuditEvent.action == "COMMITMENT_CONFIRMED",
            )
        )
    ).scalar_one_or_none()
    assert audit_confirm is not None

    # 4. DELETE
    res_del = app_client.delete(f"/api/v1/commitments/{comm_id}", headers=headers)
    assert res_del.status_code == 200

    audit_delete = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.target_id == comm_id,
                AuditEvent.action == "COMMITMENT_DELETED",
            )
        )
    ).scalar_one_or_none()
    assert audit_delete is not None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Lifecycle Operations & State Enforcement
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_commitment_with_etag(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """GET /api/v1/commitments/{id} returns commitment DTO with ETag header."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    comm = CommitmentFactory(workspace_id=ws.id, title="Test ETag Flow")
    db_session.add_all([mem, comm])
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.get(f"/api/v1/commitments/{comm.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(comm.id)
    assert data["title"] == "Test ETag Flow"
    assert "ETag" in res.headers
    assert str(comm.id) in res.headers["ETag"]


@pytest.mark.asyncio
async def test_update_commitment_invalid_transition_rejected(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Transitioning a delivered commitment to awaiting-review is rejected with 422."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    comm = CommitmentFactory(
        workspace_id=ws.id,
        status="delivered",
        status_label="Delivered",
        is_confirmed=True,
    )
    db_session.add_all([mem, comm])
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.patch(
        f"/api/v1/commitments/{comm.id}",
        json={"status": "awaiting-review"},
        headers=headers,
    )
    assert res.status_code == 422
    assert "Invalid status transition" in res.json().get("detail", "")

    # Ensure DB status is unmodified
    await db_session.refresh(comm)
    assert comm.status == "delivered"


@pytest.mark.asyncio
async def test_mark_delivered_and_evidence_enrichment(db_session: AsyncSession):
    """CommitmentService.mark_delivered marks commitment delivered and enriches engineering evidence."""
    ws = WorkspaceFactory()
    comm = CommitmentFactory(
        workspace_id=ws.id,
        status="confirmed",
        is_confirmed=True,
        engineering_evidence_json={"releaseNotes": [], "prs": []},
    )
    db_session.add_all([ws, comm])
    await db_session.commit()

    updated = await CommitmentService.mark_delivered(
        db=db_session,
        commitment_id=comm.id,
        workspace_id=ws.id,
        evidence_type="release_notes",
        evidence_title="v2.4.0 Release Notes: Security Audit Fixes",
    )
    assert updated is not None
    assert updated.status == "delivered"
    assert updated.category == "delivered"
    assert "v2.4.0 Release Notes: Security Audit Fixes" in updated.engineering_evidence_json["releaseNotes"]


@pytest.mark.asyncio
async def test_draft_update_endpoint(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """POST /api/v1/commitments/{id}/draft-update generates customer update email template."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    comm = CommitmentFactory(
        workspace_id=ws.id,
        title="Automated Data Backup",
        customer_name="Cloud Corp",
        promised_by="End of October",
    )
    db_session.add_all([mem, comm])
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.post(f"/api/v1/commitments/{comm.id}/draft-update", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["commitment_id"] == str(comm.id)
    assert "Automated Data Backup" in data["subject"]
    assert "Cloud Corp" in data["body"] or "End of October" in data["body"]
    assert data["target_channel"] == "email"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pagination & Filtering
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_commitments_pagination(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Pagination query params (page, page_size) correctly partition results and report has_next."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)

    # Seed 5 commitments
    for i in range(5):
        comm = CommitmentFactory(workspace_id=ws.id, title=f"Commitment Item #{i}")
        db_session.add(comm)
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    # Page 1, page_size 2 -> 2 items, has_next=True
    res1 = app_client.get("/api/v1/commitments?page=1&page_size=2", headers=headers)
    assert res1.status_code == 200
    p1 = res1.json()
    assert len(p1["items"]) == 2
    assert p1["total"] == 5
    assert p1["has_next"] is True

    # Page 3, page_size 2 -> 1 item, has_next=False
    res3 = app_client.get("/api/v1/commitments?page=3&page_size=2", headers=headers)
    assert res3.status_code == 200
    p3 = res3.json()
    assert len(p3["items"]) == 1
    assert p3["has_next"] is False

    # Page 4, page_size 2 -> 0 items, has_next=False
    res4 = app_client.get("/api/v1/commitments?page=4&page_size=2", headers=headers)
    assert res4.status_code == 200
    p4 = res4.json()
    assert len(p4["items"]) == 0
    assert p4["has_next"] is False


@pytest.mark.asyncio
async def test_commitments_filters_and_search(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Filtering by status and full-text ILIKE search works accurately."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    await db_session.flush()

    from modules.iam.models import Membership
    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    c1 = CommitmentFactory(workspace_id=ws.id, title="Zero Trust Security Gateway", status="confirmed")
    c2 = CommitmentFactory(workspace_id=ws.id, title="Billing Stripe Upgrade", status="awaiting-review")
    db_session.add_all([mem, c1, c2])
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    # Filter by status="awaiting-review"
    res_status = app_client.get("/api/v1/commitments?status=awaiting-review", headers=headers)
    assert res_status.status_code == 200
    items_status = res_status.json()["items"]
    assert len(items_status) == 1
    assert items_status[0]["id"] == str(c2.id)

    # Search for "Zero Trust"
    res_search = app_client.get("/api/v1/commitments?search=Zero%20Trust", headers=headers)
    assert res_search.status_code == 200
    items_search = res_search.json()["items"]
    assert len(items_search) == 1
    assert items_search[0]["id"] == str(c1.id)


@pytest.mark.asyncio
async def test_attention_commitments_prioritization(db_session: AsyncSession):
    """CommitmentService.list_attention_commitments retrieves at-risk and overdue commitments."""
    ws = WorkspaceFactory()
    db_session.add(ws)

    c_at_risk = CommitmentFactory(workspace_id=ws.id, status="at-risk", category="needs-attention")
    c_overdue = CommitmentFactory(workspace_id=ws.id, status="overdue", category="needs-attention")
    c_on_track = CommitmentFactory(workspace_id=ws.id, status="confirmed", category="on-track")
    db_session.add_all([c_at_risk, c_overdue, c_on_track])
    await db_session.commit()

    attention_items = await CommitmentService.list_attention_commitments(db_session, ws.id, limit=10)
    attention_ids = [c.id for c in attention_items]

    assert c_at_risk.id in attention_ids
    assert c_overdue.id in attention_ids
    assert c_on_track.id not in attention_ids


# ─────────────────────────────────────────────────────────────────────────────
# 5. Customer SLA Health Metrics Calculation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_customer_metrics_sla_health_calculation(db_session: AsyncSession):
    """CustomerService SLA health score calculation handles completed, on-track, and at-risk commitments."""
    ws = WorkspaceFactory()
    db_session.add(ws)

    # 1. Customer with all delivered commitments -> health_score = 100, completed
    cust_delivered = CustomerFactory(workspace_id=ws.id, name="Fully Delivered Client")
    db_session.add(cust_delivered)
    await db_session.flush()

    c_del = CommitmentFactory(
        workspace_id=ws.id,
        customer_name=cust_delivered.name,
        customer_id=cust_delivered.id,
        status="delivered",
    )
    db_session.add(c_del)

    # 2. Customer with active on-track commitment -> health_score = 95, on-track
    cust_on_track = CustomerFactory(workspace_id=ws.id, name="On-Track Client")
    db_session.add(cust_on_track)
    await db_session.flush()

    c_track = CommitmentFactory(
        workspace_id=ws.id,
        customer_name=cust_on_track.name,
        customer_id=cust_on_track.id,
        status="confirmed",
        category="on-track",
    )
    db_session.add(c_track)

    # 3. Customer with 2 at-risk commitments -> health_score = 50 (90 - 2*20 = 50), at-risk
    cust_at_risk = CustomerFactory(workspace_id=ws.id, name="At-Risk Client")
    db_session.add(cust_at_risk)
    await db_session.flush()

    c_risk1 = CommitmentFactory(
        workspace_id=ws.id,
        customer_name=cust_at_risk.name,
        customer_id=cust_at_risk.id,
        status="at-risk",
    )
    c_risk2 = CommitmentFactory(
        workspace_id=ws.id,
        customer_name=cust_at_risk.name,
        customer_id=cust_at_risk.id,
        status="at-risk",
    )
    db_session.add_all([c_risk1, c_risk2])
    await db_session.commit()

    # Query customer metrics via CustomerService
    dtos, _ = await CustomerService.list_customers_with_metrics(db_session, ws.id)
    cust_map = {c["name"]: c for c in dtos}

    assert cust_map["Fully Delivered Client"]["healthScore"] == 100
    assert cust_map["Fully Delivered Client"]["status"] == "completed"

    assert cust_map["On-Track Client"]["healthScore"] == 95
    assert cust_map["On-Track Client"]["status"] == "on-track"

    assert cust_map["At-Risk Client"]["healthScore"] == 50
    assert cust_map["At-Risk Client"]["status"] == "at-risk"
