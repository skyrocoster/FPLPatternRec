import type { Meta, StoryObj } from "@storybook/react-vite";
import { FamilyPage } from "./FamilyPage";

const meta = {
  title: "Reference/Catalogue/Surfaces and Layout",
  tags: ["status-reference"],
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Docs: Story = {
  render: () => (
    <FamilyPage
      family="Surfaces and Layout"
      intro="The retained shell, page boundaries, and content primitives demonstrate the layouts currently included in this starter."
      sections={[
        {
          heading: "Shell and page boundaries",
          body: "AppShell keeps the responsive navigation drawer and page layout. PageContentBoundary isolates page rendering and recovery behavior.",
          links: [
            { label: "App shell — wide", storyId: "production-application-shell-app-shell--wide-healthy" },
            { label: "App shell — constrained drawer", storyId: "production-application-shell-app-shell--constrained-open" },
            { label: "App shell — loading", storyId: "production-application-shell-app-shell--loading" },
            { label: "Page not found", storyId: "production-application-shell-page-not-found--default" },
          ],
        },
        {
          heading: "Reusable content surfaces",
          body: "ScrollArea, Separator, and the review composition show reusable content and tonal surface treatments without feature-specific data.",
          links: [
            { label: "Scroll area", storyId: "production-design-system-base-ui-content-primitives--scroll-area-example" },
            { label: "Separator", storyId: "production-design-system-base-ui-content-primitives--separator-example" },
            { label: "Review summary composition", storyId: "reference-compositions-review-summary--review-summary" },
          ],
        },
      ]}
    />
  ),
};
