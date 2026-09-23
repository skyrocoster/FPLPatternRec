import type { Preview } from "@storybook/react-vite";
import "../src/app.css";
import "../src/styles/material/material-theme-builder-css-export/css/dark.css";
import { storybookViewports } from "../src/storybook/viewports";
import { StorybookQueryClientProvider } from "./StorybookQueryClientProvider";

const preview: Preview = {
  decorators: [
    (Story) => (
      <StorybookQueryClientProvider>
        {/*
          Paint the isolated Storybook canvas with the application background.
          Product pages render inside #root (block-size 100% with the dark
          background), but the preview iframe has no #root, so flex ancestors
          can collapse and axe would otherwise measure dark text against the
          iframe's default white. This wrapper is test tooling only.
        */}
        <div
          className="dark"
          style={{
            backgroundColor: "var(--md-sys-color-background)",
            color: "var(--md-sys-color-on-background)",
            // Viewport units, not %, so the canvas paints behind story
            // content even when intermediate flex containers collapse without
            // the application's #root height context.
            minHeight: "100vh",
          }}
        >
          <Story />
        </div>
      </StorybookQueryClientProvider>
    ),
  ],
  parameters: {
    a11y: {
      test: "error",
    },
    viewport: {
      options: storybookViewports,
    },
    options: {
      storySort: {
        order: [
          "Production",
          ["Application", "Design System"],
          "In Development",
          ["Application"],
          "Reference",
          ["Catalogue", "Design System", "Compositions", "Reviews", "Storybook Fixtures"],
        ],
      },
    },
  },
};

export default preview;
