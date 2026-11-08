import asyncio
from logging.config import fileConfig

from alembic import context
from pgvector.sqlalchemy import Vector

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.database.models import Base
from app.database.session import make_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
settings = config.attributes.get("settings") or Settings()
config.attributes["settings"] = settings


def compare_type(
    migration_context, inspected_column, metadata_column, inspected_type, metadata_type
):
    if isinstance(inspected_type, Vector) and isinstance(metadata_type, Vector):
        # Database vector(N) is authoritative; ORM is intentionally dimension-independent.
        return False
    return None


def run_migrations(connection):
    context.configure(
        connection=connection, target_metadata=Base.metadata, compare_type=compare_type
    )
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = make_engine(settings)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    if not settings.database_url:
        raise RuntimeError("Configure DATABASE_URL before running migrations")
    context.configure(
        url=settings.database_url.get_secret_value(),
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run_migrations(config.attributes["connection"])
else:
    with asyncio.Runner(loop_factory=selector_loop) as runner:
        runner.run(online())
