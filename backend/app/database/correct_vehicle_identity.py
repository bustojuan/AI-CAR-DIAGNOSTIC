"""Apply the owner's year/engine correction to the existing vehicle; no schema change."""

import argparse
import asyncio
import json

from sqlalchemy import select

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.database.models import VehicleRow
from app.database.session import make_engine, make_sessions
from app.models.vehicle import GOLF_ID, MVP_IDENTITY


async def correct(settings):
    engine = make_engine(settings)
    try:
        async with make_sessions(engine)() as session, session.begin():
            row = await session.scalar(
                select(VehicleRow).where(VehicleRow.id == GOLF_ID).with_for_update()
            )
            if row is None:
                raise ValueError("The existing configured vehicle was not found.")
            for field in ("manufacturer", "model", "engine", "fuel_type", "transmission"):
                if getattr(row, field).strip().casefold() != MVP_IDENTITY[field].casefold():
                    raise ValueError("Existing identity differs; automatic correction refused.")
            if row.model_year not in (2006, 2009) or (
                row.engine_code or ""
            ).strip().upper() not in (
                "",
                "CFFB",
            ):
                raise ValueError("An unexpected year or engine code requires review.")
            before = {"model_year": row.model_year, "engine_code": row.engine_code}
            row.model_year = MVP_IDENTITY["model_year"]
            row.engine_code = MVP_IDENTITY["engine_code"]
            await session.flush()
            return {
                "vehicle_id": str(row.id),
                "before": before,
                "after": {"model_year": row.model_year, "engine_code": row.engine_code},
                "history_preserved": True,
                "schema_changed": False,
            }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        with asyncio.Runner(loop_factory=selector_loop) as runner:
            result = runner.run(correct(Settings()))
        print(json.dumps(result, indent=2))
    except ValueError as error:
        parser.exit(1, f"{error}\n")
