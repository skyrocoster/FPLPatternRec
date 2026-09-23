import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const tokenCss = readFileSync(join(here, "../../styles/app-tokens.css"), "utf8");

const FEEDBACK_TOKENS = [
  "--app-info-accent",
  "--app-info-on-accent",
  "--app-info-container",
  "--app-info-on-container",
  "--app-success-accent",
  "--app-success-on-accent",
  "--app-success-container",
  "--app-success-on-container",
  "--app-warning-accent",
  "--app-warning-on-accent",
  "--app-warning-container",
  "--app-warning-on-container",
  "--app-error-accent",
  "--app-error-on-accent",
  "--app-error-container",
  "--app-error-on-container",
] as const;

describe("design token contract", () => {
  it("defines the shared focus ring treatment", () => {
    expect(tokenCss).toContain("--app-focus-ring-color: var(--md-sys-color-primary);");
    expect(tokenCss).toContain("--app-focus-ring-width: 2px;");
    expect(tokenCss).toContain("--app-focus-ring-separation: 2px;");
  });

  it("defines all 16 dedicated feedback tokens", () => {
    for (const token of FEEDBACK_TOKENS) {
      expect(tokenCss).toContain(`${token}:`);
    }
  });
});
