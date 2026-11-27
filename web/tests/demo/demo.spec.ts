import { expect, test, type Page } from "@playwright/test";
import { PASSCODE } from "../../playwright.demo.config";

// S10 DONE: every scenario runs on the real engine, and the kill switch visibly stops a
// running campaign in under 5 s.
const SCENARIOS: { id: string; outcome: string; whatsapp: boolean; crm: boolean }[] = [
  { id: "failed_upi", outcome: "link_sent", whatsapp: true, crm: false },
  { id: "confirmation", outcome: "details_confirmed", whatsapp: false, crm: true },
  { id: "angry_refund", outcome: "handed_off", whatsapp: false, crm: true },
  { id: "stop_calling", outcome: "opted_out", whatsapp: false, crm: false },
  { id: "child_answers", outcome: "minor_on_line", whatsapp: false, crm: false },
  { id: "card_number", outcome: "link_sent", whatsapp: true, crm: false },
  { id: "cars24_inspection", outcome: "details_confirmed", whatsapp: false, crm: true },
  { id: "cars24_reschedule", outcome: "handed_off", whatsapp: false, crm: true },
];

async function enter(page: Page): Promise<void> {
  await page.goto("/demo");
  await expect(page).toHaveURL(/\/gate/);
  await page.getByLabel("Passcode").fill(PASSCODE);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { name: "Live demo" })).toBeVisible();
}

test("the demo is private: no passcode, no page", async ({ page, request }) => {
  await page.goto("/demo");
  await expect(page).toHaveURL(/\/gate\?next=%2Fdemo/);
  const api = await request.post("/api/demo/run", { data: { scenario: "failed_upi" } });
  expect(api.status()).toBe(401);
  await page.getByLabel("Passcode").fill("wrong-passcode");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("alert")).toContainText("did not match");
});

for (const s of SCENARIOS) {
  test(`scenario ${s.id} runs through every gate and ends ${s.outcome}`, async ({ page }) => {
    await enter(page);
    await page.getByTestId(`scenario-${s.id}`).check();
    await page.getByTestId("call").click();
    const run = page.getByTestId("run");
    // Watch the timeline fill live before skipping to the end.
    await expect(page.getByTestId("timeline").locator('li[data-kind="holdout"]')).toBeVisible();
    await page.getByTestId("skip").click();
    await expect(run).toHaveAttribute("data-done", "true");
    // A live engine run, not a recorded one (recorded runs are rec_*).
    await expect(run).toHaveAttribute("data-run-id", /^demo_/);
    if (s.id === "failed_upi") await page.screenshot({ path: "test-results/demo-failed_upi.png", fullPage: true });

    const timeline = page.getByTestId("timeline");
    await expect(timeline.locator('li[data-kind="gate"][data-status="pass"]')).toHaveCount(10);
    await expect(timeline.locator('li[data-kind="clearance"]')).toHaveCount(1);
    await expect(timeline.locator('li[data-kind="disclosure"][data-status="pass"]')).toHaveCount(1);
    await expect(timeline.locator('li[data-kind="end"]')).toContainText(s.outcome);

    const transcript = page.getByTestId("transcript");
    await expect(transcript.locator("li").first()).toContainText("AI");
    await expect(transcript).not.toContainText("4111");
    await expect(page.getByTestId("qa-score")).toContainText("100 / 100");
    await expect(page.getByTestId("whatsapp")).toHaveCount(s.whatsapp ? 1 : 0);
    await expect(page.getByTestId("crm")).toHaveCount(s.crm ? 1 : 0);
  });
}

test("the kill switch stops a running campaign in under 5 s, and releases", async ({ page }) => {
  await enter(page);
  const campaign = page.getByTestId("campaign");
  await page.getByTestId("start-campaign").click();
  await expect(campaign).toHaveAttribute("data-state", "running");
  await expect(page.getByTestId("placed")).not.toHaveText("0", { timeout: 10_000 });

  await page.getByTestId("kill").click();
  await expect(campaign).toHaveAttribute("data-state", "stopped", { timeout: 5_000 });
  const stopMs = Number(await page.getByTestId("stop-ms").textContent());
  expect(stopMs).toBeLessThan(5_000);

  const placed = await page.getByTestId("placed").textContent();
  await page.waitForTimeout(2_500);
  await expect(page.getByTestId("placed")).toHaveText(placed ?? "");

  await page.getByTestId("release").click();
  await expect(campaign).toHaveAttribute("data-state", "idle");
  await page.getByTestId("scenario-failed_upi").check();
  await page.getByTestId("call").click();
  await page.getByTestId("skip").click();
  await expect(page.getByTestId("timeline").locator('li[data-kind="end"]')).toContainText("link_sent");
});
