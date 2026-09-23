import { expect, test } from "@playwright/test";

test("shows the live backend health status", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("shell-identity-rail")).toHaveText("FPLPatternRec");
  await expect(page.getByRole("heading", { name: "System status" })).toBeVisible();
  await expect(page.getByRole("status")).toHaveText(/healthy/);
});

test("shows an accessible error when the backend is unavailable", async ({ page }) => {
  await page.route("**/api/health", (route) => route.abort("connectionrefused"));
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("Backend unavailable");
});
