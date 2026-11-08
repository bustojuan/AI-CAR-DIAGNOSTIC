"""Read-only corpus audit and indexing plan. Never creates an embedding client."""

import argparse
import asyncio
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select, text

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.database.models import DocumentChunkRow, TechnicalDocumentRow, VehicleRow
from app.database.session import inspect_database, make_engine, make_sessions
from app.models.vehicle import GOLF_ID, Vehicle
from app.rag.compatibility import compatible, related_volkswagen
from app.rag.evaluation_dataset import GroundedDataset, load_grounded_dataset
from app.rag.import_manifest import prepare_manifest


def scope_for(document, vehicle, allow_related):
    if compatible(SimpleNamespace(**document), vehicle):
        return "matching_vehicle_metadata"
    if allow_related and related_volkswagen(SimpleNamespace(**document), vehicle):
        return "related_volkswagen_learning"
    return "excluded_vehicle_scope"


def audit_corpus(documents, chunks, vehicle, settings):
    """Assess storage integrity/eligibility, not mechanical truth or semantic recall."""
    grouped = defaultdict(list)
    for chunk in chunks:
        grouped[chunk["document_id"]].append(chunk)
    inventory, hash_counts = [], Counter(c["content_hash"] for c in chunks)
    for document in sorted(documents, key=lambda d: str(d["id"])):
        rows = sorted(grouped[document["id"]], key=lambda c: c["chunk_index"])
        blockers, warnings = [], []
        for field, expected in (
            ("license_status", "authorized"),
            ("verification_status", "verified"),
            ("ingestion_status", "processed"),
        ):
            if document[field] != expected:
                blockers.append(field + "_not_" + expected)
        if not rows:
            blockers.append("no_chunks")
        if not all(document.get(key) for key in ("title", "publisher", "source_name")):
            blockers.append("incomplete_provenance")
        if [c["chunk_index"] for c in rows] != list(range(len(rows))):
            blockers.append("non_contiguous_chunk_indices")
        damaged = [
            str(c["id"])
            for c in rows
            if not c["content"].strip()
            or hashlib.sha256(c["content"].encode()).hexdigest() != c["content_hash"]
            or len(c["content"]) > settings.chunk_size
            or (document["document_type"] == "pdf" and not c["page_number"])
        ]
        if damaged:
            blockers.append("invalid_chunk_integrity")
        short = sum(len(c["content"]) < 80 for c in rows)
        replacements = sum("\ufffd" in c["content"] for c in rows)
        if short:
            warnings.append("short_chunks_review_context")
        if replacements:
            warnings.append("replacement_characters_review_source")
        scope = scope_for(document, vehicle, settings.rag_allow_related_volkswagen)
        if scope == "excluded_vehicle_scope":
            blockers.append(scope)
        pending = [
            c
            for c in rows
            if not c["has_embedding"]
            or c["embedding_model"] != settings.embedding_model
            or c["embedding_dimensions"] != settings.embedding_dimensions
        ]
        inventory.append(
            {
                "document_id": str(document["id"]),
                "title": document["title"],
                "publisher": document["publisher"],
                "source_name": document["source_name"],
                "source_url": document["source_url"] if document["public_source_url"] else None,
                "content_hash": document["content_hash"],
                "source_model": document["model"],
                "source_engine": document["engine"],
                "source_engine_code": document["engine_code"],
                "license_status": document["license_status"],
                "verification_status": document["verification_status"],
                "evidence_type": document["evidence_type"],
                "scope": scope,
                "chunks": len(rows),
                "pending_embedding_chunks": len(pending),
                "first_page": min(
                    (c["page_number"] for c in rows if c["page_number"]), default=None
                ),
                "last_page": max(
                    (c["page_number"] for c in rows if c["page_number"]), default=None
                ),
                "short_chunks": short,
                "replacement_character_chunks": replacements,
                "invalid_chunk_ids": damaged,
                "blockers": blockers,
                "warnings": warnings,
                "index_eligible": not blockers,
            }
        )
    ready = [d for d in inventory if d["index_eligible"]]
    return {
        "format": "ai-car-rag-readiness-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "database_writes_performed": False,
        "embedding_calls_performed": False,
        "semantic_quality_verified": False,
        "vehicle": vehicle.model_dump(mode="json", exclude={"vin", "additional_information"}),
        "allow_related_volkswagen": settings.rag_allow_related_volkswagen,
        "documents": len(documents),
        "chunks": len(chunks),
        "embedded_chunks": sum(c["has_embedding"] for c in chunks),
        "duplicate_chunk_copies": sum(n - 1 for n in hash_counts.values()),
        "eligible_documents": len(ready),
        "eligible_chunks": sum(d["chunks"] for d in ready),
        "blocked_documents": len(inventory) - len(ready),
        "index_plan": {
            "embedding_model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
            "document_ids": [d["document_id"] for d in ready if d["pending_embedding_chunks"]],
            "pending_chunks": sum(d["pending_embedding_chunks"] for d in ready),
            "planned_embedding_chunks": sum(
                d["chunks"] for d in ready if d["pending_embedding_chunks"]
            ),
            "requires_explicit_paid_index_operation": True,
        },
        "inventory": inventory,
    }


def validate_ground_truth(dataset, documents, chunks):
    """Check frozen citation anchors; this does not simulate semantic retrieval."""
    dataset = GroundedDataset.model_validate(dataset).model_dump(mode="json")
    by_document = {str(d["id"]): d for d in documents}
    by_chunk = {str(c["id"]): c for c in chunks}
    results = []
    for case in dataset["cases"]:
        errors = []
        for anchor in case["anchors"]:
            document = by_document.get(anchor["document_id"])
            chunk = by_chunk.get(anchor["chunk_id"])
            if not document or not chunk:
                errors.append("missing_source_anchor")
            elif (
                str(chunk["document_id"]) != anchor["document_id"]
                or chunk["content_hash"] != anchor["content_hash"]
                or chunk["page_number"] != anchor["page"]
                or document["title"] != anchor["document_title"]
            ):
                errors.append("source_anchor_changed")
        results.append({"id": case["id"], "anchors_valid": not errors, "errors": errors})
    return {"cases": results, "all_anchors_valid": all(r["anchors_valid"] for r in results)}


def audit_local_sources(manifests, documents, chunks, settings):
    """Re-extract authorized local sources and compare immutable stored provenance."""
    by_hash = {d["content_hash"]: d for d in documents}
    stored = defaultdict(list)
    for chunk in chunks:
        stored[chunk["document_id"]].append(chunk)
    results, covered = [], set()
    for manifest in manifests:
        for prepared in prepare_manifest(manifest, settings):
            digest = prepared.report.get("sha256")
            document = by_hash.get(digest)
            problems = list(prepared.report["blockers"])
            if document is None:
                problems.append("source_not_in_database")
            else:
                covered.add(str(document["id"]))
                expected = [
                    (str(c.chunk_id), c.content_hash, c.page, c.section)
                    for c in (prepared.chunks or [])
                ]
                actual = [
                    (str(c["id"]), c["content_hash"], c["page_number"], c["section"])
                    for c in sorted(stored[document["id"]], key=lambda c: c["chunk_index"])
                ]
                if expected != actual:
                    problems.append("stored_extraction_differs")
                metadata = prepared.metadata.model_dump(
                    exclude={"content_hash", "storage_path", "ingestion_status"}
                )
                if any(document[key] != value for key, value in metadata.items()):
                    problems.append("manifest_metadata_differs")
            results.append(
                {
                    "entry_id": prepared.entry.id,
                    "document_id": str(document["id"]) if document else None,
                    "source_sha256": digest,
                    "original_page_start": prepared.entry.source_page_start,
                    "reproduced_chunks": len(prepared.chunks or []),
                    "extraction_warning_count": len(prepared.report.get("warnings", [])),
                    "problems": problems,
                }
            )
    # Internal notes are source-controlled and have no PDF manifest.
    for path in sorted((Path(__file__).parent / "corpus").glob("*.md")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        document = by_hash.get(digest)
        if document and document["evidence_type"] == "internal_demo":
            covered.add(str(document["id"]))
    return {
        "entries": results,
        "all_requested_sources_reproduced": all(not r["problems"] for r in results),
        "covered_documents": len(covered),
        "uncovered_document_ids": sorted(
            str(d["id"]) for d in documents if str(d["id"]) not in covered
        ),
        "limitation": (
            "Byte identity and reproducible extraction do not verify mechanical accuracy."
        ),
    }


async def audit_database(settings, vehicle_id=GOLF_ID, dataset=None, manifests=()):
    engine = make_engine(settings)
    try:
        async with make_sessions(engine)() as session, session.begin():
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
            info = await inspect_database(await session.connection())
            row = await session.get(VehicleRow, vehicle_id)
            if row is None:
                raise ValueError("Requested vehicle does not exist.")
            vehicle = Vehicle.model_validate(
                {
                    "vehicle_id": row.id,
                    **{
                        key: getattr(row, key)
                        for key in Vehicle.model_fields
                        if key != "vehicle_id"
                    },
                }
            )
            documents = [
                {c.name: getattr(d, c.name) for c in TechnicalDocumentRow.__table__.columns}
                for d in (await session.scalars(select(TechnicalDocumentRow))).all()
            ]
            table = DocumentChunkRow.__table__
            chunks = [
                dict(c)
                for c in (
                    await session.execute(
                        select(
                            *[c for c in table.c if c.name != "embedding"],
                            table.c.embedding.is_not(None).label("has_embedding"),
                        )
                    )
                ).mappings()
            ]
            report = {**audit_corpus(documents, chunks, vehicle, settings), "database": info}
            if dataset:
                report["evaluation_preflight"] = validate_ground_truth(dataset, documents, chunks)
            if manifests:
                report["local_source_verification"] = await asyncio.to_thread(
                    audit_local_sources, manifests, documents, chunks, settings
                )
            return report
    finally:
        await engine.dispose()


if __name__ == "__main__":
    from uuid import UUID

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vehicle-id", type=UUID, default=GOLF_ID)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--manifest", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dataset = load_grounded_dataset(args.dataset) if args.dataset else None
    with asyncio.Runner(loop_factory=selector_loop) as runner:
        result = runner.run(audit_database(Settings(), args.vehicle_id, dataset, args.manifest))
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "documents",
                        "chunks",
                        "embedded_chunks",
                        "eligible_documents",
                        "eligible_chunks",
                        "blocked_documents",
                        "duplicate_chunk_copies",
                        "embedding_calls_performed",
                    )
                },
                indent=2,
            )
        )
    else:
        print(serialized, end="")
