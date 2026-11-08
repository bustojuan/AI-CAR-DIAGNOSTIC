from typing import Protocol

from app.mcp.schemas import AutomotiveResult, Part, Price

COMPONENTS = {
    "glow_plugs": (
        "glow plug",
        "glow plugs",
        "calentador",
        "calentadores",
        "bujías de precalentamiento",
    ),
    "battery": ("battery", "batteries", "batería", "baterias", "batería de arranque"),
    "starter": ("starter", "starter motor", "motor de arranque"),
    "brake_pads": ("brake pads", "pastillas de freno"),
    "turbocharger": ("turbo", "turbocharger", "turbocompresor"),
}


def normalize_component(component: str) -> str:
    normalized = " ".join(component.casefold().split())
    for canonical, aliases in COMPONENTS.items():
        if normalized == canonical or normalized in aliases:
            return canonical
    return normalized


class AutomotiveProvider(Protocol):
    name: str
    demo_data: bool

    async def execute(self, tool: str, arguments) -> AutomotiveResult: ...


class UnavailableProvider:
    name = "unavailable"
    demo_data = False

    async def execute(self, tool, arguments):
        return AutomotiveResult(
            tool=tool,
            available=False,
            provider="unavailable",
            demo_data=False,
            verification="unavailable",
            reason="No authorized live catalog, fitment or price provider is connected.",
            part_id=getattr(arguments, "part_id", None),
            vehicle_id=arguments.vehicle.vehicle_id if hasattr(arguments, "vehicle") else None,
            missing_information=["engine_code"]
            if hasattr(arguments, "vehicle") and not arguments.vehicle.engine_code
            else [],
        )


class DemoProvider:
    """Authored synthetic records, unrelated to any actual manufacturer's products."""

    name = "demo"
    demo_data = True
    samples = {key: f"DEMO-{index:03d}" for index, key in enumerate(COMPONENTS, 1)}

    async def execute(self, tool, arguments):
        result = AutomotiveResult(
            tool=tool,
            available=True,
            provider="demo",
            demo_data=True,
            verification="synthetic",
            reason="DEMONSTRATION ONLY: synthetic samples; no real fitment or market prices.",
            part_id=getattr(arguments, "part_id", None),
            vehicle_id=arguments.vehicle.vehicle_id if hasattr(arguments, "vehicle") else None,
        )
        if tool == "search_parts":
            component = normalize_component(arguments.component)
            if (
                component in self.samples
                and not arguments.oem_reference
                and (not arguments.manufacturer or arguments.manufacturer == "Synthetic Demo Parts")
                and (not arguments.category or arguments.category == component)
            ):
                result.parts = [
                    Part(
                        part_id=self.samples[component],
                        name=f"Synthetic example: {component}",
                        manufacturer="Synthetic Demo Parts",
                        brand="Demo only",
                        category=component,
                        description="Synthetic protocol test candidate. Not a purchasable product.",
                        source="demo",
                        verification="synthetic",
                    )
                ]
        elif tool == "check_compatibility":
            result.evidence = [
                "No verified provider fitment evidence; real compatibility is unknown."
            ]
            if not (arguments.engine_code or arguments.vehicle.engine_code):
                result.missing_information = ["engine_code"]
        elif (
            arguments.part_id in self.samples.values()
            and arguments.provider in (None, "demo")
            and arguments.currency == "EUR"
            and arguments.country == "ES"
        ):
            result.prices = [
                Price(
                    part_id=arguments.part_id,
                    merchant="Synthetic Demo Merchant",
                    unit_price="12.34",
                    currency=arguments.currency,
                    country=arguments.country,
                    quantity=arguments.quantity,
                    availability="demonstration",
                    verification="synthetic",
                )
            ]
        else:
            result.available = False
            result.reason = (
                "No demo price for this identifier, market or provider. Live prices unavailable."
            )
        return result


def provider_for(name: str, settings=None) -> AutomotiveProvider:
    if name == "demo":
        return DemoProvider()
    if name == "unavailable":
        return UnavailableProvider()
    if name in ("ebay", "ebay_sandbox"):
        from app.core.config import Settings
        from app.mcp.ebay import EbayProvider

        return EbayProvider(settings or Settings(), sandbox=name == "ebay_sandbox")
    raise ValueError("Unsupported provider; live integration requires a licensed adapter")
