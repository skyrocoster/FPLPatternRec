import type { Meta, StoryObj } from "@storybook/react-vite";
import { FamilyPage } from "./FamilyPage";

const meta = {
  title: "Reference/Catalogue/Foundations",
  tags: ["status-reference"],
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta;

export default meta;

type Story = StoryObj<typeof meta>;

export const Docs: Story = {
  render: () => (
    <FamilyPage
      family="Foundations"
      intro={
        <>
          The existing design-token layer that every production component consumes. Foundations are
          defined as CSS custom properties and are already fully documented by three reference
          specimen stories; this page gives plain-English notes and points at the specimens instead
          of duplicating them.
        </>
      }
      sections={[
        {
          heading: "Colours and surface tokens",
          body: (
            <>
              Base colours come from the exported Material dark theme (--md-sys-color-* roles); it
              is what the Storybook preview applies via the `&quot;dark&quot;` wrapper class.
              Semantic feedback accents (information, success, warning, error) come from
              app-tokens.css (--app-*). There is currently only a dark theme in the Storybook
              preview; light variants exist as theme files but are not exercised by stories.
            </>
          ),
          links: [
            {
              label: "Reference/Design System/Tokens — Fixed Dark Token Source",
              storyId: "reference-design-system-tokens--fixed-dark-token-source",
              note: "the complete fixed token palette",
            },
          ],
        },
        {
          heading: "Spacing, radius, elevation, and focus",
          body: (
            <>
              app-tokens.css defines spacing steps (--app-spacing-4…48), radii (--app-radius-4/8/12
              and --app-radius-default), three reserved elevations (--app-elevation-e1…e3), and the
              focus-ring tokens. Structural specimens should consume only these variables.
            </>
          ),
          links: [
            {
              label: "Reference/Design System/Foundations — Foundations",
              storyId: "reference-design-system-foundations--foundations",
              note: "spacing, radius, elevation, and focus specimens built from the tokens",
            },
          ],
        },
        {
          heading: "Typography",
          body: (
            <>
              app-typescale.css carries the type styles used across stories. The specimen shows the
              complete scale in one place.
            </>
          ),
          links: [
            {
              label: "Reference/Design System/Typography — Complete Typescale",
              storyId: "reference-design-system-typography--complete-typescale",
            },
          ],
        },
        {
          heading: "Other specimens",
          body: (
            <>
              The responsive accessibility review walks the specimens through the shared viewport
              catalogue; the responsive boundary checks for actual components live with their owning
              stories (see Surfaces and Layout).
            </>
          ),
          links: [
            {
              label: "Reference/Reviews/Responsive Accessibility — Responsive Accessibility Review",
              storyId:
                "reference-reviews-responsive-accessibility--responsive-accessibility-review",
            },
          ],
        },
      ]}
    />
  ),
};
