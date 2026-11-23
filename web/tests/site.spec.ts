import { expect, test } from "@playwright/test";
import { DISCLAIMER } from "../src/components/disclaimer";
import { DOCS } from "../src/content/docs-nav";

test("marketing page shows the disclaimer and the five promises", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("disclaimer")).toHaveText(DISCLAIMER);
  const promises = page.getByTestId("promises").locator("li");
  await expect(promises).toHaveCount(5);
  for (const id of ["P1", "P2", "P3", "P4", "P5"]) {
    await expect(page.getByTestId("promises")).toContainText(id);
  }
  await expect(page.getByTestId("demo-call")).toContainText("Simulated call, mock providers");
  await expect(page.getByTestId("demo-call")).toContainText("main Agoda ki taraf se ek AI assistant bol rahi hoon");
});

for (const doc of DOCS) {
  test(`docs page /docs/${doc.slug} renders`, async ({ page }) => {
    const res = await page.goto(`/docs/${doc.slug}`);
    expect(res?.status()).toBe(200);
    await expect(page.locator("article h1")).toBeVisible();
    await expect(page.getByTestId("disclaimer")).toHaveText(DISCLAIMER);
  });
}

test("compliance docs say engineering guidance, not legal advice", async ({ page }) => {
  await page.goto("/docs/compliance");
  await expect(page.locator("article")).toContainText("engineering guidance, not legal advice");
});
