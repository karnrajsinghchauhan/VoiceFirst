import { defineConfig } from "@playwright/test";

// /demo against the real engine: uvicorn serves the FastAPI app (mock providers), and the
// production web build talks to it over HTTP, as it does when deployed.
const PASSCODE = "playwright-demo-passcode";
const ENGINE = "http://127.0.0.1:8100";

export default defineConfig({
  testDir: "./tests/demo",
  timeout: 60_000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://localhost:3200",
    trace: "off",
    launchOptions: process.env.AV_CHROMIUM ? { executablePath: process.env.AV_CHROMIUM } : {},
  },
  webServer: [
    {
      command: "uv run --quiet uvicorn app.wiring.main:api_app --factory --port 8100",
      cwd: "../server",
      url: `${ENGINE}/healthz`,
      env: { AV_DEMO_PASSCODE: PASSCODE, AV_ENVIRONMENT: "test", AV_DATABASE_URL: "sqlite://" },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npx next start -p 3200",
      url: "http://localhost:3200",
      env: { AV_API_MODE: "http", AV_API_URL: ENGINE, AV_DEMO_PASSCODE: PASSCODE, AV_RATE_LIMIT_DEMO: "300", AV_RATE_LIMIT_GATE: "100" },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});

export { PASSCODE };
