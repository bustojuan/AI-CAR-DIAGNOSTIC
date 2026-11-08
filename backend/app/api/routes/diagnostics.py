from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import diagnostics
from app.models.diagnostic import Diagnostic, DiagnosticRequest
from app.services.diagnostic_service import DiagnosticService

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])
Service = Annotated[DiagnosticService, Depends(diagnostics)]


@router.post("", response_model=Diagnostic, status_code=201)
async def create_diagnostic(data: DiagnosticRequest, service: Service):
    return await service.create(data)


@router.get("/{diagnostic_id}", response_model=Diagnostic)
async def get_diagnostic(diagnostic_id: UUID, service: Service):
    return await service.get(diagnostic_id)
