import hashlib
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.core.exceptions import AppError
from app.main import create_app
from app.models.vehicle import GOLF_ID, seed_vehicle
from app.rag.readiness import audit_database
from app.rag.repository import PostgresKnowledgeStore
from app.rag.schemas import StoredChunk
from app.repositories.postgres import PostgresStore
from tests.conftest import FakeClient
from tests.rag.test_service import metadata

pytestmark = pytest.mark.database


async def test_duplicate_evidence_does_not_starve_distinct_sources_and_audit_is_read_only(
    db_settings,
):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        unique_id = None
        for index in range(15):
            # Different original files can contain identical extracted paragraphs.
            content = (
                "Duplicated battery paragraph." if index < 14 else "Distinct charging evidence."
            )
            chunk = StoredChunk(
                chunk_id=uuid4(),
                chunk_index=0,
                text=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
            )
            identifier, _, _ = await knowledge.ingest(
                metadata(title=f"Source {index}", publisher="Fixture"),
                hashlib.sha256(f"original-file-{index}".encode()).hexdigest(),
                [chunk],
            )
            _, snapshot = await knowledge.get(identifier)
            vector = [1.0, 0.0] if index < 14 else [0.99, 0.01]
            await knowledge.save_vectors(
                identifier,
                snapshot,
                [vector + [0.0] * 1534],
                db_settings.embedding_model,
                1536,
            )
            if index == 14:
                unique_id = identifier
        hits, count, _, _ = await knowledge.search(
            seed_vehicle(),
            [1.0] + [0.0] * 1535,
            db_settings.embedding_model,
            1536,
            2,
            0.8,
        )
        assert len(hits) == count == 2
        assert unique_id in {r["document_id"] for r in hits}
        assert len({r["relevant_text"] for r in hits}) == 2
        before = await knowledge.stats()
        report = await audit_database(db_settings)
        assert report["eligible_documents"] == 15 and report["embedded_chunks"] == 15
        assert report["duplicate_chunk_copies"] == 13
        assert report["index_plan"]["pending_chunks"] == 0
        assert report["index_plan"]["document_ids"] == []
        assert await knowledge.stats() == before
    finally:
        await store.close()


async def test_reextract_preserves_sources_and_refuses_stale_indexed_or_cited_text(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)

        def chunk(content):
            return StoredChunk(
                chunk_id=uuid4(),
                chunk_index=0,
                text=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
            )

        first, second = chunk("Old extraction fixture."), chunk("Improved extraction fixture.")
        digest = hashlib.sha256(b"immutable original source bytes").hexdigest()
        identifier, _, _ = await knowledge.ingest(metadata(publisher="Fixture"), digest, [first])
        original, snapshot = await knowledge.get(identifier)
        await knowledge.replace_unindexed_chunks(identifier, digest, snapshot, [second])
        saved, updated = await knowledge.get(identifier)
        assert saved == original and updated[0]["text"] == second.text
        with pytest.raises(AppError) as stale:
            await knowledge.replace_unindexed_chunks(identifier, digest, snapshot, [first])
        assert stale.value.code == "document_changed"
        await knowledge.save_vectors(
            identifier, updated, [[1.0] + [0.0] * 1535], db_settings.embedding_model, 1536
        )
        with pytest.raises(AppError) as indexed:
            await knowledge.replace_unindexed_chunks(identifier, digest, updated, [first])
        assert indexed.value.code == "source_already_indexed"
        app = create_app(db_settings, llm_client=FakeClient())
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
        ):
            result = await api.post(
                "/api/v1/diagnostics",
                json={
                    "vehicle_id": str(GOLF_ID),
                    "description": "My brakes have failed.",
                },
            )
            assert result.status_code == 201
            async with store.sessions() as session, session.begin():
                # A historical reference must remain valid even if its vectors were lost.
                await session.execute(
                    text(
                        "UPDATE document_chunks SET embedding=NULL, "
                        "embedding_model=NULL, embedding_dimensions=NULL WHERE document_id=:id"
                    ),
                    {"id": identifier},
                )
                await session.execute(
                    text("UPDATE diagnostics SET citations=CAST(:citations AS jsonb) WHERE id=:id"),
                    {
                        "id": result.json()["diagnostic_id"],
                        "citations": '[{"document_id":"' + str(identifier) + '"}]',
                    },
                )
            with pytest.raises(AppError) as cited:
                await knowledge.replace_unindexed_chunks(identifier, digest, updated, [first])
            assert cited.value.code == "source_already_cited"
            _, retained = await knowledge.get(identifier)
            assert retained == updated
    finally:
        await store.close()
