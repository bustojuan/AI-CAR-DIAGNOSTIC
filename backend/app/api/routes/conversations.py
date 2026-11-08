from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import conversations, diagnostics
from app.models.case import CaseSummary, CaseVersion, ResolveCaseRequest
from app.models.conversation import Conversation, ConversationCreate
from app.models.diagnostic import Diagnostic, MessageRequest
from app.services.conversation_service import ConversationService
from app.services.diagnostic_service import DiagnosticService

router = APIRouter(prefix="/conversations", tags=["conversations"])
Service = Annotated[ConversationService, Depends(conversations)]
Diagnostics = Annotated[DiagnosticService, Depends(diagnostics)]


@router.post("", response_model=Conversation, status_code=201)
async def create_conversation(data: ConversationCreate, service: Service):
    return await service.create(data)


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: UUID, service: Service):
    return await service.get(conversation_id)


@router.post("/{conversation_id}/resolve", response_model=CaseSummary)
async def resolve_case(conversation_id: UUID, data: ResolveCaseRequest, service: Service):
    return await service.resolution(conversation_id, data, resolve=True)


@router.post("/{conversation_id}/reopen", response_model=CaseSummary)
async def reopen_case(conversation_id: UUID, data: CaseVersion, service: Service):
    return await service.resolution(conversation_id, data, resolve=False)


@router.post("/{conversation_id}/messages", response_model=Diagnostic, status_code=201)
async def add_message(conversation_id: UUID, data: MessageRequest, service: Diagnostics):
    return await service.run(data, conversation_id=conversation_id)
