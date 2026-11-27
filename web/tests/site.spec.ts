import { expect, test } from "@playwright/test";
import { disclaimer } from "../src/config/brand";
import { DOCS } from "../src/content/docs-nav";

test("home shows the recorded call, the five promises and the disclaimer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("disclaimer")).toHaveText(disclaimer());
  await expect(page.locator("#promises li")).toHaveCount(5);
  await expect(page.getByTestId("transcript")).toContainText("Kya main");
  await expect(page.getByTestId("timeline")).toContainText("GateClearance issued");
});

for (const doc of DOCS) {
  test(`docs page /docs/${doc.slug} renders`, async ({ page }) => {
    const res = await page.goto(doc.slug ? `/docs/${doc.slug}` : "/docs");
    expect(res?.status()).toBe(200);
    await expect(page.locator("article h1")).toBeVisible();
    await expect(page.getByTestId("disclaimer")).toHaveText(disclaimer());
  });
}

test("compliance docs say engineering guidance, not legal advice", async ({ page }) => {
  await page.goto("/docs/compliance");
  await expect(page.locator("article")).toContainText("engineering guidance, not legal advice");
});
