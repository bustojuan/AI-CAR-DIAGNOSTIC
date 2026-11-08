from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.vehicle import seed_vehicle
from app.rag.query_expansion import QueryExpander, QueryTranslations
from app.rag.service import RagService
from tests.rag.fakes import FakeEmbeddings, FakeKnowledge
from tests.rag.test_service import metadata


def expander(english, french):
    client = AsyncMock()
    client.generate.return_value = QueryTranslations(english=english, french=french)
    return QueryExpander(Settings(_env_file=None), client=client)


async def test_faithful_translation_preserves_component_codes_and_numbers():
    worker = expander("How is the G62/G83 signal used at 2.0 bar?", "Signal G62/G83 a 2,0 bar ?")
    variants = await worker.expand("How is the G62/G83 signal used at 2.0 bar?")
    assert len(variants) == 2


@pytest.mark.parametrize(
    "invalid",
    [
        "G62 sensor signal at 2.0 bar.",
        "G62/G83 and G31 sensor signals at 2.0 bar.",
        "G62/G83 sensor signals at 3.0 bar.",
    ],
)
async def test_changed_missing_or_invented_identifiers_and_values_are_discarded(invalid):
    worker = expander(invalid, "Signal G62/G83 a 2,0 bar ?")
    assert await worker.expand("G62/G83 sensor signals at 2.0 bar.") == [
        "Signal G62/G83 a 2,0 bar ?"
    ]


async def test_a_translation_cannot_silently_drop_an_explicit_negation():
    worker = expander("Smoke from the engine bay.", "Pas de fumee sous le capot.")
    assert await worker.expand("No smoke from the engine bay.") == ["Pas de fumee sous le capot."]


@pytest.mark.parametrize(
    "failure", [TimeoutError(), AppError(503, "offline", "Offline"), ValueError()]
)
async def test_translation_failures_return_no_variants(failure):
    worker = expander("Battery test.", "Test batterie.")
    worker.client.generate.side_effect = failure
    assert await worker.expand("Battery test.") == []


async def test_translation_budget_reserves_time_for_baseline_retrieval():
    settings = Settings(
        _env_file=None, rag_timeout_seconds=2, rag_query_expansion_timeout_seconds=4
    )
    worker = QueryExpander(settings, client=AsyncMock())
    assert worker.timeout == pytest.approx(0.8)


async def test_original_query_is_retained_and_equivalent_variants_are_deduplicated():
    embeddings = FakeEmbeddings()
    expansion = AsyncMock()
    expansion.expand.return_value = ["Battery cranking?", "Batterie demarrage ?"]
    service = RagService(
        FakeKnowledge(),
        embeddings,
        Settings(_env_file=None, embedding_dimensions=4),
        query_expander=expansion,
    )
    report = await service.ingest(
        "x.md", "text/markdown", b"Battery cranking reference.", metadata()
    )
    await service.index(report.document_id)
    result = await service.retrieve(seed_vehicle(), "Battery cranking?")
    assert result.available and result.documents
    assert embeddings.calls[-1] == ["Battery cranking?", "Batterie demarrage ?"]


async def test_baseline_search_survives_unavailable_translations():
    embeddings = FakeEmbeddings()
    expansion = AsyncMock()
    expansion.expand.return_value = []
    service = RagService(
        FakeKnowledge(),
        embeddings,
        Settings(_env_file=None, embedding_dimensions=4),
        query_expander=expansion,
    )
    result = await service.retrieve(seed_vehicle(), "Battery cranking?")
    assert result.available
    assert embeddings.calls == [["Battery cranking?"]]


def test_disabled_expansion_does_not_construct_a_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Disabled translation must not construct a provider")

    monkeypatch.setattr("app.rag.service.QueryExpander", forbidden)
    service = RagService(
        FakeKnowledge(),
        FakeEmbeddings(),
        Settings(_env_file=None, openai_api_key="test-only", rag_query_expansion_enabled=False),
    )
    assert service.query_expander is None
