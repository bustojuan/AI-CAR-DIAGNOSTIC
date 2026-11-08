import { test, expect, type Page } from "@playwright/test";
import { testFrontendUrl } from "./urls";

// Trace screencasts synchronously read back the GPU on every drag event and
// distort WebGL timing on software-rendered corporate Windows sessions.
test.use({
  trace: { mode: "retain-on-failure", screenshots: false, snapshots: true },
});
test.describe("3D viewer — calibration and authorized alternative Golf VIII GTI", () => {
  test.setTimeout(90000);
  const fixture = "/e2e/viewer-fixture.html";
  const readView = (page: Page) =>
    page.getByTestId("camera").evaluate(
      (el) =>
        JSON.parse(el.textContent!) as {
          azimuth: number;
          polar: number;
          distance: number;
        } | null,
    );
  async function settle(page: Page) {
    let last = (await readView(page))?.azimuth ?? Infinity;
    await expect
      .poll(
        async () => {
          const next = (await readView(page))?.azimuth ?? Infinity;
          const delta = Math.abs(next - last);
          last = next;
          return delta;
        },
        { intervals: [150, 200, 250], timeout: 10000 },
      )
      .toBeLessThan(0.0001);
    return (await readView(page))!;
  }
  async function drag(page: Page, dx: number, dy = 0) {
    const canvas = page.locator("canvas");
    const box = (await canvas.boundingBox())!;
    const x = box.x + box.width / 2,
      y = box.y + box.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + dx, y + dy, { steps: 12 });
    await page.mouse.up();
  }

  for (const [modelName, modelPath] of [
    ["calibration", fixture],
    ["Golf VIII GTI", `${fixture}?case=vehicle`],
  ]) {
    test(`${modelName}: real WebGL loads glTF, turns through sides/rear and a full circle, holds, resets and constrains camera`, async ({
      page,
    }) => {
      // Eight drags plus screenshots and settling on Windows software WebGL.
      // Keep the same geometric assertions for the actual model and calibration.
      if (modelName === "Golf VIII GTI") test.setTimeout(180000);
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });
      await page.goto(modelPath);
      await expect(
        page.getByRole("button", { name: "Reset vehicle view" }),
      ).toBeVisible({ timeout: 20000 });
      await expect(page.locator("canvas")).toBeVisible({ timeout: 20000 });
      const initial = await settle(page);
      let previous = initial.azimuth,
        total = 0;
      for (let index = 0; index < 8; index++) {
        await drag(page, -90);
        const next = await settle(page);
        total += Math.atan2(
          Math.sin(next.azimuth - previous),
          Math.cos(next.azimuth - previous),
        );
        previous = next.azimuth;
        if (index === 1)
          await page.screenshot({
            path: `test-results/viewer-${modelName}-side.png`,
          });
        if (index === 3)
          await page.screenshot({
            path: `test-results/viewer-${modelName}-rear.png`,
          });
      }
      expect(Math.abs(total)).toBeGreaterThan(2 * Math.PI);
      const held = await settle(page);
      await page.waitForTimeout(400);
      expect((await readView(page))!.azimuth).toBeCloseTo(held.azimuth, 3);
      await drag(page, 0, 800);
      const limited = await settle(page);
      expect(limited.polar).toBeGreaterThanOrEqual(Math.PI / 4 - 0.001);
      expect(limited.polar).toBeLessThanOrEqual(Math.PI / 2 - 0.079);
      await page.mouse.wheel(0, -1000);
      expect((await readView(page))!.distance).toBeCloseTo(initial.distance, 3);
      await page.getByRole("button", { name: "Reset vehicle view" }).click();
      const reset = await settle(page);
      expect(reset.azimuth).toBeCloseTo(initial.azimuth, 3);
      expect(reset.polar).toBeCloseTo(initial.polar, 3);
      await page.locator("canvas").focus();
      await page.keyboard.press("ArrowRight");
      expect(
        Math.abs((await settle(page)).azimuth - initial.azimuth),
      ).toBeGreaterThan(0.05);
      expect(errors).toEqual([]);
    });
  }

  test("touch rotates the actual scene and vertical swipes can scroll the page", async ({
    browser,
  }) => {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
      deviceScaleFactor: 1,
    });
    try {
      const page = await context.newPage();
      await page.goto(`${testFrontendUrl}${fixture}?case=vehicle`);
      await expect(
        page.getByRole("button", { name: "Reset vehicle view" }),
      ).toBeVisible({ timeout: 20000 });
      const initial = await settle(page);
      const client = await context.newCDPSession(page);
      const box = (await page.locator("canvas").boundingBox())!;
      const x = box.x + box.width * 0.75,
        y = box.y + box.height * 0.5;
      const touch = (px: number, py: number) => [
        { x: px, y: py, id: 0, radiusX: 5, radiusY: 5, force: 1 },
      ];
      await client.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: touch(x, y),
      });
      for (let i = 1; i <= 10; i++)
        await client.send("Input.dispatchTouchEvent", {
          type: "touchMove",
          touchPoints: touch(x - i * 12, y),
        });
      await client.send("Input.dispatchTouchEvent", {
        type: "touchEnd",
        touchPoints: [],
      });
      expect(
        Math.abs((await settle(page)).azimuth - initial.azimuth),
      ).toBeGreaterThan(0.3);
      expect(
        await page
          .locator("canvas")
          .evaluate((el) => getComputedStyle(el).touchAction),
      ).toBe("pan-y");
      await client.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: touch(x, y + 80),
      });
      for (let i = 1; i <= 12; i++) {
        await client.send("Input.dispatchTouchEvent", {
          type: "touchMove",
          touchPoints: touch(x, y + 80 - i * 15),
        });
        // Native compositor scrolling needs an actual gesture duration; a burst
        // of timestamp-identical injected moves is not a physical finger swipe.
        await page.waitForTimeout(30);
      }
      await client.send("Input.dispatchTouchEvent", {
        type: "touchEnd",
        touchPoints: [],
      });
      await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(20);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    } finally {
      await context.close();
    }
  });

  test("model fetch failure preserves the photograph and retry can recover", async ({
    page,
  }) => {
    let fail = true;
    await page.route("**/orbit-calibration.gltf", (route) =>
      fail ? route.fulfill({ status: 404, body: "Missing" }) : route.continue(),
    );
    await page.goto(fixture);
    await expect(
      page.getByText("Static image · 3D viewer could not be loaded"),
    ).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("img")).toBeVisible({ timeout: 20000 });
    fail = false;
    await page.getByRole("button", { name: "Retry 3D view" }).click();
    await expect(
      page.getByRole("button", { name: "Reset vehicle view" }),
    ).toBeVisible({ timeout: 20000 });
  });

  test("WebGL context loss restores the static fallback", async ({ page }) => {
    await page.goto(fixture);
    await expect(
      page.getByRole("button", { name: "Reset vehicle view" }),
    ).toBeVisible({ timeout: 20000 });
    await page
      .locator("canvas")
      .evaluate((el) =>
        el.dispatchEvent(new Event("webglcontextlost", { cancelable: true })),
      );
    await expect(
      page.getByText("Static image · 3D viewer could not be loaded"),
    ).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("img")).toBeVisible({ timeout: 20000 });
  });

  test("unsupported WebGL is isolated from the rest of the page", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (
        this: HTMLCanvasElement,
        ...args: Parameters<typeof original>
      ) {
        if (String(args[0]).startsWith("webgl")) return null;
        return original.apply(this, args);
      } as typeof original;
    });
    await page.goto(fixture);
    await expect(
      page.getByText("Static image · 3D viewer could not be loaded"),
    ).toBeVisible({ timeout: 20000 });
    await expect(
      page.getByRole("heading", { name: "3D controls test" }),
    ).toBeVisible({ timeout: 20000 });
  });

  test("production dashboard loads the licensed alternative and retains the diagnostic Golf Plus identity", async ({
    page,
  }) => {
    const requests: string[] = [];
    page.on("request", (request) => requests.push(request.url()));
    await page.goto("/?demo=1");
    await expect(
      page.getByRole("button", { name: "Reset vehicle view" }),
    ).toBeVisible({ timeout: 25000 });
    await expect(
      page.getByText("Golf VIII illustration · diagnostic vehicle: Golf Plus"),
    ).toHaveCount(0);
    await page.getByRole("button", { name: /^Asset Credits/ }).click();
    const credits = page.getByRole("dialog", {
      name: "Asset Credits",
      exact: true,
    });
    await expect(credits).toContainText("not an exact Golf Plus");
    await expect(credits).toContainText("Mona x Supercars / Car2022");
    await expect(
      credits.getByRole("link", {
        name: "Volkswagen Golf 8. GTI (A8) on Sketchfab",
      }),
    ).toHaveAttribute("href", /e87d7c0f8937481db236529beb5ecab7/);
    await expect(
      credits.getByRole("link", { name: "CC BY 4.0", exact: true }),
    ).toHaveAttribute("href", "https://creativecommons.org/licenses/by/4.0/");
    await credits.getByRole("button", { name: "Close Asset Credits" }).click();
    await expect(
      page.getByRole("button", {
        name: "View Volkswagen Golf Plus details",
      }),
    ).toContainText("2.0 TDI");
    await expect(page.locator(".connection-loading")).toHaveCount(0);
    await page.screenshot({
      path: "test-results/vehicle-viewer-alternative-dashboard.png",
      fullPage: true,
    });
    await expect(page.locator(".hero-vehicle canvas")).toBeVisible();
    expect(
      requests.some((url) => url.endsWith("/models/golf-viii-gti.glb")),
    ).toBe(true);
    expect(requests.some((url) => url.includes("car-concept.glb"))).toBe(false);
    await expect(
      page.getByRole("button", { name: "New Diagnosis", exact: true }),
    ).toBeVisible({ timeout: 20000 });
  });

  test("the same Golf is shown while loading and in My Vehicle, without another vehicle download", async ({
    page,
  }) => {
    const models: string[] = [];
    let release: (() => void) | undefined;
    const loading = new Promise<void>((resolve) => {
      release = resolve;
    });
    page.on("request", (request) => {
      if (request.url().endsWith(".glb")) models.push(request.url());
    });
    await page.route("**/models/golf-viii-gti.glb", async (route) => {
      await loading;
      await route.continue();
    });
    await page.goto("/?demo=1", { waitUntil: "domcontentloaded" });
    await expect(
      page.locator(".hero-vehicle .vehicle-static img"),
    ).toBeVisible();
    await expect(
      page.locator(".hero-vehicle .vehicle-static img"),
    ).toHaveAttribute("src", "/images/golf-viii-gti-poster.png");
    release!();
    await expect(
      page.getByRole("button", { name: "Reset vehicle view" }),
    ).toBeVisible({ timeout: 25000 });
    await page
      .getByRole("button", { name: "View Volkswagen Golf Plus details" })
      .click();
    await expect(page.locator(".vehicle-profile canvas")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Reset vehicle view" }),
    ).toBeVisible({ timeout: 25000 });
    await page
      .locator(".vehicle-profile")
      .getByRole("button", { name: /^Asset Credits/ })
      .click();
    const credits = page.getByRole("dialog", {
      name: "Asset Credits",
      exact: true,
    });
    await expect(
      credits.getByRole("heading", {
        name: "Volkswagen Golf VIII GTI",
        exact: true,
      }),
    ).toBeVisible();
    await expect(credits).toContainText("not an exact Golf Plus");
    await credits.getByRole("button", { name: "Close Asset Credits" }).click();
    await expect(
      page
        .locator(".vehicle-profile")
        .getByRole("heading", { name: "Volkswagen Golf Plus" }),
    ).toBeVisible();
    expect(models.length).toBeGreaterThan(0);
    expect(
      models.every((url) => url.endsWith("/models/golf-viii-gti.glb")),
    ).toBe(true);
    await page.screenshot({
      path: "test-results/golf-my-vehicle.png",
      fullPage: true,
    });
  });
});
