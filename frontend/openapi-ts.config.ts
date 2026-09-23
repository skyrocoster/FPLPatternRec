import { defineConfig } from "@hey-api/openapi-ts";

/**
 * SETUP-02 generator configuration for @hey-api/openapi-ts@0.99.0.
 *
 * Paths are resolved by the generator relative to this `frontend/`
 * directory. `input` defaults to the checked-in contract.
 *
 * The client-fetch plugin runs in its default bundled (self-contained) mode:
 * the runtime client is vendored into the output directory, so no separate
 * client package is needed. Output cleaning is confined to `src/api/generated/`
 * and never touches the handwritten `src/api/client.ts`. Cleaning is disabled
 * because the checked-in `openapi.json` input intentionally lives beside the
 * generated files. Log files are disabled so generation leaves no artifact
 * outside the output directory.
 *
 * The CONSUMER-01 TanStack Query plugin emits only query keys and query
 * options. Mutation and infinite-query machinery is explicitly disabled;
 * generated React hooks (useQuery/useMutation) and get/set-query-data helpers
 * are already disabled by the plugin's defaults and stay off. No per-operation
 * filtering: the plugin emits helpers for every query operation in the checked-in
 * contract, which stays deterministic and tree-shakeable.
 */
export default defineConfig({
  input: "src/api/generated/openapi.json",
  logs: {
    file: false,
  },
  output: {
    path: "src/api/generated",
    clean: false,
  },
  plugins: [
    "@hey-api/typescript",
    "@hey-api/sdk",
    "@hey-api/client-fetch",
    {
      name: "@tanstack/react-query",
      mutationOptions: false,
      infiniteQueryKeys: false,
      infiniteQueryOptions: false,
    },
  ],
});
