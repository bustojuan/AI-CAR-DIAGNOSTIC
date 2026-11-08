import pytest
from alembic import command
from sqlalchemy import create_engine, text

from tests.database.conftest import migration_config

pytestmark = pytest.mark.database


def test_migration_upgrade_repeat_and_downgrade_only_in_temporary_schema(db_settings):
    engine = create_engine(db_settings.database_url.get_secret_value(), hide_parameters=True)
    schema = db_settings.database_schema
    try:
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            config = migration_config(db_settings, connection)
            command.upgrade(config, "head")
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "0005_resolution"
            )
            command.check(config)
            command.downgrade(config, "base")
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema=:schema "
                        "AND table_name != 'alembic_version'"
                    ),
                    {"schema": schema},
                )
                == 0
            )
            assert (
                connection.scalar(text("SELECT count(*) FROM pg_extension WHERE extname='vector'"))
                == 1
            )
            command.upgrade(config, "head")
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema=:schema "
                        "AND table_name != 'alembic_version'"
                    ),
                    {"schema": schema},
                )
                == 7
            )
    finally:
        engine.dispose()
