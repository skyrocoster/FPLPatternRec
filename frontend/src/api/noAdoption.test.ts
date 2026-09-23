import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const dirname = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(dirname, "..");
const SOURCE_EXTENSIONS = new Set([".ts", ".tsx"]);

function collectProductionSourceFiles(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const entryPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entryPath === path.resolve(dirname)) continue;
      files.push(...collectProductionSourceFiles(entryPath));
    } else if (
      SOURCE_EXTENSIONS.has(path.extname(entry.name)) &&
      !entry.name.includes(".test.") &&
      !entry.name.includes(".stories.")
    ) {
      files.push(entryPath);
    }
  }
  return files;
}

describe("generated client adoption guard", () => {
  it("keeps the health page on the central client and blocks direct generated imports", () => {
    const offenders: string[] = [];
    for (const filePath of collectProductionSourceFiles(srcDir)) {
      const content = readFileSync(filePath, "utf8");
      const relativePath = path.relative(srcDir, filePath).replaceAll(path.sep, "/");
      if (
        content.includes("api/generated") &&
        relativePath !== "api/client.ts"
      ) {
        offenders.push(`${relativePath}: direct generated import`);
      }
      if (/from ["'][^"']*api\/client["']/.test(content) && relativePath !== "features/status/StatusPage.tsx") {
        offenders.push(`${relativePath}: unexpected central client import`);
      }
    }

    expect(offenders).toEqual([]);
  });
});
