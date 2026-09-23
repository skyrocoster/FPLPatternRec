import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

import { StorySpecimenCombinedComposition } from "./StorySpecimenCombinedComposition";

afterEach(() => {
  cleanup();
});

const here = dirname(fileURLToPath(import.meta.url));
const tokenCss = readFileSync(join(here, "../../styles/app-tokens.css"), "utf8");
const typescaleCss = readFileSync(join(here, "../../styles/app-typescale.css"), "utf8");
const moduleCss = readFileSync(join(here, "StorySpecimenCombinedComposition.module.css"), "utf8");

/** Return the first rule block for a plain selector, or "" when absent. */
function ruleBlock(css: string, selector: string): string {
  const match = css.match(new RegExp(`${selector}\\s*\\{[^}]*\\}`));
  return match ? match[0] : "";
}

describe("StorySpecimenCombinedComposition", () => {
  it("composes a typescale heading region with display, headline, and title roles", () => {
    render(<StorySpecimenCombinedComposition />);

    expect(screen.getByRole("heading", { name: "ReviewSummary" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "One restrained review surface" })).toBeVisible();
    expect(screen.getByText(/accepted typescale/)).toBeVisible();

    const ROLES: ReadonlyArray<{ selector: string; block: string; scale: string }> = [
      { selector: ".display", block: ruleBlock(moduleCss, "\\.display"), scale: "display-large" },
      {
        selector: ".headline",
        block: ruleBlock(moduleCss, "\\.headline"),
        scale: "headline-medium",
      },
      { selector: ".title", block: ruleBlock(moduleCss, "\\.title"), scale: "title-medium" },
    ];

    for (const role of ROLES) {
      expect(role.block).toContain(`var(--md-sys-typescale-${role.scale}-font)`);
      expect(role.block).toContain(`var(--md-sys-typescale-${role.scale}-size)`);
      expect(role.block).toContain(`var(--md-sys-typescale-${role.scale}-line-height)`);
      expect(role.block).toContain(`var(--md-sys-typescale-${role.scale}-weight)`);
      expect(role.block).toContain(`var(--md-sys-typescale-${role.scale}-letter-spacing)`);
      expect(typescaleCss).toContain(`--md-sys-typescale-${role.scale}-font: system-ui;`);
    }
  });

  it("composes a tonal surface region with a fine border", () => {
    render(<StorySpecimenCombinedComposition />);

    const region = screen.getByRole("region", { name: "Tonal surface region" });
    expect(region).toBeVisible();
    expect(screen.getByRole("heading", { name: "Tonal surface with fine border" })).toBeVisible();

    const surfaceBlock = ruleBlock(moduleCss, "\\.surfaceRegion");
    expect(surfaceBlock).toContain("border: 1px solid var(--md-sys-color-outline-variant);");
    expect(surfaceBlock).toContain("background: var(--md-sys-color-surface-container-low);");
  });

  it("applies exactly one reserved elevation level from the e1/e2/e3 scale", () => {
    render(<StorySpecimenCombinedComposition />);

    expect(screen.getByRole("heading", { name: "Reserved elevation" })).toBeVisible();

    const elevations = [...moduleCss.matchAll(/box-shadow:\s*var\(--app-elevation-(e[0-9])\)/g)];
    expect(elevations).toHaveLength(1);
    expect(["e1", "e2", "e3"]).toContain(elevations[0][1]);

    const cardBlock = ruleBlock(moduleCss, "\\.elevatedCard");
    expect(cardBlock).toContain(`box-shadow: var(--app-elevation-${elevations[0][1]});`);
  });

  it("renders exactly one shipped feedback presentation through PanelFeedback", () => {
    render(<StorySpecimenCombinedComposition />);

    const cores = screen.getAllByTestId(/^core-/);
    expect(cores).toHaveLength(1);

    const core = cores[0];
    expect(core).toBeVisible();
    expect(core).not.toHaveAttribute("role");
    expect(core).not.toHaveAttribute("aria-live");

    expect(screen.getByRole("heading", { name: "Composition note" })).toBeVisible();
    expect(screen.getByText(/reuses the shipped feedback presentation unchanged/)).toBeVisible();
  });

  it("contains no interactive controls or product-specific content", () => {
    render(<StorySpecimenCombinedComposition />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryAllByRole("textbox")).toHaveLength(0);

    for (const phrase of ["dashboard", "account", "project", "workspace", "report", "server"]) {
      expect(screen.queryByText(new RegExp(phrase, "i"))).not.toBeInTheDocument();
    }
  });

  it("reuses the centralized tokens without redefining them", () => {
    expect(moduleCss).toContain("var(--md-sys-typescale-display-large-size)");
    expect(moduleCss).toContain("var(--app-spacing-32)");
    expect(moduleCss).toContain("var(--app-elevation-e1)");
    expect(moduleCss).toContain("var(--app-focus-ring-width)");

    expect(moduleCss).not.toMatch(/--app-[a-z0-9-]*\s*:/);
    expect(moduleCss).not.toMatch(/--md-sys-[a-z0-9-]*\s*:/);

    expect(tokenCss).toContain("--app-spacing-32: 32px;");
    expect(tokenCss).toContain("--app-elevation-e1:");
    expect(typescaleCss).toContain("--md-sys-typescale-display-large-size:");
  });
});
