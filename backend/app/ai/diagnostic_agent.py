from app.ai import prompts
from app.ai.llm_client import StructuredClient
from app.ai.safety import (
    critical_assessment,
    has_critical_hazard,
    professional_checks,
    unsafe_instruction,
)
from app.core.exceptions import AppError
from app.integrations.rag.interface import RetrievalResult
from app.models.diagnostic import (
    Assessment,
    AssessmentReview,
    RagAssessment,
    RagAssessmentReview,
    SymptomExtraction,
    Urgency,
)
from app.rag.service import validated_citations


class DiagnosticAgent:
    def __init__(self, client: StructuredClient):
        self.client = client

    async def use_automotive_tools(self, description, vehicle, gateway, settings):
        from app.ai.tool_workflow import automotive_tools

        return await automotive_tools(description, vehicle, gateway, settings)

    async def assess(self, payload: dict, *, retriever=None, vehicle=None):
        extraction = SymptomExtraction.model_validate(
            await self.client.generate(SymptomExtraction, prompts.EXTRACT, payload)
        )
        retrieval = RetrievalResult(
            available=False,
            reason="Verified manufacturer technical documentation is not connected.",
        )
        if extraction.safety_critical or has_critical_hazard(
            "\n".join([*extraction.symptoms, *extraction.warning_signs])
        ):
            return extraction, critical_assessment(payload["request"]["description"]), retrieval
        if not (
            extraction.symptoms
            or extraction.warning_signs
            or payload["request"].get("symptoms")
            or payload["request"].get("warning_lights")
            or payload["request"].get("dtcs")
        ):
            raise AppError(
                422, "symptoms_required", "Describe a symptom before urgency can be assessed."
            )
        if retriever is not None:
            try:
                retrieval = await retriever.retrieve(
                    vehicle,
                    payload["request"]["description"],
                    {"symptoms": ", ".join(extraction.symptoms)},
                )
            except Exception:
                retrieval = RetrievalResult(
                    available=False,
                    reason="Verified technical evidence was not retrieved; retrieval failed.",
                )
        schema = RagAssessment if retrieval.documents else Assessment
        assessment_payload = {
            **payload,
            "extraction": extraction.model_dump(mode="json"),
            "rag_available": retrieval.available,
            "retrieved_evidence": [doc.model_dump(mode="json") for doc in retrieval.documents],
            "allowed_citation_ids": [
                str(doc.citation.chunk_id) for doc in retrieval.documents if doc.citation
            ],
            "retrieval_limitations": retrieval.reason,
            "missing_vehicle_fields": retrieval.missing_vehicle_fields,
        }
        assessment = schema.model_validate(
            await self.client.generate(
                schema,
                prompts.ASSESS,
                assessment_payload,
            )
        )
        if unsafe_instruction(assessment):
            raise AppError(502, "unsafe_llm_output", "The AI assessment failed safety validation.")
        validated_citations(getattr(assessment, "citation_ids", []), retrieval)
        if assessment.urgency_level != Urgency.CRITICAL:
            review_schema = RagAssessmentReview if retrieval.documents else AssessmentReview
            review = review_schema.model_validate(
                await self.client.generate(
                    review_schema,
                    prompts.REVIEW,
                    {
                        **assessment_payload,
                        "draft_assessment": assessment.model_dump(mode="json"),
                    },
                )
            )
            reviewed = review.revised_assessment
            if unsafe_instruction(reviewed):
                raise AppError(
                    502, "unsafe_llm_output", "The AI assessment failed safety validation."
                )
            validated_citations(getattr(reviewed, "citation_ids", []), retrieval)
            if assessment.urgency_level == Urgency.HIGH and reviewed.urgency_level in {
                Urgency.LOW,
                Urgency.MODERATE,
            }:
                reviewed = reviewed.model_copy(
                    update={
                        "urgency_level": Urgency.HIGH,
                        "driving_recommendation": "inspection_before_driving",
                        "professional_assistance_recommended": True,
                    }
                )
            assessment = reviewed
        assessment = professional_checks(assessment)
        if "engine_code" in retrieval.missing_vehicle_fields:
            question = "What is the engine code? Please do not share the VIN."
            questions = assessment.follow_up_questions
            if question not in questions:
                assessment = assessment.model_copy(
                    update={"follow_up_questions": questions[:2] + [question]}
                )
        return extraction, assessment, retrieval
