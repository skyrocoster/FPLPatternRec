import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

import { StorySpecimenTypescale } from "./StorySpecimenTypescale";

afterEach(() => {
  cleanup();
});

const SCALE_NAMES = ["display", "headline", "title", "body", "label"] as const;
const SIZE_NAMES = ["large", "medium", "small"] as const;
const TYPESCALE_ROLES: readonly string[] = SCALE_NAMES.flatMap((scale) =>
  SIZE_NAMES.map((size) => `${scale}-${size}`),
);

const here = dirname(fileURLToPath(import.meta.url));
const tokenCss = readFileSync(join(here, "../../styles/app-typescale.css"), "utf8");
const moduleCss = readFileSync(join(here, "StorySpecimenTypescale.module.css"), "utf8");

describe("StorySpecimenTypescale", () => {
  it("enumerates all 15 Material 3 typescale roles", () => {
    render(<StorySpecimenTypescale />);

    expect(TYPESCALE_ROLES).toHaveLength(15);
    expect(screen.getByRole("heading", { name: "CompleteTypescale" })).toBeVisible();
    for (const role of TYPESCALE_ROLES) {
      expect(screen.getByText(role)).toBeVisible();
    }
  });

  it("asserts the system-ui contract for every role in the centralized tokens", () => {
    for (const role of TYPESCALE_ROLES) {
      expect(tokenCss).toContain(`--md-sys-typescale-${role}-font: system-ui;`);
    }
  });

  it("asserts every role consumes the centralized typescale variables", () => {
    for (const role of TYPESCALE_ROLES) {
      expect(moduleCss).toContain(`var(--md-sys-typescale-${role}-font)`);
      expect(moduleCss).toContain(`var(--md-sys-typescale-${role}-size)`);
      expect(moduleCss).toContain(`var(--md-sys-typescale-${role}-line-height)`);
      expect(moduleCss).toContain(`var(--md-sys-typescale-${role}-weight)`);
      expect(moduleCss).toContain(`var(--md-sys-typescale-${role}-letter-spacing)`);
    }
  });
});
