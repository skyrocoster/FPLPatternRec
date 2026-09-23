import type { Meta, StoryObj } from "@storybook/react-vite";

import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import PageNotFoundView from "./PageNotFoundView";

const meta = {
  title: "Production/Application/Shell/Page Not Found",
  tags: ["status-production"],
  component: PageNotFoundView,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof PageNotFoundView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <main
      style={{
        minHeight: "100vh",
        padding: "var(--app-spacing-24)",
        background: "var(--md-sys-color-background)",
        color: "var(--md-sys-color-on-background)",
      }}
    >
      <PageNotFoundView />
    </main>
  ),
};
