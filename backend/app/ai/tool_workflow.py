"""Bounded intent routing after diagnostic safety triage, never a purchase agent."""

import re

from app.mcp.providers import COMPONENTS
from app.mcp.retention import TRANSIENT_PROVIDERS
from app.mcp.schemas import ToolVehicle


async def automotive_tools(description, vehicle, gateway, settings):
    # This workflow feeds persistent reports. eBay is available only through the
    # transient Parts endpoints, without feeding an assessment or conversation.
    if settings.automotive_provider in TRANSIENT_PROVIDERS:
        return []
    text = description.casefold()
    prices = bool(
        re.search(r"\b(price|prices|cost|costs|precio|precios|cuestan|cuesta|costar)\b", text)
    )
    fitment = bool(re.search(r"\b(fit|fits|compatible|compatibility|compatibilidad|sirve)\b", text))
    search = bool(
        re.search(
            r"\b(replacement|replacements|replace|parts|recambio|recambios|repuesto|repuestos|comprar|sustitución)\b",
            text,
        )
    )
    if not (prices or fitment or search):
        return []
    # Only component labels and explicit part identifiers cross the boundary, never user prose.
    component = next(
        (
            key
            for key, aliases in COMPONENTS.items()
            if any(
                re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text)
                for alias in (*aliases, key)
            )
        ),
        None,
    )
    identifier = re.search(r"\bDEMO-\d{3}\b", description, flags=re.I)
    if not identifier:
        identifier = re.search(
            r"\b(?:part(?: id| number)?|pieza|referencia|reference)\s*[:#]?\s*"
            r"([A-Z0-9][A-Z0-9._-]{2,49})\b",
            description,
        )
        part_id = identifier.group(1) if identifier else None
    else:
        part_id = identifier.group().upper()
    tool_vehicle = ToolVehicle.model_validate(
        vehicle.model_dump(mode="json", include=set(ToolVehicle.model_fields))
    ).model_dump(mode="json")
    results = []
    if not part_id and component:
        result = await gateway.execute(
            "search_parts", {"vehicle": tool_vehicle, "component": component}
        )
        results.append(result)
        if result.available and result.parts:
            # Candidate identity enables lookup; it never implies a replacement recommendation.
            part_id = result.parts[0].part_id
    if part_id and (fitment or prices):
        results.append(
            await gateway.execute(
                "check_compatibility", {"vehicle": tool_vehicle, "part_id": part_id}
            )
        )
    if prices and part_id:
        results.append(
            await gateway.execute(
                "get_part_prices",
                {
                    "part_id": part_id,
                    "country": settings.parts_country,
                    "currency": settings.parts_currency,
                },
            )
        )
    # Max three calls, no retries. Failed searches never trigger invented-part pricing.
    return results
