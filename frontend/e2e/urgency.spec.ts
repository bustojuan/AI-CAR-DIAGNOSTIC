import { test, expect } from "@playwright/test";
import { startWithNoActiveTestCases } from "./case-fixtures";

test("three balanced cards display genuine backend urgency and honest uncertainty", async ({
  page,
  request,
}) => {
  test.setTimeout(60000);
  await startWithNoActiveTestCases(request);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByText("Backend connected")).toBeVisible();
  const status = page.getByRole("region", {
    name: "Latest consultation status",
  });
  await expect(status.locator(".overview-metric")).toHaveCount(3);
  await expect(status.getByText("Next step", { exact: true })).toHaveCount(0);
  await expect(status.getByText("Not assessed", { exact: true })).toBeVisible();
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1080 });
    const widths = await status
      .locator(".overview-metric")
      .evaluateAll((cards) =>
        cards.map((card) => card.getBoundingClientRect().width),
      );
    expect(Math.max(...widths) - Math.min(...widths)).toBeLessThan(1);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 1440, height: 1080 });
  await page
    .getByRole("button", { name: "New Diagnosis", exact: true })
    .click();
  await page.getByLabel("Describe the symptoms").fill("No symptoms");
  const invalid = page.waitForResponse(
    (response) =>
      response.url().endsWith("/diagnostics") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Send consultation" }).click();
  expect((await invalid).status()).toBe(422);
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(status.getByText("Not assessed", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "New Diagnosis", exact: true })
    .click();
  await page
    .getByLabel("Describe the symptoms")
    .fill("No fire, but the brakes have failed.");
  const completed = page.waitForResponse(
    (response) =>
      response.url().endsWith("/diagnostics") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Send consultation" }).click();
  const response = await completed;
  expect(response.status()).toBe(201);
  const report = await response.json();
  expect(report.urgency_level).toBe("critical");
  expect(report.urgency_assessment.warning_signs).toContain(
    "Possible loss of braking",
  );
  await expect(
    page.getByText(report.urgency_assessment.explanation),
  ).toBeVisible();
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(status.getByText("Critical", { exact: true })).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "Do not continue driving",
  );
  await page.screenshot({
    path: "test-results/urgency-three-cards.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
