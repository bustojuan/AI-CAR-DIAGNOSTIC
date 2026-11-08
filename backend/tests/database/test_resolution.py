import asyncio

import httpx
import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.main import create_app
from app.models.vehicle import GOLF_ID
from tests.conftest import FakeClient
from tests.database.conftest import migration_config

pytestmark = pytest.mark.database


async def test_resolution_and_case_aggregation_persist_across_application_restart(db_settings):
    fake = FakeClient()
    first = create_app(db_settings, llm_client=fake)
    async with (
        first.router.lifespan_context(first),
        httpx.AsyncClient(transport=httpx.ASGITransport(first), base_url="http://test") as api,
    ):
        moderate = (
            await api.post(
                "/api/v1/diagnostics",
                json={
                    "vehicle_id": str(GOLF_ID),
                    "description": "Starting is difficult when cold.",
                },
            )
        ).json()
        fake.assessment.update(
            urgency_level="high", driving_recommendation="inspection_before_driving"
        )
        high = (
            await api.post(
                f"/api/v1/conversations/{moderate['conversation_id']}/messages",
                json={"description": "Starting has become more difficult."},
            )
        ).json()
        critical = (
            await api.post(
                "/api/v1/diagnostics",
                json={
                    "vehicle_id": str(GOLF_ID),
                    "description": "My brakes have failed.",
                },
            )
        ).json()
        resolved = await api.post(
            f"/api/v1/conversations/{critical['conversation_id']}/resolve",
            json={
                "expected_latest_diagnostic_id": critical["diagnostic_id"],
                "resolution_note": (
                    "User reports a workshop visit; repair is not independently verified."
                ),
            },
        )
        assert resolved.status_code == 200, resolved.text
        expected = (await api.get(f"/api/v1/vehicles/{GOLF_ID}/case-history")).json()
        assert expected["vehicle_urgency"]["urgency_level"] == "high"
        assert expected["vehicle_urgency"]["active_case_count"] == 1
        assert expected["vehicle_urgency"]["resolved_case_count"] == 1
        assert (
            next(c for c in expected["cases"] if c["conversation_id"] == high["conversation_id"])[
                "assessment_count"
            ]
            == 2
        )
    second = create_app(db_settings, llm_client=FakeClient())
    async with (
        second.router.lifespan_context(second),
        httpx.AsyncClient(transport=httpx.ASGITransport(second), base_url="http://test") as api,
    ):
        assert (await api.get(f"/api/v1/vehicles/{GOLF_ID}/case-history")).json() == expected
        for report in (moderate, high, critical):
            assert (
                await api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}")
            ).json() == report
        reopened = await api.post(
            f"/api/v1/conversations/{critical['conversation_id']}/reopen",
            json={
                "expected_latest_diagnostic_id": critical["diagnostic_id"],
            },
        )
        assert reopened.status_code == 200
        assert (await api.get(f"/api/v1/vehicles/{GOLF_ID}/urgency")).json()[
            "urgency_level"
        ] == "critical"


async def test_concurrent_resolution_cannot_hide_a_new_critical_warning(db_settings):
    app = create_app(db_settings, llm_client=FakeClient())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        report = (
            await api.post(
                "/api/v1/diagnostics",
                json={
                    "vehicle_id": str(GOLF_ID),
                    "description": "Difficult cold starting.",
                },
            )
        ).json()
        cid = report["conversation_id"]
        critical, resolution = await asyncio.gather(
            api.post(
                f"/api/v1/conversations/{cid}/messages",
                json={"description": "There is smoke under the hood."},
            ),
            api.post(
                f"/api/v1/conversations/{cid}/resolve",
                json={"expected_latest_diagnostic_id": report["diagnostic_id"]},
            ),
        )
        assert critical.status_code == 201, critical.text
        assert resolution.status_code in (200, 409), resolution.text
        snapshot = (await api.get(f"/api/v1/vehicles/{GOLF_ID}/case-history")).json()
        assert snapshot["vehicle_urgency"]["urgency_level"] == "critical"
        assert snapshot["cases"][0]["resolution_status"] == "active"
        assert (
            await api.post(
                f"/api/v1/conversations/{cid}/resolve",
                json={
                    "expected_latest_diagnostic_id": report["diagnostic_id"],
                },
            )
        ).status_code == 409
        # Duplicate transitions are serialized, with exactly one state change.
        version = {"expected_latest_diagnostic_id": critical.json()["diagnostic_id"]}
        changes = await asyncio.gather(
            *[api.post(f"/api/v1/conversations/{cid}/resolve", json=version) for _ in range(2)]
        )
        assert sorted(r.status_code for r in changes) == [200, 409]


async def test_resolution_database_constraints(db_settings):
    app = create_app(db_settings, llm_client=FakeClient())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        created = (
            await api.post("/api/v1/conversations", json={"vehicle_id": str(GOLF_ID)})
        ).json()
        for assignment in (
            "resolution_status='unknown'",
            "resolution_status='resolved'",
            "resolved_at=now()",
            "resolution_note='unexpected active-case note'",
        ):
            async with app.state.store.sessions() as session:
                with pytest.raises(IntegrityError):
                    async with session.begin():
                        await session.execute(
                            text(f"UPDATE conversations SET {assignment} WHERE id=:id"),
                            {"id": created["conversation_id"]},
                        )


async def test_migration_backfills_existing_cases_without_changing_reports(db_settings):
    app = create_app(db_settings, llm_client=FakeClient())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        original = (
            await api.post(
                "/api/v1/diagnostics",
                json={
                    "vehicle_id": str(GOLF_ID),
                    "description": "The steering has failed.",
                },
            )
        ).json()
    engine = create_engine(db_settings.database_url.get_secret_value(), hide_parameters=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(f'SET LOCAL search_path TO "{db_settings.database_schema}", public')
            )
            config = migration_config(db_settings, connection)
            command.downgrade(config, "0004_urgency")
            command.upgrade(config, "head")
    finally:
        engine.dispose()
    second = create_app(db_settings, llm_client=FakeClient())
    async with (
        second.router.lifespan_context(second),
        httpx.AsyncClient(transport=httpx.ASGITransport(second), base_url="http://test") as api,
    ):
        snapshot = (await api.get(f"/api/v1/vehicles/{GOLF_ID}/case-history")).json()
        assert snapshot["cases"][0]["resolution_status"] == "active"
        assert snapshot["cases"][0]["resolved_at"] is None
        assert (
            await api.get(f"/api/v1/diagnostics/{original['diagnostic_id']}")
        ).json() == original
