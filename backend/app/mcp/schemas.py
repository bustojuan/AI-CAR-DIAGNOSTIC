from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.models.common import Schema, ShortText, Text, utcnow

ToolName = Literal["search_parts", "check_compatibility", "get_part_prices"]
TEST_PROVIDERS = ("demo", "ebay_sandbox")
Compatibility = Literal[
    "confirmed_compatible", "confirmed_incompatible", "requires_additional_information", "unknown"
]
Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._ /-]+$")]


class ToolVehicle(Schema):
    # Explicit allowlist: no VIN, mileage, free-form notes or conversation history.
    vehicle_id: UUID
    manufacturer: ShortText
    model: ShortText
    model_year: int = Field(ge=1886, le=2100)
    engine: ShortText
    transmission: ShortText
    fuel_type: ShortText
    engine_code: ShortText | None = None


class SearchParts(Schema):
    vehicle: ToolVehicle
    component: str = Field(min_length=2, max_length=80)
    oem_reference: Identifier | None = None
    manufacturer: ShortText | None = None
    category: ShortText | None = None
    limit: int = Field(default=5, ge=1, le=10)


class CheckCompatibility(Schema):
    vehicle: ToolVehicle
    part_id: Identifier
    engine_code: ShortText | None = None


class GetPartPrices(Schema):
    part_id: Identifier
    country: str = Field(default="ES", pattern=r"^[A-Z]{2}$")
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    provider: Identifier | None = None
    quantity: int = Field(default=1, ge=1, le=100)


class Part(Schema):
    part_id: Identifier
    name: ShortText
    manufacturer: ShortText
    brand: ShortText
    oem_reference: Identifier | None = None
    oem_verified: bool = False
    category: ShortText
    description: Text
    source: ShortText
    source_url: str | None = Field(default=None, max_length=1000)
    compatibility: Compatibility = "unknown"
    verification: Literal["unverified", "verified_provider", "synthetic"] = "unverified"

    @field_validator("source_url")
    @classmethod
    def public_url(cls, value):
        if value:
            import ipaddress

            parsed = urlsplit(value)
            host = parsed.hostname or ""
            if parsed.scheme != "https" or parsed.username or parsed.password or not host:
                raise ValueError("Only public HTTPS attribution URLs are accepted")
            if host == "localhost" or host.endswith((".localhost", ".local")) or "." not in host:
                raise ValueError("Local attribution URLs are forbidden")
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                address = None
            if address is not None and not address.is_global:
                raise ValueError("Private attribution URLs are forbidden")
        return value

    @model_validator(mode="after")
    def verified_claims(self):
        if self.oem_reference and not self.oem_verified:
            raise ValueError("An OEM reference needs verification")
        if self.oem_verified and (
            not self.oem_reference or self.verification != "verified_provider"
        ):
            raise ValueError("OEM verification needs provider evidence")
        # Search results are candidates; confirmation is exclusively a fitment tool result.
        if self.compatibility.startswith("confirmed"):
            raise ValueError("Search candidates cannot confirm fitment")
        return self


class Price(Schema):
    part_id: Identifier
    merchant: ShortText
    unit_price: Decimal = Field(ge=0, le=1000000, max_digits=12, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    country: str = Field(pattern=r"^[A-Z]{2}$")
    quantity: int = Field(ge=1, le=100)
    tax_included: bool | None = None
    availability: Literal["in_stock", "out_of_stock", "unknown", "demonstration"] = "unknown"
    product_url: str | None = Field(default=None, max_length=1000)
    retrieved_at: datetime = Field(default_factory=utcnow)
    verification: Literal["live", "historical", "synthetic"]

    _public_url = field_validator("product_url")(Part.public_url.__func__)


class AutomotiveResult(Schema):
    tool: ToolName
    execution_id: UUID = Field(default_factory=uuid4)
    available: bool
    reason: Text
    provider: Literal["unavailable", "demo", "ebay", "ebay_sandbox"]
    demo_data: bool
    verification: Literal["unavailable", "synthetic", "verified_provider"]
    retrieved_at: datetime = Field(default_factory=utcnow)
    error_category: (
        Literal["timeout", "provider_failure", "invalid_response", "mcp_unavailable"] | None
    ) = None
    parts: list[Part] = Field(default_factory=list, max_length=10)
    prices: list[Price] = Field(default_factory=list, max_length=10)
    part_id: Identifier | None = None
    vehicle_id: UUID | None = None
    compatibility: Compatibility = "unknown"
    evidence: list[Text] = Field(default_factory=list, max_length=5)
    missing_information: list[ShortText] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def provenance(self):
        if self.demo_data != (self.provider in TEST_PROVIDERS):
            raise ValueError("Provider mode mismatch")
        if self.provider == "unavailable" and (
            self.available or self.parts or self.prices or self.verification != "unavailable"
        ):
            raise ValueError("Unavailable providers cannot return data")
        if self.demo_data and (
            self.verification != "synthetic"
            or any(p.verification != "synthetic" for p in self.parts)
            or any(p.verification != "synthetic" for p in self.prices)
            or any(p.availability != "demonstration" for p in self.prices)
            or self.compatibility != "unknown"
        ):
            raise ValueError("Demo data must remain synthetic")
        if self.provider == "ebay" and (
            self.demo_data
            or self.verification == "synthetic"
            or any(p.verification == "synthetic" for p in self.parts)
            or any(p.verification != "live" for p in self.prices)
            or any(p.availability == "demonstration" for p in self.prices)
        ):
            raise ValueError("Production eBay cannot return test data")
        if self.compatibility.startswith("confirmed"):
            if self.demo_data or self.verification != "verified_provider" or not self.evidence:
                raise ValueError("Confirmed fitment needs verified provider evidence")
        if self.tool != "search_parts" and self.parts:
            raise ValueError("Unexpected parts")
        if self.tool != "get_part_prices" and self.prices:
            raise ValueError("Unexpected prices")
        if self.tool != "check_compatibility" and self.compatibility != "unknown":
            raise ValueError("Fitment belongs to check_compatibility")
        if not self.available and (self.parts or self.prices):
            raise ValueError("Unavailable results cannot contain products or prices")
        if self.error_category and self.available:
            raise ValueError("Failed executions cannot claim data availability")
        return self


INPUTS = {
    "search_parts": SearchParts,
    "check_compatibility": CheckCompatibility,
    "get_part_prices": GetPartPrices,
}
