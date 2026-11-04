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
  await page
    .getByText("Selection and stable identity", { exact: true })
    .click();
  for (const [name, description] of [
    ["Collection ID", "changing it can create duplicates"],
    ["Maximum notes", "It counts files, not companies, people or links"],
    ["Stable ID property (optional)", "brain_id: acme-meeting-001"],
    ["Company website", "when no main person is extracted"],
    ["Person’s company website", "not an automatic fallback"],
    ["Who can read these notes?", "not the public internet"],
  ]) {
    const button = page.getByRole("button", {
      name: "About " + name,
      exact: true,
    });
    await button.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".help-popover:popover-open")).toContainText(
      description,
    );
    await page.keyboard.press("Escape");
    await expect(page.locator(".help-popover:popover-open")).toHaveCount(0);
    await expect(button).toBeFocused();
  }
  await expect(page.locator(".mapping-example")).toContainText(
    "Property names must match exactly",
  );
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
    page.getByText(
      /The extracted name “Acme” matches “Acme” in Brain, but the website “kestrel.test” matches “Kestrel”/,
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      /Brain found one candidate, “Maya”, but a name alone does not prove/,
    ),
  ).toBeVisible();
  await expect(
    page.getByText("Email in Brain: maya@acme.test", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Matches extracted website", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open Kestrel in Brain" }),
  ).toHaveAttribute("href", "https://brain.example/companies/kestrel");
  await page.getByRole("button", { name: "All notes", exact: true }).click();
  const extracted = page.locator(".note[open] .extracted-clues").first();
  const known = page.locator(".note[open] .known-records").first();
  const extractedBox = await extracted.boundingBox();
  const knownBox = await known.boundingBox();
  expect(knownBox!.y).toBeGreaterThan(extractedBox!.y + extractedBox!.height);
  expect(extractedBox!.width).toBeGreaterThan(500);
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
    page.getByText("Company: Acme AI", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Settings changed. Run a new dry run before importing."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run dry run" }).click();
  await expect(
    page.getByRole("checkbox", { name: /I have reviewed/ }),
  ).toBeEnabled();
  // Resolve a suggested candidate, undo it, then select a searched identity.
  await page.getByRole("button", { name: "All notes", exact: true }).click();
  const conflict = page
    .locator(".note")
    .filter({ has: page.locator("summary strong", { hasText: "Conflict" }) });
  if (!(await conflict.getAttribute("open")))
    await conflict.locator("summary").click();
  await conflict
    .getByRole("button", { name: "Choose Acme", exact: true })
    .click();
  await expect(
    conflict.getByText("Confirmed by you", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "All notes", exact: true }).click();
  await conflict.locator("summary").click();
  await expect(
    conflict.getByText("Confirmed by you", { exact: true }),
  ).toBeVisible();
  await conflict.getByRole("button", { name: "Change choice" }).click();
  await conflict.getByLabel("Search another company").fill("Birch");
  await conflict
    .locator("article")
    .filter({ has: page.getByLabel("Search another company") })
    .getByRole("button", { name: "Search Brain" })
    .click();
  await conflict
    .getByRole("button", { name: "Choose Birch", exact: true })
    .click();
  await expect(conflict.locator(".choice-saved")).toContainText("Birch");
  const unknown = page
    .locator(".note")
    .filter({ has: page.locator("summary strong", { hasText: "Unknown" }) });
  await unknown.locator("summary").click();
  await unknown
    .getByRole("button", { name: "Leave unlinked", exact: true })
    .click();
  await expect(unknown.locator(".choice-saved")).toContainText(
    "Leave unlinked",
  );
  await unknown.getByRole("button", { name: "Change choice" }).click();
  await unknown
    .getByRole("button", { name: "Review later", exact: true })
    .click();
  await expect(unknown.locator(".choice-saved")).toContainText(
    "Review later in Sources",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByText("Selection and stable identity", { exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "About Stable ID property (optional)",
      exact: true,
    })
    .click();
  await expect(page.locator(".help-popover:popover-open")).toContainText(
    "Obsidian’s Properties panel",
  );
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({ path: "test-results/help-mobile.png" });
  await page.getByRole("button", { name: "Close explanation" }).click();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/review-choices-mobile.png",
    fullPage: true,
  });
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
