"""No eBay response is persisted; safe diagnostic history still survives restart."""

import httpx
import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.database.models import DiagnosticRow, MessageRow
from app.main import create_app
from app.mcp.schemas import ToolVehicle
from app.models.diagnostic import Diagnostic
from app.models.vehicle import GOLF_ID, seed_vehicle
from tests.conftest import FakeClient
from tests.mcp.test_ebay import provider
from tests.mcp.test_retention import TransientGateway

pytestmark = pytest.mark.database


async def test_transient_parts_and_saved_diagnosis_across_restart(db_settings):
    settings = db_settings.model_copy(update={"mcp_enabled": True, "automotive_provider": "ebay"})
    service, _ = provider()
    tools = TransientGateway(service)
    app = create_app(settings, llm_client=FakeClient(), tools=tools)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        response = await api.post("/api/v1/parts/prices", json={"part_id": "EBAY-123456789012-0"})
        assert response.status_code == 200 and response.json()["prices"]
        assert response.headers["cache-control"] == "no-store"
        async with app.state.store.sessions() as session:
            assert await session.scalar(select(func.count()).select_from(DiagnosticRow)) == 0
            assert await session.scalar(select(func.count()).select_from(MessageRow)) == 0
        calls = list(tools.calls)
        response = await api.post(
            "/api/v1/diagnostics",
            json={
                "vehicle_id": str(GOLF_ID),
                "description": "Find replacement glow plugs and prices for cold starting.",
            },
        )
        assert response.status_code == 201
        report = response.json()
        assert report["tool_results"] == [] and tools.calls == calls
        poison = Diagnostic.model_validate(report)
        poison.tool_results = [
            await service.execute(
                "check_compatibility",
                {
                    "vehicle": seed_vehicle().model_dump(
                        mode="json", include=set(ToolVehicle.model_fields)
                    ),
                    "part_id": "EBAY-123456789012-0",
                },
            )
        ]
        with pytest.raises(AppError, match="only be viewed temporarily"):
            async with app.state.store.transaction() as repository:
                await repository.save_diagnostic(poison)
        async with app.state.store.sessions() as session:
            rows = (await session.scalars(select(DiagnosticRow))).all()
            assert len(rows) == 1 and rows[0].tool_results == []
    restarted = create_app(settings, llm_client=FakeClient(), tools=tools)
    async with (
        restarted.router.lifespan_context(restarted),
        httpx.AsyncClient(transport=httpx.ASGITransport(restarted), base_url="http://test") as api,
    ):
        loaded = await api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}")
        assert loaded.json() == report
        conversation = (await api.get(f"/api/v1/conversations/{report['conversation_id']}")).json()
        assert "test-seller" not in str(conversation) and "EBAY-123456789012-0" not in str(
            conversation
        )
