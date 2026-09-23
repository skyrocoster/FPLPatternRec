import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PageFeedback } from "./PageFeedback";
import styles from "./PageFeedback.module.css";
import type { FeedbackSeverity } from "./feedbackTypes";

const here = dirname(fileURLToPath(import.meta.url));
const moduleCss = readFileSync(join(here, "PageFeedback.module.css"), "utf8");

const SEVERITIES: FeedbackSeverity[] = ["information", "success", "warning", "error"];

const ACCENT_TOKEN: Record<FeedbackSeverity, string> = {
  information: "--app-info-accent",
  success: "--app-success-accent",
  warning: "--app-warning-accent",
  error: "--app-error-accent",
};

const CONTAINER_TOKEN: Record<FeedbackSeverity, string> = {
  information: "--app-info-container",
  success: "--app-success-container",
  warning: "--app-warning-container",
  error: "--app-error-container",
};

afterEach(() => {
  cleanup();
});

describe("PageFeedback", () => {
  it("delegates presentation content to the shared FeedbackCore", () => {
    render(
      <PageFeedback severity="information" heading="Information" message="A shared message" />,
    );

    expect(screen.getByTestId("core-information")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Information" })).toBeVisible();
    expect(screen.getByText("A shared message")).toBeVisible();
  });

  it.each(SEVERITIES)(
    "renders the %s page presentation on the accepted surface with the accent cue",
    (severity) => {
      const { container } = render(
        <PageFeedback severity={severity} message={`${severity} message`} />,
      );

      const page = container.querySelector(`[data-severity="${severity}"]`);
      expect(page).toBeInTheDocument();
      expect(page).toHaveClass(styles.page);
      expect(screen.getByTestId(`core-${severity}`)).toBeVisible();

      expect(moduleCss).toContain(`var(${ACCENT_TOKEN[severity]})`);
      expect(moduleCss).toContain("--md-sys-color-surface-container");
      expect(moduleCss).not.toContain(`var(${CONTAINER_TOKEN[severity]})`);
    },
  );

  it("requires a message while allowing an optional heading", () => {
    const { rerender } = render(
      <PageFeedback severity="success" message="Message without heading" />,
    );

    expect(screen.getByText("Message without heading")).toBeVisible();
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();

    rerender(
      <PageFeedback severity="success" heading="Optional heading" message="Message with heading" />,
    );

    expect(screen.getByRole("heading", { name: "Optional heading" })).toBeVisible();
    expect(screen.getByText("Message with heading")).toBeVisible();
  });

  it.each(SEVERITIES)(
    "shows the fixed decorative %s icon with no automatic announcement semantics",
    (severity) => {
      render(<PageFeedback severity={severity} message={`${severity} message`} />);

      const icon = screen.getByTestId(`icon-${severity}`);
      expect(icon).toBeVisible();
      expect(icon).toHaveAttribute("aria-hidden", "true");

      const core = screen.getByTestId(`core-${severity}`);
      expect(core).not.toHaveAttribute("role");
      expect(core).not.toHaveAttribute("aria-live");
    },
  );

  it("forwards consumer-supplied live-region attributes as-is", () => {
    render(
      <PageFeedback
        severity="error"
        message="Consumer-owned live behavior"
        role="status"
        aria-live="polite"
      />,
    );

    const core = screen.getByTestId("core-error");
    expect(core).toHaveAttribute("role", "status");
    expect(core).toHaveAttribute("aria-live", "polite");
  });
});
