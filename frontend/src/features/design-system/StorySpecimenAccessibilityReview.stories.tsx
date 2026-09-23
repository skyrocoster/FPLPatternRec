import "../../styles/app-tokens.css";

import type { Meta, StoryObj } from "@storybook/react-vite";

import { StorySpecimenAccessibilityReview } from "./StorySpecimenAccessibilityReview";

const meta = {
  title: "Reference/Reviews/Responsive Accessibility",
  tags: ["status-reference"],
  component: StorySpecimenAccessibilityReview,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Storybook-only review fixture for responsive layout, feedback states, focus treatment, and accessibility checks.",
      },
    },
  },
} satisfies Meta<typeof StorySpecimenAccessibilityReview>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ResponsiveAccessibilityReview: Story = {};
