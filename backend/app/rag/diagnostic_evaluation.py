"""Opt-in paid diagnostic evaluation; production knowledge is read, never written.

Reports and retrieved passages stay under the ignored .local-tools directory.
Automated provenance checks do NOT judge whether a passage supports a technical claim.
"""

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.ai import prompts
from app.ai.llm_client import LangChainClient
from app.core.config import Settings
from app.core.event_loop import selector_loop
from app.core.exceptions import AppError
from app.main import create_app
from app.models.vehicle import GOLF_ID
from app.rag.compatibility import compatible, related_volkswagen
from app.rag.embeddings import OpenAIEmbeddingClient
from app.rag.repository import PostgresKnowledgeStore
from app.rag.schemas import SourceCitation
from app.rag.service import RagService
from app.repositories.memory import MemoryStore
from app.repositories.postgres import PostgresStore

DATASET = Path(__file__).with_name("diagnostic_evaluation_cases.json")
PRIVATE_ROOT = Path(__file__).resolve().parents[3] / ".local-tools" / "diagnostic-validation"
URGENCY_RANK = {"low": 0, "moderate": 1, "high": 2, "critical": 3}


class RecordingClient:
    def __init__(self, client):
        self.client = client
        self.calls = []

    async def generate(self, schema, system, payload):
        record = {"schema": schema.__name__, "payload": payload}
        self.calls.append(record)
        result = await self.client.generate(schema, system, payload)
        record["output"] = result.model_dump(mode="json")
        return result


class RecordingRetriever:
    def __init__(self, retriever):
        self.retriever = retriever
        self.results = []

    async def retrieve(self, vehicle, query, technical_context=None):
        result = await self.retriever.retrieve(vehicle, query, technical_context)
        self.results.append(result)
        return result


def citation_checks(citation, retrieved, metadata, chunks, vehicle, allow_related):
    """Compare every exposed citation field with storage, not with model assertions."""
    chunk = next((c for c in chunks if c["chunk_id"] == citation.chunk_id), None)
    if chunk is None:
        return {"chunk_exists": False}
    expected = SourceCitation(
        document_id=metadata["id"],
        chunk_id=chunk["chunk_id"],
        document_title=metadata["title"],
        publisher=metadata["publisher"],
        source_url=metadata["source_url"] if metadata["public_source_url"] else None,
        page=chunk["page"],
        section=chunk["section"],
        evidence_type=metadata["evidence_type"],
        verification_status=metadata["verification_status"],
    )
    source = SimpleNamespace(**metadata)
    return {
        "chunk_exists": True,
        "citation_metadata_matches_storage": citation == expected,
        "retrieved_text_matches_storage": retrieved.relevant_text == chunk["text"],
        "chunk_hash_matches_storage": (
            hashlib.sha256(chunk["text"].encode()).hexdigest() == chunk["content_hash"]
        ),
        "source_eligible": metadata["license_status"] == "authorized"
        and metadata["verification_status"] == "verified"
        and metadata["ingestion_status"] == "processed",
        "source_in_allowed_scope": compatible(source, vehicle)
        or (allow_related and related_volkswagen(source, vehicle)),
    }


def report_checks(case, status, report, calls, retrievals, saved):
    checks = {"expected_http_status": status == case["expected_status"]}
    if case["expected_status"] != 201:
        checks["no_provider_calls"] = not calls and not retrievals
        return checks
    if status != 201:
        return {**checks, "assessment_returned": False}
    checks.update(
        expected_generation_mode=report["generation_mode"] == case["expected_mode"],
        saved_report_unchanged=report == saved,
        all_hypotheses_unconfirmed=all(
            cause["label"] == "hypothesis" for cause in report["possible_causes"]
        ),
    )
    if "minimum_urgency" in case:
        checks["minimum_urgency_respected"] = (
            URGENCY_RANK[report["urgency_level"]] >= URGENCY_RANK[case["minimum_urgency"]]
        )
    if case["expected_mode"] == "deterministic_safety":
        checks["no_provider_calls"] = not calls and not retrievals
        checks["no_fabricated_citations"] = not report["citations"]
        checks["stop_and_get_help"] = (
            report["driving_recommendation"] == "stop_safely_do_not_drive"
            and report["professional_assistance_recommended"]
        )
    elif report["urgency_level"] == "critical" and not retrievals:
        # An extraction can conservatively escalate before assessment/retrieval.
        # This verifies that path, not the unvisited technical-question criteria.
        checks["critical_extraction_completed"] = len(calls) == 1 and "output" in calls[0]
        checks["stop_and_get_help"] = (
            report["driving_recommendation"] == "stop_safely_do_not_drive"
            and report["professional_assistance_recommended"]
            and not report["citations"]
        )
    else:
        checks["real_assessment_completed"] = len(calls) in {2, 3} and all(
            "output" in call for call in calls
        )
        checks["grounding_review_completed"] = report["urgency_level"] == "critical" or (
            len(calls) == 3 and "draft_assessment" in calls[-1]["payload"]
        )
        checks["retrieval_available"] = len(retrievals) == 1 and retrievals[0].available
    return checks


async def evaluate(cases, output_directory):
    # Never overwrite the audit trail of a previous run, even with a case selection.
    output_directory.mkdir(parents=True, exist_ok=False)
    settings = Settings()
    if not settings.openai_api_key or not settings.database_url:
        raise ValueError("Configure OPENAI_API_KEY and DATABASE_URL before evaluation.")
    # Bound paid calls. Runtime settings are not changed; tools are outside this evaluation.
    isolated_settings = settings.model_copy(update={"mcp_enabled": False, "llm_max_retries": 0})
    postgres = PostgresStore(settings)
    knowledge = PostgresKnowledgeStore(postgres)
    llm = RecordingClient(LangChainClient(isolated_settings))
    retriever = RecordingRetriever(RagService(knowledge, OpenAIEmbeddingClient(settings), settings))
    memory = MemoryStore()
    await memory.initialize()
    app = create_app(isolated_settings, store=memory, llm_client=llm, retriever=retriever)
    try:
        # Do not initialize/seed/migrate the production store: read the existing vehicle only.
        async with postgres.transaction() as repository:
            vehicle = await repository.get_vehicle(GOLF_ID)
        if vehicle is None:
            raise ValueError("The configured evaluation vehicle does not exist.")
        async with memory.transaction() as repository:
            await repository.save_vehicle(vehicle)
        summary = {
            "created_at": datetime.now(UTC).isoformat(),
            "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
            "prompts_sha256": hashlib.sha256(
                (prompts.EXTRACT + prompts.ASSESS + prompts.REVIEW).encode()
            ).hexdigest(),
            "mode": "live_openai_real_postgres_rag_isolated_case_storage",
            "diagnostic_model": settings.openai_model,
            "embedding_model": settings.embedding_model,
            "retrieval": {
                "top_k": settings.rag_top_k,
                "minimum_similarity": settings.rag_min_similarity,
                "related_volkswagen_enabled": settings.rag_allow_related_volkswagen,
                "query_expansion_enabled": settings.rag_query_expansion_enabled,
            },
            "vehicle": vehicle.model_dump(mode="json", exclude={"vin", "additional_information"}),
            "production_writes": False,
            "mcp_evaluated": False,
            "semantic_claim_review": "pending_manual_review",
            "cases": [],
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://evaluation"
        ) as api:
            for case in cases:
                llm.calls.clear()
                retriever.results.clear()
                started = perf_counter()
                response = await api.post(
                    "/api/v1/diagnostics", json={"vehicle_id": str(GOLF_ID), **case["request"]}
                )
                body = response.json()
                saved = None
                if response.status_code == 201:
                    saved_response = await api.get(f"/api/v1/diagnostics/{body['diagnostic_id']}")
                    saved = saved_response.json() if saved_response.status_code == 200 else None
                checks = report_checks(
                    case, response.status_code, body, llm.calls, retriever.results, saved
                )
                provenance = []
                retrieved = {
                    d.citation.chunk_id: d
                    for result in retriever.results
                    for d in result.documents
                    if d.citation
                }
                for raw in body.get("citations", []):
                    citation = SourceCitation.model_validate(raw)
                    hit = retrieved.get(citation.chunk_id)
                    citation_result = {"citation": raw, "checks": {"actually_retrieved": bool(hit)}}
                    if hit:
                        metadata, chunks = await knowledge.get(citation.document_id)
                        citation_result["checks"].update(
                            citation_checks(
                                citation,
                                hit,
                                metadata,
                                chunks,
                                vehicle,
                                settings.rag_allow_related_volkswagen,
                            )
                        )
                    provenance.append(citation_result)
                checks["citation_provenance_valid"] = all(
                    all(item["checks"].values()) for item in provenance
                )
                row = {
                    "id": case["id"],
                    "http_status": response.status_code,
                    "urgency": body.get("urgency_level"),
                    "citations": provenance,
                    "checks": checks,
                    "automatic_checks_passed": all(checks.values()),
                    "duration_seconds": round(perf_counter() - started, 2),
                    "technical_assessment_performed": any(
                        call["schema"] in {"Assessment", "RagAssessment"} for call in llm.calls
                    ),
                    "manual_review_criteria": case["review_criteria"],
                }
                private = {
                    "case": case,
                    "response": body,
                    "model_calls": llm.calls,
                    "retrievals": [r.model_dump(mode="json") for r in retriever.results],
                    "result": row,
                }
                (output_directory / f"{case['id']}.json").write_text(
                    json.dumps(private, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                summary["cases"].append(row)
                (output_directory / "summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                print(
                    json.dumps(
                        {
                            k: row[k]
                            for k in (
                                "id",
                                "http_status",
                                "urgency",
                                "automatic_checks_passed",
                                "duration_seconds",
                            )
                        }
                    ),
                    flush=True,
                )
        return summary
    finally:
        await postgres.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Make paid OpenAI calls.")
    parser.add_argument("--case", action="append", default=[], help="Select a fixed case ID.")
    parser.add_argument("--run-id", default="latest")
    args = parser.parse_args()
    if not args.run_id or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id
    ):
        parser.error("Use lowercase letters, digits, hyphens or underscores for --run-id.")
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    if set(args.case) - {case["id"] for case in cases}:
        parser.error("Unknown evaluation case.")
    cases = [case for case in cases if not args.case or case["id"] in args.case]
    if not args.execute:
        print(json.dumps({"plan_only": True, "cases": [c["id"] for c in cases]}))
        return
    try:
        with asyncio.Runner(loop_factory=selector_loop) as runner:
            result = runner.run(evaluate(cases, PRIVATE_ROOT / args.run_id))
    except Exception as exc:
        # No provider/SQL exception text: these can contain credentials or source text.
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        print(json.dumps({"evaluation_failed": code}), flush=True)
        raise SystemExit(1) from None
    raise SystemExit(0 if all(r["automatic_checks_passed"] for r in result["cases"]) else 1)


if __name__ == "__main__":
    main()
