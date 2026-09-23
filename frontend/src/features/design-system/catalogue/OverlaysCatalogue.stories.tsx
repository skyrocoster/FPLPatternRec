import type { Meta, StoryObj } from "@storybook/react-vite";
import { FamilyPage } from "./FamilyPage";

const meta = {
  title: "Reference/Catalogue/Overlays",
  tags: ["status-reference"],
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Docs: Story = {
  render: () => (
    <FamilyPage
      family="Overlays"
      intro="Reusable Dialog, PreviewCard, Toast, Tooltip, date picker, and responsive drawer examples."
      caution="Popover and Drawer remain composed locally where their anchor, responsive behavior, or content requires it."
      sections={[
        {
          heading: "Reusable overlays",
          body: "Dialog provides a modal surface, PreviewCard adds non-interrupting link content, ToastProvider manages notifications, and Tooltip provides a short hint.",
          links: [
            { label: "Dialog", storyId: "production-design-system-base-ui-overlays--dialog-example" },
            { label: "Preview card", storyId: "production-design-system-base-ui-overlays--preview-card-example" },
            { label: "Toast", storyId: "production-design-system-base-ui-overlays--toast-example" },
            { label: "Tooltip", storyId: "production-design-system-base-ui-overlays--tooltip-example" },
          ],
        },
        {
          heading: "Popover and drawer",
          body: "CalendarDate demonstrates a popover-hosted date picker. AppShell uses a Base UI drawer for narrow-screen navigation.",
          links: [
            { label: "Calendar date — keyboard and focus", storyId: "production-design-system-components-calendar-date--keyboard-and-focus" },
            { label: "Calendar date — selected", storyId: "production-design-system-components-calendar-date--selected" },
            { label: "App shell — constrained drawer", storyId: "production-application-shell-app-shell--constrained-open" },
          ],
        },
      ]}
    />
  ),
};
