import type { Meta, StoryObj } from "@storybook/react-vite";

import "../../../styles/app-tokens.css";
import "../../../styles/app-typescale.css";
import { NavigationMenu } from "../NavigationMenu";
import { ContextMenu } from "./ContextMenu";
import { Menu } from "./Menu";
import { Menubar } from "./Menubar";

const actions = [
  { id: "copy", label: "Copy text", shortcut: "Ctrl+C" },
  { id: "separator", separator: true as const },
  { id: "delete", label: "Delete item" },
];

const meta = {
  title: "Production/Design System/Base UI/Menus and Navigation",
  tags: ["status-production"],
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const MenuExample: Story = {
  render: () => <Menu trigger="Record actions" items={actions} />,
};

export const ContextMenuExample: Story = {
  render: () => (
    <ContextMenu items={actions}>
      <div
        style={{
          padding: "var(--app-spacing-32)",
          border: "1px solid var(--md-sys-color-outline-variant)",
        }}
      >
        Right-click this content card
      </div>
    </ContextMenu>
  ),
};

export const MenubarExample: Story = {
  render: () => (
    <Menubar
      aria-label="Editor commands"
      menus={[
        { id: "file", label: "File", items: actions },
        {
          id: "edit",
          label: "Edit",
          items: [
            { id: "undo", label: "Undo", shortcut: "Ctrl+Z" },
            { id: "redo", label: "Redo", shortcut: "Ctrl+Y" },
          ],
        },
      ]}
    />
  ),
};

export const NavigationMenuExample: Story = {
  render: () => (
    <NavigationMenu
      aria-label="Primary"
      items={[
        {
          id: "manage",
          label: "Manage",
          links: [
            {
              id: "due",
              label: "Upcoming tasks",
              href: "#upcoming",
              description: "Review the current queue",
            },
            {
              id: "browse",
              label: "Browse",
              href: "#browse",
              description: "Explore saved items",
            },
          ],
        },
        { id: "reports", label: "Reports", href: "#reports" },
      ]}
    />
  ),
};
