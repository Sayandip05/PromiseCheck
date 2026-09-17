"""Security tests for multi-tenant workspace data isolation."""

import uuid
import pytest
from fastapi.testclient import TestClient

from core.database import AsyncSessionLocal
from core.security import create_access_token, Role
from modules.commitments.models import Commitment
from modules.customers.models import Customer
from modules.identity.models import User
from modules.workspaces.models import Membership, Workspace
from src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_cross_tenant_workspace_isolation(client: TestClient):
    """Verify that User A cannot see, access, or manipulate commitments or customers from Workspace B."""
    async with AsyncSessionLocal() as db:
        # 1. Provision Workspace A and User A
        user_a = User(
            email=f"alice_{uuid.uuid4().hex[:6]}@tenant-a.com",
            full_name="Alice Tenant A",
            is_active=True,
        )
        ws_a = Workspace(name="Tenant Alpha", slug=f"tenant-alpha-{uuid.uuid4().hex[:6]}")
        db.add_all([user_a, ws_a])
        await db.flush()

        mem_a = Membership(workspace_id=ws_a.id, user_id=user_a.id, role=Role.ADMIN)
        db.add(mem_a)

        # 2. Provision Workspace B and User B
        user_b = User(
            email=f"bob_{uuid.uuid4().hex[:6]}@tenant-b.com",
            full_name="Bob Tenant B",
            is_active=True,
        )
        ws_b = Workspace(name="Tenant Beta", slug=f"tenant-beta-{uuid.uuid4().hex[:6]}")
        db.add_all([user_b, ws_b])
        await db.flush()

        mem_b = Membership(workspace_id=ws_b.id, user_id=user_b.id, role=Role.ADMIN)
        db.add(mem_b)

        # 3. Create private commitment in Workspace A
        comm_a = Commitment(
            workspace_id=ws_a.id,
            title="Secret SLA Feature for Alpha",
            customer_name="Alpha Private Corp",
            owner_name="Alice",
            owner_email=user_a.email,
            promised_by="Oct 31, 2026",
            status="on-track",
            status_label="On Track",
            category="on-track",
            is_confirmed=True,
            quote="Confidential commitment for Alpha",
            original_promise_json={"quote": "Confidential"},
            engineering_evidence_json={},
            risk_json={"level": "low"},
            recommended_step_json={},
            metadata_json={},
        )
        db.add(comm_a)

        # 4. Create private customer in Workspace B
        cust_b = Customer(
            workspace_id=ws_b.id,
            name="Confidential Beta Client",
            status="on-track",
            status_color="#10b981",
            active_promises=1,
            health_score=100,
            recent_promise="Confidential",
            due_date="Nov 2026",
            owner="Bob",
            domains_json=["beta-client.org"],
        )
        db.add(cust_b)
        await db.commit()

        token_a = create_access_token(user_id=user_a.id, email=user_a.email)
        token_b = create_access_token(user_id=user_b.id, email=user_b.email)

    # 5. User B queries commitments: MUST NOT contain comm_a
    res_b = client.get(
        "/api/v1/commitments",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 200
    # Fix #6: GET /commitments now returns a paginated response wrapper
    b_commitments = res_b.json()["items"]
    b_titles = [c["title"] for c in b_commitments]
    assert "Secret SLA Feature for Alpha" not in b_titles

    # 6. User A queries commitments: MUST contain comm_a
    res_a = client.get(
        "/api/v1/commitments",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 200
    # Fix #6: unwrap paginated wrapper
    a_commitments = res_a.json()["items"]
    a_titles = [c["title"] for c in a_commitments]
    assert "Secret SLA Feature for Alpha" in a_titles

    # 7. User A queries customers: MUST NOT contain cust_b
    res_cust_a = client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_cust_a.status_code == 200
    a_customers = [c["name"] for c in res_cust_a.json()]
    assert "Confidential Beta Client" not in a_customers

    # 8. User B queries customers: MUST contain cust_b
    res_cust_b = client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_cust_b.status_code == 200
    b_customers = [c["name"] for c in res_cust_b.json()]
    assert "Confidential Beta Client" in b_customers
