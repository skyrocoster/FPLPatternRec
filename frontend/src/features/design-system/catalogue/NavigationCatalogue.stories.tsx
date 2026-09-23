import type { Meta, StoryObj } from "@storybook/react-vite";
import { FamilyPage } from "./FamilyPage";

const meta = {
  title: "Reference/Catalogue/Navigation and Content Switching",
  tags: ["status-reference"],
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Docs: Story = {
  render: () => (
    <FamilyPage
      family="Navigation and Content Switching"
      intro="Reusable controls for menus, navigation, tabs, and expandable content."
      sections={[
        {
          heading: "Menus and navigation",
          body: "Menu, ContextMenu, Menubar, and NavigationMenu use caller-provided actions and destinations while keeping keyboard and focus behavior in Base UI.",
          links: [
            { label: "Menu", storyId: "production-design-system-base-ui-menus-and-navigation--menu-example" },
            { label: "Context menu", storyId: "production-design-system-base-ui-menus-and-navigation--context-menu-example" },
            { label: "Menubar", storyId: "production-design-system-base-ui-menus-and-navigation--menubar-example" },
            { label: "Navigation menu", storyId: "production-design-system-base-ui-menus-and-navigation--navigation-menu-example" },
          ],
        },
        {
          heading: "Tabs",
          body: "Tabs cover default, disabled, controlled, and overflowing presentations.",
          links: [
            { label: "Default tabs", storyId: "production-design-system-components-tabs--default" },
            { label: "Disabled tab", storyId: "production-design-system-components-tabs--disabled" },
            { label: "Controlled tabs", storyId: "production-design-system-components-tabs--controlled" },
            { label: "Overflowing tabs", storyId: "production-design-system-components-tabs--overflow" },
          ],
        },
        {
          heading: "Disclosure and accordion",
          body: "Disclosure exposes an expandable region; Accordion supports data-driven groups of content.",
          links: [
            { label: "Disclosure — collapsed", storyId: "production-design-system-components-disclosure--collapsed-by-default" },
            { label: "Disclosure — open", storyId: "production-design-system-components-disclosure--open-by-default" },
            { label: "Disclosure — longer content", storyId: "production-design-system-components-disclosure--with-long-content" },
            { label: "Accordion", storyId: "production-design-system-base-ui-content-primitives--accordion-example" },
          ],
        },
      ]}
    />
  ),
};
