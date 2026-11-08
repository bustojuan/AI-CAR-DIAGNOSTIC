"""Optional paid integration smoke test. Excluded unless RUN_LIVE_LLM=1."""

import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.vehicle import GOLF_ID
from app.repositories.memory import MemoryStore


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE_LLM") != "1", reason="Live OpenAI test is opt-in")
def test_live_diagnostic():
    settings = Settings()
    assert settings.openai_api_key, "Configure OPENAI_API_KEY before running live tests"
    with TestClient(create_app(settings, store=MemoryStore())) as client:
        response = client.post(
            "/api/v1/diagnostics",
            json={
                "vehicle_id": str(GOLF_ID),
                "description": "My car struggles to start cold. It starts normally when warm.",
            },
        )
    assert response.status_code == 201, response.text
    assert response.json()["generation_mode"] == "llm"
    assert response.json()["summary"]
