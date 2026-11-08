import { test, expect } from "@playwright/test";

import {
  startWithNoActiveTestCases,
  testVehicleId as vehicle,
} from "./case-fixtures";

test("resolution tracking updates current urgency, retains critical reports and survives browser reload", async ({
  page,
  request,
}) => {
  test.setTimeout(60000);
  await startWithNoActiveTestCases(request);
  const critical = await (
    await request.post("/api/v1/diagnostics", {
      data: { vehicle_id: vehicle, description: "My steering has failed." },
    })
  ).json();
  const moderate = await (
    await request.post("/api/v1/diagnostics", {
      data: {
        vehicle_id: vehicle,
        description: "Starting is difficult in cold weather.",
      },
    })
  ).json();
  await page.goto("/");
  const status = page.getByRole("region", {
    name: "Latest consultation status",
  });
  // Initial history fetch can overlap the cold WebGL import on this Windows host.
  await expect(status.getByText("Critical", { exact: true })).toBeVisible({
    timeout: 15000,
  });
  await page.getByRole("link", { name: "History", exact: true }).click();
  const entry = page.locator(`[data-case-id="${critical.conversation_id}"]`);
  await entry.getByRole("button", { name: "Mark as Resolved" }).click();
  const dialog = page.getByRole("dialog", {
    name: "Mark this case as resolved?",
  });
  await expect(dialog.getByText(/does not independently verify/)).toBeVisible();
  await dialog
    .getByLabel("Resolution note (optional)")
    .fill("Workshop visit reported by owner.");
  await page.screenshot({
    path: "test-results/resolution-confirmation.png",
    fullPage: true,
  });
  await dialog.getByRole("button", { name: "Confirm Resolution" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(entry.getByText("Resolved", { exact: true })).toBeVisible();
  await expect(entry.getByText(/Resolved on/)).toBeVisible();
  await page.reload();
  await expect(
    entry.getByText("Resolution note: Workshop visit reported by owner."),
  ).toBeVisible();
  await page
    .getByRole("group", { name: "Filter cases" })
    .getByRole("button", { name: "Active", exact: true })
    .click();
  await expect(entry).toHaveCount(0);
  await page
    .getByRole("group", { name: "Filter cases" })
    .getByRole("button", { name: "Resolved", exact: true })
    .click();
  await expect(
    entry.getByRole("button", { name: "Reopen Diagnosis" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(status.getByText("Moderate", { exact: true })).toBeVisible();
  expect(
    await (
      await request.get(`/api/v1/diagnostics/${critical.diagnostic_id}`)
    ).json(),
  ).toEqual(critical);
  await page.getByRole("link", { name: "History", exact: true }).click();
  const other = page.locator(`[data-case-id="${moderate.conversation_id}"]`);
  await other.getByRole("button", { name: "Mark as Resolved" }).click();
  await page.getByRole("button", { name: "Confirm Resolution" }).click();
  await expect(
    other.getByRole("button", { name: "Reopen Diagnosis" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(status.getByText("Not assessed", { exact: true })).toBeVisible();
  await expect(
    status.getByText("No active issues reported", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "History", exact: true }).click();
  await entry.getByRole("button", { name: "Reopen Diagnosis" }).click();
  await expect(
    entry.getByRole("button", { name: "Mark as Resolved" }),
  ).toBeVisible();
  await entry.getByRole("button", { name: "Open reports" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Do not continue driving",
  );
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(status.getByText("Critical", { exact: true })).toBeVisible();
});

test("new critical symptoms reactivate a resolved case and keep earlier assessments accessible", async ({
  page,
  request,
}) => {
  test.setTimeout(60000);
  await startWithNoActiveTestCases(request);
  const original = await (
    await request.post("/api/v1/diagnostics", {
      data: {
        vehicle_id: vehicle,
        description: "Difficult starting when cold.",
      },
    })
  ).json();
  await page.goto("/#historial");
  const entry = page.locator(`[data-case-id="${original.conversation_id}"]`);
  await entry.getByRole("button", { name: "Mark as Resolved" }).click();
  await page.getByRole("button", { name: "Confirm Resolution" }).click();
  await expect(
    entry.getByRole("button", { name: "Reopen Diagnosis" }),
  ).toBeVisible();
  await entry.getByRole("button", { name: "Open reports" }).click();
  await page
    .getByLabel("Describe the symptoms")
    .fill("There is smoke under the hood.");
  await page.getByRole("button", { name: "Send consultation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Do not continue driving",
  );
  const selector = page.getByLabel("Diagnostic assessment");
  await expect(selector).toBeEnabled();
  await selector.selectOption(original.diagnostic_id);
  await expect(page.locator(".urgency-banner")).toContainText(
    "Diagnostic urgency: Moderate",
  );
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(
    page
      .getByRole("region", { name: "Latest consultation status" })
      .getByText("Critical", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "History", exact: true }).click();
  await expect(entry.getByText("Active", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await page.screenshot({
    path: "test-results/resolution-history-mobile.png",
    fullPage: true,
  });
});
