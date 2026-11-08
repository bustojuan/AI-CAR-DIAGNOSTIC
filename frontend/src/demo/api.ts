/** Explicit browser-only examples. Never imported as a fallback for a failed real request. */
import { ApiError } from "../api/client";
import type {
  CarApi,
  CaseSummary,
  CaseHistory,
  CaseVersion,
  Conversation,
  Diagnostic,
  Observation,
  Part,
  ToolResult,
  Vehicle,
} from "../api/types";

export const demoVehicle: Vehicle = {
  vehicle_id: "00000000-0000-4000-8000-000000000001",
  manufacturer: "Volkswagen",
  model: "Golf Plus",
  model_year: 2009,
  engine: "2.0 TDI",
  fuel_type: "Diesel",
  transmission: "Manual",
  engine_code: "CFFB",
  power_output: null,
  mileage_km: null,
  vin: null,
};
const now = () => new Date().toISOString();
export function sampleTool(
  tool: ToolResult["tool"],
  partId = "DEMO-001",
): ToolResult {
  return {
    tool,
    execution_id: crypto.randomUUID(),
    retrieved_at: now(),
    provider: "demo",
    demo_data: true,
    verification: "synthetic",
    available: true,
    compatibility: "unknown",
    part_id: tool === "search_parts" ? null : partId,
    vehicle_id: demoVehicle.vehicle_id,
    reason:
      "Synthetic UI example. It is not a catalog, an offer or verified compatibility.",
    missing_information: tool === "check_compatibility" ? ["engine_code"] : [],
    evidence:
      tool === "check_compatibility"
        ? ["No real compatibility evidence exists in this example."]
        : [],
    parts:
      tool === "search_parts"
        ? [
            {
              part_id: "DEMO-001",
              name: "Synthetic glow-plug example",
              manufacturer: "Synthetic Demo Parts",
              brand: "Demo only",
              category: "glow_plugs",
              description: "UI sample. It does not represent a real product.",
              source: "demo",
              oem_reference: null,
              oem_verified: false,
              compatibility: "unknown",
              verification: "synthetic",
            } satisfies Part,
          ]
        : [],
    prices:
      tool === "get_part_prices"
        ? [
            {
              part_id: partId,
              merchant: "Fictional merchant",
              unit_price: "12.34",
              currency: "EUR",
              country: "ES",
              quantity: 1,
              tax_included: null,
              availability: "demonstration",
              verification: "synthetic",
              retrieved_at: now(),
            },
          ]
        : [],
  };
}

export function sampleReport(
  conversationId: string,
  critical = false,
): Diagnostic {
  return {
    diagnostic_id: crypto.randomUUID(),
    conversation_id: conversationId,
    vehicle_id: demoVehicle.vehicle_id,
    created_at: now(),
    summary: critical
      ? "Example safety response to possible brake failure: stop safely and do not continue driving."
      : "Illustrative example: difficult cold starting can have several causes. Battery and glow-plug systems require checks before any parts are replaced.",
    urgency_level: critical ? "critical" : "moderate",
    driving_recommendation: critical
      ? "stop_safely_do_not_drive"
      : "inspection_before_driving",
    professional_assistance_recommended: true,
    urgency_assessment: {
      level: critical ? "critical" : "moderate",
      explanation: critical
        ? "Illustrative safety alert: possible loss of braking requires stopping safely and professional assistance."
        : "Illustrative triage: safety information is incomplete. Moderate is a precautionary minimum, not a diagnosis or permission to drive.",
      warning_signs: critical ? ["Example possible loss of braking"] : [],
      missing_safety_information: [
        "Example: engine temperature and other safety warnings",
      ],
      driving_recommendation: critical
        ? "stop_safely_do_not_drive"
        : "inspection_before_driving",
      professional_assistance_recommended: true,
      basis: critical ? "deterministic_safety" : "insufficient_information",
    },
    follow_up_questions: critical
      ? []
      : [
          "Does the starter crank more slowly than usual?",
          "Does it start normally when the engine is warm?",
          "What is the engine code? Do not share the VIN.",
        ],
    possible_causes: critical
      ? []
      : [
          {
            label: "hypothesis",
            component_or_system: "Battery and starting system",
            possible_failure:
              "Reduced starting capacity is a possibility, not a confirmed fault.",
            supporting_symptoms: ["Example cold-start difficulty"],
            missing_or_contradictory_evidence: [
              "Cranking speed and battery condition are unknown.",
            ],
            recommended_verification:
              "Ask a professional to check the battery and starting system.",
            professional_inspection_required: true,
            uncertainty: "possible",
          },
          {
            label: "hypothesis",
            component_or_system: "Glow-plug system",
            possible_failure:
              "The glow-plug system is another hypothesis requiring checks.",
            supporting_symptoms: [
              "The example describes a difficulty that occurs when cold.",
            ],
            missing_or_contradictory_evidence: [
              "No readings or circuit checks are available.",
            ],
            recommended_verification:
              "Request a professional inspection of the glow-plug system.",
            professional_inspection_required: true,
            uncertainty: "uncertain",
          },
        ],
    recommended_checks: critical
      ? [
          {
            category: "professional",
            description: "Seek assistance. Do not take a test drive.",
          },
        ]
      : [
          {
            category: "safe_observation",
            description:
              "With the vehicle parked, note when it happens and which warning lights appear.",
          },
          {
            category: "professional",
            description:
              "Request checks of the battery, starter and fault codes.",
          },
        ],
    limitations: [
      "Demonstration report for exploring the UI; it does not assess your vehicle.",
      "No AI model, manufacturer documentation or live provider has been consulted.",
    ],
    next_steps: critical
      ? ["Stop safely, do not drive and seek assistance."]
      : [
          "Note whether the problem also occurs when the engine is warm.",
          "Discuss your observations with a professional before replacing parts.",
        ],
    extracted_symptoms: critical
      ? ["Example possible brake problem"]
      : ["Example cold-start difficulty"],
    evidence_sources: [
      {
        kind: "user_provided",
        description:
          "Demonstration interaction without independent verification.",
      },
    ],
    citations: [],
    rag_available: false,
    mcp_available: false,
    tool_results: [],
    generation_mode: critical ? "deterministic_safety" : "llm",
  };
}

export function createDemoApi(): CarApi {
  let vehicle = structuredClone(demoVehicle);
  const conversations = new Map<string, Conversation>();
  const reports = new Map<string, Diagnostic>();
  const wait = async <T>(value: T): Promise<T> => {
    await new Promise((resolve) => setTimeout(resolve, 220));
    return structuredClone(value);
  };
  function addReport(conversation: Conversation, observation: Observation) {
    const report = sampleReport(
      conversation.conversation_id,
      /frenos|brakes|dirección|incendio/i.test(observation.description),
    );
    if (!report.possible_causes.length) report.tool_results = [];
    else if (
      /precio|cost|recambio|repuesto|replacement/i.test(observation.description)
    ) {
      report.tool_results = [
        "search_parts",
        "check_compatibility",
        "get_part_prices",
      ].map((tool) => sampleTool(tool as ToolResult["tool"]));
      report.mcp_available = true;
    }
    conversation.resolution_status = "active";
    conversation.resolved_at = null;
    conversation.resolution_note = null;
    conversation.messages = [
      ...(conversation.messages || []),
      {
        role: "user",
        message_id: crypto.randomUUID(),
        content: JSON.stringify(observation),
        created_at: now(),
      },
      {
        role: "assistant",
        message_id: crypto.randomUUID(),
        content: report.summary,
        created_at: now(),
      },
    ];
    conversation.diagnostic_ids = [
      ...(conversation.diagnostic_ids || []),
      report.diagnostic_id,
    ];
    conversations.set(conversation.conversation_id, conversation);
    reports.set(report.diagnostic_id, report);
    return wait(report);
  }
  function caseSnapshot(): CaseHistory {
    const levels = ["low", "moderate", "high", "critical"] as const;
    const cases: CaseSummary[] = [...conversations.values()]
      .filter((c) => c.diagnostic_ids?.length)
      .map((c) => {
        const assessments = c.diagnostic_ids!.map((id) => reports.get(id)!);
        const last = assessments.at(-1)!;
        return {
          conversation_id: c.conversation_id,
          vehicle_id: c.vehicle_id,
          created_at: c.created_at,
          resolution_status: c.resolution_status || "active",
          resolved_at: c.resolved_at || null,
          resolution_note: c.resolution_note || null,
          latest_diagnostic_id: last.diagnostic_id,
          latest_assessment_at: last.created_at,
          summary: last.summary,
          assessment_count: assessments.length,
          historical_urgency:
            levels[
              Math.max(
                ...assessments.map((r) => levels.indexOf(r.urgency_level)),
              )
            ],
        };
      })
      .reverse();
    const active = cases.filter((c) => c.resolution_status === "active");
    return {
      cases,
      vehicle_urgency: {
        vehicle_id: vehicle.vehicle_id,
        urgency_level: active.length
          ? levels[
              Math.max(
                ...active.map((c) => levels.indexOf(c.historical_urgency)),
              )
            ]
          : null,
        active_case_count: active.length,
        resolved_case_count: cases.length - active.length,
        explanation:
          "Synthetic demo case aggregation. This does not assess a real vehicle.",
      },
    };
  }
  function changeResolution(
    id: string,
    version: CaseVersion,
    resolve: boolean,
    note?: string | null,
  ) {
    const conversation = conversations.get(id) || missing();
    if (
      version.expected_latest_diagnostic_id !==
      conversation.diagnostic_ids?.at(-1)
    )
      throw new ApiError("A newer assessment exists.", "stale_case");
    const target = resolve ? "resolved" : "active";
    if ((conversation.resolution_status || "active") === target)
      throw new ApiError(
        "The case status has already changed.",
        "invalid_resolution_transition",
      );
    conversation.resolution_status = target;
    conversation.resolved_at = resolve ? now() : null;
    conversation.resolution_note = resolve ? note || null : null;
    return wait(caseSnapshot().cases.find((c) => c.conversation_id === id)!);
  }
  const missing = () => {
    throw new ApiError(
      "The example is no longer in memory. Start a new consultation.",
      "not_found",
    );
  };
  return {
    health: () =>
      wait({
        status: "ok",
        persistence: "in-memory demo",
        llm_configured: false,
        rag_available: false,
        mcp_available: false,
      }),
    vehicles: () => wait([vehicle]),
    tools: () =>
      wait({
        available: true,
        reason: "Local UI simulation; it does not connect to the MCP server.",
        tools: ["search_parts", "check_compatibility", "get_part_prices"],
        provider: "demo",
        demo_data: true,
      }),
    updateVehicle: (_id, data) => {
      vehicle = { ...vehicle, ...data } as Vehicle;
      return wait(vehicle);
    },
    diagnose: (_id, data) =>
      addReport(
        {
          conversation_id: crypto.randomUUID(),
          vehicle_id: vehicle.vehicle_id,
          created_at: now(),
          messages: [],
          diagnostic_ids: [],
          resolution_status: "active",
          resolved_at: null,
          resolution_note: null,
        },
        data,
      ),
    message: (id, data) => addReport(conversations.get(id) || missing(), data),
    conversation: (id) => wait(conversations.get(id) || missing()),
    diagnostic: (id) => wait(reports.get(id) || missing()),
    caseHistory: () => wait(caseSnapshot()),
    resolveCase: (id, data) =>
      changeResolution(id, data, true, data.resolution_note),
    reopenCase: (id, data) => changeResolution(id, data, false),
    search: () => wait(sampleTool("search_parts")),
    compatibility: (data) =>
      wait(sampleTool("check_compatibility", data.part_id)),
    prices: (data) =>
      wait({
        ...sampleTool("get_part_prices", data.part_id),
        ...(data.part_id.startsWith("DEMO-") &&
        (!data.currency || data.currency === "EUR") &&
        (!data.country || data.country === "ES")
          ? {}
          : {
              available: false,
              prices: [],
              reason:
                "No sample price is available for that reference or market.",
            }),
      }),
  };
}
