import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { CircleCheck, CircleX, Info, TriangleAlert } from "lucide-react";
import { afterEach, describe, expect, it } from "vitest";

import { InlineFeedback } from "./InlineFeedback";
import { FEEDBACK_VARIANTS } from "./feedbackTypes";
import type { FeedbackSeverity } from "./feedbackTypes";

afterEach(() => {
  cleanup();
});

const here = dirname(fileURLToPath(import.meta.url));
const moduleCss = readFileSync(join(here, "InlineFeedback.module.css"), "utf8");

const SEVERITIES: FeedbackSeverity[] = ["information", "success", "warning", "error"];

describe("InlineFeedback", () => {
  it("renders all four inline presentations through the shared core", () => {
    render(
      <>
        {SEVERITIES.map((severity) => (
          <InlineFeedback key={severity} severity={severity} message={`${severity} message`} />
        ))}
      </>,
    );

    for (const severity of SEVERITIES) {
      expect(screen.getByTestId(`core-${severity}`)).toBeVisible();
      expect(screen.getByText(`${severity} message`)).toBeVisible();
    }
  });

  it("renders the required message and the optional heading when provided", () => {
    render(
      <InlineFeedback
        severity="information"
        message="Required message"
        heading="Optional heading"
      />,
    );
    expect(screen.getByText("Required message")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Optional heading" })).toBeVisible();
  });

  it("omits the heading when not provided", () => {
    render(<InlineFeedback severity="success" message="Plain message" />);
    expect(screen.getByText("Plain message")).toBeVisible();
    expect(screen.queryByRole("heading")).toBeNull();
  });

  it("maps each severity to exactly its fixed decorative icon, hidden from assistive technology", () => {
    expect(FEEDBACK_VARIANTS.information.icon).toBe(Info);
    expect(FEEDBACK_VARIANTS.success.icon).toBe(CircleCheck);
    expect(FEEDBACK_VARIANTS.warning.icon).toBe(TriangleAlert);
    expect(FEEDBACK_VARIANTS.error.icon).toBe(CircleX);

    render(
      <>
        {SEVERITIES.map((severity) => (
          <InlineFeedback key={severity} severity={severity} message={`${severity} message`} />
        ))}
      </>,
    );

    for (const severity of SEVERITIES) {
      const icon = screen.getByTestId(`icon-${severity}`);
      expect(icon.tagName).toBe("svg");
      expect(icon).toHaveAttribute("aria-hidden", "true");
    }
  });

  it("keeps the inline module compact and transparent without out-of-scope --app-feedback-* aliases", () => {
    // The inline module contributes only the compact, transparent treatment.
    // The accent-driven border belongs to the shared FeedbackCore, which sets
    // the --app-feedback-* aliases on the .core element (a child of .inline);
    // custom properties inherit downward only, so the aliases are out of
    // scope on this wrapper and must not appear here. The container surface
    // aliases are reserved for the future panel presentation.
    expect(moduleCss).toContain("max-width");
    expect(moduleCss).toContain("transparent");
    expect(moduleCss).not.toContain("--app-feedback-accent");
    expect(moduleCss).not.toContain("--app-feedback-container");
    expect(moduleCss).not.toContain("--app-feedback-on-container");
  });

  it("adds no default live-region semantics and forwards explicit consumer attributes unchanged", () => {
    render(<InlineFeedback severity="success" message="Plain message" />);
    const plain = screen.getByTestId("core-success");
    expect(plain).not.toHaveAttribute("role");
    expect(plain).not.toHaveAttribute("aria-live");
    expect(plain).not.toHaveAttribute("aria-atomic");
    expect(plain).not.toHaveAttribute("aria-relevant");
    expect(plain).not.toHaveAttribute("aria-busy");

    cleanup();
    render(
      <InlineFeedback
        severity="error"
        message="Forwarded message"
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        aria-relevant="additions text"
        aria-busy="true"
      />,
    );
    const core = screen.getByTestId("core-error");
    expect(core).toHaveAttribute("role", "alert");
    expect(core).toHaveAttribute("aria-live", "assertive");
    expect(core).toHaveAttribute("aria-atomic", "true");
    expect(core).toHaveAttribute("aria-relevant", "additions text");
    expect(core).toHaveAttribute("aria-busy", "true");
  });

  it("keeps the props contract narrow: no actions, custom icon, children, or arbitrary props", () => {
    void (
      (
        // @ts-expect-error children are not part of FeedbackProps
        <InlineFeedback severity="information" message="x">
          child
        </InlineFeedback>
      )
    );
    // @ts-expect-error actions are not part of FeedbackProps
    void (<InlineFeedback severity="information" message="x" actions={[]} />);
    // @ts-expect-error custom icon is not part of FeedbackProps
    void (<InlineFeedback severity="information" message="x" icon={Info} />);
    // @ts-expect-error arbitrary div props are not part of FeedbackProps
    void (<InlineFeedback severity="information" message="x" onClick={() => undefined} />);
  });
});
