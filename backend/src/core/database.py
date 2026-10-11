"""Centralized database engine, session management, and Base models."""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import DateTime, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from core.config import settings

# Dialect compilation adapters for SQLite development fallback
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"


import os
from pathlib import Path

from sqlalchemy.engine import make_url

# Project root directory (parent of backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Async Engine for FastAPI request handling (loaded strictly from .env)
_raw_db_url = settings.DATABASE_URL or os.getenv("DATABASE_URL") or "sqlite+aiosqlite:///./promisecheck.db"
try:
    _url_obj = make_url(_raw_db_url)
    if _url_obj.drivername.startswith("sqlite") and _url_obj.database and _url_obj.database.startswith("./"):
        _abs_path = str((_PROJECT_ROOT / _url_obj.database[2:]).resolve())
        _db_url = str(_url_obj.set(database=_abs_path))
    else:
        _db_url = _raw_db_url
except Exception:
    _db_url = _raw_db_url

if _db_url.startswith("sqlite"):
    async_engine = create_async_engine(
        _db_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    async_engine = create_async_engine(
        _db_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30.0,
        pool_recycle=1800,
    )


# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Sync Engine and Session Factory for background workers & tasks
_raw_sync_url = (
    settings.DATABASE_SYNC_URL
    or os.getenv("DATABASE_SYNC_URL")
    or "sqlite:///./promisecheck.db"
)
try:
    _sync_url_obj = make_url(_raw_sync_url)
    if _sync_url_obj.drivername.startswith("sqlite") and _sync_url_obj.database and _sync_url_obj.database.startswith("./"):
        _abs_sync_path = str((_PROJECT_ROOT / _sync_url_obj.database[2:]).resolve())
        _db_sync_url = str(_sync_url_obj.set(database=_abs_sync_path))
    else:
        _db_sync_url = _raw_sync_url
except Exception:
    _db_sync_url = _raw_sync_url

_sync_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}
if "sqlite" in _db_sync_url:
    _sync_engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _sync_engine_kwargs["pool_size"] = 5
    _sync_engine_kwargs["max_overflow"] = 10

sync_engine = create_engine(_db_sync_url, **_sync_engine_kwargs)
_sync_engine = sync_engine
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarative class with standard UUID primary keys and UTC timestamps."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TenantMixin:
    """Enforces multi-tenant isolation with required workspace_id."""

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> tuple[bool, str]:
    """Execute a lightweight query to verify database connectivity for readiness checks."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as exc:
        return False, str(exc)
