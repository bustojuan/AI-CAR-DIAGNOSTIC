import asyncio
import logging

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import request_id_context
from app.mcp.providers import DemoProvider, UnavailableProvider, provider_for
from app.mcp.schemas import AutomotiveResult, Part
from app.mcp.service import AutomotiveService
from tests.mcp.test_protocol import vehicle_input


@pytest.mark.parametrize("component", ["glow plugs", "calentadores", "GLOW PLUG", "glow_plugs"])
async def test_normalization_provenance_no_oem_and_dedup(component):
    result = await AutomotiveService(DemoProvider()).execute(
        "search_parts",
        {
            "vehicle": vehicle_input(),
            "component": component,
        },
    )
    assert len(result.parts) == 1 and result.demo_data
    assert result.parts[0].oem_reference is None and result.parts[0].verification == "synthetic"


@pytest.mark.parametrize(
    "tool,args",
    [
        ("search_parts", {"vehicle": vehicle_input(), "component": "glow plugs"}),
        ("check_compatibility", {"vehicle": vehicle_input(), "part_id": "DEMO-001"}),
        ("get_part_prices", {"part_id": "DEMO-001"}),
    ],
)
async def test_no_live_provider_means_no_verified_data(tool, args):
    result = await AutomotiveService(UnavailableProvider()).execute(tool, args)
    assert not result.available and not result.parts and not result.prices
    assert result.compatibility == "unknown" and not result.demo_data


@pytest.mark.parametrize(
    "args",
    [
        {"part_id": "REAL-123"},
        {"part_id": "DEMO-001", "currency": "USD"},
        {"part_id": "DEMO-001", "country": "US"},
    ],
)
async def test_demo_never_fabricates_missing_prices(args):
    result = await AutomotiveService(DemoProvider()).execute("get_part_prices", args)
    assert not result.available and not result.prices


async def test_engine_code_does_not_create_verified_fitment():
    result = await AutomotiveService(DemoProvider()).execute(
        "check_compatibility",
        {
            "vehicle": vehicle_input(),
            "part_id": "DEMO-001",
            "engine_code": "TEST-ONLY",
        },
    )
    assert result.compatibility == "unknown" and not result.missing_information


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("failure", "provider_failure"),
        ("timeout", "timeout"),
        ("malformed", "invalid_response"),
        ("isolation", "invalid_response"),
        ("oversize", "invalid_response"),
        ("wrong_id", "invalid_response"),
    ],
)
async def test_provider_errors_are_bounded_and_sanitized(mode, expected, caplog):
    class Broken(DemoProvider):
        async def execute(self, tool, args):
            if mode == "failure":
                raise RuntimeError("secret-api-key confidential-VIN")
            if mode == "timeout":
                await asyncio.sleep(1)
            if mode == "malformed":
                return {"price": 12}
            result = await super().execute(tool, args)
            if mode == "isolation":
                result.__dict__["demo_data"] = False
            if mode == "oversize":
                result.parts[0].description = "x" * 2000
            if mode == "wrong_id":
                result.__dict__["vehicle_id"] = None
            return result

    with caplog.at_level(logging.INFO):
        result = await AutomotiveService(Broken(), timeout=0.01, max_bytes=1200).execute(
            "search_parts", {"vehicle": vehicle_input(), "component": "glow plugs"}
        )
    assert result.error_category == expected and not result.available and not result.parts
    assert "secret-api-key" not in caplog.text and "confidential-VIN" not in caplog.text


async def test_telemetry_contains_ids_without_payload(caplog):
    token = request_id_context.set("correlation-test")
    try:
        with caplog.at_level(logging.INFO):
            result = await AutomotiveService(DemoProvider()).execute(
                "get_part_prices",
                {
                    "part_id": "DEMO-001",
                },
            )
        assert str(result.execution_id) in caplog.text and "correlation-test" in caplog.text
        for field in ("duration_ms=", "result_count=", "demo_data=", "verification="):
            assert field in caplog.text
    finally:
        request_id_context.reset(token)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "file:///tmp",
        "https://localhost/x",
        "https://127.0.0.1/x",
        "https://a:b@example.com",
    ],
)
def test_unsafe_urls_rejected(url):
    with pytest.raises(ValidationError):
        Part(
            part_id="x",
            name="x",
            manufacturer="x",
            brand="x",
            category="x",
            description="x",
            source="x",
            source_url=url,
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"demo_data": False},
        {"compatibility": "confirmed_compatible"},
        {"verification": "verified_provider"},
    ],
)
def test_forged_verification_rejected(updates):
    with pytest.raises(ValidationError):
        AutomotiveResult(
            tool="check_compatibility",
            available=True,
            provider="demo",
            reason="demo",
            **{"demo_data": True, "verification": "synthetic", **updates},
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"mcp_http_url": "http://example.com/mcp"},
        {"mcp_http_url": "http://localhost/elsewhere"},
        {"mcp_enabled": True, "mcp_transport": "http"},
        {"mcp_token": "short"},
        {"automotive_provider": "live"},
    ],
)
def test_configuration_restricts_transport_and_provider(updates):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **updates)


def test_no_unlicensed_live_adapter():
    with pytest.raises(ValueError):
        provider_for("tecdoc")


async def test_duplicate_candidates_are_deduplicated_and_limited():
    class Duplicates(DemoProvider):
        async def execute(self, tool, args):
            result = await super().execute(tool, args)
            result.parts = result.parts * 3
            return result

    result = await AutomotiveService(Duplicates()).execute(
        "search_parts",
        {
            "vehicle": vehicle_input(),
            "component": "glow plugs",
            "limit": 1,
        },
    )
    assert result.available and len(result.parts) == 1
