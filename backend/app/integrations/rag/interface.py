from typing import Protocol
from uuid import UUID

from pydantic import Field

from app.models.common import Schema, Text
from app.models.vehicle import Vehicle
from app.rag.schemas import SourceCitation


class RetrievedDocument(Schema):
    document_id: UUID
    title: str
    source: str
    relevant_text: Text
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    relevance_metadata: dict[str, str | float] = Field(default_factory=dict)
    citation: SourceCitation | None = None


class RetrievalResult(Schema):
    available: bool
    documents: list[RetrievedDocument] = Field(default_factory=list)
    reason: str | None = None
    missing_vehicle_fields: list[str] = Field(default_factory=list)
    latency_ms: float = 0
    candidate_count: int = 0


class Retriever(Protocol):
    async def retrieve(
        self, vehicle: Vehicle, query: str, technical_context: dict[str, str] | None = None
    ) -> RetrievalResult: ...


class UnavailableRetriever:
    async def retrieve(self, vehicle, query, technical_context=None) -> RetrievalResult:
        return RetrievalResult(
            available=False,
            reason="Verified manufacturer technical documentation is not connected.",
        )
