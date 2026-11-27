import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Every public page: the disclaimer, no untagged numeric claim, no 404, and WCAG 2.1 AA.
const PAGES = [
  "/",
  "/product",
  "/security",
  "/pricing",
  "/changelog",
  "/company",
  "/status",
  "/docs",
  "/docs/sources",
  "/docs/compliance",
  "/legal/terms",
  "/legal/privacy",
  "/legal/dpa",
  "/legal/subprocessors",
  "/legal/aup",
];

// A percentage or a money amount is a claim: it must sit inside a source, measurement,
// product specification or estimate mark.
const CLAIM = /(\d[\d,.]*\s?%)|((₹|Rs\.?|USD|US\$|\$)\s?\d)/;

for (const path of PAGES) {
  test(`${path}: disclaimer, sourced claims, accessible`, async ({ page }) => {
    const res = await page.goto(path);
    expect(res?.status()).toBe(200);
    await expect(page.locator("footer[data-site-footer]")).toContainText("Not affiliated with or endorsed by Agoda");

    const untagged = await page.evaluate((pattern) => {
      const re = new RegExp(pattern);
      const out: string[] = [];
      const walker = document.createTreeWalker(document.querySelector("main") ?? document.body, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const text = n.textContent ?? "";
        const el = n.parentElement;
        if (!el || !re.test(text)) continue;
        if (el.closest("[data-claim], code, pre, [data-testid='transcript']")) continue;
        out.push(text.trim().slice(0, 120));
      }
      return out;
    }, CLAIM.source);
    expect(untagged, `untagged claims on ${path}`).toEqual([]);

    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(axe.violations.map((v) => `${v.id}: ${v.nodes.length} node(s)`), `axe on ${path}`).toEqual([]);
  });
}

test("security.txt follows RFC 9116", async ({ request }) => {
  const res = await request.get("/.well-known/security.txt");
  expect(res.status()).toBe(200);
  const body = await res.text();
  expect(body).toMatch(/^Contact: mailto:/m);
  expect(body).toMatch(/^Expires: \d{4}-/m);
});
