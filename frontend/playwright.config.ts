import { defineConfig, devices } from "@playwright/test";

// The end-to-end test runs against an already running stack (e.g. `docker compose up`),
// so the app's URL must be given; there is no default.
const baseURL = process.env.E2E_BASE_URL;
if (!baseURL) {
  throw new Error("E2E_BASE_URL is not set, e.g. E2E_BASE_URL=http://127.0.0.1:3000");
}

export default defineConfig({
  testDir: "./e2e",
  // Message delivery goes through the provider simulator's lifecycle, which takes seconds.
  timeout: 90_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  reporter: "list",
  use: { baseURL, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
