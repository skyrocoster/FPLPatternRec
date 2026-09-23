import type { Meta, StoryObj } from "@storybook/react-vite";
import "../../styles/app-typescale.css";
import { StorySpecimenTypescale } from "./StorySpecimenTypescale";

const meta = {
  title: "Reference/Design System/Typography",
  tags: ["status-reference"],
  component: StorySpecimenTypescale,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: "Storybook-only documentation specimen for the production typography scale.",
      },
    },
  },
} satisfies Meta<typeof StorySpecimenTypescale>;

export default meta;

type Story = StoryObj<typeof meta>;

export const CompleteTypescale: Story = {};
