"""Process-local transactional storage for Phase 1. Restarting loses all data."""

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from uuid import UUID

from app.mcp.retention import require_persistable_report
from app.models.case import URGENCY_RANK, CaseSummary
from app.models.conversation import Conversation
from app.models.diagnostic import Diagnostic
from app.models.vehicle import Vehicle, seed_vehicle
from app.repositories.interfaces import Transaction


class MemoryRepository:
    def __init__(self):
        self.vehicles: dict[UUID, Vehicle] = {}
        self.conversations: dict[UUID, Conversation] = {}
        self.diagnostics: dict[UUID, Diagnostic] = {}

    async def list_vehicles(self):
        return deepcopy(list(self.vehicles.values()))

    async def get_vehicle(self, vehicle_id, *, lock=False):
        return deepcopy(self.vehicles.get(vehicle_id))

    async def save_vehicle(self, vehicle):
        self.vehicles[vehicle.vehicle_id] = vehicle.model_copy(deep=True)

    async def get_conversation(self, conversation_id, *, lock=False, allow_closed=False):
        return deepcopy(self.conversations.get(conversation_id))

    async def list_cases(self, vehicle_id):
        cases = []
        for conversation in self.conversations.values():
            if conversation.vehicle_id != vehicle_id or not conversation.diagnostic_ids:
                continue
            reports = [self.diagnostics[key] for key in conversation.diagnostic_ids]
            last = reports[-1]
            cases.append(
                CaseSummary(
                    **conversation.model_dump(exclude={"messages", "diagnostic_ids"}),
                    latest_diagnostic_id=last.diagnostic_id,
                    latest_assessment_at=last.created_at,
                    summary=last.summary,
                    assessment_count=len(reports),
                    historical_urgency=max(
                        (r.urgency_level for r in reports), key=URGENCY_RANK.get
                    ),
                )
            )
        return sorted(cases, key=lambda c: (c.created_at, str(c.conversation_id)), reverse=True)

    async def save_conversation(self, conversation):
        self.conversations[conversation.conversation_id] = conversation.model_copy(deep=True)

    async def get_diagnostic(self, diagnostic_id):
        return deepcopy(self.diagnostics.get(diagnostic_id))

    async def save_diagnostic(self, diagnostic):
        require_persistable_report(diagnostic)
        self.diagnostics[diagnostic.diagnostic_id] = diagnostic.model_copy(deep=True)


class MemoryStore:
    persistence = "in_memory"

    def __init__(self):
        self.repository = MemoryRepository()
        self._lock = asyncio.Lock()

    async def initialize(self):
        vehicle = seed_vehicle()
        self.repository.vehicles.setdefault(vehicle.vehicle_id, vehicle)

    @asynccontextmanager
    async def transaction(self) -> Transaction:
        async with self._lock:
            pending = deepcopy(self.repository)
            yield pending
            self.repository = pending

    async def ready(self):
        return True

    async def close(self):
        pass
