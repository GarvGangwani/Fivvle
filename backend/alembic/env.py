"""Alembic environment — async-aware, reads DATABASE_URL from app.config."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import the application's Base and ALL models so Alembic sees them.
# Importing app.db.models triggers registration of all 9 model classes
# onto Base.metadata via the models/__init__.py re-exports.
from app.config import get_settings
from app.db import Base
import app.db.models  # noqa: F401 — side-effect import registers all models

# Alembic Config object — exposes alembic.ini values.
config = context.config

# Configure Python logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the DATABASE_URL from app settings into the Alembic config.
# Settings reads from .env (dev) or env vars (prod) — never hardcoded here.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Target metadata Alembic compares against the live DB to autogenerate diffs.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without connecting to the DB.

    Use case: producing a SQL file for manual review or staged deployment.
    Run with: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,            # detect column type changes
        compare_server_default=True,  # detect server_default changes
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using the async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Online mode — connects to the DB and applies migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
