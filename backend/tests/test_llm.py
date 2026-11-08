from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.exceptions import OutputParserException
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app.ai.llm_client import LangChainClient
from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.diagnostic import SymptomExtraction
from tests.conftest import extraction_data


def configured_client(*, retries=0, timeout=1):
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key-not-real",
        llm_max_retries=retries,
        llm_timeout_seconds=timeout,
    )
    client = LangChainClient(settings)
    runnable = MagicMock()
    runnable.ainvoke = AsyncMock(return_value=extraction_data())
    client.model = MagicMock()
    client.model.with_structured_output.return_value = runnable
    return client, runnable


async def test_structured_output_configuration_and_validation():
    client, runnable = configured_client()
    result = await client.generate(
        SymptomExtraction, "system instructions", {"query": "slow start"}
    )
    assert result.symptoms == ["Difficult cold starting"]
    client.model.with_structured_output.assert_called_once_with(
        SymptomExtraction,
        method="json_schema",
        strict=True,
    )
    messages = runnable.ainvoke.call_args.args[0]
    assert messages[0].type == "system" and messages[1].type == "human"


@pytest.mark.parametrize("output", [None, {}, {**extraction_data(), "probability": 0.9}])
async def test_malformed_structured_output(output):
    client, runnable = configured_client()
    runnable.ainvoke.return_value = output
    with pytest.raises(AppError) as failure:
        await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.code == "invalid_llm_output"


async def test_parser_failure_is_sanitized():
    client, runnable = configured_client()
    runnable.ainvoke.side_effect = OutputParserException("private provider response")
    with pytest.raises(AppError) as failure:
        await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.status == 502
    assert "private" not in failure.value.message


async def test_model_refusal_is_sanitized_and_not_retried():
    client, runnable = configured_client(retries=2)
    runnable.ainvoke.side_effect = OpenAIRefusalError("private refusal")
    with pytest.raises(AppError) as failure:
        await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.code == "llm_refused"
    assert runnable.ainvoke.await_count == 1
    assert "private" not in failure.value.message


@pytest.mark.parametrize(
    "exception",
    [
        TimeoutError(),
        APITimeoutError(request=httpx.Request("POST", "https://example.invalid")),
    ],
)
async def test_timeout_mapped_to_gateway_timeout(exception):
    client, runnable = configured_client()
    runnable.ainvoke.side_effect = exception
    with pytest.raises(AppError) as failure:
        await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.status == 504


async def test_async_deadline_enforced():
    import asyncio

    client, runnable = configured_client(timeout=0.01)

    async def slow(*args, **kwargs):
        await asyncio.sleep(1)

    runnable.ainvoke.side_effect = slow
    with pytest.raises(AppError) as failure:
        await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.code == "llm_timeout"


async def test_connection_retry_bounded_exponential_backoff():
    client, runnable = configured_client(retries=2)
    runnable.ainvoke.side_effect = APIConnectionError(
        request=httpx.Request("POST", "https://example.invalid")
    )
    with patch("app.ai.llm_client.asyncio.sleep", new_callable=AsyncMock) as sleep:
        with pytest.raises(AppError) as failure:
            await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.status == 503
    assert runnable.ainvoke.await_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5]


async def test_transient_failure_can_recover():
    client, runnable = configured_client(retries=1)
    runnable.ainvoke.side_effect = [
        APIConnectionError(request=httpx.Request("POST", "https://example.invalid")),
        extraction_data(),
    ]
    with patch("app.ai.llm_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.generate(SymptomExtraction, "rules", {})
    assert result.language == "en"
    assert runnable.ainvoke.await_count == 2


@pytest.mark.parametrize(
    "status,code", [(401, "llm_provider_error"), (500, "llm_unavailable"), (429, "llm_unavailable")]
)
async def test_provider_errors(status, code):
    client, runnable = configured_client()
    response = httpx.Response(status, request=httpx.Request("POST", "https://example.invalid"))
    exception_class = RateLimitError if status == 429 else APIStatusError
    runnable.ainvoke.side_effect = exception_class(
        "private provider text", response=response, body={}
    )
    with pytest.raises(AppError) as failure:
        await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.code == code
    assert "private" not in failure.value.message


async def test_missing_key_never_constructs_provider():
    client = LangChainClient(Settings(_env_file=None, openai_api_key=None))
    with patch("app.ai.llm_client.ChatOpenAI") as model:
        with pytest.raises(AppError) as failure:
            await client.generate(SymptomExtraction, "rules", {})
    assert failure.value.code == "llm_not_configured"
    model.assert_not_called()
