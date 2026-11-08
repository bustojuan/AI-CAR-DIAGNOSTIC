import asyncio
import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.integrations.mcp.client import BoundedStream, MCPGateway, validate_schema
from app.mcp.providers import DemoProvider
from app.mcp.schemas import GetPartPrices


@pytest.mark.parametrize("selected", ["demo", "ebay", "ebay_sandbox"])
async def test_stdio_only_forwards_selected_provider_credentials(selected, settings, monkeypatch):
    settings.automotive_provider = selected
    for key in (
        "ebay_client_id",
        "ebay_client_secret",
        "ebay_sandbox_client_id",
        "ebay_sandbox_client_secret",
    ):
        setattr(settings, key, SecretStr("test-" + key))
    monkeypatch.setenv("OPENAI_API_KEY", "never-forward-openai")
    monkeypatch.setenv("DATABASE_URL", "never-forward-database")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "never-inherit-unselected-secret")
    captured = {}

    @asynccontextmanager
    async def inspect_child(parameters):
        captured.update(parameters.env)
        raise ConnectionError("test transport")
        yield  # pragma: no cover

    monkeypatch.setattr("app.integrations.mcp.client.stdio_client", inspect_child)
    with pytest.raises(ConnectionError):
        async with MCPGateway(settings).session():
            pass
    assert "OPENAI_API_KEY" not in captured and "DATABASE_URL" not in captured
    expected = set()
    if selected in ("ebay", "ebay_sandbox"):
        prefix = "EBAY_SANDBOX" if selected == "ebay_sandbox" else "EBAY"
        expected = {prefix + "_CLIENT_ID", prefix + "_CLIENT_SECRET"}
    assert {key for key in captured if key.startswith("EBAY_")} == expected
    assert "never-inherit-unselected-secret" not in captured.values()


@pytest.mark.parametrize(
    "mode",
    [
        "oversize",
        "wrong_part",
        "wrong_price_context",
        "wrong_tool",
        "malformed",
        "failure",
        "missing_artifact",
        "timeout",
    ],
)
async def test_untrusted_mcp_response_cannot_escape_client_validation(
    mode, settings, monkeypatch, caplog
):
    settings.mcp_enabled = True
    settings.automotive_provider = "demo"
    settings.mcp_timeout_seconds = 0.02
    settings.mcp_max_result_bytes = 2048
    gateway = MCPGateway(settings)
    raw = (
        await DemoProvider().execute("get_part_prices", GetPartPrices(part_id="DEMO-001"))
    ).model_dump(mode="json")
    if mode == "oversize":
        raw["reason"] = "x" * 2000
    if mode == "wrong_part":
        raw["part_id"] = "DEMO-999"
    if mode == "wrong_price_context":
        raw["prices"][0]["country"] = "US"
    if mode == "wrong_tool":
        raw["tool"] = "check_compatibility"
    if mode == "malformed":
        raw = {"secret": "sensitive-tool-payload"}

    class Tool:
        async def ainvoke(self, arguments):
            if mode == "timeout":
                await asyncio.sleep(1)
            return SimpleNamespace(
                status="error" if mode == "failure" else "success",
                artifact=None if mode == "missing_artifact" else {"structured_content": raw},
            )

    @asynccontextmanager
    async def session():
        yield None

    async def registered_tools(session):
        return {"get_part_prices": Tool()}

    monkeypatch.setattr(gateway, "session", session)
    monkeypatch.setattr(gateway, "registered_tools", registered_tools)
    with caplog.at_level(logging.INFO):
        result = await gateway.execute("get_part_prices", {"part_id": "DEMO-001"})
    assert not result.available and not result.prices
    assert result.error_category == ("timeout" if mode == "timeout" else "invalid_response")
    assert "sensitive-tool-payload" not in caplog.text


async def test_http_wire_stream_is_bounded():
    stream = BoundedStream(httpx.ByteStream(b"x" * 20), limit=10)
    with pytest.raises(ValueError):
        async for _ in stream:
            pass


async def test_disabled_gateway_does_not_launch_server(settings, monkeypatch):
    gateway = MCPGateway(settings)

    def forbidden():
        raise AssertionError("Disabled gateway attempted a connection")

    monkeypatch.setattr(gateway, "session", forbidden)
    assert not (await gateway.status()).available
    result = await gateway.execute("get_part_prices", {"part_id": "DEMO-001"})
    assert not result.available and result.error_category == "mcp_unavailable"


@pytest.mark.parametrize(
    "schema",
    [
        {"$ref": "https://attacker.invalid/schema"},
        {"$defs": {"x": {"$ref": "file:///sensitive-file"}}},
        {"$id": "https://attacker.invalid/"},
        {"$dynamicRef": "#/x"},
        {"$recursiveRef": "#/x"},
    ],
)
def test_advertised_schema_cannot_resolve_remote_resources(schema):
    with pytest.raises(ValueError):
        validate_schema(schema)


def test_local_schema_references_are_supported():
    validate_schema({"$defs": {"x": {"type": "string"}}, "$ref": "#/$defs/x"})
