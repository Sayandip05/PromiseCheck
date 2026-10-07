"""Pytest shared fixtures configuration."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provision a clean test user, workspace, and valid bearer token."""
    import uuid
    from sqlalchemy.orm import Session
    from jobs.tasks import _sync_engine
    from modules.identity.models import User
    from modules.workspaces.models import Workspace, WorkspaceMember, Role
    from core.security import create_access_token

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
    """Run Celery tasks synchronously (inline) in all tests so no Redis broker is needed.

    This sets task_always_eager=True for the duration of each test and restores
    the original setting on teardown. In production, tasks use the Redis broker normally.
    """
    from jobs.celery_app import celery_app
    original = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = original

