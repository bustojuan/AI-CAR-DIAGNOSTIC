import asyncio
import math
from typing import Protocol

from langchain_openai import OpenAIEmbeddings
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app.core.exceptions import AppError


class EmbeddingClient(Protocol):
    model: str
    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingClient:
    def __init__(self, settings):
        self.settings = settings
        self.model, self.dimensions = settings.embedding_model, settings.embedding_dimensions
        self.client = None

    async def embed(self, texts):
        if not texts or any(not text.strip() or len(text) > 6000 for text in texts):
            raise AppError(
                422, "invalid_embedding_input", "Embedding inputs are empty or too large."
            )
        if not self.settings.openai_api_key:
            raise AppError(
                503, "embeddings_not_configured", "Configure OPENAI_API_KEY for embeddings."
            )
        if self.client is None:
            self.client = OpenAIEmbeddings(
                api_key=self.settings.openai_api_key.get_secret_value(),
                model=self.model,
                dimensions=self.dimensions,
                max_retries=0,
                request_timeout=self.settings.embedding_timeout_seconds,
                check_embedding_ctx_length=False,
            )
        output = []
        batch_size = self.settings.embedding_batch_size
        for offset in range(0, len(texts), batch_size):
            for attempt in range(self.settings.embedding_max_retries + 1):
                try:
                    async with asyncio.timeout(self.settings.embedding_timeout_seconds):
                        batch = await self.client.aembed_documents(
                            texts[offset : offset + batch_size]
                        )
                    validate_vectors(
                        batch, len(texts[offset : offset + batch_size]), self.dimensions
                    )
                    output.extend(batch)
                    break
                except (TimeoutError, APITimeoutError, APIConnectionError, RateLimitError):
                    failure = AppError(
                        503, "embeddings_unavailable", "Embedding provider unavailable."
                    )
                except APIStatusError as exc:
                    if exc.status_code < 500 and exc.status_code != 429:
                        raise AppError(
                            502, "embedding_provider_error", "Embedding request rejected."
                        ) from None
                    failure = AppError(
                        503, "embeddings_unavailable", "Embedding provider unavailable."
                    )
                except (TypeError, ValueError):
                    raise AppError(
                        502, "invalid_embeddings", "Invalid embedding response."
                    ) from None
                if attempt == self.settings.embedding_max_retries:
                    raise failure from None
                await asyncio.sleep(0.25 * 2**attempt)
        return output


def validate_vectors(vectors, count, dimensions):
    if len(vectors) != count or any(
        len(vector) != dimensions
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and abs(value) <= 3e38
            for value in vector
        )
        or not any(value != 0 for value in vector)
        for vector in vectors
    ):
        raise ValueError("Embedding dimensions, count, finiteness or norm are invalid")
