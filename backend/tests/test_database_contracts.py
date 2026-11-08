from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.database.schemas import ChunkCreate, DocumentCreate
from app.main import create_app
from app.repositories.postgres import PostgresStore
from tests.database.conftest import require_test_url


def test_normal_runtime_selects_postgres_without_silent_memory_fallback(settings):
    assert isinstance(create_app(settings).state.store, PostgresStore)


async def test_missing_database_configuration_fails_cleanly(settings):
    store = PostgresStore(settings)
    with pytest.raises(AppError) as failure:
        await store.initialize()
    assert failure.value.code == "database_not_configured"


@pytest.mark.parametrize("url", ["sqlite:///local.db", "postgresql://u:p@localhost/car", "invalid"])
def test_only_psycopg_postgres_configuration_allowed(url):
    with pytest.raises(ValidationError) as failure:
        Settings(_env_file=None, database_url=url)
    assert url not in str(failure.value)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@localhost/car_diagnostic",
        "sqlite:///test_car.db",
    ],
)
def test_destructive_database_tests_reject_non_test_database(url):
    with pytest.raises(ValueError):
        require_test_url(url)


def test_tests_reject_development_database_even_with_test_prefix():
    url = "postgresql+psycopg://u:p@localhost/test_car"
    with pytest.raises(ValueError):
        require_test_url(url, url)


def test_test_database_guard_ignores_credentials_and_localhost_alias():
    with pytest.raises(ValueError):
        require_test_url(
            "postgresql+psycopg://test:other@127.0.0.1/test_car",
            "postgresql+psycopg://dev:secret@localhost:5432/test_car",
        )


def test_frozen_migration_compiles_without_database_or_destructive_upgrade():
    from io import StringIO

    from alembic import command
    from sqlalchemy.orm import configure_mappers

    from app.database.models import Base
    from tests.database.conftest import migration_config

    configure_mappers()
    assert len(Base.metadata.tables) == 7
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://unused@localhost/offline"
    )
    config = migration_config(settings)
    buffer = StringIO()
    config.output_buffer = buffer
    command.upgrade(config, "head", sql=True)
    sql = buffer.getvalue()
    assert "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public" in sql
    assert "VECTOR(1536)" in sql
    assert sql.count("CREATE TABLE") == 8  # Includes Alembic version table.
    assert "CREATE TRIGGER conversation_status_transition" in sql
    assert "DROP TABLE" not in sql


def test_document_and_embedding_validation():
    data = dict(
        title="Generic",
        source_name="Fixture",
        document_type="txt",
        evidence_type="generic_reference",
        language="en",
        content_hash="a" * 64,
    )
    with pytest.raises(ValidationError):
        DocumentCreate(**data, manufacturer="Volkswagen")
    with pytest.raises(ValidationError):
        DocumentCreate(**data, model_year_start=2006, model_year_end=2005)
    empty = ChunkCreate(
        document_id=uuid4(), chunk_index=0, content="Fixture", content_hash="b" * 64
    )
    empty.validate_dimensions(1536)
    with pytest.raises(ValueError):
        empty.model_copy(update={"embedding_model": "unavailable"}).validate_dimensions(1536)
    with pytest.raises(ValueError):
        empty.model_copy(
            update={
                "embedding": [float("nan")] * 1536,
                "embedding_model": "synthetic",
                "embedding_dimensions": 1536,
            }
        ).validate_dimensions(1536)
