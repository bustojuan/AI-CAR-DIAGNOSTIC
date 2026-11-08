import { test, expect } from "@playwright/test";

test("engine compartment photo supports inspection, zoom/pan/reset, truthful markers and draft-only actions", async ({
  page,
}) => {
  test.setTimeout(60000);
  const posts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST") posts.push(request.url());
  });
  await page.goto("/?demo=1");
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  const dialog = page.getByRole("dialog", { name: "Engine Bay" });
  const image = dialog.getByRole("img", {
    name: /Complete engine compartment/,
  });
  await expect(image).toBeVisible();
  await expect
    .poll(() => image.evaluate((img: HTMLImageElement) => img.naturalWidth))
    .toBe(2560);
  await expect(
    dialog.getByText(
      "Illustrative engine bay — component layout may differ from your vehicle.",
    ),
  ).toBeVisible();
  await expect(
    dialog.getByRole("link", { name: /CC BY-NC-SA 2.0/ }),
  ).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: /in photograph/ }),
  ).toHaveCount(3);
  await dialog
    .getByRole("button", {
      name: "Inspect Coolant expansion tank in photograph",
    })
    .click();
  await expect(
    dialog.getByRole("heading", {
      name: "Coolant expansion tank",
      exact: true,
    }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Zoom in engine bay" }).click();
  await expect(dialog.getByLabel("Engine bay zoom")).toHaveText("125%");
  const viewport = dialog.getByRole("region", {
    name: "Engine compartment photograph",
  });
  const box = (await viewport.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.8);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.7, {
    steps: 10,
  });
  await page.mouse.up();
  const transform = await dialog
    .locator(".engine-photo-transform")
    .getAttribute("style");
  expect(transform).not.toContain("translate(0px, 0px)");
  await dialog
    .getByRole("button", { name: "Reset engine bay photograph" })
    .click();
  await expect(dialog.getByLabel("Engine bay zoom")).toHaveText("100%");
  await dialog.getByRole("button", { name: "Battery General topic" }).click();
  await expect(
    dialog.getByRole("heading", { name: "Battery", exact: true }),
  ).toBeVisible();
  await expect(
    dialog.getByText(/No vehicle-specific technical evidence/),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/engine-bay-photo-desktop.png",
    fullPage: true,
  });
  await dialog
    .getByRole("button", { name: "Ask AI About This Component" })
    .click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel("Describe the symptoms")).toHaveValue(
    /battery.*No component fault has been confirmed/,
  );
  expect(posts).toEqual([]);
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  await dialog
    .getByRole("button", { name: "Air filter housing Photo location" })
    .click();
  await dialog.getByRole("button", { name: "Find Related Parts" }).click();
  await expect(
    page.getByLabel("Which component are you looking for?"),
  ).toHaveValue("air filter housing");
  expect(posts).toEqual([]);
});

test("an actual hood ray hit opens the photo without moving a panel and returns to the exterior", async ({
  page,
}) => {
  test.setTimeout(60000);
  await page.goto("/?demo=1");
  await expect(
    page.getByRole("button", { name: "Reset vehicle view" }),
  ).toBeVisible({ timeout: 30000 });
  const canvas = page.locator(".hero-vehicle canvas");
  // Readiness mounts controls; allow their first frame/layout to settle before
  // searching actual ray hits. React applies hover state after the input event.
  await canvas.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  const box = (await canvas.boundingBox())!;
  let point: { x: number; y: number } | null = null;
  for (const y of [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]) {
    for (const x of [
      0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7,
      0.75, 0.8,
    ]) {
      await page.mouse.move(box.x + box.width * x, box.y + box.height * y);
      await canvas.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => resolve()),
          ),
      );
      if (
        await canvas.evaluate((element) =>
          element.classList.contains("has-pick-target"),
        )
      ) {
        point = { x: box.x + box.width * x, y: box.y + box.height * y };
        break;
      }
    }
    if (point) break;
  }
  expect(
    point,
    "A real visible hood surface must be selectable",
  ).not.toBeNull();
  await page.screenshot({
    path: "test-results/exterior-hood-ray-hit.png",
    fullPage: true,
  });
  await page.mouse.click(point!.x, point!.y);
  const dialog = page.getByRole("dialog", { name: "Engine Bay" });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("img", { name: /Complete engine compartment/ }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Back to Vehicle" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(canvas).toBeVisible();
});

test("mobile photo inspection supports two-finger zoom and fits the screen", async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?demo=1");
  await page.getByRole("button", { name: "Explore Engine Bay" }).click();
  const dialog = page.getByRole("dialog", { name: "Engine Bay" });
  const viewport = dialog.getByRole("region", {
    name: "Engine compartment photograph",
  });
  await expect(
    dialog.getByRole("button", { name: "Zoom in engine bay" }),
  ).toBeEnabled();
  await viewport.scrollIntoViewIfNeeded();
  const box = (await viewport.boundingBox())!;
  const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  const cdp = await context.newCDPSession(page);
  const touches = (distance: number) =>
    [-1, 1].map((sign, index) => ({
      x: center.x + sign * distance,
      y: center.y,
      id: index + 1,
    }));
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: touches(30),
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: touches(65),
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await expect
    .poll(async () =>
      Number(
        (await dialog.getByLabel("Engine bay zoom").textContent())!.replace(
          "%",
          "",
        ),
      ),
    )
    .toBeGreaterThan(100);
  await expect
    .poll(() =>
      dialog.evaluate((element) => element.scrollWidth <= element.clientWidth),
    )
    .toBe(true);
  await page.screenshot({
    path: "test-results/engine-bay-photo-mobile.png",
    fullPage: true,
  });
  await dialog.getByRole("button", { name: "Back to Vehicle" }).click();
  await expect(dialog).not.toBeVisible();
});
