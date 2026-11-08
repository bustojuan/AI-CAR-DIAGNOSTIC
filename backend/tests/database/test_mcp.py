"""Opt-in real PostgreSQL persistence across new application/store instances."""

import httpx
import pytest

from app.integrations.mcp.interface import ToolResult
from app.main import create_app
from app.mcp.providers import DemoProvider
from app.mcp.service import AutomotiveService
from app.models.vehicle import GOLF_ID
from tests.conftest import FakeClient

pytestmark = pytest.mark.database


class ProviderDouble:
    async def status(self):
        return ToolResult(available=True, reason="Test-only provider gateway")

    async def execute(self, tool, arguments):
        return await AutomotiveService(DemoProvider()).execute(tool, arguments)


async def test_validated_tool_results_survive_postgres_restart(db_settings):
    settings = db_settings.model_copy(update={"mcp_enabled": True, "automotive_provider": "demo"})
    app = create_app(settings, llm_client=FakeClient(), tools=ProviderDouble())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        response = await api.post(
            "/api/v1/diagnostics",
            json={
                "vehicle_id": str(GOLF_ID),
                "description": "Find replacement glow plugs and prices",
            },
        )
        assert response.status_code == 201, response.text
        report = response.json()
        assert len(report["tool_results"]) == 3
    restarted = create_app(settings, llm_client=FakeClient())
    async with (
        restarted.router.lifespan_context(restarted),
        httpx.AsyncClient(transport=httpx.ASGITransport(restarted), base_url="http://test") as api,
    ):
        loaded = await api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}")
        assert loaded.status_code == 200 and loaded.json() == report
