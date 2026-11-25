import { defineConfig } from "@playwright/test";

// Tests run against a production build served with the mock data layer,
// so they exercise the same bundle `npm run build` produces.
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3100",
    trace: "off",
    launchOptions: { executablePath: process.env.AV_CHROMIUM ?? "/opt/pw-browsers/chromium" },
  },
  webServer: {
    command: "npx next start -p 3100",
    url: "http://localhost:3100",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
