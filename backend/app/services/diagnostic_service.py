import json
from uuid import UUID

from pydantic import ValidationError

from app.ai.diagnostic_agent import DiagnosticAgent
from app.ai.safety import (
    critical_assessment,
    finalize_urgency,
    has_critical_hazard,
    no_symptoms,
)
from app.core.config import Settings
from app.core.exceptions import AppError, not_found
from app.integrations.mcp.interface import ToolGateway
from app.integrations.rag.interface import RetrievalResult, Retriever
from app.mcp.retention import TRANSIENT_PROVIDERS
from app.models.conversation import Conversation, Message
from app.models.diagnostic import Diagnostic, DiagnosticRequest, Evidence, MessageRequest, Urgency
from app.rag.service import validated_citations
from app.repositories.interfaces import Store


def observation_text(request: MessageRequest) -> str:
    values = [request.description, *request.symptoms, *request.dtcs]
    if request.warning_lights:
        values.append("Warning lights reported: " + ", ".join(request.warning_lights))
    return "\n".join(values)


class DiagnosticService:
    def __init__(
        self,
        store: Store,
        agent: DiagnosticAgent,
        settings: Settings,
        retriever: Retriever,
        tools: ToolGateway,
    ):
        self.store, self.agent, self.settings = store, agent, settings
        self.retriever, self.tools = retriever, tools

    async def get(self, diagnostic_id: UUID):
        async with self.store.transaction() as repository:
            diagnostic = await repository.get_diagnostic(diagnostic_id)
            if not diagnostic:
                raise not_found("Diagnostic")
            return diagnostic

    async def run(
        self,
        request: MessageRequest,
        *,
        vehicle_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ):
        # One transaction serializes history updates and rolls back the entire workflow on failure.
        async with self.store.transaction() as repository:
            if conversation_id:
                conversation = await repository.get_conversation(conversation_id, lock=True)
                if not conversation:
                    raise not_found("Conversation")
                if vehicle_id and vehicle_id != conversation.vehicle_id:
                    raise AppError(
                        409, "vehicle_mismatch", "Conversation belongs to another vehicle."
                    )
                vehicle_id = conversation.vehicle_id
            else:
                conversation = Conversation(vehicle_id=vehicle_id)
            vehicle = await repository.get_vehicle(vehicle_id)
            if not vehicle:
                raise not_found("Vehicle")
            data = MessageRequest.model_validate(
                request.model_dump(include=set(MessageRequest.model_fields))
            )
            # Persist all supplied observations so structured fields survive follow-up turns.
            content = json.dumps(data.model_dump(mode="json"), ensure_ascii=False)
            safety_text = "\n".join(
                [
                    observation_text(MessageRequest.model_validate_json(m.content))
                    for m in conversation.messages
                    if m.role == "user"
                ]
                + [observation_text(data)]
            )
            previous = (
                await repository.get_diagnostic(conversation.diagnostic_ids[-1])
                if conversation.diagnostic_ids
                else None
            )
            previous_critical = previous is not None and previous.urgency_level == Urgency.CRITICAL
            # There is no professional-clearance workflow. A later model response
            # cannot clear a critical alert already recorded in this conversation.
            deterministic = has_critical_hazard(safety_text) or previous_critical
            if (
                not deterministic
                and no_symptoms(data.description)
                and not (data.symptoms or data.warning_lights or data.dtcs)
            ):
                raise AppError(
                    422, "symptoms_required", "Describe a symptom before urgency can be assessed."
                )
            extraction = None
            retrieval = RetrievalResult(
                available=False,
                reason="Verified manufacturer technical documentation is not connected.",
            )
            citations = []
            if deterministic:
                assessment = critical_assessment(data.description)
                symptoms = list(dict.fromkeys(data.symptoms + [data.description[:200]]))
            else:
                payload = {
                    "vehicle": vehicle.model_dump(mode="json", exclude={"vin"}),
                    "request": data.model_dump(mode="json"),
                    "history": [
                        m.model_dump(mode="json", include={"role", "content"})
                        for m in conversation.messages[-self.settings.max_history_messages :]
                    ],
                    "rag_available": False,
                    "mcp_available": False,
                }
                try:
                    extraction, assessment, retrieval = await self.agent.assess(
                        payload, retriever=self.retriever, vehicle=vehicle
                    )
                except ValidationError:
                    raise AppError(
                        502, "invalid_llm_output", "The AI returned invalid data."
                    ) from None
                symptoms = list(dict.fromkeys(extraction.symptoms + data.symptoms))
                if extraction.safety_critical or assessment.urgency_level == Urgency.CRITICAL:
                    assessment = critical_assessment(data.description)
                    retrieval = RetrievalResult(
                        available=False,
                        reason="Safety escalation takes priority; retrieved evidence is not used.",
                    )
                citations = validated_citations(getattr(assessment, "citation_ids", []), retrieval)
            assessment, urgency_detail = finalize_urgency(
                assessment,
                safety_text
                + (
                    "\n" + "\n".join([*extraction.symptoms, *extraction.warning_signs])
                    if extraction
                    else ""
                ),
                extraction,
                cited_evidence=bool(citations),
                reported_text=safety_text,
            )
            if previous_critical:
                prior_signs = (
                    previous.urgency_assessment.warning_signs if previous.urgency_assessment else []
                )
                urgency_detail = urgency_detail.model_copy(
                    update={
                        "basis": "deterministic_safety",
                        "warning_signs": list(
                            dict.fromkeys(
                                [
                                    "Earlier critical alert remains unresolved",
                                    *prior_signs,
                                    *urgency_detail.warning_signs,
                                ]
                            )
                        )[:40],
                    }
                )
            # Catalog calls run only after both deterministic and model safety triage.
            tool_results = []
            if (
                assessment.urgency_level != Urgency.CRITICAL
                and self.settings.mcp_enabled
                and self.settings.automotive_provider not in TRANSIENT_PROVIDERS
            ):
                tool_results = await self.agent.use_automotive_tools(
                    data.description, vehicle, self.tools, self.settings
                )
            limitations = list(assessment.limitations[:7])
            if self.settings.automotive_provider in TRANSIENT_PROVIDERS:
                limitations = limitations[:6] + [
                    "eBay offers are available only as temporary queries in Parts; "
                    "they are not used in or saved with this diagnosis."
                ]
            if retrieval.reason:
                limitations.append(retrieval.reason)
            limitations.extend(
                [
                    (
                        "Catalog candidates do not recommend replacement. "
                        "Demo data cannot verify real fitment or market prices."
                    )
                    if tool_results
                    else ("Catalogs were not used; compatibility and prices are unverified."),
                    "Hypotheses require verification; this is not a confirmed diagnosis.",
                ]
            )
            # Sources are constructed by the application, never accepted from model-generated IDs.
            evidence = [
                Evidence(
                    kind="user_provided",
                    description=("User-reported observations, not independently verified."),
                )
            ]
            if not deterministic:
                evidence.append(
                    Evidence(
                        kind="general_model_knowledge",
                        description=(
                            "General model knowledge; not verified manufacturer documentation."
                        ),
                    )
                )
            for citation in citations:
                evidence.append(
                    Evidence(
                        kind="retrieved_technical_documentation",
                        description=(
                            f"{citation.document_title} ({citation.evidence_type}); "
                            f"chunk {citation.chunk_id}."
                        ),
                    )
                )
            for result in tool_results:
                evidence.append(
                    Evidence(
                        kind="external_tool_result",
                        description=f"{result.tool}; provider={result.provider}; "
                        f"demo_data={result.demo_data}; verification={result.verification}; "
                        f"execution_id={result.execution_id}; available={result.available}; "
                        f"error={result.error_category}.",
                    )
                )
            if any("engine_code" in r.missing_information for r in tool_results):
                assessment = assessment.model_copy(
                    update={
                        "follow_up_questions": assessment.follow_up_questions[:2]
                        + ["What is the engine code? Please do not share the VIN."]
                    }
                )
            diagnostic = Diagnostic.model_validate(
                {
                    **assessment.model_dump(exclude={"citation_ids"}),
                    "limitations": list(dict.fromkeys(limitations)),
                    "conversation_id": conversation.conversation_id,
                    "vehicle_id": vehicle_id,
                    "extracted_symptoms": symptoms,
                    "evidence_sources": evidence,
                    "citations": citations,
                    "rag_available": retrieval.available,
                    "mcp_available": bool(tool_results)
                    and any(
                        r.error_category not in ("mcp_unavailable", "timeout", "invalid_response")
                        for r in tool_results
                    ),
                    "tool_results": tool_results,
                    "generation_mode": "deterministic_safety" if deterministic else "llm",
                    "urgency_assessment": urgency_detail,
                }
            )
            conversation.messages.extend(
                [
                    Message(role="user", content=content),
                    Message(role="assistant", content=diagnostic.summary),
                ]
            )
            conversation.diagnostic_ids.append(diagnostic.diagnostic_id)
            # A new completed assessment makes this case active again, including
            # critical follow-ups on a previously user-resolved case. The shared
            # conversation row lock serializes this with resolution operations.
            conversation = conversation.model_copy(
                update={
                    "resolution_status": "active",
                    "resolved_at": None,
                    "resolution_note": None,
                }
            )
            await repository.save_conversation(conversation)
            await repository.save_diagnostic(diagnostic)
            return diagnostic

    async def create(self, request: DiagnosticRequest):
        return await self.run(
            request, vehicle_id=request.vehicle_id, conversation_id=request.conversation_id
        )
