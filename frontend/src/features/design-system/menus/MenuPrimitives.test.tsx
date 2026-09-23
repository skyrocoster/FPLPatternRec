import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NavigationMenu } from "../NavigationMenu";
import { ContextMenu } from "./ContextMenu";
import { Menu } from "./Menu";
import { Menubar } from "./Menubar";

afterEach(cleanup);

describe("menu and navigation primitives", () => {
  it("runs actions from a button-triggered menu", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <Menu trigger="Record actions" items={[{ id: "copy", label: "Copy text", onSelect }]} />,
    );

    fireEvent.mouseDown(screen.getByRole("button", { name: "Record actions" }));
    await user.click(await screen.findByText("Copy text"));
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("opens a context menu for a consumer-owned region", () => {
    render(
      <ContextMenu items={[{ id: "annotate", label: "Add comment" }]}>
        <span>Selected content</span>
      </ContextMenu>,
    );

    fireEvent.contextMenu(screen.getByText("Selected content"));
    expect(screen.getByText("Add comment")).toBeInTheDocument();
  });

  it("composes related menus into a menubar", () => {
    render(
      <Menubar
        aria-label="Editor commands"
        menus={[
          { id: "file", label: "File", items: [{ id: "save", label: "Save" }] },
          { id: "edit", label: "Edit", items: [{ id: "undo", label: "Undo" }] },
        ]}
      />,
    );

    expect(screen.getByRole("menubar", { name: "Editor commands" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "File" })).toHaveAttribute("aria-haspopup", "menu");
    expect(screen.getByRole("menuitem", { name: "Edit" })).toBeVisible();
  });

  it("renders direct and grouped navigation links", () => {
    render(
      <NavigationMenu
        aria-label="Primary"
          defaultValue="manage"
        items={[
          {
            id: "manage",
            label: "Manage",
            links: [
              { id: "due", label: "Upcoming tasks", href: "/upcoming", description: "Review now" },
            ],
          },
          { id: "reports", label: "Reports", href: "/reports" },
        ]}
      />,
    );

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Reports" })).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("link", { name: /Upcoming tasks/ })).toHaveAttribute("href", "/upcoming");
  });
});
