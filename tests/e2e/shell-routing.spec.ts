import { expect, test } from "@playwright/test";

test("shows an in-shell Not Found page for an unknown route", async ({
  page,
}) => {
  await page.setViewportSize({ width: 680, height: 915 });
  await page.goto("/not-a-page");

  await expect(page).toHaveURL(/\/not-a-page$/);
  await expect(page.getByRole("heading", { name: "Page not found", level: 1 })).toBeVisible();
  await expect(
    page.getByText("The page you requested could not be found."),
  ).toBeVisible();

  await expect(page.getByTestId("shell-identity-rail")).toHaveText("FPLPatternRec");
  await expect(page.getByRole("complementary", { name: "Primary navigation" })).toBeVisible();
  await expect(page.getByRole("main")).toBeVisible();

  await expect(page.getByRole("heading", { name: "System status" })).toHaveCount(0);
  await expect(page.locator('a[href="/not-a-page"]')).toHaveCount(0);
});
