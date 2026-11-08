import type {
  Conversation,
  CaseSummary,
  CaseHistory,
  Diagnostic,
  Health,
  ToolResult,
  ToolsStatus,
  Vehicle,
} from "./types";

type ObjectValue = Record<string, unknown>;
const object = (value: unknown): value is ObjectValue =>
  !!value && typeof value === "object" && !Array.isArray(value);
const strings = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");
const fields = (value: ObjectValue, keys: string[]) =>
  keys.every((key) => typeof value[key] === "string");
const list = (value: unknown, valid: (item: unknown) => boolean): boolean =>
  Array.isArray(value) && value.every(valid);
const optionalList = (value: unknown, valid: (item: unknown) => boolean) =>
  value === undefined || list(value, valid);
export class InvalidPayload extends Error {}
function checked<T>(value: unknown, valid: boolean): T {
  if (!valid) throw new InvalidPayload();
  return value as T;
}
export function vehiclePayload(value: unknown): Vehicle {
  return checked(
    value,
    object(value) &&
      fields(value, [
        "vehicle_id",
        "manufacturer",
        "model",
        "engine",
        "transmission",
        "fuel_type",
      ]) &&
      typeof value.model_year === "number",
  );
}
export function healthPayload(value: unknown): Health {
  return checked(
    value,
    object(value) &&
      ["ok", "degraded"].includes(String(value.status)) &&
      typeof value.persistence === "string" &&
      ["llm_configured", "rag_available", "mcp_available"].every(
        (key) => typeof value[key] === "boolean",
      ),
  );
}
export function toolsPayload(value: unknown): ToolsStatus {
  return checked(
    value,
    object(value) &&
      typeof value.available === "boolean" &&
      typeof value.reason === "string" &&
      typeof value.provider === "string" &&
      typeof value.demo_data === "boolean" &&
      strings(value.tools),
  );
}
function isToolResult(value: unknown): boolean {
  return (
    object(value) &&
    ["search_parts", "check_compatibility", "get_part_prices"].includes(
      String(value.tool),
    ) &&
    typeof value.available === "boolean" &&
    typeof value.demo_data === "boolean" &&
    typeof value.reason === "string" &&
    ["unavailable", "demo", "ebay", "ebay_sandbox"].includes(
      String(value.provider),
    ) &&
    ["unavailable", "synthetic", "verified_provider"].includes(
      String(value.verification),
    ) &&
    value.demo_data ===
      ["demo", "ebay_sandbox"].includes(String(value.provider)) &&
    [
      "unknown",
      "confirmed_compatible",
      "confirmed_incompatible",
      "requires_additional_information",
    ].includes(String(value.compatibility)) &&
    optionalList(
      value.parts,
      (part) =>
        object(part) &&
        fields(part, [
          "part_id",
          "name",
          "manufacturer",
          "brand",
          "category",
          "description",
          "source",
        ]),
    ) &&
    optionalList(
      value.prices,
      (price) =>
        object(price) &&
        fields(price, [
          "part_id",
          "merchant",
          "currency",
          "country",
          "unit_price",
          "verification",
        ]) &&
        Number.isFinite(Number(price.unit_price)),
    ) &&
    (value.evidence === undefined || strings(value.evidence)) &&
    (value.missing_information === undefined ||
      strings(value.missing_information))
  );
}
export function toolPayload(value: unknown): ToolResult {
  return checked(value, isToolResult(value));
}
export function diagnosticPayload(value: unknown): Diagnostic {
  return checked(
    value,
    object(value) &&
      fields(value, [
        "diagnostic_id",
        "conversation_id",
        "vehicle_id",
        "created_at",
        "summary",
      ]) &&
      strings(value.extracted_symptoms) &&
      typeof value.professional_assistance_recommended === "boolean" &&
      ["low", "moderate", "high", "critical"].includes(
        String(value.urgency_level),
      ) &&
      [
        "stop_safely_do_not_drive",
        "inspection_before_driving",
        "caution_and_monitor",
      ].includes(String(value.driving_recommendation)) &&
      (value.urgency_level !== "critical" ||
        (value.driving_recommendation === "stop_safely_do_not_drive" &&
          value.professional_assistance_recommended === true)) &&
      (value.urgency_level !== "high" ||
        (value.driving_recommendation !== "caution_and_monitor" &&
          value.professional_assistance_recommended === true)) &&
      (value.urgency_assessment == null ||
        (object(value.urgency_assessment) &&
          value.urgency_assessment.level === value.urgency_level &&
          value.urgency_assessment.driving_recommendation ===
            value.driving_recommendation &&
          value.urgency_assessment.professional_assistance_recommended ===
            value.professional_assistance_recommended &&
          typeof value.urgency_assessment.explanation === "string" &&
          value.urgency_assessment.explanation.trim().length > 0 &&
          strings(value.urgency_assessment.warning_signs) &&
          strings(value.urgency_assessment.missing_safety_information) &&
          [
            "deterministic_safety",
            "hybrid",
            "insufficient_information",
          ].includes(String(value.urgency_assessment.basis)))) &&
      strings(value.follow_up_questions) &&
      strings(value.next_steps) &&
      strings(value.limitations) &&
      list(
        value.possible_causes,
        (cause) =>
          object(cause) &&
          fields(cause, [
            "component_or_system",
            "possible_failure",
            "recommended_verification",
          ]) &&
          cause.label === "hypothesis" &&
          strings(cause.supporting_symptoms) &&
          strings(cause.missing_or_contradictory_evidence),
      ) &&
      list(
        value.recommended_checks,
        (item) => object(item) && fields(item, ["category", "description"]),
      ) &&
      list(
        value.evidence_sources,
        (item) => object(item) && fields(item, ["kind", "description"]),
      ) &&
      optionalList(
        value.citations,
        (item) =>
          object(item) &&
          fields(item, [
            "document_title",
            "chunk_id",
            "evidence_type",
            "verification_status",
          ]),
      ) &&
      optionalList(value.tool_results, isToolResult),
  );
}
export function conversationPayload(value: unknown): Conversation {
  return checked(
    value,
    object(value) &&
      fields(value, ["conversation_id", "vehicle_id", "created_at"]) &&
      strings(value.diagnostic_ids) &&
      list(
        value.messages,
        (message) =>
          object(message) &&
          fields(message, ["role", "content"]) &&
          ["user", "assistant"].includes(String(message.role)),
      ),
  );
}

const urgencyLevels = ["low", "moderate", "high", "critical"];
function validResolution(value: ObjectValue): boolean {
  return (
    (value.resolution_status === "active" &&
      value.resolved_at === null &&
      value.resolution_note === null) ||
    (value.resolution_status === "resolved" &&
      typeof value.resolved_at === "string" &&
      Number.isFinite(Date.parse(value.resolved_at)) &&
      (value.resolution_note === null ||
        typeof value.resolution_note === "string"))
  );
}
export function casePayload(value: unknown): CaseSummary {
  return checked(
    value,
    object(value) &&
      fields(value, [
        "conversation_id",
        "vehicle_id",
        "created_at",
        "latest_diagnostic_id",
        "latest_assessment_at",
        "summary",
      ]) &&
      validResolution(value) &&
      urgencyLevels.includes(String(value.historical_urgency)) &&
      Number.isInteger(value.assessment_count) &&
      Number(value.assessment_count) >= 1,
  );
}
export function caseHistoryPayload(value: unknown): CaseHistory {
  if (
    !object(value) ||
    !Array.isArray(value.cases) ||
    !object(value.vehicle_urgency)
  )
    throw new InvalidPayload();
  const cases = value.cases.map(casePayload);
  const urgency = value.vehicle_urgency;
  const active = cases.filter((item) => item.resolution_status === "active");
  return checked(
    value,
    fields(urgency, ["vehicle_id", "explanation"]) &&
      cases.every((item) => item.vehicle_id === urgency.vehicle_id) &&
      new Set(cases.map((item) => item.conversation_id)).size ===
        cases.length &&
      urgency.active_case_count === active.length &&
      urgency.resolved_case_count === cases.length - active.length &&
      (active.length === 0
        ? urgency.urgency_level === null
        : urgencyLevels.includes(String(urgency.urgency_level))),
  );
}
