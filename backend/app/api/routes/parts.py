from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field

from app.core.exceptions import not_found
from app.integrations.mcp.interface import ToolResult
from app.mcp.schemas import AutomotiveResult, GetPartPrices, Identifier, ToolVehicle
from app.models.common import Schema, ShortText

router = APIRouter(tags=["automotive tools"])


class PartsSearchRequest(Schema):
    vehicle_id: UUID
    component: str = Field(min_length=2, max_length=80)
    oem_reference: Identifier | None = None
    manufacturer: ShortText | None = None
    category: ShortText | None = None
    limit: int = Field(default=5, ge=1, le=10)


class CompatibilityRequest(Schema):
    vehicle_id: UUID
    part_id: Identifier
    engine_code: ShortText | None = None


async def vehicle_input(request, data):
    async with request.app.state.store.transaction() as repository:
        vehicle = await repository.get_vehicle(data.vehicle_id)
    if not vehicle:
        raise not_found("Vehicle")
    args = data.model_dump(mode="json", exclude={"vehicle_id"})
    args["vehicle"] = vehicle.model_dump(mode="json", include=set(ToolVehicle.model_fields))
    return args


@router.get("/tools/status", response_model=ToolResult)
async def status(request: Request):
    return await request.app.state.tools.status()


@router.post("/parts/search", response_model=AutomotiveResult)
async def search(data: PartsSearchRequest, request: Request):
    return await request.app.state.tools.execute("search_parts", await vehicle_input(request, data))


@router.post("/parts/compatibility", response_model=AutomotiveResult)
async def compatibility(data: CompatibilityRequest, request: Request):
    return await request.app.state.tools.execute(
        "check_compatibility", await vehicle_input(request, data)
    )


@router.post("/parts/prices", response_model=AutomotiveResult)
async def prices(data: GetPartPrices, request: Request):
    # Country/currency defaults come from settings, including for omitted request fields.
    args = data.model_dump(mode="json")
    for key in ("country", "currency"):
        if key not in data.model_fields_set:
            args[key] = getattr(request.app.state.settings, f"parts_{key}")
    return await request.app.state.tools.execute("get_part_prices", args)
