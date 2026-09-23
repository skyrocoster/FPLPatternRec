import type { Meta, StoryObj } from "@storybook/react-vite";

import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import { Accordion } from "./Accordion";
import { Avatar } from "./Avatar";
import { ScrollArea } from "./ScrollArea";
import { Separator } from "./Separator";

const meta = {
  title: "Production/Design System/Base UI/Content Primitives",
  tags: ["status-production"],
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const AccordionExample: Story = {
  render: () => (
    <div style={{ width: "min(34rem, 90vw)" }}>
      <Accordion
        defaultValue={["purpose"]}
        items={[
          {
            value: "purpose",
            summary: "What should I review?",
            content: "Choose a saved collection and reveal its details when ready.",
          },
          {
            value: "review",
            summary: "When should I check again?",
            content: "Return when the next review is due or after adding a new item.",
          },
        ]}
      />
    </div>
  ),
};

export const AvatarExamples: Story = {
  render: () => (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--app-spacing-16)" }}>
      <Avatar alt="Alex Morgan" fallback="AM" size="sm" />
      <Avatar alt="Project teammate" fallback="PT" />
    </div>
  ),
};

export const ScrollAreaExample: Story = {
  render: () => (
    <ScrollArea
      aria-label="Recent activity"
      style={{ width: "20rem", height: "10rem" }}
      orientation="vertical"
    >
      <div style={{ padding: "var(--app-spacing-16)" }}>
        {Array.from({ length: 12 }, (_, index) => (
          <p key={index}>Activity {index + 1}: item updated</p>
        ))}
      </div>
    </ScrollArea>
  ),
};

export const SeparatorExample: Story = {
  render: () => (
    <div style={{ display: "grid", gap: "var(--app-spacing-16)", width: "20rem" }}>
      <span>Summary</span>
      <Separator />
      <span>Details</span>
    </div>
  ),
};
