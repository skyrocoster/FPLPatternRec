import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { retryAxeWhenBusy } from "./axe-busy-retry";

const STORYBOOK_ORIGIN = "http://127.0.0.1:6017";
const STORYBOOK_ROOT_SELECTOR = "#storybook-root";
const STORY_PREFIX = "production-application-shell-app-shell";
const STORY_IDS = {
  wideHealthy: `${STORY_PREFIX}--wide-healthy`,
  constrainedClosed: `${STORY_PREFIX}--constrained-closed`,
  constrainedOpen: `${STORY_PREFIX}--constrained-open`,
  loading: `${STORY_PREFIX}--loading`,
  healthy: `${STORY_PREFIX}--healthy`,
  unavailable: `${STORY_PREFIX}--unavailable`,
  unexpectedFailure: `${STORY_PREFIX}--unexpected-failure-try-again`,
  unexpectedFailureBrowserProof: `${STORY_PREFIX}--unexpected-failure-browser-proof`,
} as const;

function storyUrl(storyId: string) {
  return `${STORYBOOK_ORIGIN}/iframe.html?id=${storyId}&viewMode=story`;
}

async function openStory(
  page: Page,
  storyId: string,
  width: number,
  height: number,
) {
  await page.setViewportSize({ width, height });
  await page.goto(storyUrl(storyId));
  await expect(page.locator(STORYBOOK_ROOT_SELECTOR)).toBeVisible();
}

async function openDrawer(page: Page) {
  const trigger = page.getByRole("button", { name: "Open navigation menu" });
  await expect(trigger).toBeVisible();
  await trigger.focus();
  await trigger.click();

  const dialog = page.getByRole("dialog");
  const close = page.getByRole("button", { name: "Close navigation menu" });
  await expect(dialog).toBeVisible();
  await expect(page.getByRole("heading", { name: "Navigation" })).toBeVisible();
  await expect(close).toBeVisible();
  await expect(close).toBeFocused();

  return { close, dialog, trigger };
}

async function focusIsInside(
  page: Page,
  container: ReturnType<Page["getByRole"]>,
) {
  return container.evaluate((element) =>
    element.contains(document.activeElement),
  );
}

async function modalState(page: Page) {
  return page.evaluate(() => ({
    bodyInlineOverflow: document.body.style.overflow,
    bodyOverflow: getComputedStyle(document.body).overflow,
    documentInlineOverflow: document.documentElement.style.overflow,
    documentOverflow: getComputedStyle(document.documentElement).overflow,
    inertCount: document.querySelectorAll("[data-base-ui-inert]").length,
  }));
}

async function expectApplicationAxeClean(page: Page) {
  const results = await retryAxeWhenBusy(page, () =>
    new AxeBuilder({ page }).include(STORYBOOK_ROOT_SELECTOR).analyze(),
  );
  expect(results.violations).toEqual([]);
}

async function hasResponsiveBreakpointRule(page: Page) {
  return page.evaluate(() =>
    Array.from(document.styleSheets).some((sheet) => {
      try {
        return Array.from(sheet.cssRules).some((rule) => {
          const cssText = rule.cssText.replace(/\s+/g, "");
          return cssText.includes("max-width:679px");
        });
      } catch {
        return false;
      }
    }),
  );
}

for (const layoutCase of [
  {
    height: 1080,
    mode: "desktop",
    storyId: STORY_IDS.wideHealthy,
    width: 1920,
  },
  {
    height: 915,
    mode: "constrained",
    storyId: STORY_IDS.constrainedClosed,
    width: 412,
  },
  {
    height: 915,
    mode: "constrained",
    storyId: STORY_IDS.constrainedClosed,
    width: 679,
  },
  { height: 915, mode: "desktop", storyId: STORY_IDS.wideHealthy, width: 680 },
]) {
  test(`uses ${layoutCase.mode} shell mode at ${layoutCase.width}px`, async ({
    page,
  }) => {
    await openStory(
      page,
      layoutCase.storyId,
      layoutCase.width,
      layoutCase.height,
    );

    const sidebar = page.getByRole("complementary", {
      name: "Primary navigation",
    });
    const trigger = page.getByRole("button", { name: "Open navigation menu" });

    if (layoutCase.mode === "desktop") {
      await expect(sidebar).toBeVisible();
      await expect(trigger).toBeHidden();
    } else {
      await expect(sidebar).toBeHidden();
      await expect(trigger).toBeVisible();
    }

    await expect
      .poll(() =>
        page.evaluate(() => window.matchMedia("(max-width: 679px)").matches),
      )
      .toBe(layoutCase.width <= 679);
    await expect.poll(() => hasResponsiveBreakpointRule(page)).toBe(true);
  });
}

test("contains drawer focus and restores it after Close", async ({ page }) => {
  await openStory(page, STORY_IDS.constrainedClosed, 412, 915);
  const before = await modalState(page);
  const { close, dialog, trigger } = await openDrawer(page);

  for (const key of ["Tab", "Tab", "Shift+Tab", "Tab"]) {
    await page.keyboard.press(key);
    await expect.poll(() => focusIsInside(page, dialog)).toBe(true);
  }

  const during = await modalState(page);
  expect(during.inertCount).toBeGreaterThan(0);

  await close.click();
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
  await expect.poll(async () => (await modalState(page)).inertCount).toBe(0);
  const after = await modalState(page);
  expect(after.bodyInlineOverflow).toBe(before.bodyInlineOverflow);
  expect(after.documentInlineOverflow).toBe(before.documentInlineOverflow);
});

test("dismisses the drawer with Escape and restores trigger focus", async ({
  page,
}) => {
  await openStory(page, STORY_IDS.constrainedClosed, 412, 915);
  const { dialog, trigger } = await openDrawer(page);

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("dismisses the drawer by scrim activation", async ({ page }) => {
  await openStory(page, STORY_IDS.constrainedClosed, 412, 915);
  const { dialog, trigger } = await openDrawer(page);
  const backdrop = page.getByTestId("drawer-backdrop");

  await expect(backdrop).toBeVisible();
  const backdropBox = await backdrop.boundingBox();
  expect(backdropBox).not.toBeNull();
  if (!backdropBox) {
    throw new Error("Drawer backdrop has no visible bounding box");
  }
  await backdrop.click({ position: { x: backdropBox.width - 4, y: 4 } });
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("dismisses the drawer when Status is selected", async ({ page }) => {
  await openStory(page, STORY_IDS.constrainedClosed, 412, 915);
  const { dialog } = await openDrawer(page);

  await dialog
    .getByRole("link", { name: "Status" })
    .click({ noWaitAfter: true });
  await expect(dialog).toBeHidden();
});

test("suppresses drawer transitions for reduced motion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openStory(page, STORY_IDS.constrainedClosed, 412, 915);
  const { dialog } = await openDrawer(page);

  const transitionDurations = await Promise.all(
    [page.getByTestId("drawer-backdrop"), dialog].map((locator) =>
      locator.evaluate(
        (element) => getComputedStyle(element).transitionDuration,
      ),
    ),
  );
  for (const duration of transitionDurations) {
    expect(duration.split(",").every((value) => value.trim() === "0s")).toBe(
      true,
    );
  }
});

test("renders exact loading, healthy, and unavailable live-region states", async ({
  page,
}) => {
  const states = [
    {
      copy: "Checking backend health…",
      role: "status" as const,
      storyId: STORY_IDS.loading,
    },
    {
      copy: "Backend connected and healthy.",
      role: "status" as const,
      storyId: STORY_IDS.healthy,
    },
    {
      copy: "Backend unavailable.",
      role: "alert" as const,
      storyId: STORY_IDS.unavailable,
    },
  ];

  for (const state of states) {
    await openStory(page, state.storyId, 1920, 1080);
    await expect(page.getByRole(state.role)).toHaveText(state.copy);
  }
});

test("shows and locally recovers the exact unexpected-failure fallback", async ({
  page,
}) => {
  await openStory(page, STORY_IDS.unexpectedFailureBrowserProof, 412, 915);

  await expect(
    page.getByRole("heading", { name: "Page unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByText("Something went wrong while displaying this page."),
  ).toBeVisible();
  const retry = page.getByRole("button", { name: "Try again" });
  const recovered = page.getByText("Content recovered after reset.");

  await Promise.race([retry.click(), recovered.waitFor({ state: "visible" })]);
  await expect(recovered).toBeVisible();
});

for (const axeCase of [
  { storyId: STORY_IDS.wideHealthy, title: "wide healthy", width: 1920 },
  {
    storyId: STORY_IDS.constrainedClosed,
    title: "constrained closed",
    width: 412,
  },
  { storyId: STORY_IDS.constrainedOpen, title: "constrained open", width: 412 },
  { storyId: STORY_IDS.loading, title: "loading", width: 1920 },
  { storyId: STORY_IDS.healthy, title: "healthy", width: 1920 },
  { storyId: STORY_IDS.unavailable, title: "unavailable", width: 1920 },
  {
    storyId: STORY_IDS.unexpectedFailure,
    title: "unexpected failure",
    width: 412,
  },
]) {
  test(`has no application-owned axe violations in ${axeCase.title}`, async ({
    page,
  }) => {
    await openStory(
      page,
      axeCase.storyId,
      axeCase.width,
      axeCase.width === 1920 ? 1080 : 915,
    );
    await expectApplicationAxeClean(page);
  });
}
