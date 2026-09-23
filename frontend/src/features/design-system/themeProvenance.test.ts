import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const materialDir = join(here, "../../styles/material");
const previewPath = join(here, "../../../.storybook/preview.tsx");
const RUNTIME_MEMBER_HASH = "e52f0cbbeb21b2d56cb22db7dddbd99ba7611b6bf55fae04003c12350382e0fb";

const provenance = JSON.parse(
  readFileSync(join(materialDir, "material-theme-provenance.json"), "utf8"),
) as {
  schemaVersion: number;
  generator: { name: string; version: string };
  artifact: {
    runtimeAsset: string;
    runtimeMember: string;
    runtimeMemberSha256: string;
    retainedMembers: string[];
  };
  ownership: { runtimeThemeGeneration: boolean };
};

const sha256Of = (filePath: string) =>
  createHash("sha256").update(readFileSync(filePath)).digest("hex");

describe("Material dark runtime theme provenance", () => {
  it("records the source library for the retained runtime asset", () => {
    expect(provenance.schemaVersion).toBe(1);
    expect(provenance.generator.name).toBe("@material/material-color-utilities");
    expect(provenance.generator.version).toBe("0.4.0");
    expect(provenance.artifact.runtimeAsset).toBe("material-theme-builder-css-export/css/dark.css");
    expect(provenance.artifact.runtimeMember).toBe("css/dark.css");
    expect(provenance.artifact.retainedMembers).toEqual(["css/dark.css"]);
    expect("archive" in provenance.artifact).toBe(false);
    expect("archiveSha256" in provenance.artifact).toBe(false);
  });

  it("matches the preserved dark runtime asset hash", () => {
    expect(provenance.artifact.runtimeMemberSha256).toBe(RUNTIME_MEMBER_HASH);
    expect(
      sha256Of(join(materialDir, "material-theme-builder-css-export", provenance.artifact.runtimeMember)),
    ).toBe(RUNTIME_MEMBER_HASH);
  });

  it("exposes Material color roles from the retained dark stylesheet", () => {
    const darkCss = readFileSync(
      join(materialDir, "material-theme-builder-css-export", "css/dark.css"),
      "utf8",
    );
    expect(darkCss).toContain(":root");
    expect(darkCss).toContain("--md-sys-color-primary:");
    expect(darkCss).toContain("--md-sys-color-on-primary:");
    expect(darkCss).toContain("--md-sys-color-surface-tint:");
  });

  it("uses only the dark runtime stylesheet without generating themes at runtime", () => {
    const preview = readFileSync(previewPath, "utf8");
    expect(preview).toContain("css/dark.css");
    expect(preview).toContain('className="dark"');
    expect(preview).not.toContain("css/light.css");
    expect(provenance.ownership.runtimeThemeGeneration).toBe(false);
  });
});
