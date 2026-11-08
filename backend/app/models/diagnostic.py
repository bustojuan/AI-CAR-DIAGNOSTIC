from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field, StringConstraints, model_validator

from app.mcp.schemas import AutomotiveResult
from app.models.common import Schema, ShortText, Text, utcnow
from app.rag.schemas import SourceCitation

AnnotatedDTC = Annotated[
    str, StringConstraints(to_upper=True, pattern=r"(?i)^[PBCU][0-3][0-9A-F]{3}$")
]


class Urgency(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SymptomExtraction(Schema):
    language: Literal["en", "es"]
    symptoms: list[ShortText] = Field(max_length=20)
    warning_signs: list[ShortText] = Field(max_length=20)
    missing_information: list[ShortText] = Field(max_length=10)
    safety_critical: bool


class Hypothesis(Schema):
    label: Literal["hypothesis"]
    component_or_system: ShortText
    possible_failure: Text
    supporting_symptoms: list[ShortText] = Field(max_length=20)
    missing_or_contradictory_evidence: list[Text] = Field(max_length=10)
    recommended_verification: Text
    professional_inspection_required: bool
    uncertainty: Literal["possible", "uncertain", "insufficient_evidence"]


class Check(Schema):
    category: Literal["safe_observation", "technical", "professional"]
    description: Text


class Assessment(Schema):
    summary: Text
    urgency_level: Urgency
    driving_recommendation: Literal[
        "stop_safely_do_not_drive", "inspection_before_driving", "caution_and_monitor"
    ]
    follow_up_questions: list[ShortText] = Field(max_length=3)
    possible_causes: list[Hypothesis] = Field(max_length=6)
    recommended_checks: list[Check] = Field(max_length=10)
    professional_assistance_recommended: bool
    limitations: list[Text] = Field(max_length=10)
    next_steps: list[Text] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def consistent_safety(self):
        if self.urgency_level == Urgency.CRITICAL and (
            self.driving_recommendation != "stop_safely_do_not_drive"
            or not self.professional_assistance_recommended
        ):
            raise ValueError("Critical assessments must prohibit driving and recommend assistance")
        if self.urgency_level == Urgency.HIGH and (
            self.driving_recommendation == "caution_and_monitor"
            or not self.professional_assistance_recommended
        ):
            raise ValueError("High urgency requires inspection and assistance")
        return self


class Evidence(Schema):
    kind: Literal[
        "user_provided",
        "general_model_knowledge",
        "retrieved_technical_documentation",
        "external_tool_result",
    ]
    description: Text


class RagAssessment(Assessment):
    citation_ids: list[UUID] = Field(max_length=8)


class AssessmentReview(Schema):
    # Internal provider contract: findings precede the rewrite so the reviewer must
    # inspect the draft rather than simply paraphrase it. Never stored as source evidence.
    unsupported_or_conflicting_claims: list[Text] = Field(max_length=10)
    unsafe_or_unqualified_actions: list[Text] = Field(max_length=10)
    revised_assessment: Assessment


class RagAssessmentReview(AssessmentReview):
    revised_assessment: RagAssessment


class UrgencyAssessment(Schema):
    level: Urgency
    explanation: Text
    warning_signs: list[ShortText] = Field(max_length=40)
    missing_safety_information: list[ShortText] = Field(max_length=20)
    driving_recommendation: Literal[
        "stop_safely_do_not_drive", "inspection_before_driving", "caution_and_monitor"
    ]
    professional_assistance_recommended: bool
    basis: Literal["deterministic_safety", "hybrid", "insufficient_information"]


class Diagnostic(Assessment):
    diagnostic_id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    vehicle_id: UUID
    created_at: datetime = Field(default_factory=utcnow)
    extracted_symptoms: list[ShortText] = Field(max_length=40)
    evidence_sources: list[Evidence]
    citations: list[SourceCitation] = Field(default_factory=list)
    rag_available: bool = False
    mcp_available: bool = False
    tool_results: list[AutomotiveResult] = Field(default_factory=list, max_length=3)
    generation_mode: Literal["llm", "deterministic_safety"]
    # Null denotes a historical report, never a newly invented assessment.
    urgency_assessment: UrgencyAssessment | None = None

    @model_validator(mode="after")
    def urgency_details_agree(self):
        detail = self.urgency_assessment
        if detail and (
            detail.level != self.urgency_level
            or detail.driving_recommendation != self.driving_recommendation
            or detail.professional_assistance_recommended
            != self.professional_assistance_recommended
        ):
            raise ValueError("Urgency details must agree with the final assessment")
        return self


class MessageRequest(Schema):
    description: str = Field(min_length=3, max_length=6000)
    symptoms: list[ShortText] = Field(default_factory=list, max_length=20)
    warning_lights: list[ShortText] = Field(default_factory=list, max_length=20)
    dtcs: list[AnnotatedDTC] = Field(default_factory=list, max_length=20)
    mileage_km: int | None = Field(default=None, ge=0, le=3000000)


class DiagnosticRequest(MessageRequest):
    vehicle_id: UUID
    conversation_id: UUID | None = None
