import asyncio
import json
from typing import Protocol, TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError

T = TypeVar("T", bound=BaseModel)


class StructuredClient(Protocol):
    async def generate(self, schema: type[T], system: str, payload: dict) -> T: ...


class LangChainClient:
    def __init__(self, settings: Settings, *, temperature=None, max_completion_tokens=None):
        self.settings = settings
        self.model = None
        self.model_options = {
            key: value
            for key, value in {
                "temperature": temperature,
                "max_completion_tokens": max_completion_tokens,
            }.items()
            if value is not None
        }

    def _model(self):
        key = self.settings.openai_api_key
        if not key or not key.get_secret_value().strip():
            raise AppError(
                503, "llm_not_configured", "Set OPENAI_API_KEY to enable AI diagnostic assessments."
            )
        if self.model is None:
            self.model = ChatOpenAI(
                api_key=key.get_secret_value(),
                model=self.settings.openai_model,
                timeout=self.settings.llm_timeout_seconds,
                max_retries=0,
                **self.model_options,
            )
        return self.model

    async def generate(self, schema: type[T], system: str, payload: dict) -> T:
        runnable = self._model().with_structured_output(schema, method="json_schema", strict=True)
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                async with asyncio.timeout(self.settings.llm_timeout_seconds):
                    output = await runnable.ainvoke(messages)
                return schema.model_validate(output)
            except (OpenAIRefusalError, ContentFilterFinishReasonError):
                raise AppError(
                    502, "llm_refused", "The AI could not provide an assessment."
                ) from None
            except (
                ValidationError,
                OutputParserException,
                APIResponseValidationError,
                LengthFinishReasonError,
                TypeError,
                ValueError,
            ):
                raise AppError(
                    502,
                    "invalid_llm_output",
                    "The AI returned an invalid assessment. Please retry.",
                ) from None
            except (TimeoutError, APITimeoutError):
                failure = AppError(504, "llm_timeout", "The AI request timed out. Please retry.")
            except (APIConnectionError, RateLimitError):
                failure = AppError(503, "llm_unavailable", "The AI provider is unavailable.")
            except APIStatusError as exc:
                if exc.status_code < 500 and exc.status_code != 429:
                    raise AppError(
                        502, "llm_provider_error", "The AI provider rejected the request."
                    ) from None
                failure = AppError(503, "llm_unavailable", "The AI provider is unavailable.")
            if attempt == self.settings.llm_max_retries:
                raise failure from None
            await asyncio.sleep(0.25 * 2**attempt)
        raise AssertionError("unreachable")
