import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.exceptions import AppError


def make_engine(settings: Settings):
    if not settings.database_url:
        raise AppError(503, "database_not_configured", "Configure DATABASE_URL for PostgreSQL.")
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db_echo else logging.WARNING
    )
    options = "-ctimezone=UTC"
    if settings.database_schema:
        options += f" -csearch_path={settings.database_schema},public"
    connect_args = {"connect_timeout": settings.db_connect_timeout, "options": options}
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        connect_args=connect_args,
        hide_parameters=True,
    )


def make_sessions(engine):
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def inspect_database(connection) -> dict:
    version = await connection.scalar(
        text("SELECT extversion FROM pg_extension WHERE extname='vector'")
    )
    revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    dimension = await connection.scalar(
        text(
            "SELECT atttypmod FROM pg_attribute WHERE attrelid='document_chunks'::regclass "
            "AND attname='embedding' AND NOT attisdropped"
        )
    )
    return {"pgvector_version": version, "revision": revision, "embedding_dimensions": dimension}
