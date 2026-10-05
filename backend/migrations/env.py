"""Alembic environment configuration."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from core.config import settings
from core.database import Base

from pathlib import Path

# Import every model module so they register on Base.metadata before autogenerate
# runs.  Without these imports, Alembic sees an empty metadata and generates a
# no-op migration.
import modules.identity.models  # noqa: F401
import modules.workspaces.models  # noqa: F401
import modules.commitments.models  # noqa: F401
import modules.customers.models  # noqa: F401
import modules.ingestion.models  # noqa: F401
import modules.delivery.models  # noqa: F401
import modules.audit.models  # noqa: F401
import modules.operations.models  # noqa: F401
import modules.outbox.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from sqlalchemy.engine import make_url

# Ensure sync url for alembic
_raw_sync_url = os.getenv("DATABASE_SYNC_URL", settings.DATABASE_SYNC_URL)
try:
    _url_obj = make_url(_raw_sync_url)
    if _url_obj.drivername.startswith("sqlite") and _url_obj.database and _url_obj.database.startswith("./"):
        _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
        _abs_path = str((_PROJECT_ROOT / _url_obj.database[2:]).resolve())
        sync_db_url = str(_url_obj.set(database=_abs_path))
    else:
        sync_db_url = _raw_sync_url
except Exception:
    sync_db_url = _raw_sync_url

config.set_main_option("sqlalchemy.url", sync_db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
