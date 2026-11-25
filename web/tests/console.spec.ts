import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, token: string): Promise<void> {
  await page.goto("/console");
  await page.getByLabel("API token").fill(token);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByTestId("role")).toBeVisible();
}

test("read-only role cannot see or operate the kill switch", async ({ page }) => {
  await signIn(page, "dev-ro-token");
  await expect(page.getByTestId("role")).toContainText("read_only");
  await expect(page.getByRole("navigation", { name: "Console" }).getByRole("link", { name: "Kill switch" })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Console" }).getByRole("link", { name: "Audit log" })).toHaveCount(0);
  await page.goto("/console/kill-switch");
  await expect(page.getByText("cannot operate the kill switch")).toBeVisible();
  await expect(page.getByRole("button", { name: "Engage kill switch" })).toHaveCount(0);
});

test("ops engages the kill switch with a reason and the audit log records it", async ({ page }) => {
  await signIn(page, "dev-ops-token");
  await page.getByRole("navigation", { name: "Console" }).getByRole("link", { name: "Kill switch" }).click();
  const engage = page.getByRole("button", { name: "Engage kill switch" });
  await expect(engage).toBeDisabled();
  await page.getByLabel("Reason (required)").fill("complaint spike on CLI 1600");
  await engage.click();
  await page.getByRole("dialog").getByRole("button", { name: "Engage" }).click();
  await expect(page.getByTestId("kill-switch-state")).toContainText("engaged");
  await expect(page.getByTestId("kill-switch-audit")).toContainText("kill_switch.engage");
  await expect(page.getByTestId("kill-switch-audit")).toContainText("complaint spike on CLI 1600");

  await page.getByRole("navigation", { name: "Console" }).getByRole("link", { name: "Audit log" }).click();
  await expect(page.getByTestId("audit-log")).toContainText("kill_switch.engage");
  await expect(page.getByTestId("audit-log")).toContainText("ops-user");

  await page.getByRole("navigation", { name: "Console" }).getByRole("link", { name: "Calls" }).click();
  await expect(page.getByTestId("live-calls")).toContainText("No live calls.");
});

test("unknown token is refused", async ({ page }) => {
  await page.goto("/console");
  await page.getByLabel("API token").fill("not-a-token");
  await page.getByRole("button", { name: "Sign in" }).click();
  // Scope to main: Next.js adds its own empty route-announcer alert.
  await expect(page.getByRole("main").getByRole("alert")).toContainText("unknown token");
});

test("eval report page shows a report or the empty state", async ({ page }) => {
  await signIn(page, "dev-auditor-token");
  await page.goto("/console/report");
  await expect(page.getByTestId("eval-report")).toBeVisible();
  await expect(page.getByTestId("eval-report").locator("iframe, code")).not.toHaveCount(0);
});
