import json
from types import SimpleNamespace

import httpx
import pytest
from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings
from app.models.vehicle import seed_vehicle
from app.rag.compatibility import compatible
from app.rag.embeddings import OpenAIEmbeddingClient
from app.rag.evaluate import metrics


async def test_real_langchain_embedding_sdk_over_mock_http():
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "text-embedding-3-small",
                "data": [
                    {"object": "embedding", "index": index, "embedding": [1.0, 0.0, 0.0]}
                    for index in range(len(body["input"]))
                ],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            },
        )

    settings = Settings(_env_file=None, openai_api_key="test-only-key", embedding_dimensions=3)
    wrapper = OpenAIEmbeddingClient(settings)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as provider:
        wrapper.client = OpenAIEmbeddings(
            api_key="test-only-key",
            model=settings.embedding_model,
            dimensions=3,
            http_async_client=provider,
            check_embedding_ctx_length=False,
            max_retries=0,
        )
        assert await wrapper.embed(["battery", "cooling"]) == [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    assert requests[0]["dimensions"] == 3 and requests[0]["input"] == ["battery", "cooling"]


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, True),
        ({"manufacturer": "Volvo"}, False),
        ({"model": "XC60"}, False),
        ({"model_year_start": 2010}, False),
        ({"model_year_end": 2005}, False),
        ({"engine": "1.6 petrol"}, False),
        ({"engine_code": "UNVERIFIED"}, False),
        ({"engine_code": "CFFB", "model_year_start": 2009}, True),
        ({"engine_code": "CBAB"}, False),
        ({"model_year_start": 2006, "model_year_end": 2006}, False),
        ({"transmission": "Automatic"}, False),
        ({"manufacturer": "VOLKSWAGEN", "model": "Golf Plus"}, True),
    ],
)
def test_deterministic_applicability(changes, expected):
    metadata = SimpleNamespace(
        **{
            **{
                key: None
                for key in (
                    "manufacturer",
                    "model",
                    "model_year_start",
                    "model_year_end",
                    "engine",
                    "engine_code",
                    "transmission",
                )
            },
            **changes,
        }
    )
    assert compatible(metadata, seed_vehicle()) is expected


def test_recall_and_mrr_formula_fixture():
    assert metrics(["irrelevant", "relevant"], ["relevant", "missing"]) == (0.5, 0.5)
    assert metrics([], ["relevant"]) == (0.0, 0.0)
