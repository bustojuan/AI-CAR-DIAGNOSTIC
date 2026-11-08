import logging

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.mcp.client import MCPGateway
from app.mcp.ebay import EbayProvider
from app.mcp.providers import provider_for
from app.mcp.schemas import AutomotiveResult
from app.mcp.server import create_server
from app.mcp.service import AutomotiveService
from tests.mcp.test_protocol import vehicle_input


def configuration(**updates):
    return Settings(
        _env_file=None,
        ebay_client_id="test-production-app",
        ebay_client_secret="test-production-secret",
        ebay_sandbox_client_id="test-sandbox-app",
        ebay_sandbox_client_secret="test-sandbox-secret",
        **updates,
    )


def item(**updates):
    return {
        "itemId": "v1|123456789012|0",
        "title": "Seller-provided glow plug listing",
        "itemWebUrl": "https://www.ebay.es/itm/123456789012",
        "buyingOptions": ["FIXED_PRICE"],
        "condition": "New",
        "price": {"value": "21.40", "currency": "EUR"},
        "seller": {"username": "test-seller"},
        "estimatedAvailabilities": [
            {"estimatedAvailabilityStatus": "IN_STOCK", "estimatedAvailableQuantity": 2}
        ],
        **updates,
    }


def provider(*, sandbox=False, handler=None, settings=None):
    requests = []

    def respond(request):
        requests.append(request)
        if handler:
            override = handler(request)
            if override is not None:
                return override
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(
                200, json={"access_token": "test-access-token", "expires_in": 7200}
            )
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"total": 1, "itemSummaries": [item()]})
        return httpx.Response(200, json=item())

    adapter = EbayProvider(
        settings or configuration(), sandbox=sandbox, transport=httpx.MockTransport(respond)
    )
    return AutomotiveService(adapter), requests


async def test_search_uses_official_oauth_marketplace_and_does_not_infer_fitment():
    service, requests = provider()
    result = await service.execute(
        "search_parts", {"vehicle": vehicle_input(), "component": "calentadores"}
    )
    assert result.available and result.provider == "ebay" and not result.demo_data
    part = result.parts[0]
    assert part.part_id == "EBAY-123456789012-0"
    assert part.source_url == item()["itemWebUrl"]
    assert part.oem_reference is None and part.compatibility == "unknown"
    assert part.manufacturer == "Not verified"
    assert requests[0].url.host == "api.ebay.com"
    assert (
        requests[0].method == "POST"
        and "grant_type=client_credentials" in requests[0].content.decode()
    )
    assert "scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope" in requests[0].content.decode()
    assert requests[1].headers["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_ES"
    assert "glow plugs" in requests[1].url.params["q"]
    assert "CFFB" in requests[1].url.params["q"]
    assert "vin" not in str(requests[1].url).lower()


async def test_fixed_price_stock_and_link_are_real_provider_fields_and_token_is_reused():
    service, requests = provider()
    for _ in range(2):
        result = await service.execute(
            "get_part_prices", {"part_id": "EBAY-123456789012-0", "quantity": 2}
        )
        assert result.available and result.prices
        price = result.prices[0]
        assert str(price.unit_price) == "21.40" and price.verification == "live"
        assert price.availability == "in_stock" and price.product_url == item()["itemWebUrl"]
        assert price.tax_included is None and "Shipping" in result.reason
    assert sum(r.url.path.endswith("/oauth2/token") for r in requests) == 1
    assert "%7C" in str(requests[-1].url)


async def test_compatibility_never_calls_a_provider_or_confirms_from_a_title():
    service, requests = provider()
    result = await service.execute(
        "check_compatibility", {"vehicle": vehicle_input(), "part_id": "EBAY-123456789012-0"}
    )
    assert result.available and result.compatibility == "unknown" and result.evidence
    assert "verified_vehicle_application" in result.missing_information
    assert not requests


@pytest.mark.parametrize("quantity,expected", [(1, "unknown"), (3, "unknown")])
async def test_missing_or_insufficient_stock_does_not_claim_availability(quantity, expected):
    def respond(request):
        if "/item/" in request.url.path:
            data = item()
            if quantity == 1:
                data.pop("estimatedAvailabilities")
            return httpx.Response(200, json=data)

    service, _ = provider(handler=respond)
    result = await service.execute(
        "get_part_prices", {"part_id": "EBAY-123456789012-0", "quantity": quantity}
    )
    assert result.prices[0].availability == expected


@pytest.mark.parametrize(
    "data",
    [
        item(price={"value": "21.40", "currency": "USD"}),
        item(buyingOptions=["AUCTION"]),
        item(itemId="v1|999|0"),
        item(itemWebUrl="https://attacker.example/itm/123"),
        item(price={"value": "-1", "currency": "EUR"}),
    ],
)
async def test_unusable_or_untrusted_offers_fail_closed(data):
    service, _ = provider(
        handler=lambda r: httpx.Response(200, json=data) if "/item/" in r.url.path else None
    )
    result = await service.execute("get_part_prices", {"part_id": "EBAY-123456789012-0"})
    assert not result.available and not result.prices


@pytest.mark.parametrize(
    "args",
    [
        {"part_id": "https / attacker"},
        {"part_id": "EBAYSBX-123-0"},
        {"part_id": "DEMO-001"},
        {"part_id": "EBAY-123-0", "currency": "USD"},
        {"part_id": "EBAY-123-0", "country": "US"},
        {"part_id": "EBAY-123-0", "provider": "demo"},
    ],
)
async def test_foreign_identifiers_market_or_provider_never_make_requests(args):
    service, requests = provider()
    result = await service.execute("get_part_prices", args)
    assert not result.available and not result.prices and not requests


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
async def test_errors_are_sanitized_without_demo_fallback(status, caplog):
    service, _ = provider(
        handler=lambda _: httpx.Response(status, json={"secret": "private-key-and-raw-body"})
    )
    with caplog.at_level(logging.INFO):
        result = await service.execute(
            "search_parts", {"vehicle": vehicle_input(), "component": "battery"}
        )
    assert not result.available and not result.demo_data and result.provider == "ebay"
    assert not result.parts and not result.prices
    assert "private-key-and-raw-body" not in result.model_dump_json() + caplog.text
    assert "success=False error=provider_failure" in caplog.text


@pytest.mark.parametrize(
    "mode,category",
    [("timeout", "timeout"), ("malformed", "invalid_response"), ("oversized", "invalid_response")],
)
async def test_timeout_and_invalid_wire_responses(mode, category):
    def respond(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("sensitive-raw-error", request=request)
        return httpx.Response(200, content=b"x" * 524289 if mode == "oversized" else b"not-json")

    service, _ = provider(handler=respond)
    result = await service.execute(
        "search_parts", {"vehicle": vehicle_input(), "component": "battery"}
    )
    assert result.error_category == category and not result.available


async def test_missing_credentials_do_not_contact_ebay():
    service, requests = provider(settings=Settings(_env_file=None))
    result = await service.execute(
        "search_parts", {"vehicle": vehicle_input(), "component": "battery"}
    )
    assert not result.available and not requests and "Configure" in result.reason


async def test_empty_search_is_distinct_from_a_failed_request():
    service, _ = provider(
        handler=lambda r: (
            httpx.Response(200, json={"total": 0}) if r.url.path.endswith("/search") else None
        )
    )
    result = await service.execute(
        "search_parts", {"vehicle": vehicle_input(), "component": "battery"}
    )
    assert result.available and not result.parts and result.error_category is None


async def test_sandbox_has_separate_host_credentials_identifiers_and_synthetic_prices():
    def respond(request):
        if "/item/" in request.url.path:
            return httpx.Response(
                200, json=item(itemWebUrl="https://www.sandbox.ebay.com/itm/123456789012")
            )

    service, requests = provider(sandbox=True, handler=respond)
    result = await service.execute("get_part_prices", {"part_id": "EBAYSBX-123456789012-0"})
    assert result.available and result.demo_data and result.verification == "synthetic"
    assert result.prices[0].verification == "synthetic"
    assert result.prices[0].availability == "demonstration" and result.prices[0].product_url is None
    assert all(r.url.host == "api.sandbox.ebay.com" for r in requests)
    assert (
        requests[0].headers["authorization"]
        == httpx.BasicAuth("test-sandbox-app", "test-sandbox-secret")._auth_header
    )


def test_factory_and_secret_representation():
    settings = configuration()
    assert provider_for("ebay", settings).name == "ebay"
    assert provider_for("ebay_sandbox", settings).demo_data
    assert "test-production-secret" not in repr(settings)


async def test_official_mcp_session_search_fitment_and_prices(monkeypatch):
    service, requests = provider()
    settings = configuration(automotive_provider="ebay", mcp_enabled=True)
    server = create_server(settings, provider=service.provider)
    gateway = MCPGateway(settings)

    def session():
        return create_connected_server_and_client_session(server)

    monkeypatch.setattr(gateway, "session", session)
    search = await gateway.execute(
        "search_parts",
        {
            "vehicle": vehicle_input(),
            "component": "glow plugs",
        },
    )
    assert search.available and search.parts and search.provider == "ebay"
    identifier = search.parts[0].part_id
    fitment = await gateway.execute(
        "check_compatibility",
        {
            "vehicle": vehicle_input(),
            "part_id": identifier,
        },
    )
    assert fitment.compatibility == "unknown"
    prices = await gateway.execute("get_part_prices", {"part_id": identifier})
    assert prices.available and prices.prices[0].verification == "live"
    assert len(requests) == 3  # Token, search and item detail; cached token reused.


@pytest.mark.parametrize(
    "updates",
    [
        {"provider": "ebay", "demo_data": True},
        {"provider": "ebay", "demo_data": False, "verification": "synthetic"},
        {"provider": "ebay_sandbox", "demo_data": False},
    ],
)
def test_environment_provenance_cannot_be_forged(updates):
    with pytest.raises(ValidationError):
        AutomotiveResult.model_validate(
            {
                "tool": "check_compatibility",
                "available": True,
                "reason": "test",
                "provider": "ebay",
                "demo_data": False,
                "verification": "verified_provider",
                **updates,
            }
        )
