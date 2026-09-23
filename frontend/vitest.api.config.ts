import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Focused vitest config for the SETUP-02 generated API client tests.
 *
 * The root is anchored to this `frontend/` directory so the repository-root
 * invocation `npx vitest run --config frontend/vitest.api.config.ts` resolves
 * the include globs correctly. Plain node environment: these tests exercise
 * the generated client, a bounded real uvicorn call, and a static scan; no
 * DOM is involved.
 */
export default defineConfig({
  root: dirname,
  test: {
    environment: "node",
    include: ["src/api/**/*.test.ts"],
  },
});
