import type { Meta, StoryObj } from "@storybook/react-vite";
import { FamilyPage } from "./FamilyPage";

const meta = {
  title: "Reference/Catalogue/Feedback and Status",
  tags: ["status-reference"],
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Docs: Story = {
  render: () => (
    <FamilyPage
      family="Feedback and Status"
      intro="The shared feedback components and retained status presentations. FeedbackCore defines the four severities; panel, page, and inline wrappers provide matching layouts."
      sections={[
        {
          heading: "Shared feedback levels",
          body: "PanelFeedback, PageFeedback, and InlineFeedback share severity mapping while leaving live-region roles and application state to their callers.",
          links: [
            { label: "Feedback semantic variants", storyId: "reference-design-system-feedback-semantic-variants--semantic-variants" },
            { label: "Panel feedback", storyId: "production-design-system-feedback-panel--all-severities" },
            { label: "Page feedback", storyId: "production-design-system-feedback-page--all-severities" },
            { label: "Inline feedback", storyId: "production-design-system-feedback-inline--inline-matrix" },
          ],
        },
        {
          heading: "Status states",
          body: "The status view presents a pending health check, a successful connection, or an unavailable service.",
          links: [
            { label: "Status view — loading", storyId: "production-application-status-status-view--loading" },
            { label: "Status view — healthy", storyId: "production-application-status-status-view--healthy" },
            { label: "Status view — unavailable", storyId: "production-application-status-status-view--unavailable" },
            { label: "Page not found", storyId: "production-application-shell-page-not-found--default" },
          ],
        },
        {
          heading: "Meters and progress displays",
          body: "ProgressMeter supports determinate and unavailable values. OutcomeTrack displays segmented outcome values supplied by its caller.",
          links: [
            { label: "Progress meter — determinate", storyId: "production-design-system-components-progress-meter--determinate" },
            { label: "Progress meter — unavailable", storyId: "production-design-system-components-progress-meter--unavailable" },
            { label: "Outcome track — unknown segment", storyId: "production-design-system-components-outcome-track--with-unknown" },
          ],
        },
      ]}
    />
  ),
};
