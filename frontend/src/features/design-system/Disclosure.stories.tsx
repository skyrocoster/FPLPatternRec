import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import type { ReactNode } from "react";

import { Disclosure } from "./Disclosure";

const meta = {
  title: "Production/Design System/Components/Disclosure",
  tags: ["status-production"],
  component: Disclosure,
  args: {
    summary: "Disclosure",
  },
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof Disclosure>;

export default meta;
type Story = StoryObj<typeof meta>;

const shell = (children: ReactNode) => (
  <main
    style={{
      display: "flex",
      flexDirection: "column",
      gap: "var(--app-spacing-24)",
      padding: "var(--app-spacing-32)",
      minHeight: "100vh",
      backgroundColor: "var(--md-sys-color-surface)",
      color: "var(--md-sys-color-on-surface)",
      fontFamily: "system-ui",
    }}
  >
    {children}
  </main>
);

const LONG_CONTENT = Array.from(
  { length: 12 },
  (_, index) =>
    `Temporary context note number ${index + 1}: more analysis content could be placed here.`,
);

export const CollapsedByDefault: Story = {
  args: { onOpenChange: fn() },
  render: (args) =>
    shell(
      <Disclosure {...args}>
        <p style={{ margin: "var(--app-spacing-16)" }}>
          The collapsible body. Closed until the summary is activated.
        </p>
      </Disclosure>,
    ),
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const trigger = canvas.getByRole("button", { name: "Disclosure" });

    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(trigger);
    await expect(trigger).toHaveAttribute("aria-expanded", "true");
    await expect(
      canvas.getByText("The collapsible body. Closed until the summary is activated."),
    ).toBeVisible();
    await expect(args.onOpenChange).toHaveBeenCalledTimes(1);
    await expect(args.onOpenChange).toHaveBeenLastCalledWith(true);

    await userEvent.click(trigger);
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await expect(args.onOpenChange).toHaveBeenCalledTimes(2);
    await expect(args.onOpenChange).toHaveBeenLastCalledWith(false);
  },
};

export const OpenByDefault: Story = {
  render: () =>
    shell(
      <Disclosure summary="Loaded details" defaultOpen>
        <p style={{ margin: "var(--app-spacing-16)" }}>
          The collapsible body, rendered open on first paint.
        </p>
      </Disclosure>,
    ),
};

export const WithLongContent: Story = {
  render: () =>
    shell(
      <Disclosure summary="Context" defaultOpen>
        <ul
          style={{
            margin: 0,
            padding: "0 var(--app-spacing-16) var(--app-spacing-16) var(--app-spacing-32)",
          }}
        >
          {LONG_CONTENT.map((note) => (
            <li key={note} style={{ marginBlockStart: "var(--app-spacing-8)" }}>
              {note}
            </li>
          ))}
        </ul>
      </Disclosure>,
    ),
};
