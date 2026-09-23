import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import { StatusPage } from "./StatusPage";

/**
 * One stable client for a story render. The conservative defaults match the
 * production provider in `main.tsx`. The story keeps its real rendering
 * behavior; no API mocking is added.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    },
  },
});

const meta = {
  title: "Production/Application/Status/Status Page",
  tags: ["status-production"],
  component: StatusPage,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <QueryClientProvider client={queryClient}>
        <Story />
      </QueryClientProvider>
    ),
  ],
} satisfies Meta<typeof StatusPage>;

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
      <StatusPage />
    </main>
  ),
};
