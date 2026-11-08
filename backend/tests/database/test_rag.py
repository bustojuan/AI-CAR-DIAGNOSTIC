import json
from uuid import UUID

import httpx
import pymupdf
import pytest

from app.main import create_app
from app.models.vehicle import GOLF_ID, seed_vehicle
from app.rag.import_manifest import ingest_prepared, prepare_manifest
from app.rag.repository import PostgresKnowledgeStore
from app.rag.service import RagService, validated_citations
from app.repositories.postgres import PostgresStore
from tests.rag.fakes import FakeEmbeddings
from tests.rag.test_api_diagnostics import CitingClient
from tests.rag.test_service import metadata

pytestmark = pytest.mark.database


async def test_strict_golf_plus_2009_cffb_filters_year_and_engine_before_results(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        rag = RagService(PostgresKnowledgeStore(store), DatabaseEmbeddings(), db_settings)
        expected = None
        for title, start, end, code in (
            ("CFFB 2009 reference", 2009, 2014, "CFFB"),
            ("Legacy 2006 reference", 2006, 2006, "CFFB"),
            ("Other engine reference", 2009, 2014, "CBAB"),
        ):
            report = await rag.ingest(
                "reference.md",
                "text/markdown",
                f"Battery {title}.".encode(),
                metadata(
                    title=title,
                    evidence_type="third_party_technical",
                    manufacturer="Volkswagen",
                    model="Golf Plus",
                    engine="2.0 TDI",
                    model_year_start=start,
                    model_year_end=end,
                    engine_code=code,
                    transmission="Manual",
                ),
            )
            await rag.index(report.document_id)
            if code == "CFFB" and start == 2009:
                expected = report.document_id
        hits = await rag.retrieve(seed_vehicle(), "Battery")
        assert hits.available and {d.document_id for d in hits.documents} == {expected}
        assert (
            hits.documents[0].relevance_metadata["reference_scope"] == "matching_vehicle_metadata"
        )
        assert "gearbox code" in hits.reason and "PR codes" in hits.reason
    finally:
        await store.close()


async def test_batch_manifest_persists_ready_text_and_keeps_missing_manual_pending(
    db_settings, tmp_path
):
    (tmp_path / "note.md").write_text("Battery cranking reference.", encoding="utf-8")
    document_metadata = metadata().model_dump(
        exclude={"content_hash", "storage_path", "ingestion_status"}
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "format": "ai-car-rag-import-v1",
                "documents": [
                    {"id": "ready", "file": "note.md", "metadata": document_metadata},
                    {
                        "id": "missing_manual",
                        "file": "missing.pdf",
                        "metadata": {
                            **document_metadata,
                            "document_type": "pdf",
                            "license_status": "unknown",
                            "verification_status": "unverified",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    prepared = prepare_manifest(manifest, db_settings)
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        embeddings = DatabaseEmbeddings()
        rag = RagService(PostgresKnowledgeStore(store), embeddings, db_settings)
        result = await ingest_prepared(prepared, rag, index=True, embeddings_configured=False)
        assert result["reports"][0]["status"] == "processed"
        assert result["reports"][0]["index_status"] == "pending_credentials"
        assert result["reports"][1]["status"] == "pending"
        assert result["stats"]["documents"] == 1 and not embeddings.calls
    finally:
        await store.close()
    restarted = PostgresStore(db_settings)
    try:
        knowledge = PostgresKnowledgeStore(restarted)
        saved, chunks = await knowledge.get(UUID(result["reports"][0]["document_id"]))
        assert saved["ingestion_status"] == "processed" and chunks
        stats = await knowledge.stats()
        assert stats["documents"] == 1 and stats["indexed_chunks"] == 0
    finally:
        await restarted.close()


class DatabaseEmbeddings(FakeEmbeddings):
    dimensions = 1536

    async def embed(self, texts):
        return [vector + [0.0] * 1532 for vector in await super().embed(texts)]


async def test_real_pgvector_filters_precede_limit_and_generic_fallback(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        rag = RagService(PostgresKnowledgeStore(store), DatabaseEmbeddings(), db_settings)
        for index in range(8):
            result = await rag.ingest(
                "x.md",
                "text/markdown",
                f"Battery incompatible {index}".encode(),
                metadata(evidence_type="official_manufacturer", manufacturer="Volvo"),
            )
            await rag.index(result.document_id)
        good = await rag.ingest(
            "x.md", "text/markdown", b"Battery compatible generic fixture.", metadata()
        )
        await rag.index(good.document_id)
        hits = await rag.retrieve(seed_vehicle(), "Battery")
        assert hits.available and hits.documents
        assert {document.document_id for document in hits.documents} == {good.document_id}
        citations = validated_citations([hits.documents[0].citation.chunk_id], hits)
        assert citations[0].evidence_type == "internal_demo"
        await rag.index(good.document_id)
        await rag.knowledge.delete(good.document_id)
        assert not (await rag.retrieve(seed_vehicle(), "Battery")).documents
    finally:
        await store.close()


@pytest.mark.parametrize("pdf_page_start", [None, 101])
async def test_real_rag_citations_survive_app_restart(db_settings, pdf_page_start):
    app = create_app(db_settings, embedding_client=DatabaseEmbeddings(), llm_client=CitingClient())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        if pdf_page_start is None:
            result = await app.state.rag.ingest(
                "x.md", "text/markdown", b"Battery cranking reference.", metadata()
            )
        else:
            with pymupdf.open() as document:
                document.new_page().insert_text((72, 72), "Battery cranking reference.")
                content = document.tobytes()
            result = await app.state.rag.ingest(
                "part.pdf",
                "application/pdf",
                content,
                metadata(document_type="pdf"),
                source_page_start=pdf_page_start,
            )
        await app.state.rag.index(result.document_id)
        response = await api.post(
            "/api/v1/diagnostics",
            json={"vehicle_id": str(GOLF_ID), "description": "Battery cranking problem."},
        )
        assert response.status_code == 201, response.text
        report = response.json()
        assert report["citations"] and report["rag_available"]
        if pdf_page_start is not None:
            assert report["citations"][0]["page"] == pdf_page_start
    restarted = create_app(
        db_settings, embedding_client=DatabaseEmbeddings(), llm_client=CitingClient()
    )
    async with (
        restarted.router.lifespan_context(restarted),
        httpx.AsyncClient(transport=httpx.ASGITransport(restarted), base_url="http://test") as api,
    ):
        response = await api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}")
        assert response.json() == report


async def test_unknown_engine_code_and_embedding_model_are_disclosed(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        rag = RagService(PostgresKnowledgeStore(store), DatabaseEmbeddings(), db_settings)
        result = await rag.ingest(
            "x.md",
            "text/markdown",
            b"Battery engine-code specific fixture.",
            metadata(
                evidence_type="official_manufacturer",
                manufacturer="Volkswagen",
                engine_code="TEST-CODE",
            ),
        )
        await rag.index(result.document_id)
        hits = await rag.retrieve(
            seed_vehicle().model_copy(update={"engine_code": None}), "Battery"
        )
        assert not hits.documents and hits.missing_vehicle_fields == ["engine_code"]
        other = DatabaseEmbeddings()
        other.model = "different-fixture-model"
        rag.embeddings = other
        hits = await rag.retrieve(seed_vehicle(), "Battery")
        assert not hits.documents and "other embedding models" in hits.reason
    finally:
        await store.close()


@pytest.mark.parametrize("reference_year", [2002, 2009, 2015])
async def test_related_vw_learning_mode_keeps_provenance_and_excludes_other_brands(
    db_settings, reference_year
):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        strict = RagService(knowledge, DatabaseEmbeddings(), db_settings)
        identifiers = {}
        for model, manufacturer, year, engine in [
            ("Jetta", "Volkswagen", reference_year, None),
            ("XC60", "Volvo", 2009, None),
            ("Golf", "Volkswagen", 2025, None),
            ("Passat", "Volkswagen", 2009, "1.6 petrol"),
        ]:
            result = await strict.ingest(
                "reference.md",
                "text/markdown",
                f"Battery {model} learning reference".encode(),
                metadata(
                    title=f"{manufacturer} {model} {year} reference",
                    evidence_type="third_party_technical",
                    manufacturer=manufacturer,
                    model=model,
                    model_year_start=year,
                    model_year_end=year,
                    engine=engine,
                ),
            )
            await strict.index(result.document_id)
            identifiers[model] = result.document_id
        assert not (await strict.retrieve(seed_vehicle(), "Battery")).documents
        learning = RagService(
            knowledge,
            DatabaseEmbeddings(),
            db_settings.model_copy(update={"rag_allow_related_volkswagen": True}),
        )
        hits = await learning.retrieve(seed_vehicle(), "Battery")
        assert hits.available and {d.document_id for d in hits.documents} == {identifiers["Jetta"]}
        assert hits.documents[0].title == f"Volkswagen Jetta {reference_year} reference"
        assert hits.documents[0].relevance_metadata["source_model"] == "Jetta"
        assert (
            hits.documents[0].relevance_metadata["reference_scope"] == "related_volkswagen_learning"
        )
        assert "not verified for this vehicle" in hits.reason
        assert not (await strict.retrieve(seed_vehicle(), "Battery")).documents
    finally:
        await store.close()


async def test_related_tdi_engine_variant_retains_its_code_and_is_not_exact_fitment(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        strict = RagService(knowledge, DatabaseEmbeddings(), db_settings)
        report = await strict.ingest(
            "reference.md",
            "text/markdown",
            b"Cooling and EGR training reference for CBAB.",
            metadata(
                title="Tiguan CBAB training reference",
                evidence_type="third_party_technical",
                manufacturer="Volkswagen",
                model="Tiguan",
                model_year_start=2008,
                engine="2.0 TDI",
                engine_code="CBAB",
            ),
        )
        await strict.index(report.document_id)
        vehicle = seed_vehicle().model_copy(update={"engine_code": "CFFB"})
        assert not (await strict.retrieve(vehicle, "Cooling")).documents
        learning = RagService(
            knowledge,
            DatabaseEmbeddings(),
            db_settings.model_copy(update={"rag_allow_related_volkswagen": True}),
        )
        hits = await learning.retrieve(vehicle, "Cooling")
        assert hits.available and len(hits.documents) == 1
        assert hits.documents[0].relevance_metadata["source_engine_code"] == "CBAB"
        assert (
            hits.documents[0].relevance_metadata["reference_scope"] == "related_volkswagen_learning"
        )
        assert "not verified for this vehicle" in hits.reason
        petrol = vehicle.model_copy(update={"engine": "1.6 petrol"})
        assert not (await learning.retrieve(petrol, "Cooling")).documents
    finally:
        await store.close()
