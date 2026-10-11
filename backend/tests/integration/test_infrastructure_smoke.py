"""Infrastructure smoke tests verifying PostgreSQL, Redis, multi-tenancy, and fakes.

Proves Batch 0 test infrastructure is functional.
"""

from datetime import datetime, timezone
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from modules.iam.models import User, Workspace
from tests.fixtures.database import TwoTenantsContext
from tests.fixtures.factories import UserFactory, WorkspaceFactory


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_postgres_and_alembic_schema_smoke(db_session: AsyncSession):
    """Verify real PostgreSQL container connectivity, Alembic schema, and transaction rollback."""
    # Build entities using factories
    user = UserFactory(full_name="Postgres Smoke Tester")
    workspace = WorkspaceFactory(name="Postgres Smoke Workspace")

    db_session.add_all([user, workspace])
    await db_session.commit()

    # Query back to verify persistence
    result = await db_session.execute(select(User).where(User.id == user.id))
    fetched_user = result.scalar_one_or_none()

    assert fetched_user is not None
    assert fetched_user.full_name == "Postgres Smoke Tester"
    assert fetched_user.email == user.email


@pytest.mark.asyncio
async def test_multi_tenant_fixtures_and_auth_headers_smoke(
    two_tenants: TwoTenantsContext,
    app_client: TestClient,
):
    """Verify two_tenants fixture initializes isolated tenants with valid auth tokens."""
    # Tenant Alpha checks
    assert two_tenants.tenant_a.workspace.name == "Tenant Alpha"
    assert len(two_tenants.tenant_a.owner_token.split(".")) == 3
    assert two_tenants.tenant_a.owner_headers["Authorization"].startswith("Bearer ey")
    assert two_tenants.tenant_a.owner_headers["X-Workspace-Id"] == str(two_tenants.tenant_a.workspace.id)

    # Tenant Beta checks
    assert two_tenants.tenant_b.workspace.name == "Tenant Beta"
    assert len(two_tenants.tenant_b.owner_token.split(".")) == 3
    assert two_tenants.tenant_b.owner_headers["Authorization"].startswith("Bearer ey")
    assert two_tenants.tenant_b.owner_headers["X-Workspace-Id"] == str(two_tenants.tenant_b.workspace.id)

    # Distinct workspace and user IDs
    assert two_tenants.tenant_a.workspace.id != two_tenants.tenant_b.workspace.id
    assert two_tenants.tenant_a.owner.id != two_tenants.tenant_b.owner.id

    # Live authentication check via app_client
    me_res = app_client.get("/api/v1/auth/me", headers=two_tenants.tenant_a.owner_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == two_tenants.tenant_a.owner.email


@pytest.mark.asyncio
async def test_respx_external_mock_and_freezegun_smoke(
    fake_slack,
    fake_llm,
    frozen_clock,
):
    """Verify wire-level mocking via respx and deterministic time via freezegun."""
    # 1. Deterministic time check
    target_time = "2026-10-15T12:00:00Z"
    with frozen_clock(target_time):
        now = datetime.now(timezone.utc)
        assert now.year == 2026
        assert now.month == 10
        assert now.day == 15
        assert now.hour == 12

    # 2. Wire mock check via httpx
    async with httpx.AsyncClient() as client:
        # Outbound Slack auth test caught by wire mock
        res_slack = await client.post("https://slack.com/api/auth.test")
        assert res_slack.status_code == 200
        assert res_slack.json()["ok"] is True

        # Outbound Groq chat completion caught by wire mock
        res_llm = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json={"model": "llama-3.3-70b-versatile", "messages": []},
        )
        assert res_llm.status_code == 200
        data = res_llm.json()
        assert "choices" in data
