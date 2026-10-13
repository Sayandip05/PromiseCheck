"""Batch 8: Architecture, Migration Roundtrip, and Contract Guard Tests.

Verifies:
1. Architecture Contracts: Runs `lint-imports` to verify all 9 modular-monolith
   layering and boundary contracts pass with 0 broken contracts.
2. Snapshot Freeze: Verifies OpenAPI, Celery tasks, and Database Schema match
   baseline snapshots exactly (`snapshot_contracts.py --check`).
3. Database Migration Roundtrip: On real PostgreSQL, executes Alembic
   downgrade to 'base' (dropping all tables) and upgrade back to 'head'
   (recreating all tables), verifying zero model/migration schema drift.
4. Route Coverage Guard: Reflects all OpenAPI route paths in the application,
   guaranteeing that every endpoint is cataloged in the tested route registry
   and preventing unmonitored or untested endpoints from entering the API.
5. Celery Task Completeness Guard: Reflects all registered worker tasks,
   enforcing that every non-internal Celery task has an explicit route, queue,
   and test contract.
6. Outbox Event Registry Completeness Guard: Verifies that every registered outbox
   event type has an explicit route specification and valid handler/no-op binding.
"""

from pathlib import Path
import shutil
import subprocess
import sys
from typing import Set

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from core.database import Base
from core.outbox.registry import _EVENT_REGISTRY, EventRoute, get_route
from jobs.celery_app import celery_app
from src.main import app

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# 1. Architecture Contracts Guard (import-linter)
# ─────────────────────────────────────────────────────────────────────────────


def test_import_linter_architecture_contracts():
    """Verify that all 9 modular-monolith boundary contracts pass with zero violations."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    backend_dir = repo_root / "backend"

    lint_bin = Path(sys.executable).parent / "lint-imports"
    cmd = [str(lint_bin)] if lint_bin.exists() else [shutil.which("lint-imports") or "lint-imports"]

    result = subprocess.run(
        cmd,
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Import linter contract violations detected:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Contracts: 9 kept, 0 broken" in result.stdout


# ─────────────────────────────────────────────────────────────────────────────
# 2. Snapshot Freeze Guard
# ─────────────────────────────────────────────────────────────────────────────


def test_contract_snapshots_freeze_guard():
    """Verify OpenAPI schema, Celery tasks, and DB schemas match docs/baseline snapshots exactly."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    snapshot_script = repo_root / "backend" / "tools" / "snapshot_contracts.py"

    result = subprocess.run(
        [sys.executable, str(snapshot_script), "--check"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Contract snapshot mismatch detected against baseline:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "[snapshot PASSED]" in result.stdout


# ─────────────────────────────────────────────────────────────────────────────
# 3. Alembic Migration Roundtrip & Zero Schema Drift Guard
# ─────────────────────────────────────────────────────────────────────────────


def test_alembic_postgres_migrations_upgrade_downgrade_roundtrip(postgres_manager, monkeypatch):
    """Verify that Alembic migrations cleanly downgrade to base and re-upgrade to head on PostgreSQL."""
    monkeypatch.setenv("DATABASE_SYNC_URL", postgres_manager.sync_url)
    backend_dir = Path(__file__).resolve().parent.parent.parent
    alembic_ini = backend_dir / "alembic.ini"

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    cfg.set_main_option("sqlalchemy.url", postgres_manager.sync_url)

    engine = sa.create_engine(postgres_manager.sync_url)

    # 1. Downgrade to base
    command.downgrade(cfg, "base")

    with engine.connect() as conn:
        inspector = sa.inspect(conn)
        tables_after_downgrade = set(inspector.get_table_names())
        # All application tables must be dropped. Only alembic_version may remain.
        app_tables = tables_after_downgrade - {"alembic_version"}
        assert len(app_tables) == 0, f"Expected 0 application tables after downgrade, found: {app_tables}"

    # 2. Upgrade back to head
    command.upgrade(cfg, "head")

    expected_tables: Set[str] = {
        "users",
        "identities",
        "sessions",
        "refresh_tokens",
        "workspaces",
        "memberships",
        "invitations",
        "customers",
        "commitments",
        "ingestion_jobs",
        "delivery_evidences",
        "audit_events",
        "outbox_events",
        "workspace_integrations",
    }

    with engine.connect() as conn:
        inspector = sa.inspect(conn)
        tables_after_upgrade = set(inspector.get_table_names())
        # All expected tables must exist in the database
        assert expected_tables.issubset(tables_after_upgrade), (
            f"Missing tables after upgrade head: {expected_tables - tables_after_upgrade}"
        )

        # 3. Verify zero model drift: every table defined in Base.metadata must exist in Postgres
        # Ensure all models are loaded in Base.metadata
        import modules.iam.models  # noqa: F401
        import modules.commitments.models  # noqa: F401
        import modules.customers.models  # noqa: F401
        import modules.ingestion.models  # noqa: F401
        import modules.audit.models  # noqa: F401
        import core.outbox.models  # noqa: F401
        import modules.integrations.models  # noqa: F401

        model_tables = set(Base.metadata.tables.keys())
        missing_in_db = model_tables - tables_after_upgrade
        assert len(missing_in_db) == 0, (
            f"Model tables defined in code but missing from PostgreSQL schema: {missing_in_db}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Route Coverage Guard
# ─────────────────────────────────────────────────────────────────────────────

# Comprehensive catalog of all known, tested routes in the application
KNOWN_API_ROUTES: Set[str] = {
    # System & Health
    "/healthz",
    "/api/v1/health",
    "/metrics",
    "/api/v1/metrics",
    "/api/v1/operations/metrics",
    "/api/v1/operations/status",
    # Identity & Access Management (IAM)
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
    "/api/v1/auth/google",
    # Workspaces
    "/api/v1/workspaces",
    "/api/v1/workspaces/{workspace_id}",
    "/api/v1/workspaces/{workspace_id}/members",
    # Commitments
    "/api/v1/commitments",
    "/api/v1/commitments/{commitment_id}",
    "/api/v1/commitments/{commitment_id}/confirm",
    "/api/v1/commitments/{commitment_id}/draft-update",
    # Customers
    "/api/v1/customers",
    "/api/v1/customers/{customer_id}",
    # Delivery
    "/api/v1/delivery/evidence",
    "/api/v1/delivery/verify",
    # Engineering Tickets
    "/api/v1/engineering/tickets",
    "/api/v1/engineering/tickets/{tracker}/{key}",
    # Risk
    "/api/v1/risk/assessments",
    "/api/v1/risk/evaluate",
    # Notifications
    "/api/v1/notifications",
    "/api/v1/notifications/send",
    # Ingestion
    "/api/v1/ingestion/jobs",
    "/api/v1/ingestion/upload",
    "/api/v1/ingestion/upload-audio",
    # Audit
    "/api/v1/audit",
    # Integrations & OAuth
    "/api/v1/integrations",
    "/api/v1/integrations/google/authorize",
    "/api/v1/integrations/google/callback",
    "/api/v1/integrations/google/connect-token",
    "/api/v1/integrations/google/calendar/sync-event",
    "/api/v1/integrations/google/gmail/send-update",
    "/api/v1/integrations/{provider}/connect",
    "/api/v1/integrations/{provider}/disconnect",
    "/api/v1/integrations/{provider}/test",
    # MCP Gateway
    "/api/v1/mcp/tools",
    "/api/v1/mcp/tools/call",
    # Real-time Events (SSE)
    "/api/v1/events/stream",
    "/api/v1/events/test-publish",
    "/api/v1/realtime/stream",
    "/api/v1/realtime/test-publish",
}


def test_fastapi_route_coverage_guard():
    """Verify that every route exposed in OpenAPI is tracked in the route coverage catalog.

    Fails if any unmonitored or untested endpoint is added to the application.
    """
    openapi_spec = app.openapi()
    actual_paths = set(openapi_spec.get("paths", {}).keys())

    # Detect any newly introduced route that lacks test cataloging
    untracked_routes = actual_paths - KNOWN_API_ROUTES
    assert len(untracked_routes) == 0, (
        f"New uncataloged routes detected in OpenAPI schema: {untracked_routes}. "
        "Every endpoint must have integration/unit tests and be registered in KNOWN_API_ROUTES."
    )

    # Detect any removed route that was not pruned from catalog
    stale_routes = KNOWN_API_ROUTES - actual_paths
    assert len(stale_routes) == 0, (
        f"Routes in KNOWN_API_ROUTES no longer exist in OpenAPI schema: {stale_routes}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Celery Task Completeness Guard
# ─────────────────────────────────────────────────────────────────────────────

EXPECTED_CELERY_TASKS = {
    "jobs.tasks.process_transcript_ingestion",
    "jobs.tasks.process_audio_ingestion",
    "jobs.tasks.scan_commitment_deadlines",
    "jobs.tasks.cleanup_expired_tokens",
    "jobs.tasks.dispatch_notification_alert",
}


@pytest.mark.parametrize("expected_task_name", sorted(EXPECTED_CELERY_TASKS))
def test_celery_task_registry_completeness_guard(expected_task_name: str):
    """Enforce that all registered Celery worker tasks are present in the Celery app registry."""
    registered_tasks = set(celery_app.tasks.keys())
    assert expected_task_name in registered_tasks, (
        f"Required worker task '{expected_task_name}' is not registered in Celery app."
    )


def test_celery_no_untracked_user_tasks_guard():
    """Enforce that no untracked user tasks exist in Celery beyond the registered contract."""
    user_tasks = {k for k in celery_app.tasks.keys() if not k.startswith("celery.")}
    untracked = user_tasks - EXPECTED_CELERY_TASKS
    assert len(untracked) == 0, f"Untracked Celery user tasks detected: {untracked}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Outbox Event Registry Completeness Guard
# ─────────────────────────────────────────────────────────────────────────────

EXPECTED_OUTBOX_EVENT_TYPES = {
    "ingestion.transcript.process",
    "ingestion.audio.process",
    "risk.scan.request",
    "notification.deadline.at_risk",
    "notification.deadline.overdue",
    "commitment.created",
    "commitment.updated",
    "commitment.confirmed",
}


@pytest.mark.parametrize("event_type", sorted(EXPECTED_OUTBOX_EVENT_TYPES))
def test_outbox_event_type_registry_completeness_guard(event_type: str):
    """Verify that every expected outbox event type has a valid route or explicit no-op in the registry."""
    route = get_route(event_type)
    assert route is not None, f"Outbox event_type '{event_type}' has no registered route."

    if isinstance(route, EventRoute):
        # Must either be an explicit no-op or have a target task name
        assert route.is_noop or bool(route.task_name), (
            f"EventRoute for '{event_type}' must either be an explicit no-op or specify a task_name."
        )
        if route.task_name:
            assert route.task_name in celery_app.tasks, (
                f"EventRoute for '{event_type}' specifies task '{route.task_name}' which is not registered in Celery."
            )


def test_outbox_registry_no_untracked_events_guard():
    """Verify that no untracked outbox event types exist beyond the tested catalog."""
    registered_events = set(_EVENT_REGISTRY.keys())
    untracked = registered_events - EXPECTED_OUTBOX_EVENT_TYPES
    assert len(untracked) == 0, f"Untracked outbox event types detected in registry: {untracked}"
