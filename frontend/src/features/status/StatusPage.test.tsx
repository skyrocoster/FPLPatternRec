import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  QueryClientTestProvider,
  createTestQueryClient,
} from "../../test-utils/QueryClientTestProvider";
import { StatusPage } from "./StatusPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderStatusPage(client?: ReturnType<typeof createTestQueryClient>) {
  return render(
    <QueryClientTestProvider client={client}>
      <StatusPage />
    </QueryClientTestProvider>,
  );
}

function mockHealthyFetch() {
  // The generated client parses a 200 body as JSON only when the Content-Type
  // header says so (as the real backend does), so the mock must carry it. A
  // fresh Response per call keeps repeated requests independent.
  return vi.spyOn(globalThis, "fetch").mockImplementation(
    async () =>
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  );
}

describe("StatusPage", () => {
  it("shows checking then healthy", async () => {
    mockHealthyFetch();
    renderStatusPage();

    expect(screen.getByRole("status")).toHaveTextContent("Checking backend health");
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("healthy"));
  });

  it("shows the exact stable error on network rejection", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Connection refused"));
    renderStatusPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Backend unavailable.");
    expect(alert).not.toHaveTextContent("Connection refused");
  });

  it("shows the exact stable error on a non-2xx response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));
    renderStatusPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Backend unavailable.");
    expect(alert).not.toHaveTextContent("503");
  });

  it("shows the exact stable error on an explicit non-Error rejection", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue("backend exploded");
    renderStatusPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Backend unavailable.");
    expect(alert).not.toHaveTextContent("backend exploded");
  });

  it("shows the exact stable error on a malformed HTTP 200 and never shows healthy", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async () =>
        new Response(JSON.stringify({ status: "maintenance" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    renderStatusPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Backend unavailable.");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("checks again on remount when the shared cache is empty", async () => {
    const fetchMock = mockHealthyFetch();
    const client = createTestQueryClient();

    const first = renderStatusPage(client);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("healthy"));
    first.unmount();

    // gcTime 0 removes the now-inactive query from the shared cache.
    await waitFor(() => expect(client.getQueryCache().getAll()).toHaveLength(0));

    renderStatusPage(client);
    expect(screen.getByRole("status")).toHaveTextContent("Checking backend health");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it("aborts the pending generated request on unmount", async () => {
    let capturedSignal: AbortSignal | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      capturedSignal = (input as Request).signal;
      return new Promise(() => {});
    });

    const view = renderStatusPage();
    await waitFor(() => expect(capturedSignal).toBeDefined());
    expect(capturedSignal?.aborted).toBe(false);

    view.unmount();
    await waitFor(() => expect(capturedSignal?.aborted).toBe(true));
  });
});
