from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import conversations, vehicles
from app.models.case import CaseHistory, CaseSummary, VehicleUrgency
from app.models.vehicle import Vehicle, VehicleCreate, VehiclePatch
from app.services.conversation_service import ConversationService
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])
Service = Annotated[VehicleService, Depends(vehicles)]
Cases = Annotated[ConversationService, Depends(conversations)]


@router.get("", response_model=list[Vehicle])
async def list_vehicles(service: Service):
    return await service.list()


@router.get("/{vehicle_id}/cases", response_model=list[CaseSummary])
async def list_cases(
    vehicle_id: UUID,
    service: Cases,
    resolution_status: Literal["active", "resolved"] | None = None,
):
    return await service.cases(vehicle_id, resolution_status)


@router.get("/{vehicle_id}/urgency", response_model=VehicleUrgency)
async def vehicle_urgency(vehicle_id: UUID, service: Cases):
    return await service.vehicle_urgency(vehicle_id)


@router.get("/{vehicle_id}/case-history", response_model=CaseHistory)
async def case_history(vehicle_id: UUID, service: Cases):
    return await service.case_history(vehicle_id)


@router.get("/{vehicle_id}", response_model=Vehicle)
async def get_vehicle(vehicle_id: UUID, service: Service):
    return await service.get(vehicle_id)


@router.post("", response_model=Vehicle, status_code=201)
async def create_vehicle(data: VehicleCreate, service: Service):
    return await service.create(data)


@router.patch("/{vehicle_id}", response_model=Vehicle)
async def update_vehicle(vehicle_id: UUID, data: VehiclePatch, service: Service):
    return await service.update(vehicle_id, data)
