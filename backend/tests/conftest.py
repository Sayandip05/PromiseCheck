"""Pytest shared fixtures configuration."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


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
