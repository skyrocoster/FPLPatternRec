import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import { PageContentBoundary } from "./PageContentBoundary";

const meta = {
  title: "Production/Application/Shell/Page Content Boundary",
  tags: ["status-production"],
  component: PageContentBoundary,
  args: { children: <p>Page content is available.</p> },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof PageContentBoundary>;

export default meta;
type Story = StoryObj<typeof meta>;

function UnexpectedContent(): never {
  throw new Error("Storybook render failure");
}

function FailureComposition() {
  const [shouldFail, setShouldFail] = useState(true);

  return (
    <PageContentBoundary onReset={() => setShouldFail(false)}>
      {shouldFail ? <UnexpectedContent /> : <p>Content recovered after reset.</p>}
    </PageContentBoundary>
  );
}

export const HealthyContent: Story = {
  render: () => (
    <PageContentBoundary>
      <p>Page content is available.</p>
    </PageContentBoundary>
  ),
};

export const UnexpectedFailureTryAgain: Story = {
  name: "Error — try again recovers content",
  render: () => <FailureComposition />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.findByRole("heading", { name: "Page unavailable" }),
    ).resolves.toBeInTheDocument();
    await userEvent.click(await canvas.findByRole("button", { name: "Try again" }));
    await expect(canvas.findByText("Content recovered after reset.")).resolves.toBeInTheDocument();
  },
};
