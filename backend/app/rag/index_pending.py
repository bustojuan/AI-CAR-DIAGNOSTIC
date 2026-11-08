"""Plan eligible indexing by default; only --execute can call the paid provider."""

import argparse
import asyncio
import json
from uuid import UUID

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.core.exceptions import AppError
from app.models.vehicle import GOLF_ID
from app.rag.embeddings import OpenAIEmbeddingClient
from app.rag.readiness import audit_database
from app.rag.repository import PostgresKnowledgeStore
from app.rag.service import RagService
from app.repositories.postgres import PostgresStore


async def run(settings, *, execute=False, vehicle_id=GOLF_ID):
    report = await audit_database(settings, vehicle_id)
    result = {
        "mode": "execute" if execute else "plan_only",
        "plan": report["index_plan"],
        "blocked_documents": report["blocked_documents"],
        "results": [],
    }
    if not execute:
        return result
    if not settings.openai_api_key:
        raise AppError(
            503, "embeddings_not_configured", "Configure OPENAI_API_KEY before --execute."
        )
    store = PostgresStore(settings)
    try:
        await store.initialize()
        rag = RagService(PostgresKnowledgeStore(store), OpenAIEmbeddingClient(settings), settings)
        for identifier in report["index_plan"]["document_ids"]:
            try:
                indexed = await rag.index(UUID(identifier))
                result["results"].append(
                    {"document_id": identifier, "status": "indexed", **indexed}
                )
            except AppError as error:
                result["results"].append(
                    {"document_id": identifier, "status": "failed", "error_code": error.code}
                )
                # Stop rather than repeatedly spending calls after a provider failure.
                break
        return result
    finally:
        await store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute", action="store_true", help="Explicitly generate paid embeddings"
    )
    parser.add_argument("--vehicle-id", type=UUID, default=GOLF_ID)
    args = parser.parse_args()
    try:
        with asyncio.Runner(loop_factory=selector_loop) as runner:
            result = runner.run(run(Settings(), execute=args.execute, vehicle_id=args.vehicle_id))
        print(json.dumps(result, indent=2, default=str))
        if any(row["status"] == "failed" for row in result["results"]):
            raise SystemExit(1)
    except AppError as error:
        parser.exit(1, f"{error.code}: {error.message}\n")
