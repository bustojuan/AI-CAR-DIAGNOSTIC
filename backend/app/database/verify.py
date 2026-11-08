"""Readiness verification without an LLM call: python -m app.database.verify."""

import asyncio
import json

from sqlalchemy import inspect, text

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.core.exceptions import AppError
from app.database.models import Base
from app.database.session import inspect_database
from app.repositories.postgres import PostgresStore


async def verify():
    store = PostgresStore(Settings())
    try:
        await store.initialize()
        async with store.engine.connect() as connection:
            info = await inspect_database(connection)
            version = await connection.scalar(text("SELECT version()"))
            tables = await connection.run_sync(
                lambda sync: inspect(sync).get_table_names(
                    schema=store.settings.database_schema or "public"
                )
            )
            if set(Base.metadata.tables) - set(tables):
                raise AppError(
                    503, "incomplete_database_schema", "Missing required application tables."
                )
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "postgresql": version,
                        **info,
                        "application_tables": sorted(Base.metadata.tables),
                    },
                    indent=2,
                )
            )
    finally:
        await store.close()


if __name__ == "__main__":
    try:
        with asyncio.Runner(loop_factory=selector_loop) as runner:
            runner.run(verify())
    except AppError as exc:
        print(f"{exc.code}: {exc.message}")
        raise SystemExit(1) from None
