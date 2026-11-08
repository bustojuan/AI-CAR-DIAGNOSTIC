import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { testBackendUrl } from "./urls";

// GPU readbacks for a screencast on every event distort WebGL input/render timing.
// Explicit screenshots and failure DOM traces remain enabled.
test.use({
  trace: { mode: "retain-on-failure", screenshots: false, snapshots: true },
});

test("six quick starts stay editable, source navigation and compact demo disclosure work", async ({
  page,
}) => {
  const writes: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST") writes.push(request.url());
  });
  await page.goto("/?demo=1");
  await page.locator(".demo-indicator summary").click();
  await expect(
    page.getByText("Interface demonstration", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Exit demo" })).toBeVisible();
  await page.locator(".demo-indicator summary").click();
  for (const [label, text] of [
    ["Starting problems", "My car has difficulty starting. "],
    ["Engine warning light", "The engine warning light has come on. "],
    ["Loss of power", "I have noticed a loss of power in my car. "],
    ["Unusual noises", "I hear an unusual noise in my car. "],
    [
      "Overheating",
      "I have noticed that the engine temperature rises above normal. ",
    ],
    ["Excessive smoke", "I have noticed more smoke than usual from my car. "],
  ]) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.getByLabel("Describe the symptoms")).toHaveValue(text);
    await expect(page.getByLabel("Describe the symptoms")).toBeEditable();
    await page.getByRole("link", { name: "Home", exact: true }).click();
  }
  expect(writes).toEqual([]);
  await page.getByRole("button", { name: /^Technical Evidence/ }).click();
  await expect(
    page.getByRole("heading", { name: "No evidence retrieved yet." }),
  ).toBeVisible();
});

test("overview adapts from phone to wide desktop and keeps utility routes usable", async ({
  page,
}) => {
  test.setTimeout(60000); // Includes real GLB loading and seven viewport changes.
  await page.goto("/?demo=1");
  await expect(page.getByText("Demo mode")).toBeVisible();
  await expect(page.getByText("No active issues reported")).toBeVisible();
  await expect(page.locator(".connection-loading")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Reset vehicle view" }),
  ).toBeVisible({ timeout: 25000 });
  await expect(page.locator(".hero-vehicle canvas")).toBeVisible();
  for (const [width, height] of [
    [320, 800],
    [390, 844],
    [768, 1024],
    [1024, 768],
    [1440, 900],
    [1672, 941],
    [1920, 1080],
  ]) {
    await page.setViewportSize({ width, height });
    if (width >= 1440) {
      const lower = await page.locator(".dashboard-lower").boundingBox();
      expect(lower!.y + lower!.height).toBeLessThanOrEqual(height);
    }
    await expect
      .poll(
        () =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth,
          ),
        {
          message: `Responsive layout must settle without overflow at ${width}px`,
        },
      )
      .toBe(true);
    await expect(
      page.getByRole("button", { name: "New Diagnosis", exact: true }),
    ).toBeVisible();
    if (width === 390 || width === 1672)
      await page.screenshot({
        path: `test-results/overview-${width}.png`,
        fullPage: true,
      });
  }
  for (const route of ["informe", "configuracion", "ayuda"]) {
    await page.goto(`/?demo=1#${route}`);
    await expect(page.locator("main h1")).toBeVisible();
  }
  await page.goto("/?demo=1#recambios");
  await page.screenshot({
    path: "test-results/parts-desktop.png",
    fullPage: true,
  });
});

test("real FastAPI: create, follow up, reload and recover a conversation", async ({
  page,
}) => {
  await page.goto("/#diagnostico");
  await expect(page.getByText("Backend connected")).toBeVisible();
  await page
    .getByLabel("Describe the symptoms")
    .fill("My Golf starts slowly in cold weather.");
  const created = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/diagnostics") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Send consultation" }).click();
  const report = await (await created).json();
  expect(report.diagnostic_id).toBeTruthy();
  await expect(
    page.getByRole("heading", { name: "Possible causes" }),
  ).toBeVisible();
  await expect(page.getByLabel("Describe the symptoms")).toHaveValue("");
  await page
    .getByLabel("Describe the symptoms")
    .fill("It starts normally when warm.");
  const followup = page.waitForResponse((response) =>
    response
      .url()
      .endsWith(`/conversations/${report.conversation_id}/messages`),
  );
  await page.getByRole("button", { name: "Send consultation" }).click();
  expect((await (await followup).json()).conversation_id).toBe(
    report.conversation_id,
  );
  await expect(page.getByLabel("Describe the symptoms")).toHaveValue("");
  await page.reload();
  await expect(page.getByText("Backend connected")).toBeVisible();
  await page.getByRole("link", { name: "History", exact: true }).click();
  await page
    .getByRole("article", { name: "Case 1", exact: true })
    .getByRole("button", { name: "Open reports", exact: true })
    .click();
  await expect(
    page.getByText("It starts normally when warm.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("My Golf starts slowly in cold weather.", { exact: true }),
  ).toBeVisible();
  const storage = await page.evaluate(() =>
    localStorage.getItem("motor.conversations.v1"),
  );
  expect(storage).not.toContain("cold weather");
  expect(storage).toContain(report.conversation_id);
});

test("real backend brake triage remains visible across report tabs", async ({
  page,
}) => {
  await page.goto("/#diagnostico");
  await expect(page.getByText("Backend connected")).toBeVisible();
  await page
    .getByLabel("Describe the symptoms")
    .fill("My brakes stopped working. Find replacement brake pads and prices.");
  await page.getByRole("button", { name: "Send consultation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Do not continue driving",
  );
  await page.getByRole("tab", { name: "Sources and limits" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Do not continue driving",
  );
  await expect(
    page.getByRole("heading", { name: "Queried parts" }),
  ).toHaveCount(0);
});

test("real vehicle updates and explicit unavailable provider result", async ({
  page,
  request,
}) => {
  await page.goto("/#vehiculo");
  await expect(page.getByText("Backend connected")).toBeVisible();
  await page.getByLabel("Engine code", { exact: false }).fill("TEST-UI-ONLY");
  await page.getByLabel("Mileage", { exact: false }).fill("183000");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Vehicle details updated" }),
  ).toBeVisible();
  const vehicles = await (
    await request.get(`${testBackendUrl}/api/v1/vehicles`)
  ).json();
  expect(vehicles[0].engine_code).toBe("TEST-UI-ONLY");
  await page.getByRole("link", { name: "Parts", exact: true }).click();
  await page
    .getByLabel("Which component are you looking for?")
    .fill("calentadores");
  await page.getByRole("button", { name: "Search candidates" }).click();
  await expect(page.getByText("Unavailable", { exact: true })).toBeVisible();
  await expect(page.getByText("Synthetic price", { exact: false })).toHaveCount(
    0,
  );
  await request.patch(
    `${testBackendUrl}/api/v1/vehicles/${vehicles[0].vehicle_id}`,
    { data: { engine_code: null, mileage_km: null } },
  );
});

test("explicit demo is isolated and supports synthetic parts and unknown fitment", async ({
  page,
}) => {
  const apiRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/")) apiRequests.push(request.url());
  });
  await page.goto("/?demo=1#recambios");
  await expect(page.getByText("Demo mode")).toBeVisible();
  await page
    .getByLabel("Which component are you looking for?")
    .fill("calentadores");
  await page.getByRole("button", { name: "Search candidates" }).click();
  await expect(page.getByText("Synthetic glow-plug example")).toBeVisible();
  await page.getByRole("button", { name: "Check DEMO-001" }).click();
  await page
    .getByRole("button", { name: "Check compatibility", exact: true })
    .click();
  await expect(
    page.getByText("Compatibility unknown", { exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Prices", exact: true }).click();
  await page.getByRole("button", { name: "Check prices", exact: true }).click();
  await expect(page.getByText(/synthetic price/)).toBeVisible();
  expect(apiRequests).toEqual([]);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test("offline mode never silently displays a successful diagnostic", async ({
  page,
}) => {
  await page.route("**/api/v1/**", (route) => route.abort("connectionrefused"));
  await page.goto("/#diagnostico");
  await expect(
    page.getByText("Backend unavailable", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Explore demo" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Send consultation" }),
  ).toBeDisabled();
  await expect(page.getByText("Synthetic data")).toHaveCount(0);
});

test("mobile navigation, keyboard focus and no horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?demo=1");
  await expect(page.getByText("Demo mode")).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "My Vehicle", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Every detail helps." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Close navigation" }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.keyboard.press("Tab");
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
  expect(
    await page
      .locator(".sidebar")
      .evaluate((el) => el.contains(document.activeElement)),
  ).toBe(false);
  await page.screenshot({
    path: "test-results/mobile-vehicle.png",
    fullPage: true,
  });
});

test("desktop visual check has no console errors or overflow", async ({
  page,
}) => {
  // Real WebGL startup, three screenshots and a downloaded file can exceed
  // 30 seconds on the corporate Windows host. Keep all content/error assertions.
  test.setTimeout(60000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/?demo=1");
  await expect(page.getByText("Demo mode")).toBeVisible();
  await page.screenshot({
    path: "test-results/desktop-start.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Starting problems", exact: true })
    .click();
  await expect(page.getByLabel("Describe the symptoms")).toHaveValue(
    "My car has difficulty starting. ",
  );
  await page.getByRole("button", { name: "Send consultation" }).click();
  await expect(
    page.getByRole("heading", { name: "Possible causes" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/desktop-report.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open full report" }).click();
  await expect(
    page.getByRole("heading", { name: "Reported symptoms" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recommended checks" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Available evidence" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/full-report.png",
    fullPage: true,
  });
  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download report as JSON" }).click();
  const downloaded = await downloading;
  expect(downloaded.suggestedFilename()).toMatch(/^demo-report-/);
  expect(await downloaded.failure()).toBeNull();
  const exported = JSON.parse(
    await readFile((await downloaded.path())!, "utf8"),
  );
  expect(exported.demo_data).toBe(true);
  expect(exported.notice).toMatch(/synthetic/i);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
