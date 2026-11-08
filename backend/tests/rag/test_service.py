from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.database.schemas import DocumentCreate
from app.models.vehicle import seed_vehicle
from app.rag.service import RagService, validated_citations
from tests.rag.fakes import FakeEmbeddings, FakeKnowledge


def metadata(**updates):
    return DocumentCreate.model_validate(
        {
            **dict(
                title="Battery",
                source_name="Fixture",
                document_type="markdown",
                evidence_type="internal_demo",
                language="en",
                license_status="authorized",
                verification_status="verified",
                content_hash="0" * 64,
            ),
            **updates,
        }
    )


def rag():
    return RagService(
        FakeKnowledge(),
        FakeEmbeddings(),
        Settings(_env_file=None, embedding_dimensions=4, rag_min_similarity=0.8),
    )


async def test_ingest_duplicate_index_retrieve_reindex_and_delete():
    service = rag()
    result = await service.ingest(
        "x.md", "text/markdown", b"# Battery\n\nBattery cranking checks.", metadata()
    )
    assert result.status == "processed"
    duplicate = await service.ingest(
        "x.md", "text/markdown", b"# Battery\n\nBattery cranking checks.", metadata()
    )
    assert duplicate.status == "duplicate" and duplicate.document_id == result.document_id
    await service.index(result.document_id)
    hits = await service.retrieve(seed_vehicle(), "Battery cranking")
    assert hits.available and hits.documents
    assert hits.documents[0].citation.evidence_type == "internal_demo"
    assert "not verified manufacturer" in hits.reason
    ids = [hits.documents[0].citation.chunk_id]
    assert validated_citations(ids, hits)[0].document_id == result.document_id
    with pytest.raises(AppError):
        validated_citations([uuid4()], hits)
    await service.index(result.document_id)
    assert (await service.knowledge.stats())["indexed_chunks"] == result.chunk_count
    await service.knowledge.delete(result.document_id)
    assert not (await service.retrieve(seed_vehicle(), "Battery")).documents


async def test_failures_are_recorded_and_unavailable_embeddings_disclosed():
    service = rag()
    failed = await service.ingest(
        "x.pdf", "application/pdf", b"invalid", metadata(document_type="pdf")
    )
    assert failed.status == "failed" and failed.error_code == "invalid_pdf"
    assert service.knowledge.documents[failed.document_id]["extraction_error"] == "invalid_pdf"
    service.embeddings.failure = AppError(503, "offline", "Unavailable")
    result = await service.retrieve(seed_vehicle(), "battery")
    assert not result.available and not result.documents


async def test_index_failure_never_saves_partial_vectors():
    service = rag()
    report = await service.ingest("x.md", "text/markdown", b"Battery fixture.", metadata())
    service.embeddings.failure = ValueError("bad output")
    with pytest.raises(ValueError):
        await service.index(report.document_id)
    assert not service.knowledge.vectors


async def test_incompatible_vehicle_docs_excluded_before_relevance():
    service = rag()
    for options, content in [
        (
            dict(evidence_type="official_manufacturer", manufacturer="Volvo", model="XC60"),
            b"Battery Volvo",
        ),
        (
            dict(
                evidence_type="official_manufacturer",
                manufacturer="Volkswagen",
                engine="1.6 petrol",
            ),
            b"Battery petrol",
        ),
        (
            dict(
                evidence_type="official_manufacturer",
                manufacturer="Volkswagen",
                model_year_start=2020,
            ),
            b"Battery year",
        ),
        (
            dict(
                evidence_type="official_manufacturer",
                manufacturer="Volkswagen",
                transmission="Automatic",
            ),
            b"Battery automatic",
        ),
        (
            dict(
                evidence_type="official_manufacturer",
                manufacturer="Volkswagen",
                engine_code="UNKNOWN-TEST",
            ),
            b"Battery code",
        ),
    ]:
        report = await service.ingest("x.md", "text/markdown", content, metadata(**options))
        await service.index(report.document_id)
    result = await service.retrieve(
        seed_vehicle().model_copy(update={"engine_code": None}), "Battery"
    )
    assert not result.documents and result.missing_vehicle_fields == ["engine_code"]
