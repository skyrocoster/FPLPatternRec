import * as axe from "axe-core";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import axeMatchers from "@chialab/vitest-axe";
import { MemoryRouter } from "react-router-dom";

import { AppShell } from "./AppShell";

expect.extend(axeMatchers);
afterEach(cleanup);

function renderShell(initialEntries = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AppShell>
        <p>Shell content</p>
      </AppShell>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("renders landmarks, skip link, neutral identity, and status navigation", () => {
    renderShell();

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute(
      "href",
      "#main-content",
    );
    expect(screen.getByTestId("shell-identity-rail")).toHaveTextContent("FPLPatternRec");
    expect(screen.getByTestId("shell-identity-header")).toHaveTextContent("FPLPatternRec");
    const statusLinks = screen.getAllByRole("link", { name: "Status" });
    expect(statusLinks).toHaveLength(1);
    expect(statusLinks[0]).toHaveAttribute("href", "/");
    expect(statusLinks[0]).toHaveAttribute("aria-current", "page");
    expect(
      within(screen.getByRole("navigation", { name: "Desktop navigation" })).getAllByRole("link"),
    ).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Open navigation menu", hidden: true })).toBeInTheDocument();
  });

  it("uses Base UI for drawer focus and dismissal paths", async () => {
    const user = userEvent.setup();
    renderShell();

    const trigger = screen.getByRole("button", { name: "Open navigation menu", hidden: true });
    trigger.focus();
    await user.click(trigger);

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: "Navigation" })).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: "Status" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close navigation menu" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();

    await user.click(trigger);
    await user.click(screen.getByTestId("drawer-backdrop"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes the drawer when Status is selected", async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole("button", { name: "Open navigation menu", hidden: true }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("link", { name: "Status" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("passes a focused accessibility check", async () => {
    const { container } = renderShell();

    expect(await axe.run(container)).toHaveNoViolations();
  });
});
