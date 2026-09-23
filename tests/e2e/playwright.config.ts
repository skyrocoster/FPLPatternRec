import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  fullyParallel: true,
  workers: 2,
  timeout: 15_000,
  // Services are shared through Compose. Check dev.ps1 status before running;
  // this config must never start competing host servers.
  use: { baseURL: "http://localhost:8455", headless: true },
});
