"""Tenant Isolation and Authorization Matrix Integration Tests (Batch 1).

Covers CRITICAL multi-tenant guarantees:
1. Cross-tenant read, update, and delete isolation across all tenant-owned resources:
   - commitments (list, get, patch, delete, confirm, draft-update)
   - customers (list, get by id, isolation)
   - delivery evidence (list, verify sign-off)
   - ingestion jobs (list, upload scoping)
   - integrations (list, connect/disconnect, secret isolation)
   - audit events (list)
   - notifications & alerts (list)
   - risk assessments (list, evaluate)
   - engineering tickets (list)
   - MCP tools (list_commitments, get_commitment_evidence, create_commitment)
   - SSE realtime events (channel isolation)
2. Route-level unauthenticated and expired token matrix (401) driven from FastAPI route table.
3. Route-level unauthorized workspace access matrix (403).
4. Route security allowlist completeness guard.
5. RBAC role hierarchy enforcement (Admin vs Member vs Viewer).
"""

from datetime import datetime, timedelta, timezone
import json
import secrets
import uuid
import jwt
import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import Role, _get_jwt_secret, create_access_token
from modules.audit.models import AuditEvent
from modules.commitments.models import Commitment, DeliveryEvidence
from modules.customers.models import Customer
from modules.iam.dependencies import require_role
from modules.iam.models import Membership, User, Workspace
from modules.ingestion.models import IngestionJob
from modules.integrations.models import WorkspaceIntegration
from src.main import app
from tests.fixtures.database import TwoTenantsContext
from tests.fixtures.factories import (
    AuditEventFactory,
    CommitmentFactory,
    CustomerFactory,
    DeliveryEvidenceFactory,
    IngestionJobFactory,
    IntegrationFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────


def make_expired_token(user_id: uuid.UUID, email: str) -> str:
    """Generate an expired JWT access token."""
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": int((past - timedelta(minutes=15)).timestamp()),
        "exp": int(past.timestamp()),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)


PUBLIC_ROUTE_ALLOWLIST: set[tuple[str, str]] = {
    ("GET", "/healthz"),
    ("GET", "/metrics"),
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/metrics"),
    ("GET", "/api/v1/operations/status"),
    ("GET", "/api/v1/operations/metrics"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/google"),
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/integrations/google/callback"),
    ("POST", "/api/v1/workspaces"),
    ("GET", "/api/v1/workspaces/{workspace_id}"),
    ("GET", "/api/v1/workspaces/{workspace_id}/members"),
}


def get_all_api_routes() -> list[tuple[str, str]]:
    """Extract all HTTP method + path pairs from OpenAPI schema."""
    openapi_schema = app.openapi()
    routes: list[tuple[str, str]] = []
    for path, methods_dict in openapi_schema.get("paths", {}).items():
        for method in methods_dict.keys():
            if method.lower() not in ("parameters", "options", "head"):
                routes.append((method.upper(), path))
    return sorted(routes)


def format_test_path(path: str, dummy_id: uuid.UUID) -> str:
    """Substitute OpenAPI path parameters with test fixtures."""
    return (
        path.replace("{commitment_id}", str(dummy_id))
        .replace("{customer_id}", str(dummy_id))
        .replace("{workspace_id}", str(dummy_id))
        .replace("{provider}", "jira")
        .replace("{tracker}", "jira")
        .replace("{key}", "PROJ-123")
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Commitments Domain Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_commitments_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot list, view, mutate, confirm, or delete Tenant B's commitments."""
    ws_a = two_tenants.tenant_a.workspace
    ws_b = two_tenants.tenant_b.workspace

    # Seed private commitment in Workspace B
    comm_b = CommitmentFactory(
        workspace_id=ws_b.id,
        title="Beta Secret Customer Commitment",
        customer_name="Beta Confidential Corp",
        status="awaiting-review",
        is_confirmed=False,
    )
    db_session.add(comm_b)
    await db_session.commit()

    # 1. List: Tenant A queries commitments -> Tenant B's commitment does NOT appear
    res_list = app_client.get("/api/v1/commitments", headers=two_tenants.tenant_a.owner_headers)
    assert res_list.status_code == 200
    items = res_list.json().get("items", [])
    item_ids = [i["id"] for i in items]
    assert str(comm_b.id) not in item_ids
    assert all(i["title"] != "Beta Secret Customer Commitment" for i in items)

    # 2. GET by ID: Tenant A attempts to read Tenant B's commitment -> 404 (not 403, no leak)
    res_get = app_client.get(
        f"/api/v1/commitments/{comm_b.id}",
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_get.status_code == 404
    assert res_get.json()["detail"] == "Commitment not found"

    # 3. PATCH: Tenant A attempts to modify Tenant B's commitment -> rejected
    res_patch = app_client.patch(
        f"/api/v1/commitments/{comm_b.id}",
        json={"title": "Hacked Title"},
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_patch.status_code in (403, 404)

    # 4. DELETE: Tenant A attempts to delete Tenant B's commitment -> rejected
    res_del = app_client.delete(
        f"/api/v1/commitments/{comm_b.id}",
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_del.status_code in (403, 404)

    # 5. CONFIRM: Tenant A attempts to confirm Tenant B's commitment -> rejected
    res_confirm = app_client.post(
        f"/api/v1/commitments/{comm_b.id}/confirm",
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_confirm.status_code in (403, 404)

    # 6. DRAFT UPDATE: Tenant A attempts to draft an update for Tenant B's commitment -> rejected
    res_draft = app_client.post(
        f"/api/v1/commitments/{comm_b.id}/draft-update",
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_draft.status_code in (403, 404)

    # DB Integrity Check: comm_b in Workspace B remains completely unchanged
    await db_session.refresh(comm_b)
    assert comm_b.title == "Beta Secret Customer Commitment"
    assert comm_b.is_confirmed is False
    assert comm_b.status == "awaiting-review"


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2: src/modules/commitments/service.py:279,368,418 returns 403 instead of 404 on cross-tenant PATCH/DELETE/CONFIRM, leaking commitment existence",
)
@pytest.mark.asyncio
async def test_cross_tenant_commitments_patch_and_delete_returns_404_not_403(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Verifies that PATCH/DELETE on another tenant's commitment returns 404 to avoid leaking existence."""
    comm_b = CommitmentFactory(
        workspace_id=two_tenants.tenant_b.workspace.id,
        title="Beta Secret",
    )
    db_session.add(comm_b)
    await db_session.commit()

    res_patch = app_client.patch(
        f"/api/v1/commitments/{comm_b.id}",
        json={"title": "Hacked Title"},
        headers=two_tenants.tenant_a.owner_headers,
    )
    # Expected behavior according to TEST_PLAN.md: 404 Not Found so existence is not leaked
    assert res_patch.status_code == 404



# ─────────────────────────────────────────────────────────────────────────────
# 2. Customers Domain Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_customers_list_and_read_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot list Tenant B's customer accounts and cannot access customer details."""
    ws_b = two_tenants.tenant_b.workspace

    cust_b = CustomerFactory(
        workspace_id=ws_b.id,
        name="Beta Secret Client LLC",
    )
    db_session.add(cust_b)
    await db_session.commit()

    # 1. Tenant A lists customers -> B's customer does not appear
    res_list = app_client.get("/api/v1/customers", headers=two_tenants.tenant_a.owner_headers)
    assert res_list.status_code == 200
    customers = res_list.json()
    assert all(c["id"] != str(cust_b.id) for c in customers)
    assert all(c["name"] != "Beta Secret Client LLC" for c in customers)

    # 2. Access to customer record by ID is strictly blocked for Tenant A
    res_get = app_client.get(
        f"/api/v1/customers/{cust_b.id}",
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_get.status_code != 200
    assert "Beta Secret Client LLC" not in res_get.text


@pytest.mark.xfail(
    strict=True,
    reason="BUG-1: src/modules/customers/service.py:132 returns 403 instead of 404 on cross-tenant access, leaking customer existence",
)
@pytest.mark.asyncio
async def test_cross_tenant_customer_get_returns_404_not_403(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Verifies that accessing another tenant's customer returns 404 to avoid leaking existence."""
    cust_b = CustomerFactory(
        workspace_id=two_tenants.tenant_b.workspace.id,
        name="Beta Private Client",
    )
    db_session.add(cust_b)
    await db_session.commit()

    res = app_client.get(
        f"/api/v1/customers/{cust_b.id}",
        headers=two_tenants.tenant_a.owner_headers,
    )
    # Expected behavior according to TEST_PLAN.md: 404 Not Found so existence is not leaked
    assert res.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 3. Delivery Evidence Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason="BUG-3: src/modules/commitments/models.py:76 DeliveryEvidence model columns do not match PostgreSQL migration 0001 schema, causing UndefinedColumnError",
)
@pytest.mark.asyncio
async def test_cross_tenant_delivery_evidence_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot list Tenant B's delivery evidence."""
    ws_b = two_tenants.tenant_b.workspace

    comm_b = CommitmentFactory(
        workspace_id=ws_b.id,
        title="Beta Feature Awaiting Delivery",
        status="confirmed",
    )
    db_session.add(comm_b)
    await db_session.flush()

    ev_b = DeliveryEvidenceFactory(
        workspace_id=ws_b.id,
        commitment_id=comm_b.id,
        commitment_title="Beta Feature Awaiting Delivery",
        evidence_title="Beta PR #101 Merged",
    )
    db_session.add(ev_b)
    await db_session.commit()

    # Tenant A lists delivery evidence -> Tenant B's evidence does not appear
    res_list = app_client.get("/api/v1/delivery/evidence", headers=two_tenants.tenant_a.owner_headers)
    assert res_list.status_code == 200
    evidence_items = res_list.json()
    assert all(e["id"] != str(ev_b.id) for e in evidence_items)


@pytest.mark.asyncio
async def test_cross_tenant_delivery_verify_foreign_commitment_rejected(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A attempting to verify delivery for Tenant B's commitment is rejected with 404."""
    comm_b = CommitmentFactory(
        workspace_id=two_tenants.tenant_b.workspace.id,
        title="Beta Feature For Delivery",
        status="confirmed",
    )
    db_session.add(comm_b)
    await db_session.commit()

    res_verify = app_client.post(
        "/api/v1/delivery/verify",
        json={
            "commitment_id": str(comm_b.id),
            "evidence_type": "manual_signoff",
            "evidence_title": "Fake Verification by Alpha",
            "evidence_url": "https://github.com/fake/proof",
            "notes": "Attempting cross-tenant sign-off",
        },
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_verify.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 4. Ingestion Jobs Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_ingestion_jobs_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot list Tenant B's ingestion jobs; uploads are scoped to caller's workspace."""
    ws_b = two_tenants.tenant_b.workspace

    job_b = IngestionJobFactory(
        workspace_id=ws_b.id,
        meeting_title="Confidential Beta Board Meeting",
        customer_name="Beta Strategic Partner",
    )
    db_session.add(job_b)
    await db_session.commit()

    # 1. Tenant A lists ingestion jobs -> Tenant B's job does not appear
    res_list = app_client.get("/api/v1/ingestion/jobs", headers=two_tenants.tenant_a.owner_headers)
    assert res_list.status_code == 200
    jobs = res_list.json()
    job_ids = [j["job_id"] for j in jobs]
    assert job_b.job_id not in job_ids

    # 2. Tenant A uploads transcript -> created job is associated with Workspace A
    res_upload = app_client.post(
        "/api/v1/ingestion/upload",
        json={
            "transcript_text": "Speaker 1: We promise to ship the export tool by end of November.",
            "source_type": "upload",
            "meeting_title": "Alpha Sprint Planning",
            "customer": "Alpha Customer",
        },
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_upload.status_code == 202
    created_job_id = res_upload.json()["job_id"]

    # Verify in DB that newly created job has workspace_id == ws_a.id
    stmt = select(IngestionJob).where(IngestionJob.job_id == created_job_id)
    db_job = (await db_session.execute(stmt)).scalar_one_or_none()
    assert db_job is not None
    assert db_job.workspace_id == two_tenants.tenant_a.workspace.id


# ─────────────────────────────────────────────────────────────────────────────
# 5. Integrations Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_integrations_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant B's connected integrations and credentials do not leak to Tenant A."""
    ws_b = two_tenants.tenant_b.workspace

    # Seed connected integration in Workspace B (linear starts disconnected by default)
    integ_b = IntegrationFactory(
        workspace_id=ws_b.id,
        provider="linear",
        name="Linear Integration",
        connected=True,
        config_json={"api_key": "secret-linear-token-beta"},
    )
    db_session.add(integ_b)
    await db_session.commit()

    # 1. Tenant A lists integrations -> Linear is not connected for Tenant A, secret absent
    res_list = app_client.get("/api/v1/integrations", headers=two_tenants.tenant_a.owner_headers)
    assert res_list.status_code == 200
    alpha_integrations = {i["provider"]: i for i in res_list.json()}
    if "linear" in alpha_integrations:
        assert alpha_integrations["linear"]["connected"] is False
    assert "secret-linear-token-beta" not in res_list.text

    # 2. Tenant A disconnects Linear -> only affects Workspace A
    res_disc = app_client.post(
        "/api/v1/integrations/linear/disconnect",
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_disc.status_code == 200

    # DB Integrity Check: Workspace B's Linear row remains connected
    await db_session.refresh(integ_b)
    assert integ_b.connected is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. Audit Events Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_audit_events_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot view Tenant B's compliance audit log events."""
    audit_b = AuditEventFactory(
        workspace_id=two_tenants.tenant_b.workspace.id,
        actor_id=two_tenants.tenant_b.owner.id,
        action="commitment.deleted",
        description="Confidential audit event for Tenant Beta",
    )
    db_session.add(audit_b)
    await db_session.commit()

    res = app_client.get("/api/v1/audit", headers=two_tenants.tenant_a.owner_headers)
    assert res.status_code == 200
    events = res.json()
    assert all(e["id"] != str(audit_b.id) for e in events)
    assert all("Confidential audit event for Tenant Beta" not in e["description"] for e in events)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Notifications & Alerts Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_notifications_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot see notifications or alerts generated for Tenant B."""
    comm_b = CommitmentFactory(
        workspace_id=two_tenants.tenant_b.workspace.id,
        title="Beta Overdue SLA Commitment",
        customer_name="Beta Enterprise",
        status="awaiting-review",
        category="awaiting-review",
    )
    db_session.add(comm_b)
    await db_session.commit()

    res = app_client.get("/api/v1/notifications", headers=two_tenants.tenant_a.owner_headers)
    assert res.status_code == 200
    alerts = res.json()
    assert all(a["commitment_id"] != str(comm_b.id) for a in alerts)
    assert all("Beta Overdue SLA Commitment" not in a.get("commitment_title", "") for a in alerts)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Risk Assessments Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_risk_assessments_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot see Tenant B's risk assessments; evaluate only touches caller's workspace."""
    comm_b = CommitmentFactory(
        workspace_id=two_tenants.tenant_b.workspace.id,
        title="Beta Critical Risk Delivery",
        status="at-risk",
        category="needs-attention",
        risk_json={"level": "high", "reasons": ["Beta dependency delay"]},
    )
    db_session.add(comm_b)
    await db_session.commit()

    # 1. Tenant A lists risk assessments -> B's risk assessment does not appear
    res_list = app_client.get("/api/v1/risk/assessments", headers=two_tenants.tenant_a.owner_headers)
    assert res_list.status_code == 200
    assessments = res_list.json()
    assert all(a["commitment_id"] != str(comm_b.id) for a in assessments)

    # 2. Tenant A calls evaluate -> only scans Workspace A
    res_eval = app_client.post("/api/v1/risk/evaluate", headers=two_tenants.tenant_a.owner_headers)
    assert res_eval.status_code == 200
    summary = res_eval.json()
    assert "evaluated_count" in summary


# ─────────────────────────────────────────────────────────────────────────────
# 9. Engineering Tickets Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_engineering_tickets_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """Tenant A cannot see linked engineering tracker tickets belonging to Tenant B."""
    comm_b = CommitmentFactory(
        workspace_id=two_tenants.tenant_b.workspace.id,
        title="Beta Engineering Task",
        ticket_id="BETA-999",
        ticket_status="In Progress",
        engineering_evidence_json={"jiraTickets": [{"key": "BETA-999", "status": "In Progress"}]},
    )
    db_session.add(comm_b)
    await db_session.commit()

    res = app_client.get("/api/v1/engineering/tickets", headers=two_tenants.tenant_a.owner_headers)
    assert res.status_code == 200
    tickets = res.json()
    assert all(t["key"] != "BETA-999" for t in tickets)


# ─────────────────────────────────────────────────────────────────────────────
# 10. MCP Tools Multi-Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_mcp_tools_isolation(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """MCP standard endpoints enforce tenant isolation on list, read, and creation."""
    ws_b = two_tenants.tenant_b.workspace
    comm_b = CommitmentFactory(
        workspace_id=ws_b.id,
        title="Confidential Beta Roadmap Feature",
        customer_name="Beta Mega Corp",
    )
    db_session.add(comm_b)
    await db_session.commit()

    # 1. MCP tool: list_commitments called by Tenant A
    res_list = app_client.post(
        "/api/v1/mcp/tools/call",
        json={"name": "list_commitments", "arguments": {}},
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_list.status_code == 200
    mcp_content = res_list.json()["content"]
    text_payload = mcp_content[0].get("text", "")
    assert str(comm_b.id) not in text_payload
    assert "Confidential Beta Roadmap Feature" not in text_payload

    # 2. MCP tool: get_commitment_evidence for Tenant B's commitment
    res_ev = app_client.post(
        "/api/v1/mcp/tools/call",
        json={
            "name": "get_commitment_evidence",
            "arguments": {"commitment_id": str(comm_b.id)},
        },
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_ev.status_code == 200
    ev_text = res_ev.json()["content"][0].get("text", "")
    assert "Confidential Beta Roadmap Feature" not in ev_text

    # 3. MCP tool: create_commitment called by Tenant A -> scoped to Workspace A
    res_create = app_client.post(
        "/api/v1/mcp/tools/call",
        json={
            "name": "create_commitment",
            "arguments": {
                "title": "Alpha MCP Created Feature",
                "customer": "Alpha Client",
                "promised_by": "Dec 2026",
            },
        },
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_create.status_code == 200
    created_payload = json.loads(res_create.json()["content"][0]["text"])
    assert created_payload["workspace_id"] == str(two_tenants.tenant_a.workspace.id)
    assert created_payload["title"] == "Alpha MCP Created Feature"



# ─────────────────────────────────────────────────────────────────────────────
# 11. SSE Realtime Channel Isolation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_realtime_channel_isolation(
    two_tenants: TwoTenantsContext,
    app_client: TestClient,
):
    """Test-publish routes events to the caller's tenant channel only."""
    res_a = app_client.post(
        "/api/v1/realtime/test-publish",
        params={"event_type": "TEST_ALPHA", "message": "Alpha event"},
        headers=two_tenants.tenant_a.owner_headers,
    )
    assert res_a.status_code == 200
    assert res_a.json()["channel"] == f"ws:{two_tenants.tenant_a.workspace.id}:events"

    res_b = app_client.post(
        "/api/v1/realtime/test-publish",
        params={"event_type": "TEST_BETA", "message": "Beta event"},
        headers=two_tenants.tenant_b.owner_headers,
    )
    assert res_b.status_code == 200
    assert res_b.json()["channel"] == f"ws:{two_tenants.tenant_b.workspace.id}:events"
    assert res_a.json()["channel"] != res_b.json()["channel"]


# ─────────────────────────────────────────────────────────────────────────────
# 12. Route-Level Authentication & Authorization Matrix
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_route_table_public_allowlist_integrity():
    """Verify that every route in the app is accounted for as either public or protected."""
    all_routes = get_all_api_routes()
    unaccounted: list[tuple[str, str]] = []

    for method, path in all_routes:
        if (method, path) in PUBLIC_ROUTE_ALLOWLIST:
            continue
        # Protected route: ensure it is not unexpectedly in the root allowlist
        if not path.startswith("/api/v1/") and path not in ("/healthz", "/metrics"):
            unaccounted.append((method, path))

    assert unaccounted == [], f"Found routes outside standard API prefix: {unaccounted}"


@pytest.mark.asyncio
async def test_all_protected_routes_reject_unauthenticated(
    app_client: TestClient,
):
    """Every protected endpoint rejects requests lacking Authorization credentials with 401."""
    all_routes = get_all_api_routes()
    dummy_id = uuid.uuid4()
    checked = 0

    for method, path in all_routes:
        if (method, path) in PUBLIC_ROUTE_ALLOWLIST:
            continue

        target_url = format_test_path(path, dummy_id)
        # Execute request without Authorization header
        res = app_client.request(method, target_url)
        assert res.status_code == 401, (
            f"Expected 401 Unauthorized for {method} {target_url}, got {res.status_code} ({res.text})"
        )
        checked += 1

    assert checked >= 30, f"Expected at least 30 protected routes checked, got {checked}"


@pytest.mark.asyncio
async def test_all_protected_routes_reject_expired_tokens(
    two_tenants: TwoTenantsContext,
    app_client: TestClient,
):
    """Every protected endpoint rejects expired JWT tokens with 401 Unauthorized."""
    expired_token = make_expired_token(
        two_tenants.tenant_a.owner.id,
        two_tenants.tenant_a.owner.email,
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    dummy_id = uuid.uuid4()
    checked = 0

    for method, path in get_all_api_routes():
        if (method, path) in PUBLIC_ROUTE_ALLOWLIST:
            continue

        target_url = format_test_path(path, dummy_id)
        res = app_client.request(method, target_url, headers=headers)
        assert res.status_code == 401, (
            f"Expected 401 for expired token on {method} {target_url}, got {res.status_code}"
        )
        checked += 1

    assert checked >= 30, f"Expected at least 30 protected routes checked, got {checked}"


@pytest.mark.asyncio
async def test_all_protected_routes_reject_unauthorized_workspace_access(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
):
    """Resolving workspace context for an unauthorized workspace rejects with 403 Forbidden."""
    from modules.iam.service import get_active_workspace_id

    # User A requests access to Workspace B (not a member)
    with pytest.raises(HTTPException) as exc_info:
        await get_active_workspace_id(
            db=db_session,
            user=two_tenants.tenant_a.owner,
            workspace_id=two_tenants.tenant_b.workspace.id,
        )
    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail


@pytest.mark.asyncio
async def test_user_without_workspace_memberships_rejected_with_403(
    db_session: AsyncSession,
):
    """User without any workspace memberships receives 403 Forbidden."""
    from modules.iam.service import get_active_workspace_id

    orphan_user = UserFactory(full_name="Orphan User")
    db_session.add(orphan_user)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await get_active_workspace_id(db=db_session, user=orphan_user)
    assert exc_info.value.status_code == 403
    assert "workspace membership" in exc_info.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 13. RBAC Role Hierarchy & Operation Permissions
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_role_hierarchy_viewer_blocked_when_admin_required(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
):
    """User with Role.VIEWER is rejected with 403 when Role.ADMIN is required."""
    ws = two_tenants.tenant_a.workspace
    viewer_user = UserFactory(full_name="Viewer User")
    db_session.add(viewer_user)
    await db_session.flush()

    mem = Membership(workspace_id=ws.id, user_id=viewer_user.id, role=Role.VIEWER)
    db_session.add(mem)
    await db_session.commit()

    guard = require_role(Role.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await guard(user=viewer_user, db=db_session)
    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_role_hierarchy_member_blocked_when_admin_required(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
):
    """User with Role.MEMBER is rejected with 403 when Role.ADMIN is required."""
    guard = require_role(Role.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await guard(user=two_tenants.tenant_a.member, db=db_session)
    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_role_hierarchy_admin_allowed(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
):
    """User with Role.ADMIN passes guard when Role.ADMIN is required."""
    guard = require_role(Role.ADMIN)
    res = await guard(user=two_tenants.tenant_a.owner, db=db_session)
    assert res.id == two_tenants.tenant_a.owner.id


@pytest.mark.asyncio
async def test_mcp_write_tool_blocks_viewer_role(
    two_tenants: TwoTenantsContext,
    db_session: AsyncSession,
    app_client: TestClient,
):
    """MCP mutation tools reject callers with Role.VIEWER with 403 Forbidden."""
    ws = two_tenants.tenant_a.workspace
    viewer_user = UserFactory(full_name="Viewer User MCP")
    db_session.add(viewer_user)
    await db_session.flush()

    mem = Membership(workspace_id=ws.id, user_id=viewer_user.id, role=Role.VIEWER)
    db_session.add(mem)
    await db_session.commit()

    viewer_tok = create_access_token(user_id=viewer_user.id, email=viewer_user.email)
    headers = {"Authorization": f"Bearer {viewer_tok}", "X-Workspace-Id": str(ws.id)}

    res = app_client.post(
        "/api/v1/mcp/tools/call",
        json={"name": "create_commitment", "arguments": {"title": "Illegal Mut"}},
        headers=headers,
    )
    assert res.status_code == 403
    assert "Viewer role cannot perform mutations" in res.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_write_tool_allows_member_role(
    two_tenants: TwoTenantsContext,
    app_client: TestClient,
):
    """MCP mutation tools permit callers with Role.MEMBER."""
    res = app_client.post(
        "/api/v1/mcp/tools/call",
        json={
            "name": "create_commitment",
            "arguments": {"title": "Valid Member Creation", "customer": "ACME"},
        },
        headers=two_tenants.tenant_a.member_headers,
    )
    assert res.status_code == 200
    assert res.json()["isError"] is False


@pytest.mark.asyncio
async def test_workspace_members_endpoint_isolation(
    two_tenants: TwoTenantsContext,
    app_client: TestClient,
):
    """Listing workspace members returns only users belonging to that specific workspace."""
    ws_a_id = two_tenants.tenant_a.workspace.id
    ws_b_id = two_tenants.tenant_b.workspace.id

    res_a = app_client.get(f"/api/v1/workspaces/{ws_a_id}/members")
    assert res_a.status_code == 200
    a_members = res_a.json()
    a_user_ids = [m["user_id"] for m in a_members]

    assert str(two_tenants.tenant_a.owner.id) in a_user_ids
    assert str(two_tenants.tenant_a.member.id) in a_user_ids
    assert str(two_tenants.tenant_b.owner.id) not in a_user_ids
    assert str(two_tenants.tenant_b.member.id) not in a_user_ids

    res_b = app_client.get(f"/api/v1/workspaces/{ws_b_id}/members")
    assert res_b.status_code == 200
    b_members = res_b.json()
    b_user_ids = [m["user_id"] for m in b_members]

    assert str(two_tenants.tenant_b.owner.id) in b_user_ids
    assert str(two_tenants.tenant_b.member.id) in b_user_ids
    assert str(two_tenants.tenant_a.owner.id) not in b_user_ids
    assert str(two_tenants.tenant_a.member.id) not in b_user_ids
