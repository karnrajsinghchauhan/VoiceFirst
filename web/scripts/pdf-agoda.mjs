// Prints the /agoda letter to reports/agoda-letter.pdf from the production build
// (`npm run build` first). It starts `next start`, passes the passcode gate like a
// reader would, and prints with the page's own print stylesheet.
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(web, "..", "reports", "agoda-letter.pdf");
const port = 3300;
const base = `http://localhost:${port}`;
const passcode = process.env.AV_DEMO_PASSCODE ?? "pdf-export-passcode";

async function waitFor(url, ms) {
  const until = Date.now() + ms;
  while (Date.now() < until) {
    try {
      if ((await fetch(url)).status < 500) return;
    } catch {
      // not listening yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`${url} did not start within ${ms} ms`);
}

const server = spawn("npx", ["next", "start", "-p", String(port)], {
  cwd: web,
  env: { ...process.env, AV_DEMO_PASSCODE: passcode, AV_API_MODE: "mock" },
  stdio: "ignore",
});
try {
  await waitFor(`${base}/gate`, 60_000);
  const browser = await chromium.launch(process.env.AV_CHROMIUM ? { executablePath: process.env.AV_CHROMIUM } : {});
  const page = await browser.newPage();
  await page.goto(`${base}/gate?next=%2Fagoda`);
  await page.getByLabel("Passcode").fill(passcode);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForURL(`${base}/agoda`);
  await page.emulateMedia({ media: "print" });
  mkdirSync(dirname(out), { recursive: true });
  await page.pdf({ path: out, format: "A4", printBackground: false, preferCSSPageSize: true });
  await browser.close();
  console.log(`wrote ${out}`);
} finally {
  server.kill();
}
