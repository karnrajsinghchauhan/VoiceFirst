import { expect, test } from "@playwright/test";
import { PASSCODE } from "../../playwright.demo.config";

// /cars24: private, noindex, names no Agoda booking detail, and every source mark resolves.
test("the Cars24 note is gated, noindex and sourced", async ({ page }) => {
  await page.goto("/cars24");
  await expect(page).toHaveURL(/\/gate\?next=%2Fcars24/);
  await page.getByLabel("Passcode").fill(PASSCODE);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Cars24");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  await expect(page.locator("article")).toContainText("not affiliated with or endorsed by Cars24");
  await expect(page.locator("article")).toContainText("Cars24 ki taraf se");
  const ids = await page.locator('article a[href^="/docs/sources#"]').evaluateAll((as) =>
    as.map((a) => (a.getAttribute("href") ?? "").split("#")[1]),
  );
  expect(ids.length).toBeGreaterThanOrEqual(4);
  await page.goto("/docs/sources");
  for (const id of new Set(ids)) await expect(page.locator(`tr[id="${id}"]`)).toHaveCount(1);
});
