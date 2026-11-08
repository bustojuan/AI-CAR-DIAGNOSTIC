import httpx
import pytest

from app.integrations.mcp.client import MCPGateway
from app.mcp.schemas import INPUTS, AutomotiveResult, ToolVehicle
from app.models.vehicle import seed_vehicle


def vehicle_input():
    return seed_vehicle().model_dump(mode="json", include=set(ToolVehicle.model_fields))


async def test_real_http_initialize_discover_validate_and_invoke(mcp_http):
    gateway = MCPGateway(mcp_http)
    status = await gateway.status()
    assert status.available and status.demo_data and set(status.tools) == set(INPUTS)
    async with gateway.session() as session:
        initialized = await session.initialize()
        assert initialized.serverInfo.name == "Automotive tools"
        tools = (await session.list_tools()).tools
        assert {tool.name for tool in tools} == set(INPUTS)
        assert all(tool.outputSchema and tool.inputSchema for tool in tools)
        invalid = await session.call_tool("search_parts", {"input": {"component": "x"}})
        assert invalid.isError
        result = await session.call_tool(
            "search_parts",
            {
                "input": {
                    "vehicle": vehicle_input(),
                    "component": "calentadores",
                }
            },
        )
        assert not result.isError
        parsed = AutomotiveResult.model_validate(result.structuredContent)
        assert parsed.parts[0].part_id == "DEMO-001" and parsed.demo_data


async def test_real_langchain_tools_search_fitment_and_price(mcp_http):
    gateway = MCPGateway(mcp_http)
    search = await gateway.execute(
        "search_parts",
        {
            "vehicle": vehicle_input(),
            "component": "glow plugs",
        },
    )
    assert search.available and search.parts, search
    assert search.parts[0].compatibility == "unknown"
    part_id = search.parts[0].part_id
    fitment = await gateway.execute(
        "check_compatibility",
        {
            "vehicle": vehicle_input(),
            "part_id": part_id,
        },
    )
    assert vehicle_input()["engine_code"] == "CFFB"
    assert fitment.compatibility == "unknown" and fitment.missing_information == []
    prices = await gateway.execute("get_part_prices", {"part_id": part_id})
    assert prices.prices and prices.prices[0].verification == "synthetic", prices
    assert str(prices.prices[0].unit_price) == "12.34"


async def test_real_stdio_server_and_langchain_adapter(settings):
    settings.mcp_enabled = True
    settings.automotive_provider = "demo"
    settings.mcp_timeout_seconds = 30
    result = await MCPGateway(settings).execute(
        "search_parts",
        {
            "vehicle": vehicle_input(),
            "component": "battery",
        },
    )
    assert result.available and result.parts[0].part_id == "DEMO-002", result


async def test_http_requires_bearer_and_rejects_oversized_body(mcp_http):
    async with httpx.AsyncClient(trust_env=False) as http:
        unauthorized = await http.post(mcp_http.mcp_http_url, json={})
        assert unauthorized.status_code == 401
        assert unauthorized.headers["cache-control"] == "no-store"
        response = await http.post(
            mcp_http.mcp_http_url,
            content=b"x" * 70000,
            headers={
                "Authorization": "Bearer " + mcp_http.mcp_token.get_secret_value(),
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 413


async def test_client_rejects_unexpected_tools_and_inputs(mcp_http):
    gateway = MCPGateway(mcp_http)
    with pytest.raises(ValueError):
        await gateway.execute("run_shell", {})
    with pytest.raises(ValueError):
        await gateway.execute("get_part_prices", {"part_id": "DEMO-001", "url": "file:///etc"})


async def test_http_provider_mismatch_never_returns_demo_as_live(mcp_http):
    gateway = MCPGateway(mcp_http.model_copy(update={"automotive_provider": "unavailable"}))
    result = await gateway.execute("get_part_prices", {"part_id": "DEMO-001"})
    assert not result.available and not result.demo_data and not result.prices
    assert result.error_category == "invalid_response"
