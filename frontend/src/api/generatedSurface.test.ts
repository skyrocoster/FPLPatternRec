import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import * as generatedSdk from "./generated/sdk.gen";

const dirname = path.dirname(fileURLToPath(import.meta.url));

describe("generated health SDK surface", () => {
  it("exports only the health request function", () => {
    const functionExports = Object.keys(generatedSdk).filter(
      (key) => typeof (generatedSdk as Record<string, unknown>)[key] === "function",
    );

    expect(functionExports).toEqual(["getHealth"]);
  });

  it("checked-in contract contains only the health operation and schema", () => {
    const contractPath = path.resolve(dirname, "generated", "openapi.json");
    const contract = JSON.parse(readFileSync(contractPath, "utf8")) as {
      paths: Record<string, Record<string, { operationId?: string }>>;
      components: { schemas: Record<string, unknown> };
    };

    expect(Object.keys(contract.paths)).toEqual(["/api/health"]);
    expect(Object.keys(contract.paths["/api/health"])).toEqual(["get"]);
    expect(contract.paths["/api/health"]?.get?.operationId).toBe("getHealth");
    expect(Object.keys(contract.components.schemas)).toEqual(["HealthResponse"]);
  });
});
