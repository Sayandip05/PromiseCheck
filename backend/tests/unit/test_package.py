"""Test module importability without sys.path hacks."""

from src.core.config import settings
from src.core.database import Base
from src.jobs.celery_app import celery_app
from src.main import app


def test_package_exports() -> None:
    """Verify clean top-level imports."""
    assert app.version == "0.1.0"
    assert app.title == "PromiseCheck API"
    assert celery_app.main == "promisecheck"
    assert settings.APP_ENV in ["development", "testing", "production", "staging"]
    assert Base.metadata is not None
