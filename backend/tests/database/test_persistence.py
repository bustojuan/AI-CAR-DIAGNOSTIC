import asyncio
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.database.models import (
    ConversationRow,
    DiagnosticRow,
    HypothesisRow,
    MessageRow,
    VehicleRow,
)
from app.database.session import inspect_database
from app.main import create_app
from app.models.conversation import Conversation
from app.models.vehicle import GOLF_ID, seed_vehicle
from app.repositories.postgres import PostgresStore
from tests.conftest import FakeClient

pytestmark = pytest.mark.database


async def test_connect_migrate_vector_and_idempotent_seed(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        await store.initialize()
        assert await store.ready()
        async with store.engine.connect() as connection:
            info = await inspect_database(connection)
            assert info["revision"] == "0005_resolution"
            assert info["pgvector_version"]
            assert info["embedding_dimensions"] == 1536
            count = await connection.scalar(
                select(func.count()).select_from(VehicleRow).where(VehicleRow.id == GOLF_ID)
            )
            assert count == 1
        async with store.transaction() as repository:
            vehicle = await repository.get_vehicle(GOLF_ID)
            assert (
                vehicle.engine_code == "CFFB"
                and vehicle.power_output is None
                and vehicle.vin is None
            )
    finally:
        await store.close()


async def test_api_restart_preserves_vehicle_conversation_reports_and_hypotheses(db_settings):
    fake = FakeClient()
    first = create_app(db_settings, llm_client=fake)
    async with (
        first.router.lifespan_context(first),
        httpx.AsyncClient(transport=httpx.ASGITransport(first), base_url="http://test") as api,
    ):
        health = await api.get("/api/v1/health")
        assert health.status_code == 200 and health.json()["persistence"] == "postgresql"
        created = await api.post(
            "/api/v1/vehicles", json=seed_vehicle().model_dump(mode="json", exclude={"vehicle_id"})
        )
        assert created.status_code == 201, created.text
        vehicle_id = created.json()["vehicle_id"]
        updated = await api.patch(f"/api/v1/vehicles/{vehicle_id}", json={"mileage_km": 181000})
        assert updated.status_code == 200
        response = await api.post(
            "/api/v1/diagnostics",
            json={
                "vehicle_id": vehicle_id,
                "description": "Slow cranking on cold mornings.",
                "dtcs": ["p0380"],
                "mileage_km": 181000,
            },
        )
        assert response.status_code == 201, response.text
        report = response.json()
        assert report["urgency_assessment"]["level"] == report["urgency_level"]
        assert report["urgency_assessment"]["missing_safety_information"]
        cid, did = report["conversation_id"], report["diagnostic_id"]
        followup = await api.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"description": "It starts normally when warm."},
        )
        assert followup.status_code == 201, followup.text
        expected_history = (await api.get(f"/api/v1/conversations/{cid}")).json()
    # A new app, engine and pool: no Python persistence state is reused.
    second = create_app(db_settings, llm_client=FakeClient())
    async with (
        second.router.lifespan_context(second),
        httpx.AsyncClient(transport=httpx.ASGITransport(second), base_url="http://test") as api,
    ):
        assert (await api.get(f"/api/v1/vehicles/{vehicle_id}")).json() == updated.json()
        assert (await api.get(f"/api/v1/diagnostics/{did}")).json() == report
        history = (await api.get(f"/api/v1/conversations/{cid}")).json()
        assert history == expected_history
        assert [message["role"] for message in history["messages"]] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert "P0380" in history["messages"][0]["content"]
        assert len(history["diagnostic_ids"]) == 2
        async with second.state.store.sessions() as session:
            rows = list(
                await session.scalars(select(HypothesisRow).order_by(HypothesisRow.display_order))
            )
            assert len(rows) == 2
            assert rows[0].uncertainty == "possible"
            assert (await session.get(DiagnosticRow, did)).model_name == db_settings.openai_model
            assert (await session.get(DiagnosticRow, did)).urgency_assessment == report[
                "urgency_assessment"
            ]


async def test_historical_report_without_urgency_detail_remains_readable_after_restart(db_settings):
    first = create_app(db_settings, llm_client=FakeClient())
    async with (
        first.router.lifespan_context(first),
        httpx.AsyncClient(transport=httpx.ASGITransport(first), base_url="http://test") as api,
    ):
        response = await api.post(
            "/api/v1/diagnostics",
            json={
                "vehicle_id": str(GOLF_ID),
                "description": "Difficulty starting when cold.",
            },
        )
        assert response.status_code == 201
        original = response.json()
        async with first.state.store.sessions() as session, session.begin():
            row = await session.get(DiagnosticRow, original["diagnostic_id"])
            row.urgency_assessment = None  # A pre-0004 row has no invented detail.
    second = create_app(db_settings, llm_client=FakeClient())
    async with (
        second.router.lifespan_context(second),
        httpx.AsyncClient(transport=httpx.ASGITransport(second), base_url="http://test") as api,
    ):
        loaded = await api.get(f"/api/v1/diagnostics/{original['diagnostic_id']}")
        assert loaded.status_code == 200
        assert loaded.json() == {**original, "urgency_assessment": None}


async def test_full_transaction_rollback_on_provider_failure(db_settings):
    fake = FakeClient()
    fake.failure = AppError(504, "llm_timeout", "Timed out")
    app = create_app(db_settings, llm_client=fake)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        response = await api.post(
            "/api/v1/diagnostics",
            json={"vehicle_id": str(GOLF_ID), "description": "Slow starting."},
        )
        assert response.status_code == 504
        async with app.state.store.sessions() as session:
            for row_type in (ConversationRow, MessageRow, DiagnosticRow, HypothesisRow):
                assert await session.scalar(select(func.count()).select_from(row_type)) == 0


async def test_database_rejects_nonexistent_vehicle_and_rolls_back(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        cid = uuid4()
        with pytest.raises(AppError) as failure:
            async with store.transaction() as repository:
                await repository.save_conversation(
                    Conversation(conversation_id=cid, vehicle_id=uuid4())
                )
        assert failure.value.code == "database_conflict"
        async with store.transaction() as repository:
            assert await repository.get_conversation(cid) is None
            assert await repository.get_vehicle(GOLF_ID)
    finally:
        await store.close()


async def test_database_constraints_and_history_deletion_policy(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        async with store.transaction() as repository:
            conversation = Conversation(vehicle_id=GOLF_ID)
            await repository.save_conversation(conversation)
        async with store.sessions() as session:
            with pytest.raises(IntegrityError):
                async with session.begin():
                    await session.execute(
                        text("UPDATE vehicles SET mileage_km=-1 WHERE id=:id"), {"id": GOLF_ID}
                    )
        async with store.sessions() as session:
            with pytest.raises(IntegrityError):
                async with session.begin():
                    await session.execute(
                        text("DELETE FROM vehicles WHERE id=:id"), {"id": GOLF_ID}
                    )
        async with store.transaction() as repository:
            assert await repository.get_vehicle(GOLF_ID)
    finally:
        await store.close()


async def test_concurrent_conversation_turns_have_no_lost_or_duplicate_messages(db_settings):
    app = create_app(db_settings, llm_client=FakeClient())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        cid = (await api.post("/api/v1/conversations", json={"vehicle_id": str(GOLF_ID)})).json()[
            "conversation_id"
        ]
        responses = await asyncio.gather(
            *[
                api.post(f"/api/v1/conversations/{cid}/messages", json={"description": text})
                for text in ("Slow starting in cold weather.", "Slow cranking in the morning.")
            ]
        )
        assert all(response.status_code == 201 for response in responses)
        history = (await api.get(f"/api/v1/conversations/{cid}")).json()
        assert len(history["messages"]) == 4 and len(history["diagnostic_ids"]) == 2
        assert len({message["message_id"] for message in history["messages"]}) == 4


async def test_critical_advice_without_key_is_persisted(db_settings):
    app = create_app(db_settings)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        result = await api.post(
            "/api/v1/diagnostics",
            json={"vehicle_id": str(GOLF_ID), "description": "My brake pedal goes to the floor."},
        )
        assert result.status_code == 201
        report = result.json()
        assert report["urgency_level"] == "critical"
        assert (await api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}")).json() == report


async def test_dimension_mismatch_refuses_startup(db_settings):
    mismatched = db_settings.model_copy(update={"embedding_dimensions": 16})
    store = PostgresStore(mismatched)
    with pytest.raises(AppError) as failure:
        await store.initialize()
    assert failure.value.code == "embedding_dimension_mismatch"
    assert store.engine is None


async def test_status_transitions_and_closed_conversations(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        conversation = Conversation(vehicle_id=GOLF_ID)
        async with store.transaction() as repo:
            await repo.save_conversation(conversation)
        async with store.sessions() as session, session.begin():
            await session.execute(
                text("UPDATE conversations SET status='completed' WHERE id=:id"),
                {"id": conversation.conversation_id},
            )
        with pytest.raises(AppError) as failure:
            async with store.transaction() as repo:
                await repo.get_conversation(conversation.conversation_id, lock=True)
        assert failure.value.code == "conversation_closed"
        async with store.sessions() as session:
            with pytest.raises(IntegrityError):
                async with session.begin():
                    await session.execute(
                        text("UPDATE conversations SET status='active' WHERE id=:id"),
                        {"id": conversation.conversation_id},
                    )
    finally:
        await store.close()
