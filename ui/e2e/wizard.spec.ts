import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { spawn, execFileSync, type ChildProcess } from "node:child_process";
let server: ChildProcess;
let info: { url: string; vault: string };
test.beforeAll(async () => {
  const python = execFileSync(
    "uv",
    ["run", "python", "-c", "import sys; print(sys.executable)"],
    { cwd: "..", encoding: "utf8" },
  ).trim();
  server = spawn(python, ["scripts/ui_test_server.py"], {
    cwd: "..",
    stdio: ["ignore", "pipe", "pipe"],
  });
  info = await new Promise((resolve, reject) => {
    let buffer = "";
    server.stdout!.on("data", (chunk) => {
      buffer += chunk.toString();
      if (buffer.includes("\n")) {
        try {
          resolve(JSON.parse(buffer.split("\n")[0]));
        } catch (e) {
          reject(e);
        }
      }
    });
    server.on("exit", (code) => reject(new Error("Server exited " + code)));
    setTimeout(() => reject(new Error("Server not ready")), 15000);
  });
});
test.afterAll(async () => {
  if (!server || server.exitCode !== null) return;
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => {
      server.kill("SIGKILL");
      reject(new Error("Synthetic server did not stop"));
    }, 5000);
    server.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
    server.kill("SIGINT");
  });
});
test("select, map, preview, filter, invalidate and import with explicit confirmation", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(info.url);
  await page
    .getByRole("button", { name: "Connect to Brain", exact: true })
    .click();
  await expect(
    page.getByText("Browser test firm", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Vault folder", { exact: true }).fill(info.vault);
  await page.getByRole("button", { name: "Load folders" }).click();
  await page.getByRole("checkbox", { name: /Notes\s*3 files/ }).check();
  await page.getByLabel("Note type for Notes").selectOption("organization");
  await page.getByRole("button", { name: "Run dry run" }).click();
  await expect(
    page.getByRole("heading", { name: "Your dry run" }),
  ).toBeVisible();
  await expect(
    page.getByText("Nothing has been imported by this dry run.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.locator(".note")).toHaveCount(3);
  await page.reload();
  await expect(
    page.getByRole("checkbox", { name: /Notes\s*3 files/ }),
  ).toBeChecked();
  await expect(page.getByLabel("Note type for Notes")).toHaveValue(
    "organization",
  );
  await page.getByRole("button", { name: "Needs review", exact: true }).click();
  await expect(page.locator(".note")).toHaveCount(1);
  await page.locator(".note summary").click();
  await expect(
    page.getByText("Synthetic browser fixture: identifier check.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "All notes", exact: true }).click();
  await page.getByLabel("Search preview notes").fill("Unknown");
  await expect(page.locator(".note")).toHaveCount(1);
  await page.getByLabel("Search preview notes").fill("");
  await expect(
    page.getByRole("button", { name: "Import 3 notes", exact: true }),
  ).toBeDisabled();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: "test-results/preview-desktop.png",
    fullPage: true,
  });
  await page.getByLabel("Company name", { exact: true }).fill("Company");
  await expect(
    page.getByText("Settings changed. Run a new dry run before importing."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run dry run" }).click();
  await expect(
    page.getByRole("checkbox", { name: /I have reviewed/ }),
  ).toBeEnabled();
  await page.getByRole("checkbox", { name: /I have reviewed/ }).check();
  await page
    .getByRole("button", { name: "Import 3 notes", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "3 notes processed" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "test-results/complete-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(errors).toEqual([]);
});
