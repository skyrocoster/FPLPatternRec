import { useState } from "react";

import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { MemoryRouter } from "react-router-dom";

import { AppShell } from "./AppShell";
import { storyViewport } from "../../storybook/viewports";
import { PageContentBoundary } from "./PageContentBoundary";
import { StatusView } from "../status/StatusView";

const meta = {
  title: "Production/Application/Shell/App Shell",
  tags: ["status-production"],
  component: AppShell,
  args: {
    children: <StatusView state={{ kind: "success" }} />,
  },
  parameters: {
    layout: "fullscreen",
  },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <Story />
      </MemoryRouter>
    ),
  ],
} satisfies Meta<typeof AppShell>;

export default meta;
type Story = StoryObj<typeof meta>;

const healthy = <StatusView state={{ kind: "success" }} />;

export const WideHealthy: Story = {
  render: () => <AppShell>{healthy}</AppShell>,
};

export const ConstrainedClosed: Story = {
  parameters: storyViewport("constrained-412"),
  render: () => <AppShell>{healthy}</AppShell>,
};

export const ConstrainedOpen: Story = {
  parameters: storyViewport("constrained-412"),
  render: () => <AppShell>{healthy}</AppShell>,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Open navigation menu" }));

    const body = within(canvasElement.ownerDocument.body);
    await expect(body.findByRole("heading", { name: "Navigation" })).resolves.toBeInTheDocument();
    await expect(
      body.findByRole("button", { name: "Close navigation menu" }),
    ).resolves.toBeInTheDocument();
  },
};

export const Loading: Story = {
  render: () => (
    <AppShell>
      <StatusView state={{ kind: "loading" }} />
    </AppShell>
  ),
};

export const Healthy: Story = {
  render: () => <AppShell>{healthy}</AppShell>,
};

export const Unavailable: Story = {
  render: () => (
    <AppShell>
      <StatusView state={{ kind: "error" }} />
    </AppShell>
  ),
};

function UnexpectedContent(): never {
  throw new Error("Storybook render failure");
}

function UnexpectedFailureComposition() {
  const [shouldFail, setShouldFail] = useState(true);

  return (
    <PageContentBoundary onReset={() => setShouldFail(false)}>
      <AppShell>{healthy}</AppShell>
      {shouldFail ? <UnexpectedContent /> : <p>Content recovered after reset.</p>}
    </PageContentBoundary>
  );
}

export const UnexpectedFailureTryAgain: Story = {
  name: "Error — try again recovers content",
  render: () => <UnexpectedFailureComposition />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.findByRole("heading", { name: "Page unavailable" }),
    ).resolves.toBeInTheDocument();
    await expect(
      canvas.findByText("Something went wrong while displaying this page."),
    ).resolves.toBeInTheDocument();
    await userEvent.click(await canvas.findByRole("button", { name: "Try again" }));
    await expect(canvas.findByText("Content recovered after reset.")).resolves.toBeInTheDocument();
  },
};

// Browser proof owns the recovery click; reusing the play story would race its automated click.
export const UnexpectedFailureBrowserProof: Story = {
  name: "Error — manual recovery check",
  render: () => <UnexpectedFailureComposition />,
};
