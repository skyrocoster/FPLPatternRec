import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";

import type { Meta, StoryObj } from "@storybook/react-vite";

import { StorySpecimenCombinedComposition } from "./StorySpecimenCombinedComposition";

const meta = {
  title: "Reference/Compositions/Review Summary",
  tags: ["status-reference"],
  component: StorySpecimenCombinedComposition,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Storybook-only composition fixture demonstrating production design-system treatments without application behavior.",
      },
    },
  },
} satisfies Meta<typeof StorySpecimenCombinedComposition>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ReviewSummary: Story = {};
