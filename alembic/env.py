from __future__ import with_statement

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import DATABASE_URL
from app.database.db import Base
from app.database.models.broadcast import BroadcastCampaign, BroadcastDelivery  # noqa: F401
from app.database.models.broadcast_job import BroadcastJob  # noqa: F401
from app.database.models.movie import Movie  # noqa: F401
from app.database.models.movie_base import MovieBase  # noqa: F401
from app.database.models.movie_code_counter import MovieCodeCounter  # noqa: F401
from app.database.models.pending_movie_request import PendingMovieRequest  # noqa: F401
from app.database.models.subscription import Subscription  # noqa: F401
from app.database.models.user import User  # noqa: F401
from app.database.models.user_action_log import UserActionLog  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
