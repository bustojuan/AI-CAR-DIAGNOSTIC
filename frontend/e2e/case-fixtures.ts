import { expect, type APIRequestContext } from "@playwright/test";

export const testVehicleId = "00000000-0000-4000-8000-000000000001";

export async function startWithNoActiveTestCases(request: APIRequestContext) {
  const health = await (await request.get("/api/v1/health")).json();
  if (health.persistence !== "in_memory" || health.llm_configured)
    throw new Error(
      "Case fixture changes are restricted to the isolated in-memory test harness.",
    );
  const cases = await (
    await request.get(`/api/v1/vehicles/${testVehicleId}/cases`)
  ).json();
  for (const item of cases.filter(
    (item: { resolution_status: string }) =>
      item.resolution_status === "active",
  )) {
    const response = await request.post(
      `/api/v1/conversations/${item.conversation_id}/resolve`,
      {
        data: {
          expected_latest_diagnostic_id: item.latest_diagnostic_id,
          resolution_note: "Test fixture precondition",
        },
      },
    );
    expect(response.ok()).toBe(true);
  }
}
