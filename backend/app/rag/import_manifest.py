"""Explicit local batch preparation and ingestion; source URLs are never fetched."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import Field, ValidationError

from app.core.exceptions import AppError
from app.database.schemas import DocumentCreate
from app.models.common import Schema
from app.rag.extraction import chunk_sections, extract
from app.rag.schemas import StoredChunk

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "markdown": "text/markdown",
    "txt": "text/plain",
    "html": "text/html",
}


class ImportEntry(Schema):
    id: str = Field(min_length=1, max_length=150)
    file: str = Field(min_length=1, max_length=2048)
    metadata: dict
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_page_start: int = Field(default=1, strict=True, ge=1, le=1000000)


@dataclass
class PreparedDocument:
    entry: ImportEntry
    metadata: DocumentCreate
    content: bytes | None
    report: dict
    chunks: list[StoredChunk] | None = None


def prepare_manifest(manifest_path, settings):
    """Validate and extract eligible files without DB access or embedding calls."""
    manifest_path = Path(manifest_path).resolve(strict=True)
    if manifest_path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Import manifest exceeds 2 MiB.")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(data, dict)
            or set(data) != {"format", "documents"}
            or data["format"] != "ai-car-rag-import-v1"
            or not isinstance(data["documents"], list)
            or not 1 <= len(data["documents"]) <= 1000
        ):
            raise ValueError
        entries = [ImportEntry.model_validate(item) for item in data["documents"]]
        if len({entry.id for entry in entries}) != len(entries):
            raise ValueError
    except (ValueError, ValidationError):
        raise ValueError("Invalid import manifest format or duplicate identifiers.") from None
    prepared = []
    for entry in entries:
        if set(entry.metadata) & {"content_hash", "storage_path", "ingestion_status"}:
            raise ValueError("Import metadata cannot set internal storage fields.")
        try:
            metadata = DocumentCreate.model_validate({**entry.metadata, "content_hash": "0" * 64})
        except ValidationError:
            raise ValueError(f"Invalid document metadata for {entry.id}.") from None
        relative = Path(entry.file)
        path = (manifest_path.parent / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(manifest_path.parent):
            raise ValueError("Import files must remain within the manifest directory.")
        reasons = []
        if metadata.license_status != "authorized":
            reasons.append("source_not_authorized")
        if metadata.verification_status == "rejected":
            reasons.append("source_rejected")
        if not path.is_file():
            reasons.append("file_missing")
        report = {
            "id": entry.id,
            "file": entry.file,
            "title": metadata.title,
            "ingestion_ready": False,
            "verification_status": metadata.verification_status,
            "license_status": metadata.license_status,
            "source_page_start": entry.source_page_start,
            "blockers": reasons,
        }
        content, chunks = None, None
        if not reasons:
            try:
                with path.open("rb") as stream:
                    content = stream.read(settings.document_max_bytes + 1)
                digest = hashlib.sha256(content).hexdigest()
                if entry.sha256 is not None and digest != entry.sha256:
                    reasons.append("content_hash_mismatch")
                else:
                    kind, sections, warnings = extract(
                        path.name,
                        CONTENT_TYPES[metadata.document_type],
                        content,
                        settings,
                        source_page_start=entry.source_page_start,
                    )
                    if kind != metadata.document_type:
                        reasons.append("content_type_mismatch")
                    else:
                        identifier = uuid5(NAMESPACE_URL, "ai-car-document:" + digest)
                        chunks = chunk_sections(
                            identifier, sections, settings.chunk_size, settings.chunk_overlap
                        )
                        report.update(
                            sha256=digest,
                            extracted_chunks=len(chunks),
                            warnings=warnings,
                            ingestion_ready=True,
                        )
            except AppError as error:
                reasons.append(error.code)
            except OSError:
                reasons.append("file_unavailable")
        if reasons:
            content = None
        prepared.append(PreparedDocument(entry, metadata, content, report, chunks))
    return prepared


def preparation_report(prepared):
    return {
        "documents": [item.report for item in prepared],
        "ready": sum(item.report["ingestion_ready"] for item in prepared),
        "pending": sum(not item.report["ingestion_ready"] for item in prepared),
        "database_writes_performed": False,
        "embedding_calls_performed": False,
    }


async def ingest_prepared(prepared, rag, *, index=False, embeddings_configured=False):
    """Ingest only eligible files and report pending work without upgrading metadata."""
    reports = []
    for item in prepared:
        report = {**item.report, "index_status": "not_requested"}
        if not item.report["ingestion_ready"]:
            report.update(status="pending", index_status="blocked")
        else:
            result = await rag.ingest(
                item.entry.file,
                CONTENT_TYPES[item.metadata.document_type],
                item.content,
                item.metadata,
                source_page_start=item.entry.source_page_start,
            )
            report.update(result.model_dump(mode="json"))
            if index and result.status != "failed":
                # Duplicates retain their original metadata, not this request's assertions.
                stored, _ = await rag.knowledge.get(result.document_id)
                if (
                    stored["verification_status"] != "verified"
                    or stored["license_status"] != "authorized"
                ):
                    report["index_status"] = "pending_source_review"
                elif not embeddings_configured:
                    report["index_status"] = "pending_credentials"
                else:
                    try:
                        report["index_result"] = await rag.index(result.document_id)
                        report["index_status"] = "indexed"
                    except AppError as error:
                        report.update(index_status="failed", index_error=error.code)
            elif result.status == "failed":
                report["index_status"] = "blocked"
        reports.append(report)
    return {"reports": reports, "stats": await rag.knowledge.stats()}
