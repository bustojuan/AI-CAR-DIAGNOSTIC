import os
import re
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import Settings

BACKEND = Path(__file__).resolve().parents[2]


def migration_config(settings, connection=None):
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["settings"] = settings
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def require_test_url(value: str, development_url: str | None = None):
    url = make_url(value)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").startswith("test_"):
        raise ValueError("TEST_DATABASE_URL must use PostgreSQL and a database named test_...")
    if development_url:
        development = make_url(development_url)

        def identity(item):
            host = "127.0.0.1" if item.host == "localhost" else item.host
            return host, item.port or 5432, item.database

        if identity(url) == identity(development):
            raise ValueError("Test and development databases must differ")
    return url


@pytest.fixture
def db_settings():
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL database named test_...")
    require_test_url(raw, os.getenv("DATABASE_URL"))
    schema = "test_phase2_" + uuid4().hex
    settings = Settings(
        _env_file=None,
        database_url=raw,
        database_schema=schema,
        openai_api_key=None,
        llm_max_retries=0,
    )
    engine = create_engine(raw, hide_parameters=True, connect_args={"connect_timeout": 5})
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            command.upgrade(migration_config(settings, connection), "head")
        yield settings
    finally:
        # Only this invocation's freshly allocated schema is ever removed.
        assert re.fullmatch(r"test_phase2_[0-9a-f]{32}", schema)
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
