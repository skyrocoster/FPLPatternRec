import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import App from "./App";
import { QueryClientTestProvider } from "./test-utils/QueryClientTestProvider";

afterEach(cleanup);

function renderApp(initialEntries: string[]) {
  return render(
    <QueryClientTestProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <App />
      </MemoryRouter>
    </QueryClientTestProvider>,
  );
}

describe("App routes", () => {
  it("preserves the status page at the root route", () => {
    renderApp(["/"]);

    expect(screen.getByRole("heading", { name: "System status" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Checking backend health");
    expect(screen.getByTestId("shell-identity-header")).toHaveTextContent("FPLPatternRec");
  });

  it("renders the not-found page for an unmatched route", () => {
    renderApp(["/not-a-page"]);

    expect(screen.getByRole("heading", { name: "Page not found", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("The page you requested could not be found.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "System status" })).not.toBeInTheDocument();
  });
});
