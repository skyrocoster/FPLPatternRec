import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import type { ReactNode } from "react";

import { OutcomeTrack } from "./OutcomeTrack";

const meta = {
  title: "Production/Design System/Components/Outcome Track",
  tags: ["status-production"],
  component: OutcomeTrack,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof OutcomeTrack>;

export default meta;
type Story = StoryObj<typeof meta>;

function shell(children: ReactNode) {
  return (
    <main
      style={{
        display: "grid",
        gap: "var(--app-spacing-16)",
        padding: "var(--app-spacing-32)",
        maxInlineSize: "40rem",
        backgroundColor: "var(--md-sys-color-surface)",
        color: "var(--md-sys-color-on-surface)",
        fontFamily: "system-ui",
      }}
    >
      {children}
    </main>
  );
}

export const WinDrawLoss: Story = {
  name: "Result distribution",
  args: {
    values: { wins: 7, draws: 2, losses: 3 },
    accessibleLabel: "7 completed, 2 unchanged, 3 blocked",
  },
  render: (args) => shell(<OutcomeTrack {...args} />),
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByRole("img", { name: "7 completed, 2 unchanged, 3 blocked" }),
    ).toBeVisible();
  },
};

export const WithUnknown: Story = {
  name: "With unknown segment",
  args: {
    values: { wins: 7, draws: 2, losses: 3, unknown: 2 },
    accessibleLabel: "7 completed, 2 unchanged, 3 blocked, 2 unknown",
  },
  render: (args) => shell(<OutcomeTrack {...args} />),
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByRole("img", { name: "7 completed, 2 unchanged, 3 blocked, 2 unknown" }),
    ).toBeVisible();
  },
};

export const Compact: Story = {
  name: "Compact",
  args: {
    values: { wins: 5, draws: 1, losses: 4 },
    accessibleLabel: "5 completed, 1 unchanged, 4 blocked",
    compact: true,
  },
  render: (args) => shell(<OutcomeTrack {...args} />),
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByRole("img", { name: "5 completed, 1 unchanged, 4 blocked" }),
    ).toBeVisible();
  },
};
