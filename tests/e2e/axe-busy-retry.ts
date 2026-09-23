import type { Page } from "@playwright/test";

const AXE_BUSY_ERROR =
  "Axe is already running. Use await axe.run() to wait for the previous run to finish before starting a new run.";
const MAX_RETRIES = 4;
const BUSY_BACKOFF_MS = 250;
const STORYBOOK_RENDER_TIMEOUT_MS = 10_000;

function isAxeBusyError(error: unknown): error is Error {
  return error instanceof Error && error.message.includes(AXE_BUSY_ERROR);
}

async function waitForStorybookRender(page: Page): Promise<void> {
  const initialStatus = await page.evaluate(() => {
    const preview = (window as Window & { __STORYBOOK_PREVIEW__?: unknown })
      .__STORYBOOK_PREVIEW__;

    if (typeof preview !== "object" || preview === null) {
      return { available: false, finished: false };
    }

    const storyRenders = (preview as { storyRenders?: unknown }).storyRenders;
    if (!Array.isArray(storyRenders)) {
      return { available: false, finished: false };
    }

    return {
      available: true,
      finished: storyRenders.some(
        (render) =>
          typeof render === "object" &&
          render !== null &&
          (render as { phase?: unknown }).phase === "finished",
      ),
    };
  });

  if (!initialStatus.available) {
    throw new Error(
      "Storybook render lifecycle signal unavailable: expected window.__STORYBOOK_PREVIEW__.storyRenders[].phase.",
    );
  }

  if (initialStatus.finished) {
    return;
  }

  try {
    await page.waitForFunction(
      () => {
        const preview = (window as Window & { __STORYBOOK_PREVIEW__?: unknown })
          .__STORYBOOK_PREVIEW__;

        if (typeof preview !== "object" || preview === null) {
          return false;
        }

        const storyRenders = (preview as { storyRenders?: unknown })
          .storyRenders;
        return (
          Array.isArray(storyRenders) &&
          storyRenders.some(
            (render) =>
              typeof render === "object" &&
              render !== null &&
              (render as { phase?: unknown }).phase === "finished",
          )
        );
      },
      undefined,
      { timeout: STORYBOOK_RENDER_TIMEOUT_MS },
    );
  } catch (error) {
    throw new Error(
      `Storybook render lifecycle did not reach "finished" within ${STORYBOOK_RENDER_TIMEOUT_MS} ms.`,
      { cause: error },
    );
  }
}

export async function retryAxeWhenBusy<T>(
  page: Page,
  scan: () => Promise<T>,
): Promise<T> {
  for (let retry = 0; retry <= MAX_RETRIES; retry += 1) {
    try {
      await waitForStorybookRender(page);
      return await scan();
    } catch (error) {
      if (!isAxeBusyError(error)) {
        throw error;
      }

      if (retry === MAX_RETRIES) {
        throw new Error(`Axe remained busy after ${MAX_RETRIES} retries.`, {
          cause: error,
        });
      }

      await page.waitForTimeout(BUSY_BACKOFF_MS);
    }
  }

  throw new Error("Axe retry loop ended unexpectedly.");
}
