import type { Meta, StoryObj } from "@storybook/react-vite";
import { FamilyPage } from "./FamilyPage";

const meta = {
  title: "Reference/Catalogue/Data Display and Feature Compositions",
  tags: ["status-reference"],
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Docs: Story = {
  render: () => (
    <FamilyPage
      family="Data Display and Feature Compositions"
      intro="Reusable content primitives, calendars, meters, and status displays, with links to the retained production stories."
      sections={[
        {
          heading: "Content primitives",
          body: "Avatar, ScrollArea, Separator, and Accordion provide content- and layout-neutral building blocks.",
          links: [
            { label: "Avatar examples", storyId: "production-design-system-base-ui-content-primitives--avatar-examples" },
            { label: "Scroll area", storyId: "production-design-system-base-ui-content-primitives--scroll-area-example" },
            { label: "Separator", storyId: "production-design-system-base-ui-content-primitives--separator-example" },
            { label: "Accordion", storyId: "production-design-system-base-ui-content-primitives--accordion-example" },
          ],
        },
        {
          heading: "Calendars and progress",
          body: "CalendarDate covers date selection and focus handling. ProgressMeter and OutcomeTrack show determinate, unavailable, and segmented values.",
          links: [
            { label: "Calendar date — current day and future dates", storyId: "production-design-system-components-calendar-date--current-day-and-future-disabled" },
            { label: "Progress meter — determinate", storyId: "production-design-system-components-progress-meter--determinate" },
            { label: "Progress meter — unavailable", storyId: "production-design-system-components-progress-meter--unavailable" },
            { label: "Outcome track — unknown segment", storyId: "production-design-system-components-outcome-track--with-unknown" },
          ],
        },
        {
          heading: "Application status",
          body: "The retained status page demonstrates loading, success, and unavailable feedback inside the application shell.",
          links: [
            { label: "Status view — loading", storyId: "production-application-status-status-view--loading" },
            { label: "Status view — unavailable", storyId: "production-application-status-status-view--unavailable" },
          ],
        },
      ]}
    />
  ),
};
