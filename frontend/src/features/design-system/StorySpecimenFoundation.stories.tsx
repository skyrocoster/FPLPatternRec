import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import "../../styles/app-tokens.css";
import { StorySpecimenFoundation } from "./StorySpecimenFoundation";

const meta = {
  title: "Reference/Design System/Foundations",
  tags: ["status-reference"],
  component: StorySpecimenFoundation,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Storybook-only documentation specimen for the shared visual foundations and focus treatment.",
      },
    },
  },
} satisfies Meta<typeof StorySpecimenFoundation>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Foundations: Story = {
  play: async ({ canvasElement }) => {
    const focusSpecimen = within(canvasElement).getByRole("button", {
      name: "Focus specimen",
    });
    await userEvent.click(focusSpecimen);
    await expect(focusSpecimen).toHaveFocus();
  },
};
