import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  use: { viewport: { width: 1280, height: 1000 }, trace: "retain-on-failure" },
  workers: 1,
});
