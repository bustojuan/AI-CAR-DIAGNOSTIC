"""Local corpus ingestion and indexing. Both commands operate on the configured database."""

import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.database.schemas import DocumentCreate
from app.rag.embeddings import OpenAIEmbeddingClient
from app.rag.import_manifest import ingest_prepared, preparation_report, prepare_manifest
from app.rag.repository import PostgresKnowledgeStore
from app.rag.service import RagService
from app.repositories.postgres import PostgresStore


async def run(index):
    settings = Settings()
    store = PostgresStore(settings)
    try:
        await store.initialize()
        rag = RagService(PostgresKnowledgeStore(store), OpenAIEmbeddingClient(settings), settings)
        reports = []
        for path in sorted((Path(__file__).parent / "corpus").glob("*.md")):
            metadata = DocumentCreate(
                title=path.stem,
                source_name="Internal demonstration corpus",
                publisher="AI Car Diagnostic project",
                document_type="markdown",
                evidence_type="internal_demo",
                language="en-es",
                license_status="authorized",
                verification_status="verified",
                content_hash="0" * 64,
            )
            report = await rag.ingest(path.name, "text/markdown", path.read_bytes(), metadata)
            reports.append(report.model_dump(mode="json"))
            if index and report.status != "failed":
                await rag.index(report.document_id)
        print(json.dumps({"reports": reports, "stats": await rag.knowledge.stats()}, indent=2))
    finally:
        await store.close()


async def run_manifest(settings, prepared, index):
    store = PostgresStore(settings)
    try:
        await store.initialize()
        rag = RagService(PostgresKnowledgeStore(store), OpenAIEmbeddingClient(settings), settings)
        return await ingest_prepared(
            prepared, rag, index=index, embeddings_configured=bool(settings.openai_api_key)
        )
    finally:
        await store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest local demo corpus; --index makes paid embedding calls."
    )
    parser.add_argument("--index", action="store_true", help="Generate OpenAI embeddings (paid)")
    parser.add_argument("--manifest", type=Path, help="Reviewed local batch JSON manifest")
    parser.add_argument("--dry-run", action="store_true", help="Prepare manifest without DB writes")
    parser.add_argument("--output", type=Path, help="Write a new report file instead of stdout")
    args = parser.parse_args()
    if (args.dry_run or args.output) and not args.manifest:
        parser.error("--dry-run and --output require --manifest")
    if args.manifest:
        if args.output and args.output.exists():
            parser.error("Report already exists; choose a new --output path")
        try:
            settings = Settings()
            prepared = prepare_manifest(args.manifest, settings)
        except (OSError, ValueError):
            parser.exit(1, "Unable to prepare manifest; check its structure and local files.\n")
        if args.dry_run:
            result = preparation_report(prepared)
        else:
            with asyncio.Runner(loop_factory=selector_loop) as runner:
                result = runner.run(run_manifest(settings, prepared, args.index))
        serialized = json.dumps(result, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(serialized)
        else:
            print(serialized, end="")
    else:
        with asyncio.Runner(loop_factory=selector_loop) as runner:
            runner.run(run(args.index))
