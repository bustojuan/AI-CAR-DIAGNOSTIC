import { expect, test, type Page } from "@playwright/test";
import { testFrontendUrl } from "./urls";

test.use({
  trace: { mode: "retain-on-failure", screenshots: false, snapshots: true },
});
test.setTimeout(120000);
const fixture = "/e2e/viewer-fixture.html";
const view = (page: Page, id = "camera") =>
  page.getByTestId(id).evaluate(
    (el) =>
      JSON.parse(el.textContent!) as {
        azimuth: number;
        polar: number;
        distance: number;
      } | null,
  );

async function clickRealMesh(page: Page, selector: string) {
  const canvas = page.locator(selector);
  const box = (await canvas.boundingBox())!;
  // Hover feedback comes from the real R3F raycast. Reject overlaid DOM controls.
  for (const y of [0.55, 0.6, 0.5, 0.65, 0.4, 0.7, 0.35]) {
    for (const x of [0.45, 0.4, 0.5, 0.35, 0.55, 0.6, 0.3, 0.65]) {
      const point = { x: box.x + box.width * x, y: box.y + box.height * y };
      if (
        !(await page.evaluate(
          ({ x, y }) => document.elementFromPoint(x, y)?.tagName === "CANVAS",
          point,
        ))
      )
        continue;
      await page.mouse.move(point.x, point.y);
      await page.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => resolve()),
          ),
      );
      if ((await canvas.getAttribute("class"))?.includes("has-pick-target")) {
        await page.mouse.click(point.x, point.y);
        return;
      }
    }
  }
  throw new Error("No real, explicitly mapped mesh was hit");
}

test("production photo inspection uses English and prepares existing AI and MCP actions without auto-submission", async ({
  page,
}) => {
  const posts: string[] = [],
    models: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST") posts.push(request.url());
    if (/\.(glb|gltf)$/.test(request.url())) models.push(request.url());
  });
  await page.goto("/");
  await expect(page.getByText("Backend connected")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(
    page.getByRole("button", { name: "Reset vehicle view" }),
  ).toBeVisible({ timeout: 25000 });
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  const dialog = page.getByRole("dialog", { name: "Engine Bay" });
  await expect(
    dialog.getByRole("heading", {
      name: "Explore the complete engine compartment",
    }),
  ).toBeVisible();
  await expect(page.locator("#root")).toHaveAttribute("inert", "");
  await dialog.getByRole("button", { name: "Battery General topic" }).click();
  await expect(
    dialog.getByText(/No vehicle-specific technical evidence/),
  ).toBeVisible();
  expect(posts).toEqual([]);
  await dialog
    .getByRole("button", { name: "Ask AI About This Component" })
    .click();
  await expect(page.getByLabel("Describe the symptoms")).toHaveValue(
    /battery on my Volkswagen Golf Plus 2009 2.0 TDI/,
  );
  expect(posts).toEqual([]);
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  await page.getByRole("button", { name: "Battery General topic" }).click();
  await page.getByRole("button", { name: "Find Related Parts" }).click();
  await expect(
    page.getByLabel("Which component are you looking for?"),
  ).toHaveValue("battery");
  expect(posts).toEqual([]);
  const search = page.waitForRequest(
    (request) =>
      request.url().endsWith("/parts/search") && request.method() === "POST",
  );
  await page.getByRole("button", { name: "Search candidates" }).click();
  const payload = (await search).postDataJSON();
  expect(payload.component).toBe("battery");
  expect(payload.vehicle_id).toMatch(/^[0-9a-f-]{36}$/);
  await expect(page.getByText("Unavailable", { exact: true })).toBeVisible();
  expect(models.every((url) => url.endsWith("/models/golf-viii-gti.glb"))).toBe(
    true,
  );
});

test("the selected Golf opens inspection and returns to its exterior pose", async ({
  page,
}) => {
  await page.goto(`${fixture}?case=vehicle`);
  await expect(
    page.getByRole("button", { name: "Reset vehicle view" }),
  ).toBeVisible({ timeout: 25000 });
  const initial = (await view(page))!;
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  await expect(page.getByRole("dialog", { name: "Engine Bay" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Engine bay asset unavailable" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Back to Vehicle" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect
    .poll(async () => (await view(page))!.azimuth)
    .toBeCloseTo(initial.azimuth, 3);
  expect((await view(page))!.polar).toBeCloseTo(initial.polar, 3);
  await page.screenshot({ path: "test-results/explorer-actual-exterior.png" });
});

test("test-only engine geometry verifies smooth camera transition, raycasting, hotspots, bounded zoom and back", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto(`${fixture}?case=engine`);
  await expect(
    page.getByRole("button", { name: "Reset vehicle view" }),
  ).toBeVisible({ timeout: 25000 });
  const initial = (await view(page))!;
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  await expect(
    page.getByRole("button", { name: "Reset engine bay view" }),
  ).toBeVisible({ timeout: 25000 });
  const history = await page
    .getByTestId("camera-history")
    .evaluate((el) => JSON.parse(el.textContent!) as { distance: number }[]);
  expect(
    new Set(history.map((value) => value.distance.toFixed(4))).size,
  ).toBeGreaterThan(3);
  await clickRealMesh(page, ".engine-scene canvas");
  await expect(
    page.getByLabel("Component information").getByRole("heading", { level: 3 }),
  ).toHaveText(
    /Battery|Engine assembly|Coolant expansion tank|Air filter housing/,
  );
  await page
    .getByRole("button", { name: "Inspect Battery", exact: true })
    .click();
  await expect(
    page
      .getByLabel("Component information")
      .getByRole("heading", { name: "Battery", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Visible inspection feature.*illustrative layout/),
  ).toBeVisible();
  const before = (await view(page, "inspection-camera"))!;
  const box = (await page.locator(".engine-scene canvas").boundingBox())!;
  await page.mouse.move(box.x + 20, box.y + 20);
  await page.mouse.wheel(0, -600);
  await expect
    .poll(async () => (await view(page, "inspection-camera"))!.distance)
    .toBeLessThan(before.distance - 0.1);
  expect((await view(page, "inspection-camera"))!.distance).toBeGreaterThan(2);
  await page.getByRole("button", { name: "Reset engine bay view" }).click();
  await expect
    .poll(async () => (await view(page, "inspection-camera"))!.distance)
    .toBeCloseTo(before.distance, 3);
  await page.screenshot({
    path: "test-results/engine-calibration-TEST-ONLY.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Back to Vehicle" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect
    .poll(async () => (await view(page))!.distance)
    .toBeCloseTo(initial.distance, 3);
});

test("a mismatched engine code never loads the supplied engine scene", async ({
  page,
}) => {
  const engineRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("engine-calibration"))
      engineRequests.push(request.url());
  });
  await page.goto(`${fixture}?case=engine-mismatch`);
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  await expect(
    page.getByText(
      "This engine-bay asset does not match the confirmed engine code.",
    ),
  ).toBeVisible();
  await expect(page.locator(".engine-scene canvas")).toHaveCount(0);
  expect(engineRequests).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("engine load failure retains general topics and retry restores only validated mappings", async ({
  page,
}) => {
  let failed = true;
  await page.route("**/engine-calibration.gltf", (route) =>
    failed
      ? route.fulfill({ status: 404, body: "Missing test fixture" })
      : route.continue(),
  );
  await page.goto(`${fixture}?case=engine`);
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  await expect(
    page.getByRole("heading", {
      name: "The inspection model could not be loaded",
    }),
  ).toBeVisible({ timeout: 25000 });
  await page.getByRole("button", { name: "Battery General topic" }).click();
  await expect(
    page.getByText("General component topic", { exact: true }),
  ).toBeVisible();
  failed = false;
  await page.getByRole("button", { name: "Retry engine bay" }).click();
  await expect(
    page.getByRole("button", { name: "Reset engine bay view" }),
  ).toBeVisible({ timeout: 25000 });
  await expect(
    page.getByText(/Visible inspection feature.*illustrative layout/),
  ).toBeVisible();
});

test("mobile touch rotates the inspection scene, supports selection and restores the page on exit", async ({
  browser,
}) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  try {
    const page = await context.newPage();
    await page.goto(`${testFrontendUrl}${fixture}?case=engine`);
    await page.getByRole("button", { name: "Explore Engine Bay" }).tap();
    await expect(
      page.getByRole("button", { name: "Reset engine bay view" }),
    ).toBeVisible({ timeout: 25000 });
    const before = (await view(page, "inspection-camera"))!;
    const box = (await page.locator(".engine-scene canvas").boundingBox())!;
    const client = await context.newCDPSession(page);
    const x = box.x + box.width * 0.8,
      y = box.y + box.height * 0.6;
    const touch = (px: number) => [
      { x: px, y, id: 0, radiusX: 5, radiusY: 5, force: 1 },
    ];
    await client.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: touch(x),
    });
    for (let i = 1; i <= 8; i++) {
      await client.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: touch(x - i * 10),
      });
      await page.waitForTimeout(30);
    }
    await client.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await expect
      .poll(async () =>
        Math.abs(
          (await view(page, "inspection-camera"))!.azimuth - before.azimuth,
        ),
      )
      .toBeGreaterThan(0.2);
    // Let damping settle after a physical-duration touch gesture before tapping.
    let previous = (await view(page, "inspection-camera"))!.azimuth;
    await expect
      .poll(
        async () => {
          const next = (await view(page, "inspection-camera"))!.azimuth;
          const change = Math.abs(next - previous);
          previous = next;
          return change;
        },
        { intervals: [200, 250, 300] },
      )
      .toBeLessThan(0.0001);
    await page.getByRole("button", { name: "Battery 3D mapping" }).tap();
    await expect(
      page
        .getByLabel("Component information")
        .getByRole("heading", { name: "Battery", exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: "test-results/engine-mobile-TEST-ONLY.png",
      fullPage: true,
    });
    await page.getByRole("button", { name: "Back to Vehicle" }).tap();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(await page.evaluate(() => document.body.style.overflow)).not.toBe(
      "hidden",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  } finally {
    await context.close();
  }
});
