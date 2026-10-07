"""Tests for Idempotency, Safe Retries, Concurrency Control, Tenancy Authorization, and Pagination."""

import uuid
import pytest
from fastapi.testclient import TestClient

from core.database import AsyncSessionLocal
from modules.commitments.models import Commitment
from modules.customers.models import Customer
from modules.workspaces.models import Workspace
from src.main import app


@pytest.fixture
def client(auth_client: TestClient) -> TestClient:
    return auth_client



def test_idempotency_retry_prevents_duplicate_commitments(client: TestClient):
    """Verify that retrying a commitment creation with Idempotency-Key returns cached response without duplicating records."""
    idempotency_key = f"test-idem-key-{uuid.uuid4().hex}"
    payload = {
        "title": "Idempotent Promise Delivery",
        "customer": "Apex Global",
        "promised_by": "Oct 15, 2026",
    }
    headers = {"Idempotency-Key": idempotency_key}

    # 1. First request creates the resource
    res1 = client.post("/api/v1/commitments", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["title"] == payload["title"]
    commitment_id = data1["id"]
    assert "idempotent-replayed" not in res1.headers

    # 2. Second request with identical key and payload (Simulated Network Retry)
    res2 = client.post("/api/v1/commitments", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res2.headers.get("idempotent-replayed") == "true"
    data2 = res2.json()
    # The returned ID and content must be identical to the first request
    assert data2["id"] == commitment_id
    assert data2["title"] == payload["title"]

    # 3. Third request with SAME idempotency key but ALTERED payload must be rejected
    res3 = client.post(
        "/api/v1/commitments",
        json={"title": "Hacked Different Payload", "customer": "Different Corp"},
        headers=headers,
    )
    assert res3.status_code == 422
    assert "Idempotency Conflict" in res3.text or "previously used" in res3.text


def test_idempotency_retry_customer_creation(client: TestClient):
    """Verify idempotency on customer accounts creation."""
    idempotency_key = f"cust-idem-{uuid.uuid4().hex}"
    payload = {
        "name": "Starlight Ventures",
        "owner": "Sarah Connor",
        "recent_promise": "Deliver Phase 1",
    }
    headers = {"Idempotency-Key": idempotency_key}

    # Initial request
    res1 = client.post("/api/v1/customers", json=payload, headers=headers)
    assert res1.status_code == 201
    cust_id = res1.json()["id"]

    # Retry
    res2 = client.post("/api/v1/customers", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res2.headers.get("idempotent-replayed") == "true"
    assert res2.json()["id"] == cust_id


def test_concurrency_control_optimistic_locking(client: TestClient):
    """Verify If-Match header validates ETag and blocks concurrent stale updates with HTTP 412."""
    # 1. Create a commitment
    res = client.post(
        "/api/v1/commitments",
        json={"title": "Concurrent Target Test", "customer": "Beta Corp"},
    )
    assert res.status_code == 201
    comm_id = res.json()["id"]

    # 2. GET the resource to receive the authoritative ETag
    get_res = client.get(f"/api/v1/commitments/{comm_id}")
    assert get_res.status_code == 200
    etag = get_res.headers.get("etag")
    assert etag is not None

    # 3. Try update with an OUTDATED / INVALID If-Match ETag -> Must fail with 412
    stale_etag = 'W/"stale-timestamp-etag"'
    fail_res = client.patch(
        f"/api/v1/commitments/{comm_id}",
        json={"title": "Stale Attempt"},
        headers={"If-Match": stale_etag},
    )
    assert fail_res.status_code == 412
    assert "Precondition Failed" in fail_res.text

    # 4. Update with matching ETag -> Succeeds and generates new ETag
    ok_res = client.patch(
        f"/api/v1/commitments/{comm_id}",
        json={"title": "Valid Update Under OCC"},
        headers={"If-Match": etag},
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["title"] == "Valid Update Under OCC"
    new_etag = ok_res.headers.get("etag")
    assert new_etag is not None


def test_customer_pagination_and_headers(client: TestClient):
    """Verify customers list endpoint enforces pagination parameters and RFC headers."""
    res = client.get("/api/v1/customers?page=1&page_size=2")
    assert res.status_code == 200
    assert "x-total-count" in res.headers
    assert res.headers.get("x-page") == "1"
    assert res.headers.get("x-page-size") == "2"
    items = res.json()
    assert isinstance(items, list)
    assert len(items) <= 2
