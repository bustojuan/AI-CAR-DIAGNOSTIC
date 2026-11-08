import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ai.tool_workflow import automotive_tools
from app.core.exceptions import AppError
from app.integrations.mcp.interface import ToolResult
from app.main import create_app
from app.models.diagnostic import Diagnostic
from app.models.vehicle import GOLF_ID, seed_vehicle
from app.repositories.memory import MemoryRepository, MemoryStore
from app.repositories.postgres import PostgresDiagnosticRepository
from tests.conftest import FakeClient
from tests.mcp.test_ebay import configuration, item, provider


class TransientGateway:
    def __init__(self, service):
        self.service, self.calls = service, []

    async def status(self):
        return ToolResult(
            available=True, reason="Test provider", provider=self.service.provider.name
        )

    async def execute(self, name, arguments):
        self.calls.append(name)
        return await self.service.execute(name, arguments)


@pytest.mark.parametrize("selected", ["ebay", "ebay_sandbox"])
def test_parts_are_transient_and_diagnosis_never_receives_them(selected, caplog):
    caplog.set_level(logging.INFO)
    settings = configuration(automotive_provider=selected, mcp_enabled=True)
    service, requests = provider(sandbox=selected == "ebay_sandbox")
    tools, fake, store = TransientGateway(service), FakeClient(), MemoryStore()
    app = create_app(settings, store=store, llm_client=fake, tools=tools)
    with TestClient(app) as api:
        # The production fixture has a production URL; Sandbox uses its own URL.
        if selected == "ebay":
            parts = api.post(
                "/api/v1/parts/search",
                json={
                    "vehicle_id": str(GOLF_ID),
                    "component": "glow plugs",
                },
            )
            assert parts.status_code == 200 and parts.json()["parts"]
            assert parts.headers["cache-control"] == "no-store"
            assert not store.repository.diagnostics and not store.repository.conversations
            assert not fake.calls
        prior_calls = list(tools.calls)
        response = api.post(
            "/api/v1/diagnostics",
            json={
                "vehicle_id": str(GOLF_ID),
                "description": "Find replacement glow plugs and prices for cold starting.",
            },
        )
        assert response.status_code == 201
        report = response.json()
        assert tools.calls == prior_calls
        assert not report["tool_results"] and not report["mcp_available"]
        assert all(e["kind"] != "external_tool_result" for e in report["evidence_sources"])
        assert any("temporary queries in Parts" in text for text in report["limitations"])
        saved = api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}").json()
        conversation = api.get(f"/api/v1/conversations/{report['conversation_id']}").json()
        assert saved == report
        combined = str(saved) + str(conversation) + str(fake.calls)
        assert item()["itemId"] not in combined and item()["title"] not in combined
        assert item()["itemWebUrl"] not in combined and "test-seller" not in combined
        assert item()["title"] not in caplog.text and "test-seller" not in caplog.text
        assert item()["itemWebUrl"] not in caplog.text


@pytest.mark.parametrize("selected", ["ebay", "ebay_sandbox"])
async def test_workflow_itself_does_not_fetch_transient_offers(selected):
    class Forbidden:
        async def execute(self, *args):
            raise AssertionError("Persistent workflows cannot query eBay")

    result = await automotive_tools(
        "Find replacement glow plugs and prices",
        seed_vehicle(),
        Forbidden(),
        configuration(automotive_provider=selected),
    )
    assert result == []


@pytest.mark.parametrize("selected", ["ebay", "ebay_sandbox"])
async def test_both_repositories_refuse_transient_results_before_writing(client, selected):
    response = client.post(
        "/api/v1/diagnostics",
        json={"vehicle_id": str(GOLF_ID), "description": "Cold starting difficulty."},
    )
    report = Diagnostic.model_validate(response.json())
    service, _ = provider(sandbox=selected == "ebay_sandbox")
    result = await service.execute(
        "check_compatibility",
        {
            "vehicle": seed_vehicle().model_dump(
                mode="json",
                include={
                    "vehicle_id",
                    "manufacturer",
                    "model",
                    "model_year",
                    "engine",
                    "transmission",
                    "fuel_type",
                    "engine_code",
                },
            ),
            "part_id": "EBAY-123-0",
        },
    )
    report.tool_results = [result]
    memory = MemoryRepository()
    with pytest.raises(AppError, match="only be viewed temporarily"):
        await memory.save_diagnostic(report)
    assert not memory.diagnostics
    # A session without SQL methods proves the guard runs before any DB operation.
    postgres = PostgresDiagnosticRepository(SimpleNamespace(), "unused")
    with pytest.raises(AppError, match="only be viewed temporarily"):
        await postgres.save_diagnostic(report)


def test_parts_validation_and_provider_errors_are_not_cacheable(client):
    response = client.post("/api/v1/parts/prices", json={})
    assert response.status_code == 422 and response.headers["cache-control"] == "no-store"
    response = client.post("/api/v1/parts/prices", json={"part_id": "EBAY-123-0"})
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert not response.json()["available"]
