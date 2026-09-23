import { cleanup, render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

import { StorySpecimenAccessibilityReview } from "./StorySpecimenAccessibilityReview";

afterEach(() => {
  cleanup();
});

const here = dirname(fileURLToPath(import.meta.url));
const tokenCss = readFileSync(join(here, "../../styles/app-tokens.css"), "utf8");
const moduleCss = readFileSync(join(here, "StorySpecimenAccessibilityReview.module.css"), "utf8");

/** Return the first rule block for a plain selector, or "" when absent. */
function ruleBlock(css: string, selector: string): string {
  const match = css.match(new RegExp(`${selector}\\s*\\{[^}]*\\}`));
  return match ? match[0] : "";
}

describe("StorySpecimenAccessibilityReview", () => {
  it("places all presentation levels inside one constrained review container", () => {
    render(<StorySpecimenAccessibilityReview />);

    const review = screen.getByTestId("accessibility-review");
    expect(review).toBeVisible();

    const inlineRegion = within(review).getByRole("region", { name: "Inline feedback review" });
    const panelRegion = within(review).getByRole("region", { name: "Panel feedback review" });
    const pageRegion = within(review).getByRole("region", { name: "Page feedback review" });

    expect(within(inlineRegion).getByTestId("core-information")).toBeVisible();
    expect(within(panelRegion).getByTestId("core-warning")).toBeVisible();
    expect(within(pageRegion).getByTestId("core-error")).toBeVisible();

    const reviewBlock = ruleBlock(moduleCss, "\\.review");
    expect(reviewBlock).toContain("max-width: 42rem;");
    expect(reviewBlock).toContain("padding: var(--app-spacing-32);");
    expect(reviewBlock).toContain("border: 1px solid var(--md-sys-color-outline-variant);");
    expect(reviewBlock).toContain("background: var(--md-sys-color-surface-container-low);");
  });

  it("shows long-message wrapping inside the constrained container", () => {
    render(<StorySpecimenAccessibilityReview />);

    const panelRegion = screen.getByRole("region", { name: "Panel feedback review" });
    const message = within(panelRegion).getByText(/deliberately long message/);

    expect(message).toBeVisible();
    expect((message.textContent ?? "").length).toBeGreaterThan(300);
    expect(message.textContent).not.toContain("\n");

    const reviewBlock = ruleBlock(moduleCss, "\\.review");
    expect(reviewBlock).toContain("max-width:");
    expect(reviewBlock).not.toMatch(/white-space\s*:\s*nowrap/);
  });

  it("shows no-heading feedback content", () => {
    render(<StorySpecimenAccessibilityReview />);

    // The fixture keeps feedback content heading-free: only the review
    // fixture title is a heading, and no FeedbackCore instance renders the
    // optional <h3>.
    expect(screen.getAllByRole("heading")).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Responsive and accessibility review",
    );

    for (const name of [
      "Inline feedback review",
      "Panel feedback review",
      "Page feedback review",
    ]) {
      const region = screen.getByRole("region", { name });
      expect(within(region).queryByRole("heading")).not.toBeInTheDocument();
    }
  });

  it("demonstrates explicit consumer-owned live semantics with no wrapper defaults", () => {
    render(<StorySpecimenAccessibilityReview />);

    const inlineCore = screen.getByTestId("core-information");
    expect(inlineCore).toHaveAttribute("role", "status");
    expect(inlineCore).toHaveAttribute("aria-live", "polite");
    expect(inlineCore).toHaveAttribute("aria-atomic", "true");

    const pageCore = screen.getByTestId("core-error");
    expect(pageCore).toHaveAttribute("role", "alert");
    expect(pageCore).toHaveAttribute("aria-live", "assertive");
    expect(pageCore).toHaveAttribute("aria-relevant", "additions text");

    // The panel instance passes no live-region attributes; without wrapper
    // or core defaults, none may appear.
    const panelCore = screen.getByTestId("core-warning");
    expect(panelCore).not.toHaveAttribute("role");
    expect(panelCore).not.toHaveAttribute("aria-live");
    expect(panelCore).not.toHaveAttribute("aria-atomic");
    expect(panelCore).not.toHaveAttribute("aria-relevant");
    expect(panelCore).not.toHaveAttribute("aria-busy");
  });

  it("renders focus specimens with the centralized focus ring", () => {
    render(<StorySpecimenAccessibilityReview />);

    const focusRegion = screen.getByRole("region", { name: "Focus specimens review" });
    expect(within(focusRegion).getByRole("button", { name: "Focus specimen one" })).toBeVisible();
    expect(within(focusRegion).getByRole("button", { name: "Focus specimen two" })).toBeVisible();

    const focusBlock = ruleBlock(moduleCss, "\\.focusSpecimen:focus");
    expect(focusBlock).toContain(
      "outline: var(--app-focus-ring-width) solid var(--app-focus-ring-color);",
    );
    expect(focusBlock).toContain("outline-offset: var(--app-focus-ring-separation);");

    expect(tokenCss).toContain("--app-focus-ring-width: 2px;");
    expect(tokenCss).toContain("--app-focus-ring-separation: 2px;");
  });

  it("reuses centralized tokens without redefining them and stays fixture-scoped", () => {
    render(<StorySpecimenAccessibilityReview />);

    expect(moduleCss).toContain("var(--app-spacing-32)");
    expect(moduleCss).toContain("var(--app-radius-12)");
    expect(moduleCss).toContain("var(--app-focus-ring-width)");

    expect(moduleCss).not.toMatch(/--app-[a-z0-9-]*\s*:/);
    expect(moduleCss).not.toMatch(/--md-sys-[a-z0-9-]*\s*:/);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  });

  it("is a distinct review fixture, not the combined composition or production UI", () => {
    render(<StorySpecimenAccessibilityReview />);

    expect(screen.queryByText(/ReviewSummary/)).not.toBeInTheDocument();
    expect(screen.queryByText(/elevated card/i)).not.toBeInTheDocument();

    for (const phrase of ["dashboard", "account", "project", "workspace", "report", "server"]) {
      expect(screen.queryByText(new RegExp(phrase, "i"))).not.toBeInTheDocument();
    }
  });
});
