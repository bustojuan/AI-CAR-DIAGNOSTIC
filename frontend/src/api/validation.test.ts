import { expect, it } from "vitest";
import { sampleReport, sampleTool } from "../demo/api";
import {
  diagnosticPayload,
  caseHistoryPayload,
  healthPayload,
  InvalidPayload,
  toolPayload,
  vehiclePayload,
} from "./validation";
import { createDemoApi, demoVehicle } from "../demo/api";

it("accepts complete report fixtures and synthetic tool provenance", () => {
  expect(
    diagnosticPayload(sampleReport(crypto.randomUUID())).summary,
  ).toBeTruthy();
  expect(toolPayload(sampleTool("get_part_prices")).demo_data).toBe(true);
});
it.each([null, {}, { vehicle_id: "id" }])(
  "rejects malformed vehicle responses without rendering invented data",
  (value) => {
    expect(() => vehiclePayload(value)).toThrow(InvalidPayload);
  },
);
it("rejects malformed health payloads", () =>
  expect(() => healthPayload({ status: "ok" })).toThrow(InvalidPayload));
it("rejects mismatched or malformed urgency details", () => {
  const report = sampleReport(crypto.randomUUID());
  for (const detail of [
    { ...report.urgency_assessment, level: "low" },
    { ...report.urgency_assessment, explanation: "" },
    { ...report.urgency_assessment, warning_signs: "unknown" },
  ]) {
    expect(() =>
      diagnosticPayload({ ...report, urgency_assessment: detail }),
    ).toThrow(InvalidPayload);
  }
});
it("accepts historical reports without fabricated urgency details", () => {
  const report = {
    ...sampleReport(crypto.randomUUID()),
    urgency_assessment: null,
  };
  expect(diagnosticPayload(report).urgency_assessment).toBeNull();
});
it("rejects critical reports that permit continued driving", () => {
  const report = sampleReport(crypto.randomUUID(), true);
  expect(() =>
    diagnosticPayload({
      ...report,
      driving_recommendation: "caution_and_monitor",
    }),
  ).toThrow(InvalidPayload);
});
it("rejects backend data with confused demo provenance", () => {
  expect(() =>
    toolPayload({ ...sampleTool("search_parts"), demo_data: false }),
  ).toThrow(InvalidPayload);
});

it("accepts eBay Production and keeps Sandbox explicitly test-only", () => {
  const production = {
    ...sampleTool("check_compatibility"),
    provider: "ebay",
    demo_data: false,
    verification: "verified_provider",
  };
  expect(toolPayload(production).provider).toBe("ebay");
  expect(() => toolPayload({ ...production, demo_data: true })).toThrow(
    InvalidPayload,
  );
  const sandbox = {
    ...production,
    provider: "ebay_sandbox",
    demo_data: true,
    verification: "synthetic",
  };
  expect(toolPayload(sandbox).demo_data).toBe(true);
  expect(() => toolPayload({ ...sandbox, demo_data: false })).toThrow(
    InvalidPayload,
  );
});

it("validates a consistent history snapshot and rejects invalid resolution dates or counts", async () => {
  const api = createDemoApi();
  const report = await api.diagnose(demoVehicle.vehicle_id, {
    description: "Cold starting.",
  });
  const snapshot = await api.caseHistory(demoVehicle.vehicle_id);
  expect(caseHistoryPayload(snapshot).cases).toHaveLength(1);
  expect(() =>
    caseHistoryPayload({
      ...snapshot,
      vehicle_urgency: { ...snapshot.vehicle_urgency, active_case_count: 0 },
    }),
  ).toThrow(InvalidPayload);
  expect(() =>
    caseHistoryPayload({
      ...snapshot,
      cases: [
        {
          ...snapshot.cases[0],
          resolution_status: "resolved",
          resolved_at: null,
        },
      ],
    }),
  ).toThrow(InvalidPayload);
  await api.resolveCase(report.conversation_id, {
    expected_latest_diagnostic_id: report.diagnostic_id,
  });
  const resolved = await api.caseHistory(demoVehicle.vehicle_id);
  expect(caseHistoryPayload(resolved).vehicle_urgency.urgency_level).toBeNull();
  expect(() =>
    caseHistoryPayload({
      ...resolved,
      vehicle_urgency: { ...resolved.vehicle_urgency, urgency_level: "low" },
    }),
  ).toThrow(InvalidPayload);
});
