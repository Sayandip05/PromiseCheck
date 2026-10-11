"""Pytest shared fixtures configuration.

Provides core fixtures for unit and integration testing:
- Real PostgreSQL testcontainer + Alembic migration runner
- Redis test database flusher
- Two-tenant fixtures with owner/member roles
- Fake HTTP servers via respx (LLM, STT, Slack, Jira, Linear, Google)
- Deterministic clock freezing via freezegun
- Factory-boy models
- Backward-compatible fixtures for existing suite
"""

import os
import uuid
from typing import AsyncGenerator, Callable, Generator
import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time
import respx
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from core.database import _sync_engine, get_db
from core.security import Role, create_access_token, hash_password
from modules.iam.models import Invitation, Membership, User, Workspace, WorkspaceMember
from sqlalchemy import Enum as SAEnum

# Align SQLAlchemy Enum with PostgreSQL lowercase enum values defined in migration 0001
Membership.__table__.c.role.type = SAEnum(Role, name="role", values_callable=lambda x: [e.value for e in x])
Invitation.__table__.c.role.type = SAEnum(Role, name="role", values_callable=lambda x: [e.value for e in x])
from tests.fixtures.database import (
    PostgresTestManager,
    TenantContext,
    TwoTenantsContext,
    auth_headers_for,
    get_pg_manager,
)
from tests.fixtures.factories import (
    CommitmentFactory,
    CustomerFactory,
    DeliveryEvidenceFactory,
    IntegrationFactory,
    MembershipFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.fixtures.fakes import (
    fake_google_server,
    fake_jira_server,
    fake_linear_server,
    fake_llm_server,
    fake_slack_server,
    fake_stt_server,
)


# ─────────────────────────────────────────────────────────────────────────────
# Backward-Compatible Fixtures (Unchanged for existing 66 tests)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provision a clean test user, workspace, and valid bearer token."""
    with Session(_sync_engine) as session:
        user = User(
            email=f"suite_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Suite User",
            is_active=True,
        )
        ws = Workspace(
            name="Suite Workspace",
            slug=f"suite-ws-{uuid.uuid4().hex[:8]}",
        )

        session.add_all([user, ws])
        session.flush()
        mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN)
        session.add(mem)
        session.commit()
        token = create_access_token(user_id=user.id, email=user.email)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_client(auth_headers: dict[str, str]) -> TestClient:
    """FastAPI TestClient pre-configured with valid bearer token for an active workspace."""
    tc = TestClient(app)
    tc.headers.update(auth_headers)
    return tc


@pytest.fixture(autouse=True)
def celery_eager_mode():
    """Run Celery tasks synchronously (inline) in tests.

    Sets task_always_eager=True for the duration of each test and restores original on teardown.
    """
    from jobs.celery_app import celery_app
    original = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = original


@pytest.fixture
def celery_eager():
    """Explicit helper fixture ensuring Celery runs tasks eagerly."""
    from jobs.celery_app import celery_app
    orig = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    yield celery_app
    celery_app.conf.task_always_eager = orig


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL & Database Session Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def postgres_manager() -> Generator[PostgresTestManager, None, None]:
    """Session-scoped real PostgreSQL container with Alembic migrations applied."""
    manager = get_pg_manager()
    yield manager
    # Teardown at end of test session
    manager.stop()


@pytest.fixture
async def db_session(postgres_manager: PostgresTestManager) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped AsyncSession connected to real PostgreSQL with truncation cleanup."""
    postgres_manager.truncate_all_tables()
    async with postgres_manager.session_factory() as session:
        yield session
    postgres_manager.truncate_all_tables()


@pytest.fixture
def sync_db_session(postgres_manager: PostgresTestManager) -> Generator[Session, None, None]:
    """Function-scoped sync Session connected to real PostgreSQL with truncation cleanup."""
    postgres_manager.truncate_all_tables()
    with Session(postgres_manager.sync_engine) as session:
        yield session
    postgres_manager.truncate_all_tables()


@pytest.fixture
def app_client(postgres_manager: PostgresTestManager) -> Generator[TestClient, None, None]:
    """FastAPI TestClient wired to the real PostgreSQL test database via dependency override."""
    async def _test_get_db():
        async with postgres_manager.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _test_get_db
    try:
        with TestClient(app) as tc:
            yield tc
    finally:
        app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# Redis Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def clean_redis():
    """Provides isolated Redis client on test database (DB 15) with flush per test."""
    import redis.asyncio as aioredis
    test_redis_url = os.getenv("TEST_REDIS_URL") or "redis://localhost:6379/15"
    r = aioredis.from_url(test_redis_url, decode_responses=True)
    try:
        await r.flushdb()
        yield r
    finally:
        await r.flushdb()
        await r.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# Multi-Tenant Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def auth_headers_helper() -> Callable[[User, Workspace], dict[str, str]]:
    """Helper function to build bearer headers for given user and workspace."""
    return auth_headers_for


@pytest.fixture
async def two_tenants(db_session: AsyncSession) -> TwoTenantsContext:
    """Provisions two completely isolated tenants in real PostgreSQL:

    - Tenant A: workspace_a, owner_a (Role.ADMIN), member_a (Role.MEMBER)
    - Tenant B: workspace_b, owner_b (Role.ADMIN), member_b (Role.MEMBER)
    """
    # Create Tenant A
    ws_a = Workspace(name="Tenant Alpha", slug=f"tenant-alpha-{uuid.uuid4().hex[:6]}")
    owner_a = User(
        email=f"owner_a_{uuid.uuid4().hex[:6]}@alpha.test",
        full_name="Alpha Owner",
        is_active=True,
        password_hash=hash_password("PassAlpha123!"),
    )
    member_a = User(
        email=f"member_a_{uuid.uuid4().hex[:6]}@alpha.test",
        full_name="Alpha Member",
        is_active=True,
        password_hash=hash_password("PassAlpha123!"),
    )
    db_session.add_all([ws_a, owner_a, member_a])
    await db_session.flush()

    mem_owner_a = Membership(workspace_id=ws_a.id, user_id=owner_a.id, role=Role.ADMIN)
    mem_member_a = Membership(workspace_id=ws_a.id, user_id=member_a.id, role=Role.MEMBER)
    db_session.add_all([mem_owner_a, mem_member_a])

    # Create Tenant B
    ws_b = Workspace(name="Tenant Beta", slug=f"tenant-beta-{uuid.uuid4().hex[:6]}")
    owner_b = User(
        email=f"owner_b_{uuid.uuid4().hex[:6]}@beta.test",
        full_name="Beta Owner",
        is_active=True,
        password_hash=hash_password("PassBeta123!"),
    )
    member_b = User(
        email=f"member_b_{uuid.uuid4().hex[:6]}@beta.test",
        full_name="Beta Member",
        is_active=True,
        password_hash=hash_password("PassBeta123!"),
    )
    db_session.add_all([ws_b, owner_b, member_b])
    await db_session.flush()

    mem_owner_b = Membership(workspace_id=ws_b.id, user_id=owner_b.id, role=Role.ADMIN)
    mem_member_b = Membership(workspace_id=ws_b.id, user_id=member_b.id, role=Role.MEMBER)
    db_session.add_all([mem_owner_b, mem_member_b])
    await db_session.commit()

    # Generate Tokens and Headers
    tok_oa = create_access_token(user_id=owner_a.id, email=owner_a.email)
    tok_ma = create_access_token(user_id=member_a.id, email=member_a.email)
    tok_ob = create_access_token(user_id=owner_b.id, email=owner_b.email)
    tok_mb = create_access_token(user_id=member_b.id, email=member_b.email)

    tenant_a = TenantContext(
        workspace=ws_a,
        owner=owner_a,
        member=member_a,
        owner_token=tok_oa,
        member_token=tok_ma,
        owner_headers={"Authorization": f"Bearer {tok_oa}", "X-Workspace-Id": str(ws_a.id)},
        member_headers={"Authorization": f"Bearer {tok_ma}", "X-Workspace-Id": str(ws_a.id)},
    )
    tenant_b = TenantContext(
        workspace=ws_b,
        owner=owner_b,
        member=member_b,
        owner_token=tok_ob,
        member_token=tok_mb,
        owner_headers={"Authorization": f"Bearer {tok_ob}", "X-Workspace-Id": str(ws_b.id)},
        member_headers={"Authorization": f"Bearer {tok_mb}", "X-Workspace-Id": str(ws_b.id)},
    )
    return TwoTenantsContext(tenant_a=tenant_a, tenant_b=tenant_b)


# ─────────────────────────────────────────────────────────────────────────────
# Mock Time & Wire HTTP Fakes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def frozen_clock():
    """Factory fixture returning a context manager that freezes time."""
    def _freeze(time_str: str = "2026-10-15T12:00:00Z"):
        return freeze_time(time_str)
    return _freeze


@pytest.fixture
def fake_llm(respx_mock: respx.MockRouter):
    """Configures respx mock for Groq LLM extraction."""
    return fake_llm_server(respx_mock)


@pytest.fixture
def fake_stt(respx_mock: respx.MockRouter):
    """Configures respx mock for Speech-To-Text audio transcription."""
    return fake_stt_server(respx_mock)


@pytest.fixture
def fake_slack(respx_mock: respx.MockRouter):
    """Configures respx mock for Slack API and webhooks."""
    return fake_slack_server(respx_mock)


@pytest.fixture
def fake_jira(respx_mock: respx.MockRouter):
    """Configures respx mock for Jira REST API."""
    return fake_jira_server(respx_mock)


@pytest.fixture
def fake_linear(respx_mock: respx.MockRouter):
    """Configures respx mock for Linear GraphQL API."""
    return fake_linear_server(respx_mock)


@pytest.fixture
def fake_google(respx_mock: respx.MockRouter):
    """Configures respx mock for Google OAuth and APIs."""
    return fake_google_server(respx_mock)
