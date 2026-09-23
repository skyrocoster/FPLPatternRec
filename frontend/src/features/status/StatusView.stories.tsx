import type { Meta, StoryObj } from "@storybook/react-vite";

import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import { StatusView, type StatusViewState } from "./StatusView";

const meta = {
  title: "Production/Application/Status/Status View",
  tags: ["status-production"],
  component: StatusView,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof StatusView>;

export default meta;
type Story = StoryObj<typeof meta>;

const frame = (state: StatusViewState) => (
  <main
    style={{
      minHeight: "100vh",
      padding: "var(--app-spacing-24)",
      background: "var(--md-sys-color-background)",
      color: "var(--md-sys-color-on-background)",
    }}
  >
    <StatusView state={state} />
  </main>
);

export const Loading: Story = {
  args: { state: { kind: "loading" } },
  render: () => frame({ kind: "loading" }),
};

export const Healthy: Story = {
  args: { state: { kind: "success" } },
  render: () => frame({ kind: "success" }),
};

export const Unavailable: Story = {
  args: { state: { kind: "error" } },
  render: () => frame({ kind: "error" }),
};
