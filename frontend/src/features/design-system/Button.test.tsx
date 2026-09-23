import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

import { Button, type ButtonVariant } from "./Button";

afterEach(() => {
  cleanup();
});

const here = dirname(fileURLToPath(import.meta.url));
const moduleCss = readFileSync(join(here, "Button.module.css"), "utf8");

const VARIANTS: ButtonVariant[] = ["primary", "secondary", "ghost"];

/** Remove all whitespace so formatting never changes the asserted value. */
function normalize(css: string): string {
  return css.replace(/\s+/g, "");
}

function ruleBlock(css: string, selector: string): string {
  const match = css.match(new RegExp(`${selector}\\s*\\{[^}]*\\}`));
  return match ? match[0] : "";
}

describe("Button", () => {
  it("renders the Base UI button with the supplied label", () => {
    render(<Button>Save changes</Button>);

    const button = screen.getByRole("button", { name: "Save changes" });
    expect(button).toBeVisible();
    expect(button.tagName).toBe("BUTTON");
  });

  it("defaults to type button and applies the variant class", () => {
    render(<Button variant="secondary">Tonal</Button>);

    const button = screen.getByRole("button", { name: "Tonal" });
    expect(button).toHaveAttribute("type", "button");
    expect(button.className).toContain("secondary");
  });

  it("forwards the disabled state", () => {
    render(<Button disabled>Disabled</Button>);

    expect(screen.getByRole("button", { name: "Disabled" })).toBeDisabled();
  });

  it("exposes every variant through the public type", () => {
    for (const variant of VARIANTS) {
      render(<Button variant={variant}>{variant}</Button>);
      expect(screen.getByRole("button", { name: variant })).toBeVisible();
    }
  });

  it("keeps the focus ring consistent with the foundation treatment", () => {
    const focusBlock = ruleBlock(moduleCss, "\\.button:focus-visible");
    expect(normalize(focusBlock)).toContain(
      normalize("outline: var(--app-focus-ring-width) solid var(--app-focus-ring-color);"),
    );
    expect(normalize(focusBlock)).toContain(
      normalize("outline-offset: var(--app-focus-ring-separation);"),
    );
  });

  it("uses only token-driven color roles for the variants", () => {
    expect(ruleBlock(moduleCss, "\\.primary")).toContain(
      "background: var(--md-sys-color-primary);",
    );
    expect(ruleBlock(moduleCss, "\\.secondary")).toContain(
      "background: var(--md-sys-color-secondary-container);",
    );
    expect(ruleBlock(moduleCss, "\\.ghost")).toContain("background: transparent;");
  });
});
