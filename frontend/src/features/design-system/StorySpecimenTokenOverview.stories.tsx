import type { Meta, StoryObj } from "@storybook/react-vite";
import { StorySpecimenTokenOverview } from "./StorySpecimenTokenOverview";

const meta = {
  title: "Reference/Design System/Tokens",
  tags: ["status-reference"],
  component: StorySpecimenTokenOverview,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: "Storybook-only documentation fixture for the fixed production token source.",
      },
    },
  },
} satisfies Meta<typeof StorySpecimenTokenOverview>;

export default meta;

type Story = StoryObj<typeof meta>;

export const FixedDarkTokenSource: Story = {};
