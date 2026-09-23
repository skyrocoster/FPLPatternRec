import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StatusView } from "../status/StatusView";
import { PageContentBoundary } from "./PageContentBoundary";

let shouldThrow = true;

function ThrowingContent() {
  if (shouldThrow) {
    throw new Error("Expected test-only render failure");
  }

  return <p>Recovered content</p>;
}

afterEach(() => {
  shouldThrow = true;
  cleanup();
  vi.restoreAllMocks();
});

describe("PageContentBoundary", () => {
  it("preserves the surrounding content and resets to recovered content", async () => {
    const user = userEvent.setup();
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <div>
        <p>Shell remains available</p>
        <PageContentBoundary
          onReset={() => {
            shouldThrow = false;
          }}
        >
          <ThrowingContent />
        </PageContentBoundary>
      </div>,
    );

    expect(screen.getByText("Shell remains available")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Page unavailable" })).toBeInTheDocument();
    expect(
      screen.getByText("Something went wrong while displaying this page."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByText("Recovered content")).toBeInTheDocument();
  });

  it("keeps expected StatusView health errors out of the boundary fallback", () => {
    render(
      <PageContentBoundary>
        <StatusView state={{ kind: "error" }} />
      </PageContentBoundary>,
    );

    expect(screen.getByRole("alert")).toHaveAttribute("role", "alert");
    expect(screen.getByText("Backend unavailable.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Page unavailable" })).not.toBeInTheDocument();
  });
});
