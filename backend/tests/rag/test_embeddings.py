from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.rag.embeddings import OpenAIEmbeddingClient, validate_vectors


async def test_embedding_batches_and_bounded_retry():
    settings = Settings(
        _env_file=None,
        openai_api_key="test-not-real",
        embedding_dimensions=3,
        embedding_batch_size=1,
        embedding_max_retries=1,
    )
    embedder = OpenAIEmbeddingClient(settings)
    embedder.client = AsyncMock()
    embedder.client.aembed_documents.side_effect = [TimeoutError(), [[1, 0, 0]], [[0, 1, 0]]]
    with patch("app.rag.embeddings.asyncio.sleep", new_callable=AsyncMock) as sleep:
        assert await embedder.embed(["first", "second"]) == [[1, 0, 0], [0, 1, 0]]
    assert embedder.client.aembed_documents.await_count == 3
    sleep.assert_awaited_once_with(0.25)


async def test_embedding_timeout_exhaustion_and_missing_key():
    embedder = OpenAIEmbeddingClient(
        Settings(_env_file=None, openai_api_key="test-not-real", embedding_max_retries=0)
    )
    embedder.client = AsyncMock()
    embedder.client.aembed_documents.side_effect = TimeoutError()
    with pytest.raises(AppError) as failure:
        await embedder.embed(["text"])
    assert failure.value.code == "embeddings_unavailable"
    with pytest.raises(AppError):
        await OpenAIEmbeddingClient(Settings(_env_file=None, openai_api_key=None)).embed(["text"])


@pytest.mark.parametrize(
    "vectors,count,dim",
    [
        ([[1, 0]], 1, 3),
        ([[0, 0, 0]], 1, 3),
        ([[float("nan"), 1, 0]], 1, 3),
        ([], 1, 3),
    ],
)
def test_embedding_validation(vectors, count, dim):
    with pytest.raises(ValueError):
        validate_vectors(vectors, count, dim)
