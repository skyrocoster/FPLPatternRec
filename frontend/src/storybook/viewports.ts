/**
 * Shared, deterministic Storybook viewport catalogue.
 *
 * Browser viewport presets and component-container breakpoint tests are
 * different concerns: these presets pin realistic page/story sizes so play
 * assertions do not depend on Storybook manager chrome width. Controlled
 * component-width boundary tests (for example 699/700/1039/1040) stay in
 * their owning stories and are intentionally absent here.
 */

export const storybookViewports = {
  "phone-390": {
    name: "Phone 390",
    styles: { width: "390px", height: "844px" },
  },
  "constrained-412": {
    name: "Constrained 412",
    styles: { width: "412px", height: "915px" },
  },
  "panel-breakpoint-640": {
    name: "Panel breakpoint 640",
    styles: { width: "640px", height: "900px" },
  },
  "workspace-medium-800": {
    name: "Workspace medium 800",
    styles: { width: "800px", height: "1000px" },
  },
  "workspace-wide-1280": {
    name: "Workspace wide 1280",
    styles: { width: "1280px", height: "1000px" },
  },
} as const;

export type StoryViewportName = keyof typeof storybookViewports;

/**
 * Typed viewport parameter helper.
 *
 * Usage: `parameters: storyViewport("workspace-wide-1280")`.
 * Invalid names fail TypeScript because the argument is constrained to
 * `StoryViewportName`.
 */
export function storyViewport(name: StoryViewportName) {
  return {
    viewport: {
      defaultViewport: name,
      options: storybookViewports,
    },
  };
}
