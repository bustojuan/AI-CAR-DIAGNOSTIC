import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models.vehicle import seed_vehicle
from app.rag.evaluation_dataset import load_grounded_dataset
from app.rag.import_manifest import prepare_manifest
from app.rag.readiness import audit_corpus, audit_local_sources, validate_ground_truth


def corpus():
    document = dict(
        id=uuid4(),
        title="Workshop reference",
        publisher="Reviewed publisher",
        source_name="Learning source",
        source_url=None,
        public_source_url=False,
        content_hash="a" * 64,
        manufacturer=None,
        model=None,
        engine=None,
        engine_code=None,
        transmission=None,
        model_year_start=None,
        model_year_end=None,
        license_status="authorized",
        verification_status="verified",
        ingestion_status="processed",
        evidence_type="internal_demo",
        document_type="markdown",
    )
    content = "An independently authored reference with enough context for this fixture. " * 2
    chunk = dict(
        id=uuid4(),
        document_id=document["id"],
        chunk_index=0,
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        page_number=None,
        has_embedding=False,
        embedding_model=None,
        embedding_dimensions=None,
    )
    return document, chunk


def test_readiness_separates_storage_permissions_scope_and_pending_embeddings():
    document, chunk = corpus()
    settings = Settings(_env_file=None)
    report = audit_corpus([document], [chunk], seed_vehicle(), settings)
    assert report["eligible_chunks"] == report["index_plan"]["pending_chunks"] == 1
    assert report["index_plan"]["document_ids"] == [str(document["id"])]
    assert report["embedded_chunks"] == 0
    assert not report["embedding_calls_performed"] and not report["semantic_quality_verified"]
    for field, value in (("license_status", "unknown"), ("verification_status", "unverified")):
        blocked = audit_corpus([{**document, field: value}], [chunk], seed_vehicle(), settings)
        assert blocked["blocked_documents"] == 1 and not blocked["index_plan"]["document_ids"]


def test_corrupt_chunks_block_indexing_but_quality_warnings_do_not_rewrite_text():
    document, chunk = corpus()
    settings = Settings(_env_file=None)
    bad = audit_corpus([document], [{**chunk, "content": "tampered"}], seed_vehicle(), settings)
    assert "invalid_chunk_integrity" in bad["inventory"][0]["blockers"]
    content = "Short label \ufffd"
    warning = {
        **chunk,
        "content": content,
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
    }
    report = audit_corpus([document], [warning], seed_vehicle(), settings)
    assert report["inventory"][0]["warnings"] == [
        "short_chunks_review_context",
        "replacement_characters_review_source",
    ]
    assert warning["content"] == content and report["eligible_documents"] == 1


def test_learning_plan_retains_actual_source_identity_and_counts_duplicate_copies():
    document, chunk = corpus()
    source = {
        **document,
        "manufacturer": "Volkswagen",
        "model": "Tiguan",
        "model_year_start": 2007,
        "engine": "2.0 TDI",
        "engine_code": "CBAB",
        "evidence_type": "third_party_technical",
    }
    vehicle = seed_vehicle().model_copy(update={"model_year": 2009, "engine_code": "CFFB"})
    settings = Settings(_env_file=None)
    assert audit_corpus([source], [chunk], vehicle, settings)["blocked_documents"] == 1
    copy = {**chunk, "id": uuid4(), "chunk_index": 1}
    report = audit_corpus(
        [source],
        [chunk, copy],
        vehicle,
        settings.model_copy(update={"rag_allow_related_volkswagen": True}),
    )
    assert report["duplicate_chunk_copies"] == 1
    assert report["inventory"][0]["source_engine_code"] == "CBAB"
    assert report["inventory"][0]["scope"] == "related_volkswagen_learning"
    assert report["eligible_documents"] == 1


def test_ground_truth_checks_frozen_document_chunk_hash_and_original_page():
    document, chunk = corpus()
    anchor = dict(
        document_id=str(document["id"]),
        chunk_id=str(chunk["id"]),
        content_hash=chunk["content_hash"],
        page=None,
        document_title=document["title"],
    )
    dataset = {
        "format": "ai-car-rag-evaluation-v1",
        "description": "Test only",
        "cases": [
            {
                "id": "battery",
                "query": "Battery warning",
                "expected_scope": "matching_vehicle_metadata",
                "review_expectation": "Do not infer a confirmed fault.",
                "anchors": [anchor],
            }
        ],
    }
    assert validate_ground_truth(dataset, [document], [chunk])["all_anchors_valid"]
    assert not validate_ground_truth(dataset, [document], [{**chunk, "page_number": 10}])[
        "all_anchors_valid"
    ]
    assert not validate_ground_truth(dataset, [], [chunk])["all_anchors_valid"]


def test_workshop_dataset_has_nonempty_citation_anchors_and_unique_cases():
    path = Path(__file__).parents[2] / "app/rag/workshop_evaluation.json"
    dataset = load_grounded_dataset(path)
    assert len(dataset["cases"]) == 20
    assert all(case["anchors"] and case["review_expectation"] for case in dataset["cases"])
    with pytest.raises(ValidationError):
        validate_ground_truth({**dataset, "cases": [dataset["cases"][0]] * 2}, [], [])
    with pytest.raises(ValidationError):
        validate_ground_truth(
            {**dataset, "cases": [{**dataset["cases"][0], "anchors": []}]}, [], []
        )


def test_local_source_audit_detects_changed_files_and_metadata_without_promoting_sources(tmp_path):
    settings = Settings(_env_file=None)
    raw = b"# Battery\n\nA local learning fixture, not manufacturer evidence."
    (tmp_path / "battery.md").write_bytes(raw)
    document, _ = corpus()
    metadata = {k: v for k, v in document.items() if k not in ("id", "content_hash")}
    metadata.pop("ingestion_status")
    metadata["language"] = "en"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "format": "ai-car-rag-import-v1",
                "documents": [
                    {
                        "id": "battery",
                        "file": "battery.md",
                        "metadata": metadata,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    prepared = prepare_manifest(manifest, settings)[0]
    from uuid import NAMESPACE_URL, uuid5

    identifier = uuid5(NAMESPACE_URL, "ai-car-document:" + prepared.report["sha256"])
    saved = {
        **prepared.metadata.model_dump(),
        "id": identifier,
        "content_hash": prepared.report["sha256"],
    }
    chunks = [
        {
            "id": c.chunk_id,
            "document_id": identifier,
            "chunk_index": c.chunk_index,
            "content_hash": c.content_hash,
            "page_number": c.page,
            "section": c.section,
        }
        for c in prepared.chunks
    ]
    result = audit_local_sources([manifest], [saved], chunks, settings)
    assert result["all_requested_sources_reproduced"] and result["covered_documents"] == 1
    result = audit_local_sources(
        [manifest], [{**saved, "verification_status": "unverified"}], chunks, settings
    )
    assert "manifest_metadata_differs" in result["entries"][0]["problems"]
    (tmp_path / "battery.md").write_bytes(b"Changed file")
    result = audit_local_sources([manifest], [saved], chunks, settings)
    assert "content_hash_mismatch" in result["entries"][0]["problems"]


@pytest.mark.parametrize("anchors_valid,eligible", [(False, True), (True, False)])
async def test_live_evaluation_refuses_stale_or_ineligible_sources_before_paid_calls(
    monkeypatch,
    anchors_valid,
    eligible,
):
    from app.rag import evaluate

    path = Path(__file__).parents[2] / "app/rag/workshop_evaluation.json"
    dataset = load_grounded_dataset(path)
    monkeypatch.setattr(evaluate, "Settings", lambda: Settings(_env_file=None))
    monkeypatch.setattr(
        evaluate,
        "audit_database",
        AsyncMock(
            return_value={
                "evaluation_preflight": {"all_anchors_valid": anchors_valid},
                "inventory": [
                    {"document_id": a["document_id"], "index_eligible": eligible}
                    for case in dataset["cases"]
                    for a in case["anchors"]
                ],
            }
        ),
    )

    def forbidden(*args):
        raise AssertionError("Invalid evaluation must not construct paid services")

    monkeypatch.setattr(evaluate, "OpenAIEmbeddingClient", forbidden)
    monkeypatch.setattr(evaluate, "PostgresStore", forbidden)
    with pytest.raises(RuntimeError):
        await evaluate.evaluate(path)
