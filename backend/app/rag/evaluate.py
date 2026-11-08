"""Real retrieval evaluation; requires a migrated/indexed DB and makes paid query embeddings."""

import argparse
import asyncio
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from types import SimpleNamespace

from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.models.vehicle import GOLF_ID
from app.rag.compatibility import compatible, related_volkswagen
from app.rag.embeddings import OpenAIEmbeddingClient
from app.rag.evaluation_dataset import load_evaluation_cases, load_grounded_dataset
from app.rag.readiness import audit_database
from app.rag.repository import PostgresKnowledgeStore
from app.rag.service import RagService, validated_citations
from app.repositories.postgres import PostgresStore


def metrics(retrieved, relevant):
    relevant = set(relevant)
    hits = set(retrieved) & relevant
    recall = len(hits) / len(relevant) if relevant else None
    reciprocal = (
        next((1 / (index + 1) for index, value in enumerate(retrieved) if value in relevant), 0.0)
        if relevant
        else None
    )
    return recall, reciprocal


def mean_or_none(values):
    values = [value for value in values if value is not None]
    return mean(values) if values else None


async def evaluate(dataset_path=None, vehicle_id=GOLF_ID):
    settings = Settings()
    dataset_path = dataset_path or Path(__file__).parent / "evaluation.json"
    cases, judgment_type = load_evaluation_cases(dataset_path)
    if judgment_type == "source_chunks":
        preflight = await audit_database(settings, vehicle_id, load_grounded_dataset(dataset_path))
        if not preflight["evaluation_preflight"]["all_anchors_valid"]:
            raise RuntimeError(
                "Evaluation anchors changed; review the dataset before paid queries."
            )
        eligible_ids = {d["document_id"] for d in preflight["inventory"] if d["index_eligible"]}
        if any(a["document_id"] not in eligible_ids for case in cases for a in case["anchors"]):
            raise RuntimeError("Evaluation sources are outside the eligible vehicle/source scope.")
    store = PostgresStore(settings)
    try:
        await store.initialize()
        async with store.transaction() as repository:
            vehicle = await repository.get_vehicle(vehicle_id)
        if vehicle is None:
            raise ValueError("Requested evaluation vehicle does not exist.")
        rag = RagService(PostgresKnowledgeStore(store), OpenAIEmbeddingClient(settings), settings)
        rows = []
        for case in cases:
            started = perf_counter()
            result = await rag.retrieve(vehicle, case["query"])
            if not result.available:
                raise RuntimeError(
                    "Retrieval unavailable; evaluation cannot produce valid metrics."
                )
            titles = list(dict.fromkeys(document.title for document in result.documents))
            if judgment_type == "source_chunks":
                relevant = [a["chunk_id"] for a in case["anchors"]]
                retrieved = [str(d.citation.chunk_id) for d in result.documents]
            else:
                relevant, retrieved = case["relevant"], titles
            recall, reciprocal = metrics(retrieved, relevant)
            citations = validated_citations(
                [doc.citation.chunk_id for doc in result.documents], result
            )
            valid, applicability = [], []
            for citation in citations:
                metadata, chunks = await rag.knowledge.get(citation.document_id)
                valid.append(
                    any(chunk["chunk_id"] == citation.chunk_id for chunk in chunks)
                    and metadata["title"] == citation.document_title
                )
                source = SimpleNamespace(**metadata)
                applicability.append(
                    compatible(source, vehicle)
                    or (
                        settings.rag_allow_related_volkswagen
                        and related_volkswagen(source, vehicle)
                    )
                )
            rows.append(
                dict(
                    id=case["id"],
                    retrieved=titles,
                    retrieved_chunk_ids=[str(c.chunk_id) for c in citations],
                    recall=recall,
                    reciprocal_rank=reciprocal,
                    latency_ms=(perf_counter() - started) * 1000,
                    citations_valid=all(valid),
                    vehicle_compatible=all(applicability),
                    no_evidence_correct=not titles if not relevant else None,
                    expected_scope=case.get("expected_scope"),
                    returned_scopes=[
                        d.relevance_metadata.get("reference_scope") for d in result.documents
                    ],
                )
            )
        return {
            "mode": "live_postgres_openai_embeddings",
            "judgment_type": judgment_type,
            "vehicle_id": str(vehicle_id),
            "k": settings.rag_top_k,
            "recall_at_k": mean_or_none(row["recall"] for row in rows),
            "mrr": mean_or_none(row["reciprocal_rank"] for row in rows),
            "citation_validity": mean(row["citations_valid"] for row in rows),
            "vehicle_compatibility_correctness": mean(row["vehicle_compatible"] for row in rows),
            "no_evidence_accuracy": (
                mean(r["no_evidence_correct"] for r in rows if r["no_evidence_correct"] is not None)
                if any(r["no_evidence_correct"] is not None for r in rows)
                else None
            ),
            "mean_latency_ms": mean(row["latency_ms"] for row in rows),
            "unsupported_technical_claims": None,
            "limitation": "Semantic diagnostic claim evaluation requires human review.",
            "cases": rows,
        }
    finally:
        await store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate indexed demo corpus (paid embedding queries)."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dataset", type=Path)
    from uuid import UUID

    parser.add_argument("--vehicle-id", type=UUID, default=GOLF_ID)
    args = parser.parse_args()
    with asyncio.Runner(loop_factory=selector_loop) as runner:
        result = runner.run(evaluate(args.dataset, args.vehicle_id))
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
