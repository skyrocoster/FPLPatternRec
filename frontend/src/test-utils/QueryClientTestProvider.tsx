import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

/**
 * Test-only provider support for components that consume the application
 * QueryClient.
 *
 * The conservative defaults here match the production provider in
 * `main.tsx`: no automatic retry, no refetch on window focus, no refetch on
 * reconnect; no staleTime, persistence, or mutation configuration.
 *
 * A fresh `QueryClient` is created for every mounted provider instance, so
 * each `render()` call in a test starts with an empty cache and no state
 * leaks between tests. A test that deliberately needs one shared client
 * across several renders (for example, a remount-freshness check) creates
 * its own client with `createTestQueryClient()` and passes it via `client`.
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
      },
    },
  });
}

type QueryClientTestProviderProps = {
  children?: ReactNode;
  /**
   * Optional explicitly shared client. When omitted, the provider lazily
   * creates one fresh client per mounted instance.
   */
  client?: QueryClient;
};

export function QueryClientTestProvider({ children, client }: QueryClientTestProviderProps) {
  const [fallbackClient] = useState(() => createTestQueryClient());
  return <QueryClientProvider client={client ?? fallbackClient}>{children}</QueryClientProvider>;
}
