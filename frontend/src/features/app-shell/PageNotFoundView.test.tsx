import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import PageNotFoundView from "./PageNotFoundView";

afterEach(cleanup);

describe("PageNotFoundView", () => {
  it("renders an in-shell not-found message without a back link", () => {
    render(<PageNotFoundView />);

    expect(screen.getByRole("heading", { name: "Page not found", level: 1 })).toBeInTheDocument();
    const message = screen.getByText("The page you requested could not be found.");
    expect(message).toBeInTheDocument();
    expect(message.closest("[data-severity]")).toHaveAttribute("data-severity", "error");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
