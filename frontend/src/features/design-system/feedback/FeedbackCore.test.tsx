import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { CircleCheck, CircleX, Info, TriangleAlert } from "lucide-react";
import { afterEach, describe, expect, it } from "vitest";

import { FeedbackCore } from "./FeedbackCore";
import { FEEDBACK_VARIANTS } from "./feedbackTypes";
import type { FeedbackSeverity } from "./feedbackTypes";

afterEach(() => {
  cleanup();
});

const here = dirname(fileURLToPath(import.meta.url));
const moduleCss = readFileSync(join(here, "FeedbackCore.module.css"), "utf8");

const SEVERITIES: FeedbackSeverity[] = ["information", "success", "warning", "error"];

const TOKEN_SET: Record<FeedbackSeverity, [string, string, string, string]> = {
  information: [
    "--app-info-accent",
    "--app-info-on-accent",
    "--app-info-container",
    "--app-info-on-container",
  ],
  success: [
    "--app-success-accent",
    "--app-success-on-accent",
    "--app-success-container",
    "--app-success-on-container",
  ],
  warning: [
    "--app-warning-accent",
    "--app-warning-on-accent",
    "--app-warning-container",
    "--app-warning-on-container",
  ],
  error: [
    "--app-error-accent",
    "--app-error-on-accent",
    "--app-error-container",
    "--app-error-on-container",
  ],
};

describe("FeedbackCore", () => {
  it("renders all four severity variants through the shared core", () => {
    render(
      <>
        {SEVERITIES.map((severity) => (
          <FeedbackCore key={severity} severity={severity} message={`${severity} message`} />
        ))}
      </>,
    );

    for (const severity of SEVERITIES) {
      expect(screen.getByTestId(`core-${severity}`)).toBeVisible();
      expect(screen.getByText(`${severity} message`)).toBeVisible();
    }
  });

  it("maps each severity to exactly its fixed icon, hidden from assistive technology", () => {
    expect(FEEDBACK_VARIANTS.information.icon).toBe(Info);
    expect(FEEDBACK_VARIANTS.success.icon).toBe(CircleCheck);
    expect(FEEDBACK_VARIANTS.warning.icon).toBe(TriangleAlert);
    expect(FEEDBACK_VARIANTS.error.icon).toBe(CircleX);

    render(
      <>
        {SEVERITIES.map((severity) => (
          <FeedbackCore key={severity} severity={severity} message={`${severity} message`} />
        ))}
      </>,
    );

    for (const severity of SEVERITIES) {
      const icon = screen.getByTestId(`icon-${severity}`);
      expect(icon.tagName).toBe("svg");
      expect(icon).toHaveAttribute("aria-hidden", "true");
    }
  });

  it("renders the required message and the optional heading when provided", () => {
    render(
      <FeedbackCore severity="information" message="Required message" heading="Optional heading" />,
    );
    expect(screen.getByText("Required message")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Optional heading" })).toBeVisible();
  });

  it("omits the heading and applies no announcement defaults when not provided", () => {
    render(<FeedbackCore severity="success" message="Plain message" />);
    expect(screen.getByText("Plain message")).toBeVisible();
    expect(screen.queryByRole("heading")).toBeNull();

    const core = screen.getByTestId("core-success");
    expect(core).not.toHaveAttribute("role");
    expect(core).not.toHaveAttribute("aria-live");
    expect(core).not.toHaveAttribute("aria-atomic");
    expect(core).not.toHaveAttribute("aria-relevant");
    expect(core).not.toHaveAttribute("aria-busy");
  });

  it("uses only the dedicated --app-* feedback tokens", () => {
    for (const severity of SEVERITIES) {
      const [accent, onAccent, container, onContainer] = TOKEN_SET[severity];
      expect(FEEDBACK_VARIANTS[severity].tokens).toEqual({
        accent,
        onAccent,
        container,
        onContainer,
      });
    }

    // The CSS Module consumes exactly the two core aliases (accent for the
    // border/icon/heading cue and on-container for the message). The
    // on-accent and container aliases are wired inline from FEEDBACK_VARIANTS
    // (asserted below) but are not consumed by module rules yet - they are
    // saved for the future panel presentation that owns the container-backed surface.
    for (const alias of ["--app-feedback-accent", "--app-feedback-on-container"]) {
      expect(moduleCss).toContain(alias);
    }

    render(<FeedbackCore severity="warning" message="Token wiring" />);
    const core = screen.getByTestId("core-warning");
    expect(core.style.getPropertyValue("--app-feedback-accent")).toBe("var(--app-warning-accent)");
    expect(core.style.getPropertyValue("--app-feedback-on-accent")).toBe(
      "var(--app-warning-on-accent)",
    );
    expect(core.style.getPropertyValue("--app-feedback-container")).toBe(
      "var(--app-warning-container)",
    );
    expect(core.style.getPropertyValue("--app-feedback-on-container")).toBe(
      "var(--app-warning-on-container)",
    );
  });

  it("forwards explicit consumer live-region attributes to the rendered root", () => {
    render(
      <FeedbackCore
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
        <FeedbackCore severity="information" message="x">
          child
        </FeedbackCore>
      )
    );
    // @ts-expect-error actions are not part of FeedbackProps
    void (<FeedbackCore severity="information" message="x" actions={[]} />);
    // @ts-expect-error custom icon is not part of FeedbackProps
    void (<FeedbackCore severity="information" message="x" icon={Info} />);
    // @ts-expect-error arbitrary div props are not part of FeedbackProps
    void (<FeedbackCore severity="information" message="x" onClick={() => undefined} />);
  });
});
