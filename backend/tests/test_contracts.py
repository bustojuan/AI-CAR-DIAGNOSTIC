import asyncio

import pytest
from pydantic import ValidationError

from app.integrations.mcp.interface import UnavailableTools
from app.integrations.rag.interface import UnavailableRetriever
from app.models.diagnostic import Assessment, Hypothesis
from app.models.vehicle import GOLF_ID, seed_vehicle
from app.repositories.memory import MemoryStore
from tests.conftest import assessment_data


async def test_unavailable_integrations():
    retrieval = await UnavailableRetriever().retrieve(seed_vehicle(), "workshop procedure", {})
    assert not retrieval.available and not retrieval.documents and retrieval.reason
    tools = await UnavailableTools().execute("search_parts", {"component": "glow plugs"})
    assert not tools.available and tools.reason


@pytest.mark.parametrize(
    "updates",
    [
        {"urgency_level": "critical"},
        {"urgency_level": "high", "professional_assistance_recommended": False},
        {"urgency_level": "certain"},
        {"confidence": 0.98},
    ],
)
def test_assessment_rejects_inconsistent_or_unvalidated_values(updates):
    with pytest.raises(ValidationError):
        Assessment.model_validate(assessment_data(**updates))


def test_hypothesis_cannot_be_confirmed_fault():
    data = assessment_data()["possible_causes"][0]
    data["label"] = "confirmed_fault"
    with pytest.raises(ValidationError):
        Hypothesis.model_validate(data)


async def test_memory_transactions_rollback_and_copy_isolation():
    store = MemoryStore()
    await store.initialize()
    await store.initialize()
    async with store.transaction() as repo:
        listed = await repo.list_vehicles()
        assert len(listed) == 1
        listed[0].mileage_km = 123
    with pytest.raises(RuntimeError):
        async with store.transaction() as repo:
            vehicle = await repo.get_vehicle(GOLF_ID)
            vehicle.mileage_km = 456
            await repo.save_vehicle(vehicle)
            raise RuntimeError("rollback")
    async with store.transaction() as repo:
        assert (await repo.get_vehicle(GOLF_ID)).mileage_km is None


async def test_memory_serializes_concurrent_updates():
    store = MemoryStore()
    await store.initialize()

    async def increment():
        async with store.transaction() as repo:
            vehicle = await repo.get_vehicle(GOLF_ID)
            await asyncio.sleep(0)
            vehicle.mileage_km = (vehicle.mileage_km or 0) + 1
            await repo.save_vehicle(vehicle)

    await asyncio.gather(increment(), increment())
    async with store.transaction() as repo:
        assert (await repo.get_vehicle(GOLF_ID)).mileage_km == 2
