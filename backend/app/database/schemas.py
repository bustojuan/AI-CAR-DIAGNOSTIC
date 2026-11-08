"""Internal storage validation only. No ingestion, indexing, or document API."""

import ipaddress
import math
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, model_validator

from app.models.common import Schema


class DocumentCreate(Schema):
    title: str = Field(min_length=1, max_length=500)
    source_name: str = Field(min_length=1, max_length=300)
    source_url: str | None = None
    publisher: str | None = Field(default=None, max_length=300)
    document_type: Literal["pdf", "markdown", "txt", "html"]
    evidence_type: Literal[
        "official_manufacturer", "third_party_technical", "generic_reference", "internal_demo"
    ]
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    model_year_start: int | None = Field(default=None, ge=1886, le=2100)
    model_year_end: int | None = Field(default=None, ge=1886, le=2100)
    engine: str | None = Field(default=None, max_length=200)
    engine_code: str | None = Field(default=None, max_length=200)
    transmission: str | None = Field(default=None, max_length=200)
    language: str = Field(min_length=2, max_length=10)
    license_status: Literal["unknown", "authorized", "restricted"] = "unknown"
    verification_status: Literal["unverified", "verified", "rejected"] = "unverified"
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    storage_path: str | None = None
    ingestion_status: Literal["pending", "processed", "failed"] = "pending"
    public_source_url: bool = False

    @model_validator(mode="after")
    def applicable_scope(self):
        if self.public_source_url:
            parsed = urlsplit(self.source_url or "")
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Public source links must be HTTPS without credentials")
            if (
                parsed.hostname == "localhost"
                or parsed.hostname.endswith((".localhost", ".local", ".internal"))
                or "." not in parsed.hostname
            ):
                raise ValueError("Private source links cannot be exposed")
            try:
                address = ipaddress.ip_address(parsed.hostname)
            except ValueError:
                address = None
            if address and not address.is_global:
                raise ValueError("Private source links cannot be exposed")
            if self.license_status != "authorized":
                raise ValueError("Public links require an authorized source")
        if (
            self.model_year_start is not None
            and self.model_year_end is not None
            and self.model_year_start > self.model_year_end
        ):
            raise ValueError("Invalid document year range")
        if self.evidence_type in ("generic_reference", "internal_demo") and any(
            getattr(self, key) is not None
            for key in (
                "manufacturer",
                "model",
                "model_year_start",
                "model_year_end",
                "engine",
                "engine_code",
                "transmission",
            )
        ):
            raise ValueError("Generic or demonstration evidence cannot claim vehicle applicability")
        return self


class ChunkCreate(Schema):
    document_id: UUID
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    section: str | None = Field(default=None, max_length=500)
    page_number: int | None = Field(default=None, ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedding: list[float] | None = None
    embedding_model: str | None = Field(default=None, min_length=1, max_length=200)
    embedding_dimensions: int | None = Field(default=None, ge=1, le=2000)

    def validate_dimensions(self, configured_dimension: int) -> None:
        if self.embedding is None:
            if self.embedding_model is not None or self.embedding_dimensions is not None:
                raise ValueError("A null embedding cannot carry model/dimension metadata")
        elif (
            not self.embedding_model
            or self.embedding_dimensions != configured_dimension
            or len(self.embedding) != configured_dimension
            or not all(math.isfinite(value) for value in self.embedding)
        ):
            raise ValueError("Embedding dimension/model metadata does not match configuration")
