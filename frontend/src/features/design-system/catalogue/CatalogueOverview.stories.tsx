import type { Meta, StoryObj } from "@storybook/react-vite";
import { FamilyPage, type CatalogueSection } from "./FamilyPage";
import styles from "./catalogue.module.css";

const meta = {
  title: "Reference/Catalogue/Overview",
  tags: ["status-reference"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Top-level entry point for the component catalogue: the current production Storybook inventory.",
      },
    },
  },
} satisfies Meta;

export default meta;

type Story = StoryObj<typeof meta>;

function familyLinks(
  items: ReadonlyArray<{ heading: string; storyId: string; note: string }>,
): CatalogueSection[] {
  return [
    {
      heading: "Families",
      body: "Each family page explains what the components currently do, links to their existing Production stories, and adds missing stories where the coverage was thin.",
      links: items.map((item) => ({
        label: item.heading,
        note: item.note,
        storyId: item.storyId,
      })),
    },
  ];
}

export const Docs: Story = {
  render: () => (
    <FamilyPage
      family="Catalogue — Component inventory"
      intro={
        <>
          This is the current inventory of the frontend components that already exist in this
          repository, organized into practical families. It is a first pass built from the existing
          production stories: it renders the real production components with the real production
          styles and tokens, and it is <strong>not</strong> a final design-system contract. Nothing
          in it decides or freezes future architecture.
          <br />
          <br />
          Before creating another component, check the catalogue first: a similar presentation or
          behavior may already have a production implementation with variants and states listed on
          its family page. Reusing, adapting, or extracting existing components is preferred over
          adding new ones.
        </>
      }
      caution="This catalogue may be reorganized after review. Story titles and boundaries here are provisional and expected to change; the Production stories themselves are unchanged."
      sections={[
        ...familyLinks([
          {
            heading: "Foundations",
            storyId: "reference-catalogue-foundations--docs",
            note: "colors, surfaces, spacing, radius, elevation, focus, typography",
          },
          {
            heading: "Actions and Form Controls",
            storyId: "reference-catalogue-actions-and-form-controls--docs",
            note: "buttons, fields, dropdowns, grouped choices, numeric and range controls, toggles, form structure",
          },
          {
            heading: "Navigation and Content Switching",
            storyId: "reference-catalogue-navigation-and-content-switching--docs",
            note: "menus, primary navigation, Tabs, Accordion, and Disclosure",
          },
          {
            heading: "Feedback and Status",
            storyId: "reference-catalogue-feedback-and-status--docs",
            note: "feedback variants plus loading, empty, error, progress, and outcome presentations",
          },
          {
            heading: "Surfaces and Layout",
            storyId: "reference-catalogue-surfaces-and-layout--docs",
            note: "application shell, content surfaces, and narrow-width behavior",
          },
          {
            heading: "Overlays",
            storyId: "reference-catalogue-overlays--docs",
            note: "popover, drawer, and alert dialog presentations where they exist",
          },
          {
            heading: "Data Display and Feature Compositions",
            storyId: "reference-catalogue-data-display-and-feature-compositions--docs",
            note: "content primitives, calendars, meters, and status displays",
          },
        ]),
        {
          heading: "How to browse",
          body: (
            <>
              Follow the family links above, or use the Storybook sidebar: the{" "}
              <span className={styles.linkLabel}>Reference/Catalogue</span> pages hold the family
              documentation and the missing catalogued coverage; the{" "}
              <span className={styles.linkLabel}>Production</span> group contains the retained
              reusable component stories. Each link opens the exact story in the URL.
            </>
          ),
          links: [
            {
              label: "Example Production entry",
              storyId: "production-design-system-components-button--variant-matrix",
              note: "the Button variant matrix, representative of the Production group",
            },
          ],
        },
        {
          heading: "Not catalogued",
          body: (
            <>
              Anything that cannot be rendered here without substantial application state is
              documented under its family with links to the closest existing story instead of a
              recreated copy. Known gaps are noted on each family page, for example: there is
              currently no shared standalone Checkbox, Toolbar, Popover, Drawer, or AlertDialog
              component. Those Base UI behaviors either have a grouped wrapper such as CheckboxGroup
              or remain composed locally inside feature components.
            </>
          ),
        },
      ]}
    />
  ),
};
