import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { Dialog } from "./Dialog";
import { PreviewCard } from "./PreviewCard";
import { ToastProvider, createToastManager, useToast } from "./Toast";
import { Tooltip } from "./Tooltip";

afterEach(cleanup);

function ToastHarness() {
  const toast = useToast();
  return (
    <button
      type="button"
      onClick={() => toast.add({ title: "Settings saved", description: "Your changes are available." })}
    >
      Notify
    </button>
  );
}

describe("overlay primitives", () => {
  it("renders and dismisses a dialog", async () => {
    const user = userEvent.setup();
    render(
      <Dialog defaultOpen title="Delete saved item" description="This cannot be undone.">
        Confirm the selected item.
      </Dialog>,
    );

    expect(screen.getByRole("dialog", { name: "Delete saved item" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog", { name: "Delete saved item" })).not.toBeInTheDocument();
  });

  it("shows reusable preview-card content", () => {
    render(
      <PreviewCard defaultOpen href="/profiles" trigger="Profiles">
        <strong>Profile directory</strong>
      </PreviewCard>,
    );
    expect(screen.getByRole("link", { name: "Profiles" })).toHaveAttribute("href", "/profiles");
    expect(screen.getByText("Profile directory")).toBeInTheDocument();
  });

  it("shows tooltip content for a focusable trigger", () => {
    render(<Tooltip defaultOpen trigger="?" content="Keyboard shortcuts" />);
    expect(screen.getByRole("tooltip", { hidden: true })).toHaveTextContent("Keyboard shortcuts");
  });

  it("provides a working toast queue and global manager", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider timeout={0}>
        <ToastHarness />
      </ToastProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Notify" }));
    expect(screen.getByText("Settings saved")).toBeVisible();
    expect(screen.getByText("Your changes are available.")).toBeVisible();
    expect(createToastManager()).toEqual(expect.objectContaining({ add: expect.any(Function) }));
  });
});
