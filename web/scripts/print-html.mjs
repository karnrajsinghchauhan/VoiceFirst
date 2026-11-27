// Prints standalone HTML files to PDF with Playwright's Chromium (used for docs/sales).
// Usage: node scripts/print-html.mjs <in.html> <out.pdf> [<in.html> <out.pdf> ...]
import { chromium } from "@playwright/test";
import { pathToFileURL } from "node:url";

const args = process.argv.slice(2);
if (args.length === 0 || args.length % 2 !== 0) throw new Error("pass pairs of <in.html> <out.pdf>");
const browser = await chromium.launch(process.env.AV_CHROMIUM ? { executablePath: process.env.AV_CHROMIUM } : {});
const page = await browser.newPage();
for (let i = 0; i < args.length; i += 2) {
  await page.goto(pathToFileURL(args[i]).href);
  await page.pdf({ path: args[i + 1], format: "A4", margin: { top: "18mm", bottom: "20mm", left: "18mm", right: "18mm" } });
  console.log(`wrote ${args[i + 1]}`);
}
await browser.close();
