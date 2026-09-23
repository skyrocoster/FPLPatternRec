import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { playwright } from "@vitest/browser-playwright";
import { storybookTest } from "@storybook/addon-vitest/vitest-plugin";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: ["recharts"],
  },
  test: {
    projects: [
      {
        extends: true,
        test: {
          name: "unit",
          environment: "jsdom",
          setupFiles: ["./src/test-setup.ts"],
          include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
          // The real-server health check runs through the focused API config
          // (frontend/vitest.api.config.ts), not the fast unit project.
          exclude: ["src/api/healthClient.test.ts"],
          // Cap the unit project at six workers. Vitest 4 requires projects with
          // different maxWorkers to use distinct sequence.groupOrder values, so the
          // unit project gets its own group; the Storybook project is untouched.
          maxWorkers: 6,
          sequence: {
            groupOrder: 1,
          },
        },
      },
      {
        extends: true,
        plugins: [
          storybookTest({
            configDir: path.join(dirname, ".storybook"),
          }),
        ],
        test: {
          name: "storybook",
          browser: {
            enabled: true,
            provider: playwright({}),
            headless: true,
            instances: [{ browser: "chromium" }],
            // Windows Hyper-V/Docker can reserve the default 63315 port
            // (EACCES on excluded ranges); use a fixed port outside the
            // excluded ranges so Storybook browser tests can start locally.
            api: { port: 47111 },
          },
        },
      },
    ],
    // Vitest 4 routes this callback through the workspace state, so gate its
    // one exact diagnostic by the Storybook story path; all other errors, and
    // all unit-project errors, retain the default failing disposition.
    onUnhandledError: (error) => {
      const testPath = (error as Error & { VITEST_TEST_PATH?: unknown }).VITEST_TEST_PATH;
      return typeof testPath === "string" &&
        testPath.includes(".stories.") &&
        (error.message === "ResizeObserver loop completed with undelivered notifications" ||
          error.message === "ResizeObserver loop completed with undelivered notifications.")
        ? false
        : undefined;
    },
  },
});
