import hashlib
import json

import pymupdf
import pytest

from app.core.config import Settings
from app.rag.import_manifest import ingest_prepared, preparation_report, prepare_manifest
from app.rag.service import RagService
from tests.rag.fakes import FakeEmbeddings, FakeKnowledge
from tests.rag.test_service import metadata


def write_manifest(folder, *, file="note.md", updates=None, **fields):
    values = metadata(**(updates or {})).model_dump(
        exclude={"content_hash", "storage_path", "ingestion_status"}
    )
    path = folder / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "format": "ai-car-rag-import-v1",
                "documents": [{"id": "fixture", "file": file, "metadata": values, **fields}],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_prepare_extracts_without_database_or_embeddings_and_checks_integrity(tmp_path):
    content = b"# Battery\n\nBattery cranking reference."
    (tmp_path / "note.md").write_bytes(content)
    path = write_manifest(tmp_path, sha256=hashlib.sha256(content).hexdigest())
    settings = Settings(_env_file=None, database_url=None, openai_api_key=None)
    prepared = prepare_manifest(path, settings)
    report = preparation_report(prepared)
    assert report["ready"] == 1 and report["pending"] == 0
    assert report["documents"][0]["extracted_chunks"] > 0
    assert not report["database_writes_performed"] and not report["embedding_calls_performed"]
    assert "content" not in json.dumps(report)
    path = write_manifest(tmp_path, sha256="0" * 64)
    report = preparation_report(prepare_manifest(path, settings))
    assert report["documents"][0]["blockers"] == ["content_hash_mismatch"]


def test_missing_restricted_manual_is_pending_without_fabricated_text(tmp_path):
    path = write_manifest(
        tmp_path,
        file="missing.pdf",
        updates={
            "document_type": "pdf",
            "license_status": "restricted",
            "verification_status": "unverified",
        },
    )
    prepared = prepare_manifest(path, Settings(_env_file=None))
    assert prepared[0].content is None
    assert prepared[0].report["blockers"] == ["source_not_authorized", "file_missing"]
    assert prepared[0].metadata.license_status == "restricted"
    assert prepared[0].metadata.verification_status == "unverified"


@pytest.mark.parametrize("file", ["../outside.md", "nested/../../outside.md"])
def test_import_paths_cannot_escape_manifest_directory(tmp_path, file):
    with pytest.raises(ValueError, match="within the manifest directory"):
        prepare_manifest(write_manifest(tmp_path, file=file), Settings(_env_file=None))


def test_reserved_storage_metadata_and_invalid_manifest_are_rejected(tmp_path):
    path = write_manifest(tmp_path)
    data = json.loads(path.read_text())
    data["documents"][0]["metadata"]["storage_path"] = "not-allowed"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="internal storage fields"):
        prepare_manifest(path, Settings(_env_file=None))
    data["documents"].append(data["documents"][0])
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="duplicate identifiers"):
        prepare_manifest(path, Settings(_env_file=None))


async def test_pdf_batch_can_ingest_without_key_and_later_index_with_original_pages(tmp_path):
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "Battery cranking reference.")
        document.save(tmp_path / "part.pdf")
    path = write_manifest(
        tmp_path, file="part.pdf", source_page_start=101, updates={"document_type": "pdf"}
    )
    settings = Settings(_env_file=None, embedding_dimensions=4)
    prepared = prepare_manifest(path, settings)
    embeddings = FakeEmbeddings()
    rag = RagService(FakeKnowledge(), embeddings, settings)
    first = await ingest_prepared(prepared, rag, index=True, embeddings_configured=False)
    assert first["reports"][0]["status"] == "processed"
    assert first["reports"][0]["index_status"] == "pending_credentials"
    assert first["stats"]["indexed_chunks"] == 0 and not embeddings.calls
    assert next(iter(rag.knowledge.chunks.values()))[0]["page"] == 101
    second = await ingest_prepared(prepared, rag, index=True, embeddings_configured=True)
    assert second["reports"][0]["status"] == "duplicate"
    assert second["reports"][0]["index_status"] == "indexed"
    assert second["stats"]["documents"] == 1 and second["stats"]["indexed_chunks"] > 0


async def test_duplicate_request_cannot_upgrade_unverified_source_for_indexing(tmp_path):
    (tmp_path / "note.md").write_text("Battery reference.")
    settings = Settings(_env_file=None, embedding_dimensions=4)
    rag = RagService(FakeKnowledge(), FakeEmbeddings(), settings)
    path = write_manifest(tmp_path, updates={"verification_status": "unverified"})
    await ingest_prepared(prepare_manifest(path, settings), rag)
    path = write_manifest(tmp_path)
    result = await ingest_prepared(
        prepare_manifest(path, settings), rag, index=True, embeddings_configured=True
    )
    assert result["reports"][0]["status"] == "duplicate"
    assert result["reports"][0]["index_status"] == "pending_source_review"
    assert not rag.embeddings.calls


async def test_blocked_batch_never_ingests_or_calls_provider(tmp_path):
    path = write_manifest(tmp_path, updates={"license_status": "unknown"})
    settings = Settings(_env_file=None, embedding_dimensions=4)
    rag = RagService(FakeKnowledge(), FakeEmbeddings(), settings)
    result = await ingest_prepared(
        prepare_manifest(path, settings), rag, index=True, embeddings_configured=True
    )
    assert result["reports"][0]["status"] == "pending"
    assert result["stats"]["documents"] == 0 and not rag.embeddings.calls
