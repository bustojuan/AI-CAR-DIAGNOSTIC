// Real UI screenshots in explicit browser-only demo mode. No video/provider calls.
import {
  chromium,
  expect,
} from "../frontend/node_modules/@playwright/test/index.mjs";
import { createServer } from "../frontend/node_modules/vite/dist/node/index.js";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const output = path.join(root, "docs/screenshots");
const server = await createServer({
  root: path.join(root, "frontend"),
  configFile: path.join(root, "frontend/vite.config.ts"),
  server: { host: "127.0.0.1", port: 15175, strictPort: true },
});
let browser;
try {
  await mkdir(output, { recursive: true });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1200 },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });
  const apiCalls = [],
    errors = [],
    files = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/"))
      apiCalls.push(request.method());
  });
  async function shot(filename) {
    await page.evaluate(() => document.fonts.ready);
    await page.locator("img").evaluateAll(async (images) => {
      for (const image of images) {
        if (
          image.getClientRects().length &&
          getComputedStyle(image).visibility !== "hidden"
        )
          await image.decode();
      }
      await new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      );
    });
    const visibleText = await page.locator("body").innerText();
    if (
      /npg_[A-Za-z0-9]{10,}|sk-proj-[A-Za-z0-9_-]{20,}|@(?:gmail|accenture)\./i.test(
        visibleText,
      )
    )
      throw new Error("Sensitive text detected; refusing screenshot");
    await page.screenshot({ path: path.join(output, filename) });
    files.push(filename);
  }
  await page.goto("http://127.0.0.1:15175/?demo=1");
  await expect(page.getByText("Demo mode", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Reset vehicle view" }),
  ).toBeVisible({ timeout: 45000 });
  await shot("01-home.png");
  await page
    .getByRole("button", { name: "New Diagnosis", exact: true })
    .click();
  await page
    .getByLabel("Describe the symptoms")
    .fill("My car struggles to start when cold and starts normally when warm.");
  await page.getByRole("button", { name: "Send consultation" }).click();
  const openReport = page.getByRole("button", {
    name: "Open full report",
    exact: true,
  });
  await expect(openReport).toBeEnabled();
  await shot("02-diagnosis.png");
  await openReport.click();
  await expect(
    page.getByRole("heading", { name: "Recommended checks" }),
  ).toBeVisible();
  await shot("03-report.png");
  await page.getByRole("link", { name: "History", exact: true }).click();
  await page
    .getByRole("button", { name: "Mark as Resolved", exact: true })
    .click();
  const confirmation = page.getByRole("dialog", {
    name: "Mark this case as resolved?",
  });
  await confirmation
    .getByLabel("Resolution note (optional)")
    .fill(
      "Demonstration of user-reported resolution only; no real repair was performed.",
    );
  await confirmation
    .getByRole("button", { name: "Confirm Resolution", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Reopen Diagnosis", exact: true }),
  ).toBeEnabled();
  await shot("04-history.png");
  await page.getByRole("link", { name: "Parts", exact: true }).click();
  await page
    .getByLabel("Which component are you looking for?")
    .fill("glow plugs");
  await page
    .getByRole("button", { name: "Search candidates", exact: true })
    .click();
  await expect(
    page.getByText("Synthetic glow-plug example", { exact: true }),
  ).toBeVisible();
  await shot("05-parts.png");
  await page.getByRole("link", { name: "My Vehicle", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Reset vehicle view" }),
  ).toBeVisible({ timeout: 45000 });
  await shot("06-vehicle.png");
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await page
    .getByRole("button", { name: "Explore Engine Bay", exact: true })
    .click();
  const inspection = page.getByRole("dialog", {
    name: "Engine Bay",
    exact: true,
  });
  await expect(
    inspection.getByRole("img", { name: /Complete engine compartment/ }),
  ).toBeVisible();
  await expect(
    inspection.getByRole("link", { name: /CC BY-NC-SA 2.0/ }),
  ).toBeVisible();
  await shot("07-engine-bay.png");
  if (apiCalls.length || errors.length)
    throw new Error("Unexpected backend call or browser runtime error");
  await writeFile(
    path.join(output, "capture-metadata.json"),
    JSON.stringify(
      {
        mode: "explicit_browser_demo",
        viewport: [1440, 1200],
        real_ui_screenshots: true,
        synthetic_reports_and_parts: true,
        video_created: false,
        api_calls: 0,
        browser_errors: 0,
        console_errors: 0,
        files,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    JSON.stringify({
      screenshots: files.length,
      api_calls: 0,
      browser_errors: 0,
      video_created: false,
    }),
  );
} finally {
  if (browser) await browser.close();
  await server.close();
}
