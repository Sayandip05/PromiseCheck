"""Database and tenancy fixtures for PostgreSQL, Redis, and multi-tenant test suites."""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from core.database import Base
from core.security import Role, create_access_token
from modules.iam.models import Membership, User, Workspace

ALL_TABLES = [
    "delivery_evidences",
    "commitments",
    "customers",
    "audit_events",
    "outbox_events",
    "workspace_integrations",
    "ingestion_jobs",
    "identities",
    "sessions",
    "refresh_tokens",
    "invitations",
    "memberships",
    "workspaces",
    "users",
    # Evidence lineage (FR-07 / NFR-08)
    "source_documents",
    "source_versions",
    "source_segments",
    "evidence_links",
    # Ticket sync (FR-11)
    "tickets",
    "commitment_tickets",
    "dependencies",
    # Approvals & exact-approval sending (FR-13 / FR-14)
    "notification_drafts",
    "approvals",
    "notification_attempts",
    # MCP surface (FR-17 / FR-18)
    "external_mcp_servers",
    "mcp_grants",
    # Retention & deletion (FR-20 / NFR-13)
    "deletion_jobs",
]


@dataclass
class TenantContext:
    """Encapsulates a tenant workspace with owner and member users and auth credentials."""

    workspace: Workspace
    owner: User
    member: User
    owner_token: str
    member_token: str
    owner_headers: dict[str, str]
    member_headers: dict[str, str]


@dataclass
class TwoTenantsContext:
    """Encapsulates two isolated tenants for cross-tenant authorization testing."""

    tenant_a: TenantContext
    tenant_b: TenantContext


class PostgresTestManager:
    """Manages the PostgreSQL test container and database lifecycle."""

    def __init__(self) -> None:
        self.container: PostgresContainer | None = None
        self.sync_url: str = ""
        self.async_url: str = ""
        self.sync_engine = None
        self.async_engine = None
        self.session_factory = None

    def start(self) -> None:
        # Check if an external test database is already provided via environment
        env_sync_url = os.getenv("TEST_DATABASE_SYNC_URL") or os.getenv("DATABASE_SYNC_URL")
        env_async_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

        if env_sync_url and "postgres" in env_sync_url:
            self.sync_url = env_sync_url
            self.async_url = env_async_url or env_sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        else:
            self.container = PostgresContainer("postgres:16-alpine")
            self.container.start()
            self.sync_url = self.container.get_connection_url()
            self.async_url = self.sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

        # Run Alembic migrations against the PostgreSQL schema
        self._run_alembic_upgrade()

        # Initialize engines
        self.sync_engine = create_engine(self.sync_url, pool_pre_ping=True)
        self.async_engine = create_async_engine(self.async_url, poolclass=NullPool)
        self.session_factory = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    def _run_alembic_upgrade(self) -> None:
        backend_dir = Path(__file__).resolve().parent.parent.parent
        alembic_ini_path = backend_dir / "alembic.ini"

        old_sync = os.environ.get("DATABASE_SYNC_URL")
        old_async = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_SYNC_URL"] = self.sync_url
            os.environ["DATABASE_URL"] = self.async_url
            cfg = Config(str(alembic_ini_path))
            cfg.set_main_option("script_location", str(backend_dir / "migrations"))
            cfg.set_main_option("sqlalchemy.url", self.sync_url)
            command.upgrade(cfg, "head")
        finally:
            if old_sync is not None:
                os.environ["DATABASE_SYNC_URL"] = old_sync
            else:
                os.environ.pop("DATABASE_SYNC_URL", None)
            if old_async is not None:
                os.environ["DATABASE_URL"] = old_async
            else:
                os.environ.pop("DATABASE_URL", None)

    def truncate_all_tables(self) -> None:
        """Truncate all application tables using cascade for fast test isolation."""
        if not self.sync_engine:
            return
        table_str = ", ".join(f'"{t}"' for t in ALL_TABLES)
        with self.sync_engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_str} CASCADE;"))

    def stop(self) -> None:
        if self.sync_engine:
            self.sync_engine.dispose()
        if self.container:
            self.container.stop()


# Session-wide PostgreSQL instance
_pg_manager: PostgresTestManager | None = None


def get_pg_manager() -> PostgresTestManager:
    global _pg_manager
    if _pg_manager is None:
        _pg_manager = PostgresTestManager()
        _pg_manager.start()
    return _pg_manager


def auth_headers_for(user: User, workspace: Workspace) -> dict[str, str]:
    """Build Authorization bearer headers for given user and workspace."""
    token = create_access_token(user_id=user.id, email=user.email)
    return {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": str(workspace.id),
    }
