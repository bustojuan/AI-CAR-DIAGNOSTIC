import asyncio
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.diagnostic import Assessment, AssessmentReview, SymptomExtraction
from app.repositories.memory import MemoryStore


def pytest_asyncio_loop_factories(config, item):
    return {"selector": asyncio.SelectorEventLoop}


def extraction_data(**updates):
    return {
        "language": "en",
        "symptoms": ["Difficult cold starting"],
        "warning_signs": [],
        "missing_information": ["Cranking speed"],
        "safety_critical": False,
        **updates,
    }


def assessment_data(**updates):
    return {
        "summary": "Cold starting has several possible causes; inspection is needed.",
        "urgency_level": "moderate",
        "driving_recommendation": "caution_and_monitor",
        "follow_up_questions": [
            "Does the starter crank slowly?",
            "Does it start normally when warm?",
        ],
        "possible_causes": [
            {
                "label": "hypothesis",
                "component_or_system": "Battery or starting system",
                "possible_failure": "Reduced cranking performance is possible.",
                "supporting_symptoms": ["Difficult cold starting"],
                "missing_or_contradictory_evidence": [
                    "Cranking speed and battery condition unknown"
                ],
                "recommended_verification": "Ask a technician to check the battery and starter.",
                "professional_inspection_required": True,
                "uncertainty": "possible",
            }
        ],
        "recommended_checks": [
            {
                "category": "safe_observation",
                "description": "With the car parked, note the warning lights.",
            }
        ],
        "professional_assistance_recommended": True,
        "limitations": ["This is an unverified hypothesis, not a confirmed diagnosis."],
        "next_steps": ["Arrange a professional inspection if the problem persists."],
        **updates,
    }


class FakeClient:
    """Deterministic structured provider double; never selected by application runtime."""

    def __init__(self):
        self.calls = []
        self.extraction = extraction_data()
        self.assessment = assessment_data()
        self.failure = None

    async def generate(self, schema, system, payload):
        self.calls.append((schema, system, deepcopy(payload)))
        if self.failure:
            raise self.failure
        if schema is AssessmentReview:
            return AssessmentReview(
                unsupported_or_conflicting_claims=[],
                unsafe_or_unqualified_actions=[],
                revised_assessment=Assessment.model_validate(self.assessment),
            )
        data = self.extraction if schema is SymptomExtraction else self.assessment
        assert schema in (SymptomExtraction, Assessment)
        return schema.model_validate(data)


@pytest.fixture
def fake():
    return FakeClient()


@pytest.fixture
def settings():
    return Settings(_env_file=None, openai_api_key=None, database_url=None, llm_max_retries=0)


@pytest.fixture
def client(fake, settings):
    with TestClient(create_app(settings, store=MemoryStore(), llm_client=fake)) as client:
        yield client
