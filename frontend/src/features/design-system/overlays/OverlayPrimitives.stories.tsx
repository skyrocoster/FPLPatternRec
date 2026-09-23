import type { Meta, StoryObj } from "@storybook/react-vite";

import "../../../styles/app-tokens.css";
import "../../../styles/app-typescale.css";
import { Button } from "../Button";
import { Dialog } from "./Dialog";
import { PreviewCard } from "./PreviewCard";
import { ToastProvider, useToast } from "./Toast";
import { Tooltip, TooltipProvider } from "./Tooltip";

const meta = {
  title: "Production/Design System/Base UI/Overlays",
  tags: ["status-production"],
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const DialogExample: Story = {
  render: () => (
    <Dialog
      trigger="Open dialog"
      title="Delete saved item?"
      description="This removes the selected item from the collection."
    >
      Other saved items are not affected.
    </Dialog>
  ),
};

export const PreviewCardExample: Story = {
  render: () => (
    <PreviewCard href="#profile" trigger="Profile details">
      <strong>Profile details</strong>
      <p>Review the saved information for this profile.</p>
    </PreviewCard>
  ),
};

function ToastDemo() {
  const toast = useToast();
  return (
    <Button
      onClick={() =>
        toast.add({
          type: "success",
          title: "Settings saved",
          description: "Your changes are available.",
        })
      }
    >
      Show toast
    </Button>
  );
}

export const ToastExample: Story = {
  render: () => (
    <ToastProvider timeout={0}>
      <ToastDemo />
    </ToastProvider>
  ),
};

export const TooltipExample: Story = {
  render: () => (
    <TooltipProvider delay={200}>
      <Tooltip trigger="?" content="Keyboard shortcuts" />
    </TooltipProvider>
  ),
};
