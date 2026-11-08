"""Read-only Browse adapter. Listing relevance never establishes vehicle fitment."""

import asyncio
import json
import re
import time
from urllib.parse import quote, urlsplit

import httpx

from app.mcp.schemas import AutomotiveResult, Part, Price

SCOPE = "https://api.ebay.com/oauth/api_scope"
MAX_RESPONSE_BYTES = 524288
ITEM_ID = re.compile(r"v1\|(\d{1,20})\|(\d{1,20})")


class EbayFailure(Exception):
    """Only application-owned messages cross the provider boundary."""


def listing_url(value, *, sandbox):
    if not isinstance(value, str):
        raise ValueError("Missing listing URL")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    expected = (
        r"(?:www\.)?sandbox\.ebay\.(?:com|es)"
        if sandbox
        else r"(?:www\.)?ebay\.(?:com|es|de|fr|it|co\.uk)"
    )
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not re.fullmatch(expected, host)
        or not parsed.path.startswith("/itm/")
    ):
        raise ValueError("Unexpected listing URL")
    return value


class EbayProvider:
    def __init__(self, settings, *, sandbox=False, transport=None):
        self.name = "ebay_sandbox" if sandbox else "ebay"
        self.demo_data = sandbox
        self.base_url = "https://api.sandbox.ebay.com" if sandbox else "https://api.ebay.com"
        self.prefix = "EBAYSBX" if sandbox else "EBAY"
        self.client_id = settings.ebay_sandbox_client_id if sandbox else settings.ebay_client_id
        self.client_secret = (
            settings.ebay_sandbox_client_secret if sandbox else settings.ebay_client_secret
        )
        self.timeout = settings.mcp_provider_timeout_seconds
        self.transport = transport
        self._token = None
        self._expires_at = 0.0
        self._token_lock = asyncio.Lock()

    def local_id(self, remote_id):
        match = ITEM_ID.fullmatch(remote_id) if isinstance(remote_id, str) else None
        if not match:
            raise ValueError("Unsupported eBay item ID")
        return f"{self.prefix}-{match[1]}-{match[2]}"

    def remote_id(self, local_id):
        match = re.fullmatch(self.prefix + r"-(\d{1,20})-(\d{1,20})", local_id)
        if not match:
            raise EbayFailure("Use an item identifier returned by this eBay provider.")
        return f"v1|{match[1]}|{match[2]}"

    async def request(self, client, method, path, **kwargs):
        # No response URL, user URL, redirect or arbitrary host is ever followed.
        async with client.stream(method, self.base_url + path, **kwargs) as response:
            if response.status_code in (401, 403):
                raise EbayFailure(
                    "eBay rejected authentication or Browse access. Check the matching "
                    "environment's App ID, Cert ID and authorized API access."
                )
            if response.status_code == 429:
                raise EbayFailure("eBay rate limit reached. Try again later.")
            if response.status_code == 404:
                raise EbayFailure("This eBay listing is no longer available.")
            if response.status_code != 200:
                raise EbayFailure("eBay did not return a successful response.")
            data = bytearray()
            async for block in response.aiter_bytes():
                data.extend(block)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise ValueError("eBay response exceeded the size limit")
        payload = json.loads(data)
        if not isinstance(payload, dict) or payload.get("errors"):
            raise ValueError("Invalid eBay response")
        return payload

    async def token(self, client):
        async with self._token_lock:
            if self._token and self._expires_at > time.monotonic():
                return self._token
            if not (
                self.client_id
                and self.client_secret
                and self.client_id.get_secret_value()
                and self.client_secret.get_secret_value()
            ):
                raise EbayFailure(
                    "Configure the App ID and Cert ID for the selected eBay environment."
                )
            payload = await self.request(
                client,
                "POST",
                "/identity/v1/oauth2/token",
                auth=httpx.BasicAuth(
                    self.client_id.get_secret_value(), self.client_secret.get_secret_value()
                ),
                data={"grant_type": "client_credentials", "scope": SCOPE},
            )
            token, expires = payload.get("access_token"), payload.get("expires_in")
            if (
                not isinstance(token, str)
                or not token
                or len(token) > 16384
                or not isinstance(expires, int)
                or expires <= 0
            ):
                raise ValueError("Invalid eBay token response")
            self._token, self._expires_at = token, time.monotonic() + max(0, expires - 60)
            return token

    def result(self, tool, args, *, available=True, reason=None, **kwargs):
        return AutomotiveResult(
            tool=tool,
            provider=self.name,
            demo_data=self.demo_data,
            available=available,
            verification=(
                "synthetic"
                if self.demo_data
                else "verified_provider"
                if available
                else "unavailable"
            ),
            reason=reason
            or (
                "eBay Sandbox test data, not real offers or verified fitment."
                if self.demo_data
                else "eBay listing data. Search relevance does not verify vehicle compatibility."
            ),
            vehicle_id=args.vehicle.vehicle_id if hasattr(args, "vehicle") else None,
            part_id=getattr(args, "part_id", None),
            **kwargs,
        )

    async def execute(self, tool, args):
        try:
            if tool == "check_compatibility":
                return self.result(
                    tool,
                    args,
                    reason="Vehicle-specific eBay fitment mapping is not implemented. "
                    "Listing titles and search matches cannot confirm compatibility.",
                    evidence=["No verified vehicle application was obtained for this listing."],
                    missing_information=["verified_vehicle_application"],
                )
            if tool == "get_part_prices":
                if (
                    args.country != "ES"
                    or args.currency != "EUR"
                    or args.provider not in (None, self.name)
                ):
                    raise EbayFailure(
                        "This adapter supports the eBay Spain marketplace in EUR only."
                    )
                remote_id = self.remote_id(args.part_id)
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
            ) as client:
                headers = {
                    "Authorization": "Bearer " + await self.token(client),
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_ES",
                    "Accept-Language": "es-ES",
                }
                if tool == "search_parts":
                    return await self.search(client, headers, args)
                payload = await self.request(
                    client,
                    "GET",
                    "/buy/browse/v1/item/" + quote(remote_id, safe=""),
                    headers=headers,
                )
                return self.price(payload, args)
        except EbayFailure as exc:
            self._token, self._expires_at = None, 0
            return self.result(
                tool, args, available=False, reason=str(exc), error_category="provider_failure"
            )
        except httpx.TimeoutException:
            return self.result(
                tool,
                args,
                available=False,
                reason="eBay request timed out.",
                error_category="timeout",
            )

    async def search(self, client, headers, args):
        from app.mcp.providers import normalize_component

        component = normalize_component(args.component).replace("_", " ")
        terms = [
            component,
            args.vehicle.manufacturer,
            args.vehicle.model,
            str(args.vehicle.model_year),
            args.vehicle.engine_code or args.vehicle.engine,
        ]
        terms.extend(v for v in (args.oem_reference, args.manufacturer, args.category) if v)
        payload = await self.request(
            client,
            "GET",
            "/buy/browse/v1/item_summary/search",
            headers=headers,
            params={
                "q": " ".join(terms)[:300],
                "limit": args.limit,
                "filter": "buyingOptions:{FIXED_PRICE}",
            },
        )
        items = payload.get("itemSummaries", [])
        if not isinstance(items, list):
            raise ValueError("Invalid eBay search items")
        if not items and "total" not in payload:
            raise ValueError("Missing eBay search result count")
        parts = []
        for item in items[: args.limit]:
            if not isinstance(item, dict):
                raise ValueError("Invalid eBay item")
            if "FIXED_PRICE" not in item.get("buyingOptions", []):
                continue
            parts.append(
                Part(
                    part_id=self.local_id(item.get("itemId")),
                    name=item["title"][:200],
                    manufacturer="Not verified",
                    brand="Not verified",
                    category=component[:200],
                    description="eBay listing candidate. The title and seller claims have not been "
                    "verified against the vehicle. Condition: "
                    + str(item.get("condition", "Not supplied"))[:100],
                    source=self.name,
                    source_url=listing_url(item.get("itemWebUrl"), sandbox=self.demo_data),
                    verification="synthetic" if self.demo_data else "verified_provider",
                )
            )
        return self.result("search_parts", args, parts=parts)

    def price(self, payload, args):
        if self.local_id(payload.get("itemId")) != args.part_id:
            raise ValueError("Mismatched eBay item")
        if "FIXED_PRICE" not in payload.get("buyingOptions", []):
            raise EbayFailure("This listing has no supported fixed-price offer.")
        price = payload.get("price", {})
        if price.get("currency") != args.currency:
            raise EbayFailure(
                "The listing currency does not match the request; no conversion is assumed."
            )
        merchant = payload.get("seller", {}).get("username")
        if not merchant:
            raise ValueError("Missing eBay seller")
        url = listing_url(payload.get("itemWebUrl"), sandbox=self.demo_data)
        availability = "unknown"
        for entry in payload.get("estimatedAvailabilities", []):
            status, quantity = (
                entry.get("estimatedAvailabilityStatus"),
                entry.get("estimatedAvailableQuantity"),
            )
            if status == "OUT_OF_STOCK" or quantity == 0:
                availability = "out_of_stock"
                break
            if (
                status in ("IN_STOCK", "LIMITED_STOCK")
                and isinstance(quantity, int)
                and quantity >= args.quantity
            ):
                availability = "in_stock"
        return self.result(
            "get_part_prices",
            args,
            reason=(
                "eBay Sandbox test offer, not a real price."
                if self.demo_data
                else "Current eBay price per listing/lot, not necessarily per physical component. "
                "Shipping, taxes, delivery eligibility and final checkout total are not verified. "
                "Availability is the provider's estimate, not a stock reservation."
            ),
            prices=[
                Price(
                    part_id=args.part_id,
                    merchant=merchant,
                    unit_price=price["value"],
                    currency=args.currency,
                    country=args.country,
                    quantity=args.quantity,
                    tax_included=None,
                    availability="demonstration" if self.demo_data else availability,
                    product_url=None if self.demo_data else url,
                    verification="synthetic" if self.demo_data else "live",
                )
            ],
        )
