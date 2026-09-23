import { expect, test, type Page } from "@playwright/test";

const desktopWidths = [1920, 680];
const constrainedWidths = [412, 679];

async function openStatus(page: Page, width: number) {
  await page.setViewportSize({ width, height: 915 });
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByTestId(width <= 679 ? "shell-identity-header" : "shell-identity-rail"),
  ).toHaveText("FPLPatternRec");
  await expect(page.getByRole("heading", { name: "System status" })).toBeVisible();
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
}

test("uses the shell layout at desktop and breakpoint widths", async ({ page }) => {
  for (const width of desktopWidths) {
    await openStatus(page, width);
    await expect(page.getByRole("complementary", { name: "Primary navigation" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Open navigation menu" })).toBeHidden();
    await expect(page.locator("main")).toHaveCSS("padding-left", "24px");
    await expectNoHorizontalOverflow(page);
  }

  for (const width of constrainedWidths) {
    await openStatus(page, width);
    await expect(page.getByRole("complementary", { name: "Primary navigation" })).toBeHidden();
    await expect(page.getByRole("button", { name: "Open navigation menu" })).toBeVisible();
    await expect(page.locator("main")).toHaveCSS("padding-left", "16px");
    await expectNoHorizontalOverflow(page);
  }
});

test("supports drawer focus containment and each dismissal path", async ({ page }) => {
  await openStatus(page, 412);
  const trigger = page.getByRole("button", { name: "Open navigation menu" });
  await trigger.click();

  const drawer = page.getByRole("dialog");
  const close = drawer.getByRole("button", { name: "Close navigation menu" });
  const status = drawer.getByRole("link", { name: "Status" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("heading", { name: "Navigation" })).toBeVisible();
  await expect(close).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(status).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await close.click();
  await expect(drawer).toBeHidden();
  await expect(trigger).toBeFocused();

  await trigger.click();
  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(trigger).toBeFocused();

  await trigger.click();
  await page.locator('[data-testid="drawer-backdrop"]').click({ position: { x: 380, y: 450 } });
  await expect(drawer).toBeHidden();
  await expect(trigger).toBeFocused();

  await trigger.click();
  await status.click();
  await expect(page).toHaveURL(/\/$/);
  await expect(drawer).toBeHidden();
});

test("removes shell motion when reduced motion is requested", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openStatus(page, 412);
  await page.getByRole("button", { name: "Open navigation menu" }).click();
  await expect(page.locator('[data-testid="drawer-backdrop"]')).toHaveCSS("transition-duration", "0s");
  await expect(page.getByRole("dialog")).toHaveCSS("transition-duration", "0s");
});

test("keeps the status shell available when the backend is unavailable", async ({ page }) => {
  await page.route("**/api/health", (route) => route.abort("connectionrefused"));
  await openStatus(page, 680);
  await expect(page.getByRole("alert")).toContainText("Backend unavailable");
  await expect(page.getByRole("link", { name: "Status" }).first()).toHaveAttribute("href", "/");
});
