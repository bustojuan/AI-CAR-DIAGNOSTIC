from copy import deepcopy
from uuid import uuid4

import pytest

from app.ai.diagnostic_agent import DiagnosticAgent
from app.ai.safety import professional_checks
from app.core.exceptions import AppError
from app.integrations.rag.interface import RetrievalResult, RetrievedDocument
from app.models.diagnostic import (
    Assessment,
    AssessmentReview,
    RagAssessment,
    RagAssessmentReview,
    SymptomExtraction,
)
from app.models.vehicle import seed_vehicle
from app.rag.schemas import SourceCitation
from tests.conftest import assessment_data, extraction_data


class ReviewClient:
    def __init__(self, citation=None):
        self.calls = []
        self.citation = citation
        self.draft = assessment_data(summary="Draft with an unsupported circuit conclusion.")
        self.revised = assessment_data(summary="The circuit connection is not established.")
        self.review_error = None
        self.invalid_review_citation = False

    async def generate(self, schema, system, payload):
        self.calls.append((schema, system, deepcopy(payload)))
        if schema is SymptomExtraction:
            return schema(**extraction_data())
        if schema in {AssessmentReview, RagAssessmentReview}:
            if self.review_error:
                raise self.review_error
            report = deepcopy(self.revised)
            if schema is RagAssessmentReview:
                report["citation_ids"] = [
                    uuid4() if self.invalid_review_citation else self.citation.chunk_id
                ]
            return schema(
                unsupported_or_conflicting_claims=["The draft infers an unverified connection."],
                unsafe_or_unqualified_actions=[],
                revised_assessment=report,
            )
        report = deepcopy(self.draft)
        if schema is RagAssessment:
            report["citation_ids"] = [self.citation.chunk_id]
        return schema(**report)


class EvidenceRetriever:
    def __init__(self):
        self.citation = SourceCitation(
            document_id=uuid4(),
            chunk_id=uuid4(),
            document_title="Authored diagram fixture",
            evidence_type="third_party_technical",
            verification_status="verified",
            page=101,
            publisher="Authored test fixture",
            source_url=None,
            section=None,
        )
        self.result = RetrievalResult(
            available=True,
            reason="Labels do not establish pin-to-pin connections.",
            documents=[
                RetrievedDocument(
                    document_id=self.citation.document_id,
                    title=self.citation.document_title,
                    source="Test fixture",
                    relevant_text="SC2 J500: labels only.",
                    page=101,
                    citation=self.citation,
                )
            ],
        )

    async def retrieve(self, *args, **kwargs):
        return self.result


def payload():
    return {
        "request": {"description": "The radio resets while parked."},
        "vehicle": seed_vehicle().model_dump(mode="json"),
        "history": [],
    }


async def test_review_receives_exact_evidence_and_replaces_draft_before_storage(client):
    retriever = EvidenceRetriever()
    model = ReviewClient(retriever.citation)
    client.app.state.diagnostics.agent = DiagnosticAgent(model)
    client.app.state.diagnostics.retriever = retriever
    response = client.post(
        "/api/v1/diagnostics",
        json={
            "vehicle_id": str(seed_vehicle().vehicle_id),
            "description": "The radio resets while parked.",
        },
    )
    assert response.status_code == 201
    report = response.json()
    assert report["summary"] == model.revised["summary"]
    assert "unsupported_or_conflicting_claims" not in report
    assert len(model.calls) == 3
    review_payload = model.calls[-1][2]
    assert review_payload["draft_assessment"]["summary"] == model.draft["summary"]
    assert review_payload["retrieved_evidence"] == [
        d.model_dump(mode="json") for d in retriever.result.documents
    ]
    assert review_payload["allowed_citation_ids"] == [str(retriever.citation.chunk_id)]
    assert client.get(f"/api/v1/diagnostics/{report['diagnostic_id']}").json() == report


async def test_review_cannot_invent_a_valid_citation():
    retriever = EvidenceRetriever()
    model = ReviewClient(retriever.citation)
    model.invalid_review_citation = True
    with pytest.raises(AppError) as error:
        await DiagnosticAgent(model).assess(payload(), retriever=retriever, vehicle=seed_vehicle())
    assert error.value.code == "invalid_citations"


async def test_failed_review_does_not_publish_unreviewed_draft(client):
    model = ReviewClient()
    model.review_error = AppError(503, "llm_unavailable", "Provider unavailable.")
    client.app.state.diagnostics.agent = DiagnosticAgent(model)
    response = client.post(
        "/api/v1/diagnostics",
        json={
            "vehicle_id": str(seed_vehicle().vehicle_id),
            "description": "Slow cranking.",
        },
    )
    assert response.status_code == 503
    assert not client.app.state.store.repository.diagnostics
    assert not client.app.state.store.repository.conversations


async def test_review_cannot_downgrade_high_draft():
    model = ReviewClient()
    model.draft.update(urgency_level="high", driving_recommendation="inspection_before_driving")
    model.revised.update(urgency_level="low", professional_assistance_recommended=False)
    _, report, _ = await DiagnosticAgent(model).assess(payload())
    assert report.urgency_level == "high"
    assert report.driving_recommendation == "inspection_before_driving"
    assert report.professional_assistance_recommended


async def test_critical_draft_skips_review_and_cannot_be_downgraded():
    model = ReviewClient()
    model.draft.update(urgency_level="critical", driving_recommendation="stop_safely_do_not_drive")
    model.review_error = AssertionError("Critical drafts must not reach review.")
    _, report, _ = await DiagnosticAgent(model).assess(payload())
    assert report.urgency_level == "critical"
    assert len(model.calls) == 2


async def test_unsafe_review_is_rejected():
    model = ReviewClient()
    model.revised["next_steps"] = ["Disable the airbag and test drive."]
    with pytest.raises(AppError) as error:
        await DiagnosticAgent(model).assess(payload())
    assert error.value.code == "unsafe_llm_output"


@pytest.mark.parametrize(
    "description",
    [
        "Check battery terminals for corrosion.",
        "Measure voltage using a multimeter.",
        "Inspect fuse SC2 for poor contacts.",
        "Listen around the engine bay with the engine idling.",
        "Inspect coolant level and condition.",
        "Observe the temperature gauge during steady driving.",
    ],
)
def test_physical_checks_are_never_safe_observations(description):
    report = Assessment(
        **assessment_data(
            recommended_checks=[{"category": "safe_observation", "description": description}],
            next_steps=[description],
        )
    )
    result = professional_checks(report)
    assert result.recommended_checks[0].category == "professional"
    assert result.recommended_checks[0].description.startswith("Qualified technician only:")
    assert result.next_steps[0].startswith("Qualified technician only:")
    assert professional_checks(result) == result
    assert report.recommended_checks[0].category == "safe_observation"


def test_existing_dashboard_observation_remains_available():
    report = Assessment(
        **assessment_data(
            recommended_checks=[
                {
                    "category": "safe_observation",
                    "description": "Report dashboard indications already observed while parked.",
                }
            ]
        )
    )
    assert professional_checks(report).recommended_checks == report.recommended_checks


def test_stop_and_do_not_drive_instructions_remain_addressed_to_user():
    steps = ["Do not drive to reproduce this symptom.", "Avoid touching battery terminals."]
    report = Assessment(**assessment_data(next_steps=steps))
    assert professional_checks(report).next_steps == steps
