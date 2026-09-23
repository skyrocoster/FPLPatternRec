import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Disclosure } from "./Disclosure";

afterEach(() => {
  cleanup();
});

describe("Disclosure", () => {
  it("renders closed by default with collapsed ARIA state", () => {
    render(
      <Disclosure summary="Details picker">
        <p>Picker content</p>
      </Disclosure>,
    );

    const trigger = screen.getByRole("button", { name: "Details picker" });

    expect(trigger).toHaveAttribute("type", "button");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Picker content")).not.toBeInTheDocument();
  });

  it("opens by default and exposes the panel content", () => {
    render(
      <Disclosure summary="Loaded details" defaultOpen>
        <p>Loaded content</p>
      </Disclosure>,
    );

    const trigger = screen.getByRole("button", { name: "Loaded details" });
    const content = screen.getByText("Loaded content");

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(content).toBeVisible();
  });

  it("toggles its uncontrolled state when the summary is activated", async () => {
    const user = userEvent.setup();
    render(
      <Disclosure summary="Context">
        <p>Context content</p>
      </Disclosure>,
    );

    const trigger = screen.getByRole("button", { name: "Context" });
    expect(screen.queryByText("Context content")).not.toBeInTheDocument();

    await user.click(trigger);
    const content = screen.getByText("Context content");
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(content).toBeVisible();

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Context content")).not.toBeInTheDocument();
  });

  it("forwards controlled changes and consumer props", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const { rerender } = render(
      <Disclosure
        className="custom-placement"
        data-testid="disclosure"
        summary="Details"
        open={false}
        onOpenChange={onOpenChange}
      >
        <p>Details content</p>
      </Disclosure>,
    );

    const trigger = screen.getByRole("button", { name: "Details" });
    expect(screen.getByTestId("disclosure")).toHaveClass("custom-placement");
    expect(screen.queryByText("Details content")).not.toBeInTheDocument();

    await user.click(trigger);
    expect(onOpenChange).toHaveBeenCalledWith(true);
    expect(screen.queryByText("Details content")).not.toBeInTheDocument();

    rerender(
      <Disclosure
        className="custom-placement"
        data-testid="disclosure"
        summary="Details"
        open
        onOpenChange={onOpenChange}
      >
        <p>Details content</p>
      </Disclosure>,
    );

    expect(screen.getByRole("button", { name: "Details" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText("Details content")).toBeVisible();
  });
});
