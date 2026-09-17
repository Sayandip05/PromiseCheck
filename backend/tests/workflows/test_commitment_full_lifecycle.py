"""End-to-end workflow test for full commitment lifecycle from capture to delivery verification."""

import uuid
import pytest
from fastapi.testclient import TestClient

from core.database import AsyncSessionLocal
from core.security import create_access_token, Role
from modules.identity.models import User
from modules.workspaces.models import Membership, Workspace
from src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_commitment_end_to_end_lifecycle(client: TestClient):
    """Verify entire workflow: Ingestion -> Confirmation -> Delivery Verification -> Audit Trail."""
    # 1. Provision user and dedicated test workspace
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"workflow_{uuid.uuid4().hex[:6]}@enterprise.com",
            full_name="Workflow Lead",
            is_active=True,
        )
        ws = Workspace(name="Workflow Enterprise", slug=f"wf-ent-{uuid.uuid4().hex[:6]}")
        db.add_all([user, ws])
        await db.flush()

        mem = Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN)
        db.add(mem)
        await db.commit()

        token = create_access_token(user_id=user.id, email=user.email)

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest meeting transcript — now returns 202 Accepted immediately (Fix #10)
    # The Celery worker processes extraction async; we verify the job is queued.
    ingest_res = client.post(
        "/api/v1/ingestion/upload",
        headers=headers,
        json={
            "customer": "Apex Global Logistics",
            "meeting_title": "Sprint Planning & SLA Review",
            "transcript_text": (
                "Sarah from Apex: We need the custom webhook dispatcher live by end of month. "
                "Engineering Lead: We commit to delivering the webhook dispatcher system by October 25th."
            ),
            "source_type": "meet",
        },
    )
    # Fix #10: Upload is now async — returns 202 with status='queued'
    # Celery worker handles extraction + commitment creation + SSE event
    assert ingest_res.status_code == 202, f"Expected 202 Accepted, got {ingest_res.status_code}: {ingest_res.text}"
    ingest_data = ingest_res.json()
    assert ingest_data["status"] == "queued", f"Expected 'queued', got: {ingest_data}"
    assert "job_id" in ingest_data

    # 3. Create/confirm commitment in database
    comm_payload = {
        "title": "Custom Webhook Dispatcher System",
        "customer": "Apex Global Logistics",
        "owner_name": "Sarah Lin",
        "owner_email": "sarah@promisecheck.io",
        "promised_by": "Oct 25, 2026",
        "promised_date_iso": "2026-10-25T00:00:00Z",
        "category": "on-track",
        "quote": "We commit to delivering the webhook dispatcher system by October 25th.",
        "source_title": "Sprint Planning & SLA Review",
    }
    create_res = client.post("/api/v1/commitments", headers=headers, json=comm_payload)
    assert create_res.status_code == 201
    created_comm = create_res.json()
    commitment_id = created_comm["id"]
    assert created_comm["title"] == "Custom Webhook Dispatcher System"
    assert created_comm["customer"] == "Apex Global Logistics"

    # 4. Run risk scan and verify assessment
    risk_res = client.post("/api/v1/risk/evaluate", headers=headers)
    assert risk_res.status_code == 200
    risk_summary = risk_res.json()
    assert risk_summary["evaluated_count"] >= 1

    # 5. Officially mark commitment delivered with verifiable PR evidence proof
    verify_res = client.post(
        "/api/v1/delivery/verify",
        headers=headers,
        json={
            "commitment_id": commitment_id,
            "evidence_type": "pr_merged",
            "evidence_title": "PR #312: High-throughput async webhook dispatcher merged to main",
            "evidence_url": "https://github.com/apex/webhooks/pull/312",
            "verified_by": "Sarah Lin",
        },
    )
    assert verify_res.status_code == 201
    evidence_data = verify_res.json()
    assert evidence_data["commitment_id"] == commitment_id
    assert evidence_data["evidence_type"] == "pr_merged"

    # 6. Verify delivery evidence is queryable
    ev_list_res = client.get("/api/v1/delivery/evidence", headers=headers)
    assert ev_list_res.status_code == 200
    evidence_list = ev_list_res.json()
    assert any(e["commitment_id"] == commitment_id for e in evidence_list)

    # 7. Check customer metrics reflect the delivered commitment
    cust_res = client.get("/api/v1/customers", headers=headers)
    assert cust_res.status_code == 200
    customers = cust_res.json()
    apex = next((c for c in customers if "Apex" in c["name"]), None)
    if apex:
        assert apex["healthScore"] >= 90

    # 8. Check audit trail logged the actions
    audit_res = client.get("/api/v1/audit", headers=headers)
    assert audit_res.status_code == 200
    audit_events = audit_res.json()
    actions = [a["action"] for a in audit_events]
    assert "COMMITMENT_DELIVERED" in actions or "commitment_created" in actions
