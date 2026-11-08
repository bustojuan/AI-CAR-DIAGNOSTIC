from uuid import UUID

from app.core.exceptions import AppError, not_found
from app.models.case import CaseHistory, CaseVersion, ResolveCaseRequest, aggregate_vehicle_urgency
from app.models.common import utcnow
from app.models.conversation import Conversation, ConversationCreate
from app.repositories.interfaces import Store


class ConversationService:
    def __init__(self, store: Store):
        self.store = store

    async def create(self, data: ConversationCreate):
        async with self.store.transaction() as repository:
            if not await repository.get_vehicle(data.vehicle_id):
                raise not_found("Vehicle")
            conversation = Conversation(vehicle_id=data.vehicle_id)
            await repository.save_conversation(conversation)
            return conversation

    async def get(self, conversation_id: UUID):
        async with self.store.transaction() as repository:
            conversation = await repository.get_conversation(conversation_id)
            if not conversation:
                raise not_found("Conversation")
            return conversation

    async def cases(self, vehicle_id: UUID, resolution_status: str | None = None):
        async with self.store.transaction() as repository:
            if not await repository.get_vehicle(vehicle_id):
                raise not_found("Vehicle")
            cases = await repository.list_cases(vehicle_id)
            return [
                case
                for case in cases
                if resolution_status is None or case.resolution_status == resolution_status
            ]

    async def vehicle_urgency(self, vehicle_id: UUID):
        return (await self.case_history(vehicle_id)).vehicle_urgency

    async def case_history(self, vehicle_id: UUID):
        # One consistent SELECT covers every assessed case, including cases not
        # referenced by the current browser. No LLM or retrieval participates.
        async with self.store.transaction() as repository:
            if not await repository.get_vehicle(vehicle_id):
                raise not_found("Vehicle")
            cases = await repository.list_cases(vehicle_id)
            return CaseHistory(
                cases=cases, vehicle_urgency=aggregate_vehicle_urgency(vehicle_id, cases)
            )

    async def resolution(self, conversation_id: UUID, data: CaseVersion, *, resolve: bool):
        async with self.store.transaction() as repository:
            conversation = await repository.get_conversation(
                conversation_id,
                lock=True,
                allow_closed=True,
            )
            if not conversation:
                raise not_found("Conversation")
            if not conversation.diagnostic_ids:
                raise AppError(
                    409, "case_not_assessed", "This conversation has no assessment to resolve."
                )
            if data.expected_latest_diagnostic_id != conversation.diagnostic_ids[-1]:
                raise AppError(
                    409,
                    "stale_case",
                    "A newer assessment exists. Refresh before changing resolution.",
                )
            target = "resolved" if resolve else "active"
            if conversation.resolution_status == target:
                raise AppError(
                    409, "invalid_resolution_transition", "The case is already in that state."
                )
            note = data.resolution_note if isinstance(data, ResolveCaseRequest) else None
            updated = conversation.model_copy(
                update={
                    "resolution_status": target,
                    "resolved_at": utcnow() if resolve else None,
                    "resolution_note": (note or None) if resolve else None,
                }
            )
            await repository.save_conversation(updated)
            return next(
                case
                for case in await repository.list_cases(updated.vehicle_id)
                if case.conversation_id == conversation_id
            )
