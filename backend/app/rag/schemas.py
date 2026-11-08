from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.common import Schema


class SourceCitation(Schema):
    document_id: UUID
    chunk_id: UUID
    document_title: str
    publisher: str | None
    source_url: str | None
    page: int | None
    section: str | None
    evidence_type: Literal[
        "official_manufacturer", "third_party_technical", "generic_reference", "internal_demo"
    ]
    verification_status: str


class TextSection(Schema):
    text: str
    page: int | None = None
    section: str | None = None


class StoredChunk(TextSection):
    chunk_id: UUID
    chunk_index: int
    content_hash: str


class IngestionReport(Schema):
    document_id: UUID
    status: Literal["processed", "failed", "duplicate"]
    chunk_count: int
    error_code: str | None = None
    warnings: list[str] = Field(default_factory=list)


class SearchRequest(Schema):
    vehicle_id: UUID
    query: str = Field(min_length=3, max_length=6000)
