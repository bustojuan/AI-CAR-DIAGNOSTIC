"""Real pgvector regression cases for relevance, eligibility and duplicate ranking."""

import hashlib
from uuid import uuid4

import pytest

from app.models.vehicle import seed_vehicle
from app.rag.repository import PostgresKnowledgeStore
from app.rag.schemas import StoredChunk
from app.rag.service import RagService
from app.repositories.postgres import PostgresStore
from tests.rag.test_service import metadata

pytestmark = pytest.mark.database

EXACT = dict(
    evidence_type="third_party_technical",
    manufacturer="Volkswagen",
    model="Golf Plus",
    model_year_start=2009,
    engine="2.0 TDI",
    engine_code="CFFB",
    transmission="Manual",
)
RELATED = {**EXACT, "model": "Golf"}


async def test_service_reranks_beyond_four_without_relaxing_pgvector_gates(db_settings):
    from sqlalchemy import update

    from app.database.models import TechnicalDocumentRow

    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        for index in range(5):
            await add_source(knowledge, db_settings, f"Battery discussion {index}", [1.0, 0.15])
        target = await add_source(
            knowledge,
            db_settings,
            "Battery hazard warning",
            [1.0, 0.5],
            content="Battery electrolyte is corrosive acid; use protective gloves.",
        )
        restricted = await add_source(
            knowledge,
            db_settings,
            "Restricted battery warning",
            [1.0, 0.0],
            content="Battery electrolyte is corrosive acid; use protective gloves. Restricted.",
        )
        await add_source(
            knowledge,
            db_settings,
            "Wrong-brand battery warning",
            [1.0, 0.0],
            scope={**EXACT, "manufacturer": "Volvo"},
        )
        await add_source(knowledge, db_settings, "Battery corrosive acid low relevance", [0.0, 1.0])
        async with knowledge.sessions() as session, session.begin():
            await session.execute(
                update(TechnicalDocumentRow)
                .where(TechnicalDocumentRow.id == restricted)
                .values(license_status="restricted")
            )

        class QueryEmbedding:
            model = db_settings.embedding_model

            async def embed(self, texts):
                return [[1.0] + [0.0] * 1535 for _ in texts]

        query = "Battery hazard warning about corrosive acid and protective gloves"
        baseline = RagService(
            knowledge, QueryEmbedding(), db_settings.model_copy(update={"rag_lexical_weight": 0})
        )
        original = await baseline.retrieve(seed_vehicle(), query)
        assert original.available and target not in {d.document_id for d in original.documents}
        improved = await RagService(knowledge, QueryEmbedding(), db_settings).retrieve(
            seed_vehicle(), query
        )
        assert improved.available and len(improved.documents) == 4
        assert target in {d.document_id for d in improved.documents}
        assert restricted not in {d.document_id for d in improved.documents}
        assert improved.candidate_count == 6
        hit = next(d for d in improved.documents if d.document_id == target)
        assert hit.citation.page == 7
        assert hit.relevant_text == "Battery electrolyte is corrosive acid; use protective gloves."
    finally:
        await store.close()


async def add_source(knowledge, settings, title, vector, *, scope=None, content=None):
    content = content or title
    chunk = StoredChunk(
        chunk_id=uuid4(),
        chunk_index=0,
        text=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        page=7,
    )
    identifier, _, _ = await knowledge.ingest(
        metadata(title=title, **(scope or {})),
        hashlib.sha256(title.encode()).hexdigest(),
        [chunk],
    )
    _, snapshot = await knowledge.get(identifier)
    await knowledge.save_vectors(
        identifier,
        snapshot,
        [vector + [0.0] * (1536 - len(vector))],
        settings.embedding_model,
        1536,
    )
    return identifier


async def search(
    knowledge,
    settings,
    *,
    limit=1,
    related=False,
    minimum=0.35,
    additional_vectors=None,
    requested_identifiers=(),
):
    return await knowledge.search(
        seed_vehicle(),
        [1.0] + [0.0] * 1535,
        settings.embedding_model,
        1536,
        limit,
        minimum,
        allow_related_volkswagen=related,
        additional_vectors=additional_vectors,
        requested_identifiers=requested_identifiers,
    )


@pytest.mark.parametrize("source_scope", [{}, RELATED], ids=["generic", "related-vw"])
async def test_relevance_precedes_vehicle_specificity_without_relaxing_scope(
    db_settings,
    source_scope,
):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        weak = await add_source(
            knowledge, db_settings, "Unrelated brake passage", [0.6, 0.8], scope=EXACT
        )
        relevant = await add_source(
            knowledge,
            db_settings,
            "Relevant starter passage",
            [1.0, 0.0],
            scope=source_scope,
        )
        hits, _, _, _ = await search(knowledge, db_settings, related=True)
        assert [hit["document_id"] for hit in hits] == [relevant]
        assert hits[0]["citation"].page == 7
        assert hits[0]["relevance_metadata"]["cosine_similarity"] == pytest.approx(1.0)
        if source_scope:
            assert hits[0]["relevance_metadata"]["reference_scope"] == "related_volkswagen_learning"
            strict, _, _, _ = await search(knowledge, db_settings)
            assert [hit["document_id"] for hit in strict] == [weak]
        # A higher cutoff excludes the weak passage instead of filling the quota.
        cutoff, _, _, _ = await search(knowledge, db_settings, minimum=0.8)
        assert {hit["document_id"] for hit in cutoff} == (set() if source_scope else {relevant})
    finally:
        await store.close()


async def test_multilingual_vectors_do_not_bypass_eligibility_or_cutoff(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        await add_source(
            knowledge,
            db_settings,
            "Broad pressure discussion",
            [0.8, 0.6, 0.0],
            content="Engine pressure can vary. Generic engine operating information.",
        )
        relevant = await add_source(
            knowledge,
            db_settings,
            "Technical sensor passage",
            [0.0, 1.0, 0.0],
            scope=RELATED,
            content="Le transmetteur G247 mesure la pression du carburant.",
        )
        wrong_brand = await add_source(
            knowledge,
            db_settings,
            "Incompatible G247 reference",
            [0.0, 1.0, 0.0],
            scope={**EXACT, "manufacturer": "Volvo"},
            content="G247 fuel pressure sensor signal.",
        )
        below_cutoff = await add_source(
            knowledge,
            db_settings,
            "Irrelevant lexical match",
            [0.0, 0.0, 1.0],
            content="G247 fuel pressure sensor signal. " * 5,
        )
        hits, _, _, _ = await search(
            knowledge,
            db_settings,
            related=True,
            limit=4,
            additional_vectors=[[0.0, 1.0] + [0.0] * 1534],
        )
        assert hits[0]["document_id"] == relevant
        assert not {wrong_brand, below_cutoff} & {hit["document_id"] for hit in hits}
        strict, _, _, _ = await search(
            knowledge,
            db_settings,
            limit=4,
            additional_vectors=[[0.0, 1.0] + [0.0] * 1534],
        )
        assert relevant not in {hit["document_id"] for hit in strict}
    finally:
        await store.close()


async def test_code_coverage_is_exact_and_cannot_override_scope_or_similarity(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        partial = await add_source(knowledge, db_settings, "G31 single signal", [1.0, 0.01])
        complete = await add_source(knowledge, db_settings, "G31 and G42 signals", [0.8, 0.6])
        wrong_prefix = await add_source(knowledge, db_settings, "G310 and G420 signals", [1.0, 0.0])
        wrong_brand = await add_source(
            knowledge,
            db_settings,
            "G31 and G42 foreign source",
            [1.0, 0.0],
            scope={**EXACT, "manufacturer": "Volvo"},
        )
        low_score = await add_source(knowledge, db_settings, "G31 and G42 irrelevant", [0.0, 1.0])
        hits, _, _, _ = await search(
            knowledge,
            db_settings,
            limit=4,
            requested_identifiers=["G31", "G42"],
        )
        assert [hit["document_id"] for hit in hits] == [complete, partial]
        assert hits[0]["relevance_metadata"]["matched_identifiers"] == "G31, G42"
        assert not {wrong_prefix, wrong_brand, low_score} & {hit["document_id"] for hit in hits}
        unknown, _, _, _ = await search(knowledge, db_settings, requested_identifiers=["G9999"])
        assert not unknown
    finally:
        await store.close()


async def test_equal_distance_duplicates_prefer_exact_source_before_limit(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        knowledge = PostgresKnowledgeStore(store)
        exact = None
        for label, scope in (
            ("Related duplicate", RELATED),
            ("Generic duplicate", {}),
            ("Exact duplicate", EXACT),
        ):
            identifier = await add_source(
                knowledge,
                db_settings,
                label,
                [1.0, 0.0],
                scope=scope,
                content="Repeated starter inspection paragraph.",
            )
            if label == "Exact duplicate":
                exact = identifier
        distinct = await add_source(
            knowledge,
            db_settings,
            "Distinct relevant reference",
            [0.98, 0.2],
        )
        await add_source(knowledge, db_settings, "Weak exact passage", [0.6, 0.8], scope=EXACT)
        first, count, _, _ = await search(knowledge, db_settings, related=True, limit=2)
        repeated, _, _, _ = await search(knowledge, db_settings, related=True, limit=2)
        assert [hit["document_id"] for hit in first] == [exact, distinct]
        assert count == 2
        assert [hit["citation"].chunk_id for hit in first] == [
            hit["citation"].chunk_id for hit in repeated
        ]
        assert len({hit["relevant_text"] for hit in first}) == 2
    finally:
        await store.close()
