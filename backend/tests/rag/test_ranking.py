from copy import deepcopy
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.integrations.rag.interface import RetrievedDocument
from app.models.vehicle import seed_vehicle
from app.rag.evaluate import mean_or_none, metrics
from app.rag.ranking import lexical_scores, rerank, terms
from app.rag.schemas import SourceCitation
from app.rag.service import RagService
from tests.rag.fakes import FakeEmbeddings, FakeKnowledge
from tests.rag.test_service import metadata


def passage(text, similarity=0.6):
    document_id = uuid4()
    citation = SourceCitation(
        document_id=document_id,
        chunk_id=uuid4(),
        document_title="Authored fixture",
        publisher="Test publisher",
        source_url=None,
        page=101,
        section="Safety",
        evidence_type="internal_demo",
        verification_status="verified",
    )
    return RetrievedDocument(
        document_id=document_id,
        title=citation.document_title,
        source="Fixture",
        relevant_text=text,
        page=101,
        section="Safety",
        citation=citation,
        relevance_metadata={"cosine_similarity": similarity},
    )


def test_warning_is_not_crowded_out_by_general_procedures():
    candidates = [
        passage(f"Brake fluid bleeding equipment procedure {i}.", 0.66 - i * 0.01) for i in range(5)
    ]
    warning = passage("Brake fluid is poisonous and corrosive; use protective gloves.", 0.60)
    candidates.append(warning)
    result = rerank(candidates, ["What cautions concern poisonous corrosive brake fluid?"], 4)
    assert warning.citation in [d.citation for d in result]
    assert len(result) == 4 and warning not in candidates[:4]


def test_bounded_bonus_does_not_replace_semantic_relevance():
    relevant = passage("Charging system discussion.", 0.9)
    distant = passage("Battery terminals voltage resistance safety.", 0.4)
    result = rerank([relevant, distant], ["Battery terminals voltage resistance safety"], 1)
    assert result[0].citation == relevant.citation
    assert 0 <= result[0].relevance_metadata["lexical_score"] <= 1


@pytest.mark.parametrize(
    "question",
    [
        "Show contents index for battery charging",
        "Mostrar el \u00edndice de bater\u00eda",
        "Sommaire de la batterie",
    ],
)
def test_contents_penalty_is_disabled_for_contents_questions(question):
    toc = passage("Battery charging . . . . . . . . . . 7", 0.65)
    content = passage("Battery charging guidance with a qualified technician.", 0.64)
    assert rerank([toc, content], ["Battery charging guidance"], 1)[0].citation == content.citation
    result = rerank([toc, content], [question], 2)
    assert all(d.relevance_metadata["contents_penalty"] == 0 for d in result)


def test_source_text_pages_and_input_objects_are_preserved():
    candidates = [passage("Battery starting system."), passage("Corrosive fluid warning.")]
    snapshot = deepcopy(candidates)
    result = rerank(candidates, ["corrosive fluid warning"], 2)
    assert candidates == snapshot
    for hit in result:
        original = next(d for d in candidates if d.citation.chunk_id == hit.citation.chunk_id)
        assert (hit.citation, hit.relevant_text, hit.page, hit.section) == (
            original.citation,
            original.relevant_text,
            original.page,
            original.section,
        )
    assert result == rerank(candidates, ["corrosive fluid warning"], 2)


@pytest.mark.parametrize("bad", [None, "not-a-score", float("nan"), float("inf")])
def test_invalid_semantic_metadata_keeps_original_order(bad):
    candidates = [passage("Starter."), passage("Battery warning.")]
    candidates[0].relevance_metadata = {} if bad is None else {"cosine_similarity": bad}
    assert rerank(candidates, ["battery warning"], 2) == candidates


def test_disabled_empty_and_nonmatching_queries_are_safe():
    candidates = [passage("Starting system."), passage("Battery warning.")]
    assert rerank(candidates, ["Battery"], 1, weight=0) == candidates[:1]
    assert rerank([], ["Battery"], 4) == []
    assert lexical_scores(candidates, ["quantum astronomy"]) == [0.0, 0.0]
    assert rerank(candidates, [], 2) == candidates


def test_multilingual_terms_keep_negations_tags_and_rejoin_pdf_words():
    tokens = terms(
        "No G31 or G310. Never test with an ohm meter. Per\u2010\nformed r\u00e9parations."
    )
    assert {"no", "never", "g31", "g310", "performed", "reparation"} <= set(tokens)
    candidates = [passage("Temperature sensor."), passage("Liquide de refroidissement corrosif.")]
    scores = lexical_scores(candidates, ["Coolant cautions", "Liquide de refroidissement corrosif"])
    assert scores[1] > scores[0]


@pytest.mark.parametrize(
    "query,weight,expected_limit",
    [
        ("Battery cautions", 0.15, 40),
        ("What is G31?", 0.15, 4),
        ("Battery cautions", 0, 4),
    ],
)
async def test_service_bounded_pool_and_code_specific_path(query, weight, expected_limit):
    knowledge = FakeKnowledge()
    knowledge.search = AsyncMock(wraps=knowledge.search)
    embeddings = FakeEmbeddings()
    service = RagService(
        knowledge,
        embeddings,
        Settings(
            _env_file=None,
            openai_api_key=None,
            embedding_dimensions=4,
            rag_lexical_weight=weight,
        ),
    )
    result = await service.retrieve(seed_vehicle(), query)
    assert result.available and not result.documents
    assert knowledge.search.call_args.args[4] == expected_limit
    assert len(embeddings.calls) == 1


async def test_restricted_source_is_never_resurrected():
    service = RagService(
        FakeKnowledge(),
        FakeEmbeddings(),
        Settings(
            _env_file=None,
            openai_api_key=None,
            embedding_dimensions=4,
        ),
    )
    report = await service.ingest(
        "x.md", "text/markdown", b"Battery corrosive warning.", metadata()
    )
    await service.index(report.document_id)
    service.knowledge.documents[report.document_id]["license_status"] = "restricted"
    result = await service.retrieve(seed_vehicle(), "Battery corrosive warning")
    assert result.available and not result.documents


def test_negative_only_metrics_do_not_fabricate_recall():
    assert metrics([], []) == (None, None)
    assert mean_or_none([None, None]) is None
    assert mean_or_none([0.0, None, 1.0]) == 0.5
