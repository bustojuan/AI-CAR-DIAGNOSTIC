"""Re-extract existing local sources. Default is a plan; --apply replaces derived text only."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.core.exceptions import AppError
from app.rag.import_manifest import prepare_manifest
from app.rag.repository import PostgresKnowledgeStore
from app.repositories.postgres import PostgresStore


async def run(settings, manifests, *, apply=False):
    prepared = [p for path in manifests for p in prepare_manifest(path, settings)]
    if any(not p.report["ingestion_ready"] for p in prepared):
        raise ValueError("All requested files must pass extraction preflight.")
    store = PostgresStore(settings)
    reports = []
    try:
        knowledge = PostgresKnowledgeStore(store)
        for p in prepared:
            digest = p.report["sha256"]
            identifier = uuid5(NAMESPACE_URL, "ai-car-document:" + digest)
            document, old = await knowledge.get(identifier)
            if any(
                document[key] != value
                for key, value in p.metadata.model_dump(
                    exclude={"content_hash", "storage_path", "ingestion_status"}
                ).items()
            ):
                raise ValueError("Stored metadata differs; review before re-extraction.")
            changed = [
                (c["chunk_id"], c["content_hash"], c["page"], c["section"]) for c in old
            ] != [(c.chunk_id, c.content_hash, c.page, c.section) for c in p.chunks]
            if changed and apply:
                await knowledge.replace_unindexed_chunks(identifier, digest, old, p.chunks)
            reports.append(
                {
                    "document_id": str(identifier),
                    "old_chunks": len(old),
                    "new_chunks": len(p.chunks),
                    "status": "refreshed"
                    if changed and apply
                    else "planned"
                    if changed
                    else "unchanged",
                }
            )
        return {
            "mode": "apply" if apply else "plan_only",
            "embedding_calls_performed": False,
            "reports": reports,
        }
    finally:
        await store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with asyncio.Runner(loop_factory=selector_loop) as runner:
            result = runner.run(run(Settings(), args.manifest, apply=args.apply))
        serialized = json.dumps(result, indent=2) + "\n"
        if args.output:
            args.output.write_text(serialized, encoding="utf-8")
            print(
                json.dumps(
                    {
                        "mode": result["mode"],
                        "documents": len(result["reports"]),
                        "statuses": {
                            status: sum(r["status"] == status for r in result["reports"])
                            for status in ("planned", "refreshed", "unchanged")
                        },
                        "embedding_calls_performed": False,
                    },
                    indent=2,
                )
            )
        else:
            print(serialized)
    except (AppError, ValueError) as error:
        parser.exit(1, f"Re-extraction stopped: {error}\n")
