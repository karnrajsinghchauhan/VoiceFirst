import { expect, test } from "@playwright/test";
import { PASSCODE } from "../../playwright.demo.config";

// The /agoda letter: private, noindex, all twelve sections, and every source mark lands on
// a row of /docs/sources.
test("the letter is gated, noindex, complete and sourced", async ({ page }) => {
  await page.goto("/agoda");
  await expect(page).toHaveURL(/\/gate\?next=%2Fagoda/);
  await page.getByLabel("Passcode").fill(PASSCODE);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("A voice layer for Agoda");

  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  await expect(page.locator("article h2")).toHaveCount(12);
  await expect(page.locator("article")).toContainText("is not affiliated with or endorsed by Agoda");

  const ids = await page.locator('article a[href^="/docs/sources#"]').evaluateAll((as) =>
    as.map((a) => (a.getAttribute("href") ?? "").split("#")[1]),
  );
  expect(ids.length).toBeGreaterThan(10);
  await page.goto("/docs/sources");
  for (const id of new Set(ids)) await expect(page.locator(`tr[id="${id}"]`)).toHaveCount(1);
});
