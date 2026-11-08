"""Human-authored retrieval judgments anchored to immutable source chunks."""

import json
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.models.common import Schema


class EvidenceAnchor(Schema):
    document_id: UUID
    chunk_id: UUID
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    document_title: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)


class GroundedCase(Schema):
    id: str = Field(min_length=1)
    query: str = Field(min_length=3, max_length=6000)
    anchors: list[EvidenceAnchor] = Field(min_length=1)
    expected_scope: Literal["matching_vehicle_metadata", "related_volkswagen_learning"]
    review_expectation: str = Field(min_length=1)


class GroundedDataset(Schema):
    format: Literal["ai-car-rag-evaluation-v1"]
    description: str
    cases: list[GroundedCase] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_cases(self):
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Evaluation case identifiers must be unique.")
        return self


def load_grounded_dataset(path):
    return GroundedDataset.model_validate_json(Path(path).read_text(encoding="utf-8")).model_dump(
        mode="json"
    )


def load_evaluation_cases(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return GroundedDataset.model_validate(data).model_dump(mode="json")[
            "cases"
        ], "source_chunks"
    if not isinstance(data, list) or not data:
        raise ValueError("An evaluation dataset cannot be empty.")
    return data, "legacy_document_titles"
