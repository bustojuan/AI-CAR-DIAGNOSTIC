"""Exercise real LangChain + SDK serialization/parsing with HTTP mocked at the boundary."""

import json

import httpx
from langchain_openai import ChatOpenAI

from app.ai.llm_client import LangChainClient
from app.core.config import Settings
from app.main import create_app
from app.models.vehicle import GOLF_ID
from app.repositories.memory import MemoryStore
from tests.conftest import assessment_data, extraction_data


async def test_api_through_real_structured_langchain_and_mock_http():
    requests = []

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        name = payload["response_format"]["json_schema"]["name"]
        data = extraction_data() if name == "SymptomExtraction" else assessment_data()
        if name == "AssessmentReview":
            data = {
                "unsupported_or_conflicting_claims": [],
                "unsafe_or_unqualified_actions": [],
                "revised_assessment": assessment_data(),
            }
        return httpx.Response(
            200,
            json={
                "id": "test-completion",
                "object": "chat.completion",
                "created": 1,
                "model": "gpt-4.1-mini",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(data)},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    settings = Settings(_env_file=None, openai_api_key="test-key-not-real", llm_max_retries=0)
    client = LangChainClient(settings)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as provider:
        client.model = ChatOpenAI(
            api_key="test-key-not-real",
            model="gpt-4.1-mini",
            max_retries=0,
            http_async_client=provider,
        )
        app = create_app(settings, store=MemoryStore(), llm_client=client)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app),
                base_url="http://testserver",
            ) as api,
        ):
            result = await api.post(
                "/api/v1/diagnostics",
                json={
                    "vehicle_id": str(GOLF_ID),
                    "description": "Slow starting on cold mornings.",
                },
            )
            assert result.status_code == 201, result.text
            report = result.json()
            assert report["generation_mode"] == "llm"
            assert report["possible_causes"][0]["label"] == "hypothesis"
            assert (
                await api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}")
            ).json() == report
    assert len(requests) == 3
    assert requests[-1]["response_format"]["json_schema"]["name"] == "AssessmentReview"
    assert requests[0]["response_format"]["json_schema"]["strict"]
